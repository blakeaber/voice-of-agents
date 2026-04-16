"""Tests for pure helper functions in voice_of_agents.explorer.browser."""

import pytest

from voice_of_agents.explorer.browser import (
    NavLink,
    _find_best_link,
    _derive_input_text,
    _is_relevant_to_persona,
    _react_to_landing,
    _react_to_nav,
    _quote_cant_find,
)
from voice_of_agents.contracts.personas import Objective


# ── _find_best_link ──────────────────────────────────────────────────


def test_find_best_link_knowledge_objective(sample_nav_links):
    """Knowledge-retrieval objective should match Workspace or Knowledge Library."""
    obj = Objective(
        id="OBJ-01",
        goal="Retrieve Past Visa Strategy for Similar Case",
        trigger="New client intake with a case type handled before",
        success_definition="Found prior petition strategy in under 60 seconds",
    )
    result = _find_best_link(obj, sample_nav_links)
    assert result is not None
    assert result.text in ("Workspace", "Knowledge Library")


def test_find_best_link_delegation_objective(sample_nav_links):
    """Delegation-related objective should match Find Expert."""
    obj = Objective(
        id="OBJ-02",
        goal="Delegate complex compliance question to expert",
        trigger="Client asks about obscure regulation",
        success_definition="Expert responds within 2 hours",
    )
    result = _find_best_link(obj, sample_nav_links)
    assert result is not None
    assert result.text in ("Find Expert", "Delegation Inbox")


def test_find_best_link_no_match():
    """When no links match the objective, returns None."""
    obj = Objective(
        id="OBJ-99",
        goal="Check weather forecast",
        trigger="Morning routine",
        success_definition="See today's weather",
    )
    links = [
        NavLink(text="Past Runs", href="/"),
        NavLink(text="Settings", href="/settings"),
    ]
    result = _find_best_link(obj, links)
    assert result is None


# ── _derive_input_text ───────────────────────────────────────────────


def test_derive_input_text_uses_trigger(maria):
    """When objective has a trigger, _derive_input_text returns it directly."""
    obj = maria.objectives[0]
    assert obj.trigger  # precondition
    result = _derive_input_text(maria, obj)
    assert result == obj.trigger


def test_derive_input_text_fallback_without_trigger(maria):
    """Without a trigger, generates fallback text based on goal/role/industry."""
    obj = Objective(
        id="OBJ-X",
        goal="Retrieve prior case notes",
        trigger="",
        success_definition="Found notes",
    )
    result = _derive_input_text(maria, obj)
    assert result != ""
    # Fallback should reference persona context
    assert "Legal" in result or "legal" in result.lower() or "Immigration Paralegal" in result


# ── _is_relevant_to_persona ──────────────────────────────────────────


def test_is_relevant_solo_user_filters_team_links(maria):
    """Solo user (team_size=1) should NOT see team-specific links as relevant."""
    assert maria.team_size == 1
    team_link = NavLink(text="Delegation Inbox", href="/pro/delegations")
    assert _is_relevant_to_persona(team_link, maria) is False


def test_is_relevant_team_user_includes_team_links(rachel):
    """Team user (team_size>1) should see delegation/expert links as relevant."""
    assert rachel.team_size > 1
    team_link = NavLink(text="Delegation Inbox", href="/pro/delegations")
    assert _is_relevant_to_persona(team_link, rachel) is True


# ── _react_to_landing ────────────────────────────────────────────────


def test_react_to_landing_login_url(maria):
    """Login URL reaction should mention login."""
    reaction = _react_to_landing(maria, "http://localhost:3000/login")
    assert "log in" in reaction.lower()


def test_react_to_landing_workspace_url(maria):
    """Workspace URL reaction should mention workspace."""
    reaction = _react_to_landing(maria, "http://localhost:3000/pro/workspace")
    assert "workspace" in reaction.lower()


# ── _react_to_nav ────────────────────────────────────────────────────


def test_react_to_nav_many_links(maria, sample_nav_links):
    """When there are many nav links (>10), reaction should mention the count."""
    assert len(sample_nav_links) > 10
    reaction = _react_to_nav(maria, sample_nav_links)
    assert str(len(sample_nav_links)) in reaction


# ── _quote_cant_find ─────────────────────────────────────────────────


def test_quote_cant_find_fear_motivation(maria):
    """Fear-motivated persona's quote should mention liability."""
    assert maria.voice.motivation == "fear"
    obj = maria.objectives[0]
    quote = _quote_cant_find(maria, obj)
    assert "liability" in quote.lower()


def test_quote_cant_find_compliance_motivation():
    """Compliance-motivated persona's quote should mention audit."""
    from voice_of_agents.contracts.personas import Persona, Voice, PainPoint
    persona = Persona(
        id="UXW-99",
        name="Test Compliance",
        role="Compliance Officer",
        industry="Finance",
        experience_years=10,
        income=90000,
        team_size=1,
        tier="TEAM",
        objectives=[
            Objective(
                id="OBJ-01",
                goal="Verify audit trail for knowledge decisions",
                trigger="Quarterly audit",
                success_definition="Full audit trail visible",
            ),
        ],
        pain_points=[PainPoint(description="No audit trail", severity=8, theme="E")],
        trust_requirements=["Full audit trail"],
        voice=Voice(skepticism="high", vocabulary="financial", motivation="compliance", price_sensitivity="moderate"),
    )
    quote = _quote_cant_find(persona, persona.objectives[0])
    assert "audit" in quote.lower()
