"""Stop-condition check used inside the agent loop."""

from __future__ import annotations

import time
from typing import Literal

from agentforge.core.runtime.limits import RunLimits

StopReason = Literal[
    "end_turn",
    "max_steps",
    "max_cost",
    "max_time",
    "confidence_threshold",
    "force_synthesis",
]


def check_limits(
    *, step: int, cost_usd: float, started_at: float, limits: RunLimits
) -> StopReason | None:
    if step >= limits.max_steps:
        return "max_steps"
    if cost_usd >= limits.max_cost_usd:
        return "max_cost"
    if (time.monotonic() - started_at) >= limits.max_seconds:
        return "max_time"
    return None
