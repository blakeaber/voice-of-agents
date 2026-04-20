"""Tests for research/quick.py — QuickResearchResult and related models."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from voice_of_agents.research.quick import (
    QuickPersona,
    QuickResearchResult,
    _QUICK_SUBJECT_COUNT,
)


class TestQuickPersona:
    def test_creates_with_required_fields(self):
        persona = QuickPersona(
            uxw_id="UXW-01",
            archetype="The Overwhelmed Manager",
            top_concern="too many tools, not enough time to learn them",
            would_pay_if="it saves me more than 2 hours per week",
        )
        assert persona.uxw_id == "UXW-01"
        assert persona.archetype == "The Overwhelmed Manager"


class TestQuickResearchResult:
    def _make_session(self):
        from voice_of_agents.research.models import ProductResearchInput
        from voice_of_agents.research.session import ResearchSession

        return ResearchSession.create(
            ProductResearchInput(
                question="Do users abandon because of X?",
                scope="US, 2024",
                slug="test-quick",
                product_context="test product",
            )
        )

    def test_creates_with_required_fields(self):
        session = self._make_session()
        result = QuickResearchResult(
            top_findings=["finding one", "finding two"],
            build_this_first="Build the onboarding flow first",
            churn_triggers=["if it breaks trust", "if it's slower than manual"],
            validate_with=["q1", "q2", "q3"],
            personas=[
                QuickPersona(
                    uxw_id="UXW-01",
                    archetype="The Skeptic",
                    top_concern="losing data",
                    would_pay_if="it has zero-failure guarantee",
                )
            ],
            session=session,
        )
        assert result.build_this_first == "Build the onboarding flow first"
        assert len(result.top_findings) == 2
        assert len(result.personas) == 1

    def test_session_is_accessible(self):
        session = self._make_session()
        result = QuickResearchResult(
            top_findings=["x"],
            build_this_first="x",
            churn_triggers=["x"],
            validate_with=["x", "y", "z"],
            personas=[],
            session=session,
        )
        assert result.session.slug == "test-quick"


class TestQuickSubjectCount:
    def test_quick_subject_count_is_low_for_speed(self):
        assert _QUICK_SUBJECT_COUNT <= 12


class TestTranslateToConfig:
    """Tests for _translate_to_config using mocked Claude responses."""

    @pytest.mark.asyncio
    async def test_translates_plain_english_to_config(self):
        from unittest.mock import AsyncMock, MagicMock
        from voice_of_agents.research.quick import _translate_to_config

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="""```yaml
research_question: "Do developers abandon AI tools because they break their flow?"
scope: "Senior developers at startups, 2024-2026"
slug: "dev-tool-abandonment"
product_context: "A coding assistant that helps write tests"
```""")
        ]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        config = await _translate_to_config(
            what="a coding assistant",
            who="senior developers",
            understand="why they abandon AI tools",
            client=mock_client,
            model="claude-opus-4-7",
        )

        assert config.slug == "dev-tool-abandonment"
        assert "abandon" in config.research_question.lower() or "flow" in config.research_question.lower()

    @pytest.mark.asyncio
    async def test_falls_back_gracefully_on_malformed_yaml(self):
        from unittest.mock import AsyncMock, MagicMock
        from voice_of_agents.research.quick import _translate_to_config

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="not yaml at all")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception):
            await _translate_to_config(
                what="a tool",
                who="developers",
                understand="why they leave",
                client=mock_client,
                model="claude-opus-4-7",
            )
