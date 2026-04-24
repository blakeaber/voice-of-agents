"""Tests for helper functions in voice_of_agents.phases.phase3_evaluate."""

from voice_of_agents.eval.phase3_evaluate import (
    _build_voice_profile,
    _validate_evaluation,
    _fix_consistency,
    _classify_theme,
    _monthly_price,
)


# ── _build_voice_profile ─────────────────────────────────────────────


def test_voice_profile_maria(maria):
    """Maria: 15yr experience, legal vocab, fear motivation → high skepticism, legal vocabulary, fear framing."""
    profile = _build_voice_profile(maria)
    assert profile["skepticism_level"] == "high"
    assert "legal" in profile["vocabulary_style"].lower()
    assert (
        "fear" in profile["motivation_framing"].lower()
        or "mistake" in profile["motivation_framing"].lower()
    )


def test_voice_profile_rachel(rachel):
    """Rachel: 12yr HR, efficiency motivation → includes trust requirements."""
    profile = _build_voice_profile(rachel)
    assert "trust" in profile["trust_bar"].lower() or "approved" in profile["trust_bar"].lower()


# ── _validate_evaluation ─────────────────────────────────────────────


def test_validate_consistent_scores():
    """Consistent scores and narrative should return no issues."""
    evaluation = {
        "scores": {
            "overall": 6,
            "goal_achievement": 5,
            "efficiency": 6,
            "trust": 6,
            "value_for_price": 6,
        },
        "narrative": {
            "frustration_moment": "The page was slow.",
            "objection": "Price is a bit high.",
        },
        "verdict": {"would_pay": True, "retention_risk": "medium"},
    }
    assert _validate_evaluation(evaluation) == []


def test_validate_catches_low_goal_high_overall():
    """Goal=3 but overall=8 should be flagged as inconsistent."""
    evaluation = {
        "scores": {
            "overall": 8,
            "goal_achievement": 3,
            "efficiency": 5,
            "trust": 5,
            "value_for_price": 5,
        },
        "narrative": {"frustration_moment": "Nothing worked.", "objection": "Not ready."},
        "verdict": {"would_pay": False, "retention_risk": "medium"},
    }
    issues = _validate_evaluation(evaluation)
    assert any("overall" in i and "goal_achievement" in i for i in issues)


def test_validate_catches_high_efficiency_low_goal():
    """Efficiency=10 but goal=2 should be flagged (gap too large)."""
    evaluation = {
        "scores": {
            "overall": 5,
            "goal_achievement": 2,
            "efficiency": 10,
            "trust": 5,
            "value_for_price": 5,
        },
        "narrative": {"frustration_moment": "Blocked.", "objection": "Can't use it."},
        "verdict": {"would_pay": False, "retention_risk": "high"},
    }
    issues = _validate_evaluation(evaluation)
    assert any("efficiency" in i and "goal_achievement" in i for i in issues)


def test_validate_catches_high_trust_with_trust_concerns():
    """Trust=8 with trust-concern words in narrative should be flagged."""
    evaluation = {
        "scores": {
            "overall": 7,
            "goal_achievement": 7,
            "efficiency": 7,
            "trust": 8,
            "value_for_price": 7,
        },
        "narrative": {
            "frustration_moment": "I have trust concerns about the accuracy.",
            "objection": "I'm not certain it won't give wrong advice.",
        },
        "verdict": {"would_pay": True, "retention_risk": "low"},
    }
    issues = _validate_evaluation(evaluation)
    assert any("trust" in i for i in issues)


def test_validate_catches_low_value_would_pay():
    """Value=3 but would_pay=true should be flagged."""
    evaluation = {
        "scores": {
            "overall": 5,
            "goal_achievement": 5,
            "efficiency": 5,
            "trust": 5,
            "value_for_price": 3,
        },
        "narrative": {"frustration_moment": "Meh.", "objection": "Not worth it."},
        "verdict": {"would_pay": True, "retention_risk": "medium"},
    }
    issues = _validate_evaluation(evaluation)
    assert any("value_for_price" in i and "would_pay" in i for i in issues)


# ── _fix_consistency ─────────────────────────────────────────────────


def test_fix_consistency_caps_overall_relative_to_goal():
    """When goal<=3 and overall>=7, overall should be capped."""
    evaluation = {
        "scores": {
            "overall": 8,
            "goal_achievement": 2,
            "efficiency": 4,
            "trust": 5,
            "learnability": 5,
            "value_for_price": 5,
        },
        "verdict": {"would_pay": True, "retention_risk": "medium"},
    }
    fixed = _fix_consistency(evaluation, ["overall=8 but goal_achievement=2"])
    # After fix, overall is recalculated as average of sub-scores
    assert fixed["scores"]["overall"] <= fixed["scores"]["goal_achievement"] + 3


def test_fix_consistency_sets_would_pay_false_low_value():
    """When value_for_price<=3, would_pay should be set to False."""
    evaluation = {
        "scores": {
            "overall": 5,
            "goal_achievement": 5,
            "efficiency": 5,
            "trust": 5,
            "learnability": 5,
            "value_for_price": 3,
        },
        "verdict": {"would_pay": True, "retention_risk": "medium"},
    }
    fixed = _fix_consistency(evaluation, ["value_for_price=3 but would_pay=true"])
    assert fixed["verdict"]["would_pay"] is False


# ── _classify_theme ──────────────────────────────────────────────────


def test_classify_theme_retrieval():
    """Retrieval-related words should map to theme A."""
    assert _classify_theme("Cannot find or retrieve past decisions") == "A"


def test_classify_theme_governance():
    """Governance-related words should map to theme E."""
    assert _classify_theme("No audit trail or compliance visibility") == "E"


def test_classify_theme_integration():
    """Integration-related words should map to theme F."""
    assert _classify_theme("Need to import from external systems") == "F"


# ── _monthly_price ───────────────────────────────────────────────────


def test_monthly_price_free(james):
    assert _monthly_price(james) == 0


def test_monthly_price_developer(maria):
    assert _monthly_price(maria) == 29


def test_monthly_price_team(rachel):
    assert _monthly_price(rachel) == 99


def test_monthly_price_enterprise():
    """ENTERPRISE tier should return 299."""
    from voice_of_agents.core.persona import Persona, VoiceProfile

    persona = Persona(
        id=99,
        name="Enterprise User",
        role="CTO",
        industry="Tech",
        segment="b2b",
        tier="ENTERPRISE",
        org_size=50,
        income=250000,
        voice=VoiceProfile(
            skepticism="low", vocabulary="technical", motivation="ambition", price_sensitivity="low"
        ),
    )
    assert _monthly_price(persona) == 299
