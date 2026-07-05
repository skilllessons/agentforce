"""Structured logging via structlog.

configure_logging() is called once per process. After that, get_logger() gives
a bound logger, and bind_run() attaches run_id/tenant/vertical to the async-local
context so every log line in a run carries them automatically (no re-passing).

In prod (ENV=prod) logs render as JSON; in dev as a colored console.
"""

from __future__ import annotations

import structlog
import logging

from agentforge.core.config import get_settings


def configure_logging() -> None:
    """Build the structlog processor pipeline. Idempotent — safe to re-call."""
    settings = get_settings()

    shared = [
        structlog.contextvars.merge_contextvars,  # FIRST — pulls in bound run_id/tenant/vertical
        structlog.processors.add_log_level,  # adds "level": "info"
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # adds ISO timestamp
        structlog.processors.StackInfoRenderer(),  # renders stack_info=True
        structlog.processors.format_exc_info,  # turns exc_info into a readable traceback
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    processors = [*shared, renderer]

    level = logging.getLevelName(settings.log_level.upper())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a bound logger. What every module imports."""
    return structlog.get_logger(name)


def bind_run(*, run_id: str, tenant_id: str, vertical: str) -> None:
    """Attach run context to the async-local contextvars for this task."""
    structlog.contextvars.bind_contextvars(run_id=run_id, tenant_id=tenant_id, vertical=vertical)


def clear_run() -> None:
    """Clear bound run context so the next run starts clean."""
    structlog.contextvars.clear_contextvars()
