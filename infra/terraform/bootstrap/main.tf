# One-time bootstrap: the S3 bucket that holds every environment's Terraform
# state and lock files. Run once per AWS account, with LOCAL state (this
# folder's own state is tiny and only describes this one bucket):
#
#   terraform -chdir=infra/terraform/bootstrap init
#   terraform -chdir=infra/terraform/bootstrap apply
#
# Locking: each environment's backend.hcl sets `use_lockfile = true`, so
# Terraform writes <key>.tflock next to the state in this bucket while a run
# is in progress. No DynamoDB table is needed (Terraform >= 1.10).

terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

variable "region" {
  type    = string
  default = "us-west-1"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "agentforge"
      ManagedBy = "terraform-bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}

# Bucket names are global, so the account id makes it unique.
resource "aws_s3_bucket" "tfstate" {
  bucket = "agentforge-tfstate-${data.aws_caller_identity.current.account_id}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled" # recover from a bad apply by restoring an earlier state version
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket" {
  description = "Put this in envs/<env>/backend.hcl as `bucket`."
  value       = aws_s3_bucket.tfstate.bucket
}
