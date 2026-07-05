# ───────────────────────────────────────────────────────────────────
# RDS Postgres for tenants/runs/llm_spend/files/review_items.
# pgvector is shipped with the AWS RDS Postgres 16 image — we just
# enable it via shared_preload_libraries below; the migration runner
# does CREATE EXTENSION on first apply.
# ───────────────────────────────────────────────────────────────────

resource "random_password" "db_master" {
  length           = 32
  special          = true
  override_special = "_-"
}

resource "aws_secretsmanager_secret" "db_master" {
  name                    = "${local.name}/rds/master-password"
  description             = "AgentForge RDS master password (auto-generated)"
  recovery_window_in_days = 0
  tags                    = local.tags
}

resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  secret_string = jsonencode({
    username = "agentforge"
    password = random_password.db_master.result
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
  })

  depends_on = [aws_db_instance.main]
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "AgentForge RDS — accessible from EKS nodes only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Postgres from EKS node SG"
    from_port       = 5432
    to_port         = 5432
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

resource "aws_db_parameter_group" "main" {
  name   = "${local.name}-pg16"
  family = "postgres16"

  # pgvector + pg_trgm are required by 0000_init.sql.
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "500"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }

  tags = local.tags
}

resource "aws_db_instance" "main" {
  identifier = "${local.name}-pg"

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_storage_gb
  max_allocated_storage = var.db_max_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "agentforge"
  username = "agentforge"
  password = random_password.db_master.result
  port     = 5432

  multi_az               = var.db_multi_az
  publicly_accessible    = false
  deletion_protection    = var.db_deletion_protection
  skip_final_snapshot    = var.env != "prod"
  final_snapshot_identifier = var.env == "prod" ? "${local.name}-pg-final-${formatdate("YYYYMMDDhhmmss", timestamp())}" : null

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name

  backup_retention_period = var.db_backup_retention_days
  backup_window           = "07:00-08:00"
  maintenance_window      = "sun:08:30-sun:09:30"

  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  apply_immediately = var.env != "prod"

  tags = local.tags

  lifecycle {
    ignore_changes = [
      # `final_snapshot_identifier` would otherwise drift on every plan due to timestamp().
      final_snapshot_identifier,
    ]
  }
}

resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
