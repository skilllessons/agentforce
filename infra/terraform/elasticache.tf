# ───────────────────────────────────────────────────────────────────
# ElastiCache Redis — tool result cache, run queue, run-event pub/sub.
# Encryption at rest + transit, auth-token auth, replication group with
# optional read replica for failover.
# ───────────────────────────────────────────────────────────────────

resource "random_password" "redis_auth" {
  length  = 48
  special = false # ElastiCache rejects most special chars in auth tokens
}

resource "aws_secretsmanager_secret" "redis_auth" {
  name                    = "${local.name}/redis/auth-token"
  description             = "AgentForge Redis auth token"
  recovery_window_in_days = 0
  tags                    = local.tags
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id = aws_secretsmanager_secret.redis_auth.id
  secret_string = jsonencode({
    auth_token = random_password.redis_auth.result
    host       = aws_elasticache_replication_group.main.primary_endpoint_address
    port       = aws_elasticache_replication_group.main.port
    url        = "rediss://:${random_password.redis_auth.result}@${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  })

  depends_on = [aws_elasticache_replication_group.main]
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "AgentForge Redis — accessible from EKS nodes only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from EKS node SG"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = local.tags
}

resource "aws_elasticache_parameter_group" "main" {
  name   = "${local.name}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = local.tags
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${local.name}-redis"
  description          = "AgentForge Redis (cache + queue + pubsub)"

  engine               = "redis"
  engine_version       = var.redis_engine_version
  node_type            = var.redis_node_type
  parameter_group_name = aws_elasticache_parameter_group.main.name
  port                 = 6379

  num_cache_clusters = 1 + var.redis_num_replicas
  automatic_failover_enabled = var.redis_num_replicas > 0
  multi_az_enabled           = var.redis_num_replicas > 0

  subnet_group_name  = module.vpc.elasticache_subnet_group_name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result

  snapshot_retention_limit = var.env == "prod" ? 7 : 1
  snapshot_window          = "03:00-04:00"
  maintenance_window       = "sun:05:00-sun:06:00"

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  apply_immediately = var.env != "prod"

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${local.name}/slow-log"
  retention_in_days = 14
  tags              = local.tags
}
