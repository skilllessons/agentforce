#!/usr/bin/env bash
# Brings up local Postgres + Redis and waits until both are healthy.
# Idempotent — safe to re-run.
#
# Future steps (added as the corresponding code lands):
#   - apply Postgres migrations (when src/agentforge/core/db/migrate.py exists)
#   - seed a default 'local-dev' tenant row (when the tenants repo exists)

set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ docker compose up -d"
docker compose up -d

echo "→ waiting for postgres..."
for _ in {1..60}; do
  if docker compose exec -T postgres pg_isready -U agentforge -d agentforge >/dev/null 2>&1; then
    echo "  postgres ready"
    break
  fi
  sleep 1
done

echo "→ waiting for redis..."
for _ in {1..30}; do
  if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo "  redis ready"
    break
  fi
  sleep 1
done

echo "→ applying migrations..."
uv run agentforge-migrate

echo "→ seeding local-dev tenant..."
uv run agentforge-seed

echo "✓ local stack ready"
echo "  postgres:  postgresql://agentforge:agentforge@localhost:5432/agentforge"
echo "  redis:     redis://localhost:6379"
