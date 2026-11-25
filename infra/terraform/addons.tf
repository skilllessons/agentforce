# ───────────────────────────────────────────────────────────────────
# Cluster add-ons the app's Helm chart depends on (docs/roadmap.md, M3.0.5a):
#
#   aws-load-balancer-controller  turns `ingressClassName: alb` Ingresses into
#                                 a real ALB (values-staging.yaml)
#   external-secrets              syncs Secrets Manager → Kubernetes Secrets
#                                 (the ClusterSecretStore/ExternalSecret live in
#                                 the app chart, M3.0.7)
#
# Both IAM roles already exist in iam.tf (IRSA); this only installs the charts
# and binds each service account to its role.
#
# First apply on a new cluster: if the helm provider can't reach the cluster
# yet, run `terraform apply -target=module.eks` once, then a normal apply.
# ───────────────────────────────────────────────────────────────────

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    # Short-lived token from the same AWS credentials Terraform is using.
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
    }
  }
}

resource "helm_release" "aws_load_balancer_controller" {
  count = var.enable_addons ? 1 : 0

  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = var.alb_controller_chart_version
  namespace  = "kube-system"

  values = [yamlencode({
    clusterName  = module.eks.cluster_name
    region       = var.region
    vpcId        = module.vpc.vpc_id
    replicaCount = var.env == "prod" ? 2 : 1
    serviceAccount = {
      create = true
      name   = "aws-load-balancer-controller" # must match iam.tf irsa_alb_controller
      annotations = {
        "eks.amazonaws.com/role-arn" = module.irsa_alb_controller.iam_role_arn
      }
    }
  })]

  depends_on = [module.eks]
}

resource "helm_release" "external_secrets" {
  count = var.enable_addons ? 1 : 0

  name             = "external-secrets"
  repository       = "https://charts.external-secrets.io"
  chart            = "external-secrets"
  version          = var.external_secrets_chart_version
  namespace        = "external-secrets"
  create_namespace = true

  values = [yamlencode({
    installCRDs = true
    serviceAccount = {
      create = true
      name   = "external-secrets" # must match iam.tf irsa_external_secrets
      annotations = {
        "eks.amazonaws.com/role-arn" = module.irsa_external_secrets.iam_role_arn
      }
    }
  })]

  depends_on = [module.eks]
}
