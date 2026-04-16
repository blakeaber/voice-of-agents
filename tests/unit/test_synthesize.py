"""Tests for helper functions in voice_of_agents.phases.phase4_synthesize."""

import pytest

from voice_of_agents.phases.phase4_synthesize import (
    _cluster_key,
    _classify_segment,
)


# ── _cluster_key ─────────────────────────────────────────────────────


def test_cluster_key_removes_stopwords():
    """Stopwords should be stripped; result is first 3 significant words."""
    result = _cluster_key("the inability to retrieve past decisions")
    words = result.split()
    assert "the" not in words
    assert "to" not in words
    assert len(words) <= 3
    assert words[0] == "inability"


# ── _classify_segment ────────────────────────────────────────────────


def test_classify_segment_universal():
    """80% coverage (8 of 10) should be 'universal'."""
    assert _classify_segment(8, 10) == "universal"


def test_classify_segment_segment():
    """40% coverage (4 of 10) should be 'segment'."""
    assert _classify_segment(4, 10) == "segment"


def test_classify_segment_niche():
    """10% coverage (1 of 10) should be 'niche'."""
    assert _classify_segment(1, 10) == "niche"


def test_classify_segment_zero_total():
    """Zero total personas should return 'unknown'."""
    assert _classify_segment(0, 0) == "unknown"
