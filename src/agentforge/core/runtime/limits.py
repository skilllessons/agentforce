"""Hard stop limits for an agent run."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class RunLimits:
    max_steps: int = 8
    max_cost_usd: float = 0.50
    max_seconds: int = 90
    max_tool_output_chars: int = 16_000
    early_stop_confidence: float = 0.85

    def merged_with(self, overrides: dict[str, float | int] | None) -> RunLimits:
        if not overrides:
            return self
        kwargs = {k: v for k, v in overrides.items() if k in {f.name for f in field_specs()}}
        return replace(self, **kwargs)  # type: ignore[arg-type]


DEFAULT_LIMITS = RunLimits()


def field_specs() -> list:
    # Helper for merged_with; avoids importing dataclasses.fields at call time.
    return list(DEFAULT_LIMITS.__dataclass_fields__.values())  # type: ignore[attr-defined]


# Re-export for typing convenience.
_ = field
