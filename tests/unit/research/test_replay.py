"""Unit tests for the offline demo replay path."""

from __future__ import annotations

from io import StringIO

import yaml
from rich.console import Console

from voice_of_agents.research.replay import load_demo_fixture, render_offline_demo


# ── Fixture loading ──────────────────────────────────────────────


def test_load_demo_fixture_returns_dict():
    data = load_demo_fixture()
    assert isinstance(data, dict)


def test_load_demo_fixture_has_required_keys():
    data = load_demo_fixture()
    for key in (
        "version",
        "preset_question",
        "top_findings",
        "build_this_first",
        "personas",
        "churn_triggers",
        "validate_with",
        "next_steps",
    ):
        assert key in data, f"fixture missing key: {key}"


def test_load_demo_fixture_has_minimum_content():
    """The fixture must have at least 5 top_findings so the demo output is
    substantial enough to demonstrate the pipeline."""
    data = load_demo_fixture()
    assert len(data["top_findings"]) >= 5
    assert len(data["personas"]) >= 2
    assert len(data["churn_triggers"]) >= 3
    assert len(data["validate_with"]) >= 3


def test_load_demo_fixture_personas_have_required_fields():
    data = load_demo_fixture()
    for p in data["personas"]:
        assert "archetype" in p
        assert "top_concern" in p
        # uxw_id and would_pay_if are soft-required; tolerate missing for
        # future-compat.


# ── Rendering ────────────────────────────────────────────────────


def _capture_render(data: dict) -> str:
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True, width=120)
    render_offline_demo(console, data)
    return buf.getvalue()


def test_render_offline_demo_prints_all_sections():
    data = load_demo_fixture()
    out = _capture_render(data)
    # Section headings
    assert "Top Findings" in out
    assert "Build This First" in out
    assert "User Archetypes" in out
    assert "What Would Make Them Leave" in out
    assert "Validate With Real Users" in out
    assert "What to do next" in out


def test_render_offline_demo_prints_fixture_content():
    data = load_demo_fixture()
    out = _capture_render(data)
    # Spot-check that real content makes it through (not just headings)
    assert data["build_this_first"][:40] in out
    assert data["personas"][0]["archetype"] in out
    assert data["validate_with"][0][:30] in out


def test_render_offline_demo_handles_minimal_input():
    """Render must not crash on sparse input (missing optional sections)."""
    minimal = {
        "preset_question": "Test?",
        "top_findings": ["Finding A"],
        "build_this_first": "Do X.",
        "personas": [],
        "churn_triggers": [],
        "validate_with": [],
        "next_steps": [],
    }
    out = _capture_render(minimal)
    assert "Finding A" in out
    assert "Do X." in out


def test_render_offline_demo_declares_offline_mode():
    """Output must clearly signal that it's the offline fixture, not a live run."""
    data = load_demo_fixture()
    out = _capture_render(data)
    assert "offline" in out.lower()
    assert "no API key" in out or "bundled" in out.lower()


# ── Fixture YAML sanity ──────────────────────────────────────────


def test_fixture_file_is_valid_yaml():
    import importlib.resources

    path = importlib.resources.files("voice_of_agents.fixtures") / "demo_result.yaml"
    parsed = yaml.safe_load(path.read_text())
    assert isinstance(parsed, dict)


def test_fixture_file_size_is_reasonable():
    """Fixture should be small enough not to bloat the wheel."""
    import importlib.resources

    path = importlib.resources.files("voice_of_agents.fixtures") / "demo_result.yaml"
    size = len(path.read_text())
    assert size < 10_000, f"fixture unexpectedly large: {size} bytes"
