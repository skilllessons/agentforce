"""Single source of truth for runtime configuration.

Everything pulls from environment variables (or a local ``.env``). Strings only
in here — no business logic. Modules that need a typed Settings instance call
:func:`get_settings`; the instance is cached so reads after the first are free.

For local dev, copy ``.env.example`` to ``.env`` and adjust. For production,
the same env vars are set by the K8s pod spec (via external-secrets in the
EKS-backed deploy).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All AgentForge env config in one place.

    Field names match env var names case-insensitively. Optional fields default
    to None and the relevant subsystem treats them as "feature disabled".
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Core infrastructure ────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://agentforge:agentforge@localhost:5432/agentforge",
        description="Async-compatible Postgres URL (asyncpg uses it without driver prefix).",
    )
    redis_url: str = Field(default="redis://localhost:6379")

    # ── LLM providers ──────────────────────────────────────────────
    anthropic_api_key: str | None = None
    anthropic_default_model: str = "claude-opus-4-7"
    openai_api_key: str | None = None
    litellm_api_base: str | None = None

    # ── Domain tool credentials ───────────────────────────────────
    tavily_api_key: str | None = None

    # ── Observability ──────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "agentforge"
    log_level: str = "info"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Platform ───────────────────────────────────────────────────
    env: str = "dev"  # dev | staging | prod
    user_agent: str = "AgentForge/0.1"

    # ── Run limits (overridable per request later) ────────────────
    max_steps: int = 8
    max_cost_usd: float = 0.50
    max_seconds: int = 90


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings instance.

    Cached because env doesn't change at runtime. Tests that need to override
    can call ``get_settings.cache_clear()`` between cases.
    """
    return Settings()
