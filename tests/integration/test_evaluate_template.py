"""Integration tests: Full template evaluation with sample exploration data."""

import pytest

from voice_of_agents.eval.phase3_evaluate import (
    _template_generate_evaluation,
    _validate_evaluation,
)


class TestTemplateEvaluation:
    def test_generates_all_required_fields(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        assert "persona" in result
        assert "scores" in result
        assert "narrative" in result
        assert "verdict" in result
        assert "unmet_needs" in result
        assert result["generation_method"] == "template"

    def test_scores_are_in_range(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        for key, val in result["scores"].items():
            assert 1 <= val <= 10, f"Score {key}={val} out of range"

    def test_scores_are_consistent(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        issues = _validate_evaluation(result)
        assert issues == [], f"Consistency issues: {issues}"

    def test_blocked_goals_produce_low_scores(self, maria, sample_exploration):
        # Modify exploration to have all blocked outcomes
        for obj in sample_exploration["objectives"]:
            obj["outcome"] = "blocked"
            obj["friction_points"] = [{"type": "gap", "severity": "critical", "description": "Totally broken"}]
        result = _template_generate_evaluation(maria, sample_exploration)
        assert result["scores"]["goal_achievement"] <= 3
        assert result["scores"]["overall"] <= 4
        assert result["verdict"]["would_pay"] is False
        assert result["verdict"]["retention_risk"] == "high"

    def test_narrative_references_persona_industry(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        all_narrative = " ".join(result["narrative"].values()).lower()
        assert "legal" in all_narrative, "Narrative should reference persona's industry"

    def test_fear_motivated_objection(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        assert "wrong information" in result["narrative"]["objection"].lower() or \
               "liability" in result["narrative"]["objection"].lower() or \
               "incorrect" in result["narrative"]["objection"].lower()

    def test_unmet_needs_extracted(self, maria, sample_exploration):
        result = _template_generate_evaluation(maria, sample_exploration)
        assert len(result["unmet_needs"]) > 0
        for need in result["unmet_needs"]:
            assert "need" in need
            assert "pain_theme" in need
            assert "severity" in need
            assert "persona_quote" in need

    def test_team_persona_different_scores(self, rachel, sample_exploration):
        # Rachel has different voice (moderate skepticism, efficiency motivation)
        result = _template_generate_evaluation(rachel, sample_exploration)
        # Efficiency-motivated objection should mention ROI or cost
        objection = result["narrative"]["objection"].lower()
        assert "roi" in objection or "$" in objection or "income" in objection or "month" in objection
