data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs              = slice(data.aws_availability_zones.available.names, 0, var.az_count)
  private_subnets  = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets   = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 4, i + 8)]
  database_subnets = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, i + 192)]
}

# ───────────────────────────────────────────────────────────────────
# VPC
# ───────────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets   = local.private_subnets
  public_subnets    = local.public_subnets
  database_subnets  = local.database_subnets
  elasticache_subnets = local.database_subnets

  create_database_subnet_group     = true
  create_elasticache_subnet_group  = true

  enable_nat_gateway     = true
  single_nat_gateway     = var.env != "prod" # cost-saving in non-prod
  one_nat_gateway_per_az = var.env == "prod"

  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb"                        = 1
    "kubernetes.io/cluster/${local.name}"           = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"               = 1
    "kubernetes.io/cluster/${local.name}"           = "shared"
  }

  tags = local.tags
}

# ───────────────────────────────────────────────────────────────────
# EKS cluster + managed node group
# ───────────────────────────────────────────────────────────────────
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.24"

  cluster_name    = local.name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  enable_irsa = true

  cluster_addons = {
    coredns = {
      addon_version = null # latest compatible
    }
    kube-proxy = {
      addon_version = null
    }
    vpc-cni = {
      addon_version = null
    }
    aws-ebs-csi-driver = {
      addon_version = null
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }

  eks_managed_node_groups = {
    primary = {
      instance_types = [var.node_instance_type]
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size
      labels = {
        role = "general"
      }
    }
  }

  tags = local.tags
}

# IRSA role for the EBS CSI driver — required for pgvector / persistent
# volumes. Created out of the EKS module so it can run in parallel.
module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name             = "${local.name}-ebs-csi"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = local.tags
}

# ───────────────────────────────────────────────────────────────────
# S3 bucket for run outputs / file uploads
# ───────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "files" {
  bucket        = "${local.name}-files"
  force_destroy = var.env != "prod"

  tags = local.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "files" {
  bucket = aws_s3_bucket.files.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "files" {
  bucket                  = aws_s3_bucket.files.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "files" {
  bucket = aws_s3_bucket.files.id
  versioning_configuration {
    status = var.env == "prod" ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "files" {
  bucket = aws_s3_bucket.files.id

  rule {
    id     = "expire-tmp"
    status = "Enabled"
    filter {
      prefix = "tmp/"
    }
    expiration {
      days = 7
    }
  }
}
