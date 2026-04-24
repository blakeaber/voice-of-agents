"""Tests for _derive_goals() seed helper."""

from voice_of_agents.core.pain import PainTheme
from voice_of_agents.core.persona import Persona, VoiceProfile
from voice_of_agents.eval.seed import _derive_goals


def _make_persona(
    org_size=1,
    income=60000,
    price_sensitivity="moderate",
    pain_themes=None,
):
    """Build a minimal canonical Persona with controllable attributes."""
    themes = [PainTheme(theme=code, intensity="MEDIUM") for code in (pain_themes or ["A"])]
    return Persona(
        id=99,
        name="Test User",
        role="Tester",
        industry="General",
        segment="b2c" if org_size <= 1 else "b2b",
        tier="DEVELOPER",
        org_size=org_size,
        income=income,
        pain_themes=themes,
        voice=VoiceProfile(price_sensitivity=price_sensitivity),
    )


class TestDeriveGoals:
    """_derive_goals() maps persona attributes to onboarding goals."""

    def test_solo_knowledge_user(self):
        """Solo user with no special attributes gets only 'knowledge'."""
        persona = _make_persona(
            org_size=1, income=80000, price_sensitivity="low", pain_themes=["A"]
        )
        goals = _derive_goals(persona)
        assert goals == ["knowledge"]

    def test_team_user_includes_delegation(self):
        """Team user (org_size=8) gets 'delegation' added."""
        persona = _make_persona(
            org_size=8, income=130000, price_sensitivity="low", pain_themes=["B"]
        )
        goals = _derive_goals(persona)
        assert "knowledge" in goals
        assert "delegation" in goals

    def test_cost_sensitive_by_income(self):
        """User with income < 60000 gets 'cost' goal."""
        persona = _make_persona(income=45000, price_sensitivity="moderate", pain_themes=["A"])
        goals = _derive_goals(persona)
        assert "cost" in goals

    def test_cost_sensitive_by_price_sensitivity(self):
        """User with high price_sensitivity gets 'cost' goal."""
        persona = _make_persona(income=80000, price_sensitivity="high", pain_themes=["A"])
        goals = _derive_goals(persona)
        assert "cost" in goals

    def test_governance_pain_theme_adds_delegation(self):
        """Pain theme E (Governance) adds 'delegation' even for solo users."""
        persona = _make_persona(org_size=1, pain_themes=["E"])
        goals = _derive_goals(persona)
        assert "delegation" in goals

    def test_integration_pain_theme_adds_workflows(self):
        """Pain theme F (Integration) adds 'workflows'."""
        persona = _make_persona(pain_themes=["F"])
        goals = _derive_goals(persona)
        assert "workflows" in goals

    def test_no_duplicate_delegation_from_team_and_governance(self):
        """Team user with governance pain should have delegation only once."""
        persona = _make_persona(org_size=5, pain_themes=["E"])
        goals = _derive_goals(persona)
        assert goals.count("delegation") == 1

    def test_james_fixture_gets_cost(self, james):
        """James (income=45000, high price_sensitivity) should get 'cost'."""
        goals = _derive_goals(james)
        assert "knowledge" in goals
        assert "cost" in goals

    def test_rachel_fixture_gets_delegation(self, rachel):
        """Rachel (org_size=8) should get 'delegation'."""
        goals = _derive_goals(rachel)
        assert "knowledge" in goals
        assert "delegation" in goals

    def test_maria_fixture_solo_knowledge(self, maria):
        """Maria (solo, income=52000) should get 'knowledge' and 'cost'."""
        goals = _derive_goals(maria)
        assert "knowledge" in goals
        assert "cost" in goals
