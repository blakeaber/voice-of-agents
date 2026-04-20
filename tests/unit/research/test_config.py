"""Tests for research/config.py — ResearchConfig construction and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from voice_of_agents.research.config import ResearchConfig
from voice_of_agents.research.models import Hypothesis


def _minimal_config_dict() -> dict:
    return {
        "research_question": "Do abandoners quit because cost-per-outcome is invisible?",
        "scope": "US knowledge workers, 2024",
        "slug": "test-run-abc",
        "product_context": "A knowledge management tool",
    }


class TestResearchConfigFromDict:
    def test_from_dict_minimal(self):
        config = ResearchConfig.from_dict(_minimal_config_dict())
        assert config.slug == "test-run-abc"
        assert config.subject_count == 12  # default

    def test_from_dict_with_overrides(self):
        data = {**_minimal_config_dict(), "subject_count": 14, "skip_topup": True}
        config = ResearchConfig.from_dict(data)
        assert config.subject_count == 14
        assert config.skip_topup is True

    def test_from_dict_missing_required_raises(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ResearchConfig.from_dict({"research_question": "Q?", "scope": "US"})


class TestResearchConfigFromFile:
    def test_from_yaml_file(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(_minimal_config_dict(), f)
            tmp_path = Path(f.name)

        config = ResearchConfig.from_file(tmp_path)
        assert config.research_question.startswith("Do abandoners")
        tmp_path.unlink()


class TestResearchConfigValidation:
    def test_valid_config_no_problems(self):
        config = ResearchConfig.from_dict(_minimal_config_dict())
        problems = config.validate_before_run()
        assert problems == []

    def test_long_slug_flagged(self):
        data = {**_minimal_config_dict(), "slug": "one-two-three-four-five-six-seven"}
        config = ResearchConfig.from_dict(data)
        problems = config.validate_before_run()
        assert any("slug" in p for p in problems)

    def test_market_string_flagged(self):
        data = {
            **_minimal_config_dict(),
            "research_question": "How can we reach US small business target market?",
        }
        config = ResearchConfig.from_dict(data)
        problems = config.validate_before_run()
        assert any("target-market" in p or "target market" in p.lower() for p in problems)

    def test_insufficient_hypotheses_flagged(self):
        data = {
            **_minimal_config_dict(),
            "hypotheses": [
                {"id": "H1", "statement": "s", "falsification_condition": "f"},
                {"id": "H2", "statement": "s", "falsification_condition": "f"},
            ],
        }
        config = ResearchConfig.from_dict(data)
        problems = config.validate_before_run()
        assert any("4" in p for p in problems)

    def test_hypothesis_missing_falsification_condition_flagged(self):
        data = {
            **_minimal_config_dict(),
            "hypotheses": [
                {"id": f"H{i+1}", "statement": "stmt", "falsification_condition": "f" if i < 3 else ""}
                for i in range(4)
            ],
        }
        config = ResearchConfig.from_dict(data)
        problems = config.validate_before_run()
        assert any("falsification_condition" in p for p in problems)


class TestResearchConfigToProductResearchInput:
    def test_converts_correctly(self):
        config = ResearchConfig.from_dict(_minimal_config_dict())
        inp = config.to_product_research_input()
        assert inp.question == config.research_question
        assert inp.scope == config.scope
        assert inp.slug == config.slug
        assert inp.product_context == config.product_context
        assert inp.subject_count == config.subject_count
        assert inp.ratified_hypotheses is None
