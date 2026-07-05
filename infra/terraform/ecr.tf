# ───────────────────────────────────────────────────────────────────
# ECR repositories for the deployable Python services.
# ───────────────────────────────────────────────────────────────────

locals {
  ecr_repos = toset([
    "api-gateway",
    "worker",
    "migrate",
  ])
}

resource "aws_ecr_repository" "service" {
  for_each = local.ecr_repos

  name                 = "agentforge/${each.value}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.tags, { Component = each.value })
}

resource "aws_ecr_lifecycle_policy" "service" {
  for_each   = aws_ecr_repository.service
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 30 production-tagged images"
        selection = {
          tagStatus      = "tagged"
          tagPatternList = ["v*", "prod-*"]
          countType      = "imageCountMoreThan"
          countNumber    = 30
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = { type = "expire" }
      },
    ]
  })
}
