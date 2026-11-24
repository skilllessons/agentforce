"""Which tenant the current agent run belongs to.

Set by run_agent, read by tools. Tools get only the model's input, so this is
the one way a tool learns the tenant; the model can never choose it.
ContextVar values are per async task, and tasks started by asyncio.gather
copy the context they were created in, so every tool call in a run sees the
same tenant and concurrent runs never see each other's.
"""

from __future__ import annotations

from contextvars import ContextVar

current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


def get_tenant() -> str | None:
    return current_tenant.get()
