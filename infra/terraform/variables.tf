variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-west-1"
}

variable "env" {
  description = "Environment name (dev | staging | prod). Used in naming + tagging."
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "EKS cluster name. Final name is \"agentforge-$${env}-$${cluster_name}\"."
  type        = string
  default     = "agentforge"
}

variable "kubernetes_version" {
  description = "EKS control-plane version."
  type        = string
  default     = "1.30"
}

# ── Networking ─────────────────────────────────────────────────────
variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of AZs (must be >= 2 for RDS multi-AZ + EKS)."
  type        = number
  default     = 3
}

# ── EKS node group ─────────────────────────────────────────────────
variable "node_instance_type" {
  type    = string
  default = "m6i.large"
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 10
}

variable "node_desired_size" {
  type    = number
  default = 3
}

# ── RDS ────────────────────────────────────────────────────────────
variable "db_engine_version" {
  # Major only: RDS picks the newest 16.x, and auto minor upgrades cause no
  # plan drift. A pinned minor goes stale (16.4 was retired; 16.11–16.15 offered
  # in us-west-1 on 2026-11-25). pgvector requires >= 16.
  description = "Postgres engine version (major only, e.g. \"16\")."
  type        = string
  default     = "16"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_storage_gb" {
  type    = number
  default = 50
}

variable "db_max_storage_gb" {
  type    = number
  default = 200
}

variable "db_multi_az" {
  type    = bool
  default = false
}

variable "db_deletion_protection" {
  type    = bool
  default = false
}

variable "db_performance_insights" {
  description = "RDS Performance Insights. Off in staging (smallest classes may not support it; extra cost)."
  type        = bool
  default     = true
}

variable "db_backup_retention_days" {
  description = "Automated backup retention. The AWS free plan caps this (7 was refused); staging uses 1."
  type        = number
  default     = 7
}

variable "db_monitoring_interval" {
  description = "RDS enhanced monitoring interval in seconds (0 = off). Off in staging: extra cost, and free-plan sensitive."
  type        = number
  default     = 60
}

# ── ElastiCache (Redis) ────────────────────────────────────────────
variable "enable_elasticache" {
  description = "Create ElastiCache Redis. Off in staging: Redis runs in the cluster instead."
  type        = bool
  default     = true
}

variable "redis_engine_version" {
  type    = string
  default = "7.1"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "redis_num_replicas" {
  description = "Number of read replicas in the replication group (0 = primary only)."
  type        = number
  default     = 1
}

# ── Cluster add-ons (addons.tf) ────────────────────────────────────
variable "enable_addons" {
  description = "Install the AWS Load Balancer Controller and external-secrets into the cluster."
  type        = bool
  default     = true
}

variable "alb_controller_chart_version" {
  description = "eks/aws-load-balancer-controller chart. Check: helm search repo eks/aws-load-balancer-controller"
  type        = string
  default     = "3.7.0"
}

variable "external_secrets_chart_version" {
  description = "external-secrets/external-secrets chart. Check: helm search repo external-secrets/external-secrets"
  type        = string
  default     = "2.15.0"
}

# ── DNS / TLS (optional) ───────────────────────────────────────────
variable "domain_api" {
  description = "FQDN for the public API (used for the ALB ingress + ACM)."
  type        = string
  default     = ""
}

variable "domain_studio" {
  description = "FQDN for the studio (Vercel-hosted is fine; leave empty if not on this cluster)."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Pre-existing Route53 hosted zone ID to add records to. Leave empty to skip."
  type        = string
  default     = ""
}

# ── Secrets seed values (placeholder; rotate after apply) ──────────
variable "anthropic_api_key" {
  description = "Anthropic API key. Pass via TF_VAR_anthropic_api_key in CI; never commit."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tavily_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

# ── Tagging ────────────────────────────────────────────────────────
variable "extra_tags" {
  type    = map(string)
  default = {}
}

locals {
  name = "agentforge-${var.env}-${var.cluster_name}"
  tags = merge(
    {
      Project     = "agentforge"
      Environment = var.env
      ManagedBy   = "terraform"
    },
    var.extra_tags,
  )
}
