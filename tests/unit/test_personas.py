"""Tests for Persona contract."""

from voice_of_agents.contracts.personas import (
    Objective,
    PainPoint,
    Persona,
    Voice,
    validate_persona,
)


class TestPersonaSlug:
    """Persona.slug generates correct URL-safe string."""

    def test_slug_from_maria(self, maria):
        assert maria.slug == "UXW-01-maria-gutierrez"

    def test_slug_from_rachel(self, rachel):
        assert rachel.slug == "UXW-20-rachel-okafor"

    def test_slug_strips_special_chars(self):
        p = Persona(id="UXW-99", name="Jean-Luc O'Brien III", role="Tester")
        # Special chars replaced with hyphens, consecutive hyphens collapsed
        slug = p.slug
        assert slug.startswith("UXW-99-")
        assert "'" not in slug
        assert slug == "UXW-99-jean-luc-o-brien-iii"

    def test_slug_lowercases(self):
        p = Persona(id="UXW-05", name="ALICE SMITH", role="Dev")
        assert "alice-smith" in p.slug


class TestPersonaToDict:
    """to_dict() returns all fields."""

    def test_to_dict_has_all_top_level_keys(self, maria):
        d = maria.to_dict()
        expected_keys = {
            "id", "name", "role", "industry", "experience_years",
            "income", "team_size", "tier", "objectives", "pain_points",
            "trust_requirements", "voice",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_objectives_serialized(self, maria):
        d = maria.to_dict()
        assert len(d["objectives"]) == 2
        assert d["objectives"][0]["id"] == "OBJ-01"
        assert "goal" in d["objectives"][0]

    def test_to_dict_pain_points_serialized(self, maria):
        d = maria.to_dict()
        assert len(d["pain_points"]) == 2
        assert d["pain_points"][0]["severity"] == 9

    def test_to_dict_voice_is_flat_dict(self, maria):
        d = maria.to_dict()
        assert isinstance(d["voice"], dict)
        assert d["voice"]["skepticism"] == "high"
        assert d["voice"]["vocabulary"] == "legal"


class TestValidatePersona:
    """validate_persona() checks for required fields."""

    def test_valid_persona_returns_empty(self, maria):
        issues = validate_persona(maria)
        assert issues == []

    def test_valid_rachel_returns_empty(self, rachel):
        assert validate_persona(rachel) == []

    def test_missing_id(self):
        p = Persona(
            id="", name="Test", role="Tester",
            objectives=[Objective(id="O1", goal="Do something")],
            pain_points=[PainPoint(description="Ouch")],
        )
        issues = validate_persona(p)
        assert "Missing id" in issues

    def test_missing_objectives(self):
        p = Persona(id="X-01", name="Test", role="Tester",
                    pain_points=[PainPoint(description="Ouch")])
        issues = validate_persona(p)
        assert "No objectives defined" in issues

    def test_invalid_tier(self):
        p = Persona(
            id="X-01", name="Test", role="Tester", tier="PLATINUM",
            objectives=[Objective(id="O1", goal="Do something")],
            pain_points=[PainPoint(description="Ouch")],
        )
        issues = validate_persona(p)
        assert any("Invalid tier" in i for i in issues)

    def test_missing_name_and_role(self):
        p = Persona(
            id="X-01", name="", role="",
            objectives=[Objective(id="O1", goal="G")],
            pain_points=[PainPoint(description="P")],
        )
        issues = validate_persona(p)
        assert "Missing name" in issues
        assert "Missing role" in issues

    def test_objective_without_goal(self):
        p = Persona(
            id="X-01", name="Test", role="Tester",
            objectives=[Objective(id="O1", goal="")],
            pain_points=[PainPoint(description="Ouch")],
        )
        issues = validate_persona(p)
        assert any("no goal" in i for i in issues)


class TestObjectiveDefaults:
    """Objective defaults are correct."""

    def test_defaults(self):
        o = Objective(id="O1", goal="Test goal")
        assert o.trigger == ""
        assert o.success_definition == ""
        assert o.efficiency_baseline == ""
        assert o.target_efficiency == ""


class TestVoiceDefaults:
    """Voice defaults are correct."""

    def test_defaults(self):
        v = Voice()
        assert v.skepticism == "moderate"
        assert v.vocabulary == "general"
        assert v.motivation == "efficiency"
        assert v.price_sensitivity == "moderate"
