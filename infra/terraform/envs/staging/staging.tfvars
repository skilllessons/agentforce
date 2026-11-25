# Staging: EKS lite in us-west-1, ~$180/mo running (docs/roadmap.md, M3.0).
#
#   terraform -chdir=infra/terraform plan -var-file=envs/staging/staging.tfvars
#
# Secrets (anthropic_api_key, ...) are NOT here: pass them as TF_VAR_* env vars.

env          = "staging"
cluster_name = "core"
region       = "us-west-1"

# us-west-1 exposes 2 AZs to most accounts; the default of 3 fails.
az_count = 2

# Must be a version in EKS *standard* support: extended support bills the
# control plane at ~6x. Confirm before the first apply:
#   aws eks describe-cluster-versions --region us-west-1 --profile agentforge \
#     --query "clusterVersions[?versionStatus=='STANDARD_SUPPORT'].clusterVersion"
kubernetes_version = "1.34"

# One small node; min 0 so `make staging-stop` can scale it away.
node_instance_type = "t3.medium"
node_min_size      = 0
node_max_size      = 2
node_desired_size  = 1

# Smallest RDS that runs Postgres 16 + pgvector.
db_instance_class       = "db.t4g.micro"
db_storage_gb           = 20
db_max_storage_gb       = 50
db_performance_insights = false

# Redis runs inside the cluster in staging; ElastiCache comes back in M7.
enable_elasticache = false
