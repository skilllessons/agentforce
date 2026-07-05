"""Per-million-token pricing for cost estimation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_mtok: float
    output_usd_per_mtok: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-7": ModelPricing(15, 75),
    "claude-sonnet-4-6": ModelPricing(3, 15),
    "claude-haiku-4-5-20251001": ModelPricing(0.8, 4),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-opus-4-7"])
    return (
        (input_tokens / 1_000_000) * pricing.input_usd_per_mtok
        + (output_tokens / 1_000_000) * pricing.output_usd_per_mtok
    )
