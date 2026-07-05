# ───────────────────────────────────────────────────────────────────
# IRSA — IAM Roles for Service Accounts.
# Each pod gets credentials via the EKS pod identity webhook; no static
# keys, scoped to the minimum the workload needs.
# ───────────────────────────────────────────────────────────────────

# ── Application IAM policy: S3 file bucket + Secrets Manager read ──
data "aws_iam_policy_document" "app_runtime" {
  statement {
    sid    = "FileBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.files.arn,
      "${aws_s3_bucket.files.arn}/*",
    ]
  }

  statement {
    sid    = "ReadAppSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = [
      aws_secretsmanager_secret.app.arn,
      aws_secretsmanager_secret.db_master.arn,
      aws_secretsmanager_secret.redis_auth.arn,
    ]
  }
}

resource "aws_iam_policy" "app_runtime" {
  name        = "${local.name}-app-runtime"
  description = "AgentForge runtime: S3 file bucket + Secrets Manager read"
  policy      = data.aws_iam_policy_document.app_runtime.json
  tags        = local.tags
}

# ── api-gateway service-account role ───────────────────────────────
module "irsa_api_gateway" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name      = "${local.name}-api-gateway"
  role_policy_arns = {
    runtime = aws_iam_policy.app_runtime.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["agentforge:agentforge-api-gateway"]
    }
  }

  tags = local.tags
}

# ── worker service-account role ────────────────────────────────────
module "irsa_worker" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name      = "${local.name}-worker"
  role_policy_arns = {
    runtime = aws_iam_policy.app_runtime.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["agentforge:agentforge-worker"]
    }
  }

  tags = local.tags
}

# ── external-secrets-operator role ─────────────────────────────────
# Lets ESO sync Secrets Manager → K8s Secret resources.
data "aws_iam_policy_document" "external_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecrets",
    ]
    resources = ["arn:aws:secretsmanager:${var.region}:*:secret:${local.name}/*"]
  }
}

resource "aws_iam_policy" "external_secrets" {
  name        = "${local.name}-external-secrets"
  description = "External Secrets Operator: read AgentForge secrets"
  policy      = data.aws_iam_policy_document.external_secrets.json
  tags        = local.tags
}

module "irsa_external_secrets" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name = "${local.name}-external-secrets"
  role_policy_arns = {
    eso = aws_iam_policy.external_secrets.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["external-secrets:external-secrets"]
    }
  }

  tags = local.tags
}

# ── AWS Load Balancer Controller role ──────────────────────────────
module "irsa_alb_controller" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name                              = "${local.name}-alb-controller"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = local.tags
}
