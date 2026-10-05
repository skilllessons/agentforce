# syntax=docker/dockerfile:1.7
#
# One build, three images. api-gateway / worker / migrate differ only by the
# command they run, so they share every layer up to `runtime` and diverge in a
# final stage that costs nothing to build.
#
#   docker build --target api-gateway -t agentforge/api-gateway .
#   docker build --target worker      -t agentforge/worker      .
#   docker build --target migrate     -t agentforge/migrate     .
#
# Image names match infra/helm/agentforge/templates/_helpers.tpl, which renders
# {registry}/agentforge/{component}:{tag}, and the ECR repos in infra/terraform/ecr.tf.

# ── builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies resolve from the lockfile alone, so this layer is cached until
# pyproject.toml or uv.lock actually changes — source edits don't re-resolve.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable

# --no-editable puts a real copy in site-packages, so the runtime stage can take
# the venv and leave the source tree behind.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ── runtime base ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# AGENTFORGE_MIGRATIONS_DIR is required here: the package is installed into
# site-packages, so migrate.py's repo-relative path walk resolves nowhere.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    AGENTFORGE_MIGRATIONS_DIR=/app/infra/postgres/migrations

RUN useradd --system --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Migrations are read at runtime by agentforge-migrate, not importable code.
COPY --chown=app:app infra/postgres/migrations /app/infra/postgres/migrations

USER app

# ── api-gateway ────────────────────────────────────────────────────
FROM runtime AS api-gateway
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["agentforge-api"]

# ── worker ─────────────────────────────────────────────────────────
# No healthcheck: the worker blocks in BRPOP and serves no port. Liveness is
# the Helm probe, which already execs a sleep.
FROM runtime AS worker
CMD ["agentforge-worker"]

# ── migrate ────────────────────────────────────────────────────────
# Run-to-completion Job, not a service.
FROM runtime AS migrate
CMD ["agentforge-migrate"]
