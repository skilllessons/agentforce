# ───────────────────────────────────────────────────────────────────
# Application secrets — one bundled Secrets Manager entry that
# external-secrets-operator syncs into a K8s Secret in the agentforge
# namespace. RDS and Redis credentials get their own secrets (they're
# auto-rotated separately).
# ───────────────────────────────────────────────────────────────────

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "api_key_salt" {
  length  = 64
  special = false
}

resource "random_password" "webhook_signing_secret" {
  length  = 48
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app/runtime"
  description             = "AgentForge app runtime secrets"
  recovery_window_in_days = 0
  tags                    = local.tags
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    ANTHROPIC_API_KEY      = var.anthropic_api_key
    TAVILY_API_KEY         = var.tavily_api_key
    JWT_SECRET             = random_password.jwt_secret.result
    API_KEY_SALT           = random_password.api_key_salt.result
    WEBHOOK_SIGNING_SECRET = random_password.webhook_signing_secret.result
  })

  lifecycle {
    # Don't overwrite values rotated out-of-band by ops.
    ignore_changes = [secret_string]
  }
}
