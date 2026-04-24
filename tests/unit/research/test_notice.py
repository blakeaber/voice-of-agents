"""Tests for research/notice.py — synthetic data notice generation."""

import tempfile
from pathlib import Path


from voice_of_agents.research.notice import (
    generate_notice,
    write_notice,
)


class TestGenerateNotice:
    def test_generates_with_question(self):
        notice = generate_notice("Do users abandon because of X?")
        assert notice.research_question == "Do users abandon because of X?"

    def test_default_validation_questions_count(self):
        notice = generate_notice("Do users abandon because of X?")
        assert len(notice.validation_questions) == 3

    def test_custom_validation_questions(self):
        notice = generate_notice("question", validation_questions=["q1", "q2"])
        assert notice.validation_questions == ["q1", "q2"]


class TestSyntheticDataNoticeRender:
    def test_render_contains_what_it_is(self):
        notice = generate_notice("Do users quit because of friction?")
        rendered = notice.render()
        assert "Synthetic Data Notice" in rendered

    def test_render_contains_what_it_is_not(self):
        notice = generate_notice("Do users quit because of friction?")
        rendered = notice.render()
        assert "NOT" in rendered

    def test_render_contains_research_question(self):
        notice = generate_notice("Do users quit because of friction?")
        rendered = notice.render()
        assert "Do users quit because of friction?" in rendered

    def test_render_contains_validation_questions(self):
        notice = generate_notice("question", validation_questions=["ask this", "then this"])
        rendered = notice.render()
        assert "ask this" in rendered
        assert "then this" in rendered

    def test_render_uses_plain_english(self):
        notice = generate_notice("test question")
        rendered = notice.render()
        assert "hypothesis" in rendered.lower()


class TestWriteNotice:
    def test_writes_file_to_directory(self):
        notice = generate_notice("Do users abandon because of X?")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_notice(notice, Path(tmpdir))
            assert path.exists()
            assert path.name == "SYNTHETIC-DATA-NOTICE.md"

    def test_file_contains_notice_content(self):
        notice = generate_notice("Do users abandon because of X?")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_notice(notice, Path(tmpdir))
            content = path.read_text()
            assert "Synthetic Data Notice" in content

    def test_creates_directory_if_needed(self):
        notice = generate_notice("question")
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "nested" / "dir"
            path = write_notice(notice, nested)
            assert path.exists()


class TestSessionNoticeIntegration:
    def test_save_writes_notice_file(self):
        from voice_of_agents.research.models import ProductResearchInput
        from voice_of_agents.research.session import ResearchSession

        session = ResearchSession.create(
            ProductResearchInput(
                question="Do users abandon because of X?",
                scope="US, 2024",
                slug="test-notice",
                product_context="test product",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir) / "session.yaml"
            session.save(session_path)
            notice_path = Path(tmpdir) / "SYNTHETIC-DATA-NOTICE.md"
            assert notice_path.exists()

    def test_export_summary_contains_synthetic_warning(self):
        from voice_of_agents.research.models import ProductResearchInput
        from voice_of_agents.research.session import ResearchSession

        session = ResearchSession.create(
            ProductResearchInput(
                question="Do users abandon because of X?",
                scope="US, 2024",
                slug="test-summary-notice",
                product_context="test product",
            )
        )
        summary = session.export_summary()
        assert "Synthetic" in summary or "synthetic" in summary
