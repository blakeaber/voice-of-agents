"""Tests for _template_generate_evaluation and related helpers."""

import pytest

from voice_of_agents.core.persona import Persona, VoiceProfile
from voice_of_agents.eval.phase3_evaluate import (
    _generate_missing_quote,
    _generate_quote,
    _monthly_price,
    _persona_header,
    _template_generate_evaluation,
)


def _make_persona(**kwargs) -> Persona:
    defaults = dict(
        id=1,
        name="Test User",
        role="Analyst",
        industry="Finance",
        segment="b2c",
        tier="DEVELOPER",
        experience_years=5,
        income=80000,
        org_size=1,
    )
    defaults.update(kwargs)
    return Persona(**defaults)


def _empty_exploration(persona_id=1, persona_name="Test User") -> dict:
    return {
        "persona_id": persona_id,
        "persona_name": persona_name,
        "run_timestamp": "20260402_120000",
        "objectives": [],
    }


def _exploration_with_friction(friction_type="empty_state", severity="medium") -> dict:
    return {
        "persona_id": 1,
        "persona_name": "Test User",
        "run_timestamp": "20260402_120000",
        "objectives": [
            {
                "objective": "Complete a task",
                "outcome": "partial",
                "pages_visited": ["/dashboard", "/workspace"],
                "journey": [],
                "friction_points": [
                    {"type": friction_type, "description": f"Issue: {friction_type}",
                     "severity": severity},
                ],
                "missing_capabilities": [],
            }
        ],
    }


class TestTemplateGenerateEvaluation:
    def test_returns_required_keys(self):
        persona = _make_persona()
        result = _template_generate_evaluation(persona, _empty_exploration())
        assert "scores" in result
        assert "narrative" in result
        assert "verdict" in result
        assert "persona" in result
        assert "unmet_needs" in result

    def test_scores_in_valid_range(self):
        persona = _make_persona()
        result = _template_generate_evaluation(persona, _empty_exploration())
        for key, val in result["scores"].items():
            assert 1 <= val <= 10, f"{key}={val} out of range"

    def test_overall_capped_by_goal_plus_one(self):
        persona = _make_persona()
        exploration = {
            "persona_id": 1,
            "persona_name": "Test User",
            "run_timestamp": "20260402_120000",
            "objectives": [
                {"outcome": "blocked", "pages_visited": [], "journey": [],
                 "friction_points": [], "missing_capabilities": []},
                {"outcome": "blocked", "pages_visited": [], "journey": [],
                 "friction_points": [], "missing_capabilities": []},
            ],
        }
        result = _template_generate_evaluation(persona, exploration)
        scores = result["scores"]
        best = max(scores["goal_achievement"], scores["efficiency"],
                   scores["trust"], scores["learnability"], scores["value_for_price"])
        assert scores["overall"] <= best + 1

    def test_high_price_sensitivity_lowers_value(self):
        persona_sensitive = _make_persona(
            voice=VoiceProfile(price_sensitivity="high")
        )
        persona_insensitive = _make_persona(
            voice=VoiceProfile(price_sensitivity="low")
        )
        r_sens = _template_generate_evaluation(persona_sensitive, _empty_exploration())
        r_insens = _template_generate_evaluation(persona_insensitive, _empty_exploration())
        assert r_sens["scores"]["value_for_price"] <= r_insens["scores"]["value_for_price"]

    def test_high_skepticism_lowers_trust_base(self):
        persona = _make_persona(
            voice=VoiceProfile(skepticism="high"),
        )
        exploration = _exploration_with_friction(friction_type="gap", severity="high")
        result = _template_generate_evaluation(persona, exploration)
        assert result["scores"]["trust"] < 7

    def test_verdict_would_pay_false_when_low_goal(self):
        persona = _make_persona()
        exploration = {
            "persona_id": 1, "persona_name": "Test User",
            "run_timestamp": "20260402_120000",
            "objectives": [
                {"outcome": "blocked", "pages_visited": [], "journey": [],
                 "friction_points": [], "missing_capabilities": []},
            ],
        }
        result = _template_generate_evaluation(persona, exploration)
        if result["scores"]["goal_achievement"] < 4:
            assert result["verdict"]["would_pay"] is False

    def test_retention_risk_high_when_low_overall(self):
        persona = _make_persona()
        exploration = {
            "persona_id": 1, "persona_name": "Test User",
            "run_timestamp": "20260402_120000",
            "objectives": [
                {"outcome": "blocked", "pages_visited": [], "journey": [],
                 "friction_points": [
                     {"type": "gap", "description": "Nothing works",
                      "severity": "critical"},
                 ], "missing_capabilities": ["everything"]},
            ],
        }
        result = _template_generate_evaluation(persona, exploration)
        assert result["verdict"]["retention_risk"] in ("medium", "high")

    def test_missing_capabilities_appear_in_unmet_needs(self):
        persona = _make_persona()
        exploration = {
            "persona_id": 1, "persona_name": "Test User",
            "run_timestamp": "20260402_120000",
            "objectives": [
                {"outcome": "partial", "pages_visited": [], "journey": [],
                 "friction_points": [],
                 "missing_capabilities": ["export to PDF"]},
            ],
        }
        result = _template_generate_evaluation(persona, exploration)
        needs = [n["need"] for n in result["unmet_needs"]]
        assert any("export to PDF" in n for n in needs)

    def test_friction_points_appear_in_unmet_needs(self):
        persona = _make_persona()
        exploration = _exploration_with_friction("empty_state", "medium")
        result = _template_generate_evaluation(persona, exploration)
        needs = [n["need"] for n in result["unmet_needs"]]
        assert len(needs) > 0

    def test_fear_motivation_objection_mentions_liability(self):
        persona = _make_persona(
            industry="Legal",
            voice=VoiceProfile(motivation="fear"),
        )
        result = _template_generate_evaluation(persona, _empty_exploration())
        assert "liability" in result["narrative"]["objection"].lower() or \
               "wrong" in result["narrative"]["objection"].lower()

    def test_compliance_motivation_objection_mentions_audit(self):
        persona = _make_persona(
            voice=VoiceProfile(motivation="compliance"),
        )
        result = _template_generate_evaluation(persona, _empty_exploration())
        assert "audit" in result["narrative"]["objection"].lower()

    def test_multiple_pages_in_highlight(self):
        persona = _make_persona()
        exploration = {
            "persona_id": 1, "persona_name": "Test User",
            "run_timestamp": "20260402_120000",
            "objectives": [
                {"outcome": "achieved", "pages_visited": ["/a", "/b", "/c"],
                 "journey": [], "friction_points": [], "missing_capabilities": []},
            ],
        }
        result = _template_generate_evaluation(persona, exploration)
        assert "3" in result["narrative"]["highlight_moment"] or \
               "navigate" in result["narrative"]["highlight_moment"].lower()


class TestPersonaHeader:
    def test_returns_tier_as_string(self, maria):
        header = _persona_header(maria)
        assert header["tier"] == "DEVELOPER"
        assert isinstance(header["tier"], str)

    def test_returns_id_as_int(self, maria):
        header = _persona_header(maria)
        assert header["id"] == 1


class TestQuoteGenerators:
    def test_generate_quote_non_empty(self, maria):
        friction = {"description": "Can't find old cases", "type": "gap", "severity": "high"}
        quote = _generate_quote(maria, friction)
        assert len(quote) > 10

    def test_generate_missing_quote_non_empty(self, maria):
        quote = _generate_missing_quote(maria, "bulk knowledge import")
        assert len(quote) > 10
        assert "bulk knowledge import" in quote.lower() or "import" in quote.lower()
