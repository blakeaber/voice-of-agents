"""Tests for research/cost.py — cost estimation and tracking."""

import pytest

from voice_of_agents.research.cost import (
    CostEstimate,
    CostTracker,
    estimate_run_cost,
    track_cost,
)


class TestEstimateRunCost:
    def test_returns_cost_estimate(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        assert isinstance(estimate, CostEstimate)

    def test_estimate_has_all_stages_by_default(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        assert len(estimate.stages) == 4

    def test_estimate_stages_subset(self):
        estimate = estimate_run_cost(
            model="claude-opus-4-7",
            subject_count=12,
            stages=["product_research"],
        )
        assert estimate.stages == ["product_research"]

    def test_high_cost_exceeds_low_cost(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        assert estimate.high_usd > estimate.low_usd

    def test_haiku_cheaper_than_opus(self):
        opus = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        haiku = estimate_run_cost(model="claude-haiku-4-5-20251001", subject_count=12)
        assert haiku.high_usd < opus.low_usd

    def test_more_subjects_costs_more(self):
        small = estimate_run_cost(model="claude-opus-4-7", subject_count=10)
        large = estimate_run_cost(model="claude-opus-4-7", subject_count=16)
        assert large.high_usd > small.low_usd

    def test_time_estimate_positive(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        assert estimate.time_minutes_low >= 1
        assert estimate.time_minutes_high >= estimate.time_minutes_low

    def test_display_contains_model(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        display = estimate.display()
        assert "claude-opus-4-7" in display

    def test_display_contains_dollar_sign(self):
        estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
        display = estimate.display()
        assert "$" in display

    def test_unknown_model_uses_default_pricing(self):
        estimate = estimate_run_cost(model="claude-unknown-99", subject_count=10)
        assert estimate.high_usd > 0


class TestCostTracker:
    def test_initial_total_is_zero(self):
        tracker = CostTracker(model="claude-opus-4-7")
        assert tracker.total_usd == 0.0

    def test_add_tokens_increases_total(self):
        tracker = CostTracker(model="claude-opus-4-7")
        tracker.add(1000, 500)
        assert tracker.total_usd > 0

    def test_display_contains_dollar_sign(self):
        tracker = CostTracker(model="claude-opus-4-7")
        tracker.add(500, 200)
        assert "$" in tracker.display()

    def test_accumulates_multiple_calls(self):
        tracker = CostTracker(model="claude-opus-4-7")
        tracker.add(100, 50)
        after_one = tracker.total_usd
        tracker.add(100, 50)
        assert tracker.total_usd > after_one


class TestTrackCostContextManager:
    def test_yields_tracker(self):
        with track_cost("claude-opus-4-7") as tracker:
            assert isinstance(tracker, CostTracker)

    def test_tracker_model_matches(self):
        with track_cost("claude-haiku-4-5-20251001") as tracker:
            assert tracker.model == "claude-haiku-4-5-20251001"
