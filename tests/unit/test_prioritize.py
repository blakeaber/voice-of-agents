"""Tests for helper functions in voice_of_agents.phases.phase5_prioritize."""

import pytest

from voice_of_agents.eval.phase5_prioritize import (
    _estimate_effort,
    _revenue_score,
)


# ── _estimate_effort ─────────────────────────────────────────────────


def test_estimate_effort_trivial():
    """Finding with 'empty state' in title should be trivial."""
    finding = {"title": "Fix empty state messaging", "description": ""}
    assert _estimate_effort(finding) == "trivial"


def test_estimate_effort_small():
    """Finding with 'button' should be small."""
    finding = {"title": "Add save button to form", "description": ""}
    assert _estimate_effort(finding) == "small"


def test_estimate_effort_large():
    """Finding with 'import' should be large."""
    finding = {"title": "Support CSV import for learnings", "description": ""}
    assert _estimate_effort(finding) == "large"


def test_estimate_effort_epic():
    """Finding with 'bulk migration' should be epic."""
    finding = {"title": "Bulk migration of existing knowledge", "description": ""}
    assert _estimate_effort(finding) == "epic"


def test_estimate_effort_unknown_defaults_to_medium():
    """Finding with no matching keywords should default to medium."""
    finding = {"title": "Improve persona response quality", "description": "Make it better"}
    assert _estimate_effort(finding) == "medium"


# ── _revenue_score ───────────────────────────────────────────────────


def test_revenue_score_enterprise():
    """ENTERPRISE persona should yield weight 1.0."""
    tiers = {"UXW-50": "ENTERPRISE"}
    assert _revenue_score(["UXW-50"], tiers) == 1.0


def test_revenue_score_free():
    """FREE persona should yield weight 0.1."""
    tiers = {"UXW-04": "FREE"}
    assert _revenue_score(["UXW-04"], tiers) == pytest.approx(0.1)


def test_revenue_score_empty_personas():
    """Empty persona list should return 0.0."""
    assert _revenue_score([], {}) == 0.0


def test_revenue_score_mixed_tiers():
    """Mixed tiers should return the max weight."""
    tiers = {"UXW-01": "FREE", "UXW-20": "TEAM", "UXW-50": "ENTERPRISE"}
    result = _revenue_score(["UXW-01", "UXW-20", "UXW-50"], tiers)
    assert result == pytest.approx(1.0)
