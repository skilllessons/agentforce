terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.32"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.15"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # NOTE: configure remote state in a backend.tf you keep out of version control
  # for credentials reasons. Example:
  #
  # backend "s3" {
  #   bucket         = "agentforge-tfstate-<account-id>"
  #   key            = "envs/dev/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "agentforge-tfstate-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}
