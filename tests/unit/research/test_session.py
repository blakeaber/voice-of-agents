"""Tests for research/session.py — ResearchSession state, persistence, and summary export."""

import tempfile
from pathlib import Path


from voice_of_agents.research.models import ProductResearchInput
from voice_of_agents.research.session import ResearchSession


def _minimal_input() -> ProductResearchInput:
    return ProductResearchInput(
        question="Do abandoners quit because X?",
        scope="US, 2024",
        slug="test-session",
        product_context="A test product",
    )


class TestResearchSessionCreate:
    def test_creates_with_correct_slug(self):
        session = ResearchSession.create(_minimal_input())
        assert session.slug == "test-session"

    def test_creates_unique_session_id(self):
        s1 = ResearchSession.create(_minimal_input())
        s2 = ResearchSession.create(_minimal_input())
        assert s1.session_id != s2.session_id

    def test_no_stages_completed_initially(self):
        session = ResearchSession.create(_minimal_input())
        assert session.stages_completed == []

    def test_no_outputs_initially(self):
        session = ResearchSession.create(_minimal_input())
        assert session.product_research_output is None
        assert session.persona_research_output is None
        assert session.workflow_research_output is None
        assert session.journey_redesign_output is None


class TestResearchSessionStageTracking:
    def test_mark_stage_complete(self):
        session = ResearchSession.create(_minimal_input())
        session.mark_stage_complete("product_research")
        assert session.is_stage_complete("product_research")

    def test_mark_same_stage_idempotent(self):
        session = ResearchSession.create(_minimal_input())
        session.mark_stage_complete("product_research")
        session.mark_stage_complete("product_research")
        assert session.stages_completed.count("product_research") == 1

    def test_is_stage_complete_false_by_default(self):
        session = ResearchSession.create(_minimal_input())
        assert not session.is_stage_complete("product_research")

    def test_log_error_appends(self):
        session = ResearchSession.create(_minimal_input())
        session.log_error("product_research", "API timeout")
        assert any("API timeout" in e for e in session.error_log)


class TestResearchSessionPersistence:
    def test_save_and_load_roundtrip(self):
        session = ResearchSession.create(_minimal_input())
        session.mark_stage_complete("product_research")

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = Path(f.name)

        try:
            session.save(path)
            loaded = ResearchSession.load(path)

            assert loaded.slug == session.slug
            assert loaded.session_id == session.session_id
            assert loaded.stages_completed == ["product_research"]
            assert loaded.product_research_input.question == session.product_research_input.question
        finally:
            path.unlink(missing_ok=True)

    def test_save_creates_parent_dirs(self):
        session = ResearchSession.create(_minimal_input())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "session.yaml"
            session.save(path)
            assert path.exists()
            loaded = ResearchSession.load(path)
            assert loaded.slug == "test-session"


class TestResearchSessionExportSummary:
    def test_export_includes_question(self):
        session = ResearchSession.create(_minimal_input())
        summary = session.export_summary()
        assert "Do abandoners quit because X?" in summary

    def test_export_includes_session_id(self):
        session = ResearchSession.create(_minimal_input())
        summary = session.export_summary()
        assert session.session_id in summary

    def test_export_shows_no_stages_complete(self):
        session = ResearchSession.create(_minimal_input())
        summary = session.export_summary()
        assert "none" in summary

    def test_export_shows_completed_stages(self):
        session = ResearchSession.create(_minimal_input())
        session.mark_stage_complete("product_research")
        summary = session.export_summary()
        assert "product_research" in summary

    def test_export_saves_to_file(self):
        session = ResearchSession.create(_minimal_input())
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = Path(f.name)
        try:
            session.export_summary(path)
            content = path.read_text()
            assert "Research Session" in content
        finally:
            path.unlink(missing_ok=True)

    def test_export_includes_error_log(self):
        session = ResearchSession.create(_minimal_input())
        session.log_error("product_research", "network failure")
        summary = session.export_summary()
        assert "network failure" in summary
