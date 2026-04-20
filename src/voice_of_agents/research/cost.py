"""Cost and time estimation for research pipeline runs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator, Optional

from pydantic import BaseModel

# Approximate token usage per stage (input + output), per subject where applicable.
# Based on measured runs — conservative high-end estimates.
_TOKENS_PER_SUBJECT_INPUT = 800
_TOKENS_PER_SUBJECT_OUTPUT = 1200

COST_PER_STAGE = {
    "product_research": {
        # subject_count parallel researcher-brief calls + hypothesis scoring + segmentation
        "input_tokens_per_subject": _TOKENS_PER_SUBJECT_INPUT,
        "output_tokens_per_subject": _TOKENS_PER_SUBJECT_OUTPUT,
        "fixed_input_tokens": 2000,   # hypothesis scoring + segmentation
        "fixed_output_tokens": 3000,
        "time_seconds_per_subject": 15,
        "fixed_time_seconds": 30,
    },
    "personas_from_research": {
        "input_tokens_per_subject": 600,
        "output_tokens_per_subject": 1000,
        "fixed_input_tokens": 3000,
        "fixed_output_tokens": 4000,
        "time_seconds_per_subject": 12,
        "fixed_time_seconds": 45,
    },
    "workflows_from_interviews": {
        "input_tokens_per_subject": 700,
        "output_tokens_per_subject": 1500,
        "fixed_input_tokens": 2000,
        "fixed_output_tokens": 3000,
        "time_seconds_per_subject": 18,
        "fixed_time_seconds": 30,
    },
    "journey_redesign": {
        "input_tokens_per_subject": 900,
        "output_tokens_per_subject": 1800,
        "fixed_input_tokens": 3000,
        "fixed_output_tokens": 5000,
        "time_seconds_per_subject": 20,
        "fixed_time_seconds": 60,
    },
}

# Pricing per million tokens (as of 2025-04-20, subject to change)
_MODEL_PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}
_DEFAULT_PRICING = {"input": 15.0, "output": 75.0}


class CostEstimate(BaseModel):
    model: str
    subject_count: int
    stages: list[str]
    low_usd: float
    high_usd: float
    time_minutes_low: int
    time_minutes_high: int

    def display(self) -> str:
        return (
            f"  Model:          {self.model}\n"
            f"  Subjects:       {self.subject_count}\n"
            f"  Stages:         {', '.join(self.stages)}\n"
            f"  Estimated cost: ${self.low_usd:.2f}–${self.high_usd:.2f}\n"
            f"  Estimated time: {self.time_minutes_low}–{self.time_minutes_high} minutes"
        )


def estimate_run_cost(
    model: str,
    subject_count: int,
    stages: Optional[list[str]] = None,
) -> CostEstimate:
    """Estimate cost and time for a pipeline run before any API calls are made.

    Uses documented token-usage constants per stage and current Anthropic pricing.
    Returns a low/high range (±20-40% of base estimate) and a time estimate in minutes.

    Args:
        model: Anthropic model ID (e.g. "claude-opus-4-7", "claude-haiku-4-5-20251001").
        subject_count: Number of parallel interview subjects (10-16).
        stages: List of stage keys to estimate. Defaults to all 4 stages.
            Valid values: "product_research", "personas_from_research",
            "workflows_from_interviews", "journey_redesign".

    Returns:
        CostEstimate with low_usd, high_usd, time_minutes_low, time_minutes_high.
        Call .display() for a formatted string suitable for terminal output.

    Example:
        estimate = estimate_run_cost("claude-opus-4-7", subject_count=12)
        print(estimate.display())
        # Model:          claude-opus-4-7
        # Subjects:       12
        # Estimated cost: $1.20–$2.10
        # Estimated time: 8–15 minutes
    """
    if stages is None:
        stages = list(COST_PER_STAGE.keys())

    pricing = _MODEL_PRICING.get(model, _DEFAULT_PRICING)
    input_rate = pricing["input"] / 1_000_000
    output_rate = pricing["output"] / 1_000_000

    total_input = 0
    total_output = 0
    total_seconds = 0

    for stage in stages:
        cfg = COST_PER_STAGE.get(stage, {})
        n = subject_count if stage == "product_research" else max(3, subject_count // 2)
        total_input += cfg.get("input_tokens_per_subject", 0) * n + cfg.get("fixed_input_tokens", 0)
        total_output += cfg.get("output_tokens_per_subject", 0) * n + cfg.get("fixed_output_tokens", 0)
        total_seconds += cfg.get("time_seconds_per_subject", 0) * n + cfg.get("fixed_time_seconds", 0)

    base_cost = total_input * input_rate + total_output * output_rate
    low = round(base_cost * 0.8, 2)
    high = round(base_cost * 1.4, 2)

    time_low = max(1, int(total_seconds * 0.7 / 60))
    time_high = max(2, int(total_seconds * 1.3 / 60))

    return CostEstimate(
        model=model,
        subject_count=subject_count,
        stages=stages,
        low_usd=low,
        high_usd=high,
        time_minutes_low=time_low,
        time_minutes_high=time_high,
    )


@dataclass
class CostTracker:
    """Tracks actual token usage during a pipeline run."""

    model: str
    _input_tokens: int = field(default=0)
    _output_tokens: int = field(default=0)

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self._input_tokens += input_tokens
        self._output_tokens += output_tokens

    @property
    def total_usd(self) -> float:
        pricing = _MODEL_PRICING.get(self.model, _DEFAULT_PRICING)
        return (
            self._input_tokens * pricing["input"] / 1_000_000
            + self._output_tokens * pricing["output"] / 1_000_000
        )

    def display(self) -> str:
        return f"${self.total_usd:.4f} ({self._input_tokens:,} in / {self._output_tokens:,} out tokens)"


@contextmanager
def track_cost(model: str) -> Generator[CostTracker, None, None]:
    """Context manager that yields a CostTracker for accumulating token usage."""
    tracker = CostTracker(model=model)
    yield tracker
