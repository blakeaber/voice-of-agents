"""Tests for backlog event replay."""

import json

from voice_of_agents.contracts.backlog import (
    BacklogItem,
    _dict_to_item,
    _item_to_dict,
    add_item,
    change_status,
    materialize_backlog,
    render_backlog_markdown,
    update_score,
)


class TestMaterializeBacklog:
    """materialize_backlog() replays events into current state."""

    def test_empty_file_returns_empty(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        # File doesn't exist
        assert materialize_backlog(path) == []

    def test_empty_existing_file_returns_empty(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        path.write_text("")
        assert materialize_backlog(path) == []

    def test_single_item_added(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        item = BacklogItem(id="B-001", title="First item", score=50.0)
        add_item(path, item)

        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].id == "B-001"
        assert result[0].title == "First item"
        assert result[0].score == 50.0

    def test_score_updated_changes_score(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        item = BacklogItem(id="B-001", title="Item", score=50.0)
        add_item(path, item)
        update_score(path, "B-001", prev_score=50.0, new_score=80.0, reason="Re-evaluated")

        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].score == 80.0

    def test_status_changed_changes_status(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        item = BacklogItem(id="B-001", title="Item", score=50.0, status="open")
        add_item(path, item)
        change_status(path, "B-001", prev_status="open", new_status="in_progress")

        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].status == "in_progress"

    def test_multiple_items_sorted_by_score_descending(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, BacklogItem(id="B-001", title="Low", score=30.0))
        add_item(path, BacklogItem(id="B-002", title="High", score=90.0))
        add_item(path, BacklogItem(id="B-003", title="Mid", score=60.0))

        result = materialize_backlog(path)
        assert len(result) == 3
        assert result[0].id == "B-002"
        assert result[1].id == "B-003"
        assert result[2].id == "B-001"
        assert result[0].score > result[1].score > result[2].score

    def test_score_update_on_nonexistent_item_is_ignored(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, BacklogItem(id="B-001", title="Item", score=50.0))
        update_score(path, "B-999", prev_score=0, new_score=100)

        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].score == 50.0


class TestRenderBacklogMarkdown:
    """render_backlog_markdown() produces valid output."""

    def test_empty_returns_no_items(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        md = render_backlog_markdown(path)
        assert "No items yet" in md

    def test_with_items_produces_markdown_table(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, BacklogItem(
            id="B-001", title="Bulk import", description="Import files",
            score=78.0, personas=["UXW-01", "UXW-20"],
            pain_themes=["A", "F"], effort="large", status="open",
        ))
        add_item(path, BacklogItem(
            id="B-002", title="Quick search", description="Fast lookup",
            score=65.0, effort="small", status="open",
        ))

        md = render_backlog_markdown(path)
        assert "# Backlog" in md
        assert "Bulk import" in md
        assert "Quick search" in md
        assert "| Rank |" in md
        # Items present in table
        assert "| 1 |" in md
        assert "| 2 |" in md

    def test_with_acceptance_criteria_renders_checklist(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, BacklogItem(
            id="B-001", title="Feature X", score=80.0, status="open",
            acceptance_criteria=["Criterion A", "Criterion B"],
        ))
        md = render_backlog_markdown(path)
        assert "- [ ] Criterion A" in md
        assert "- [ ] Criterion B" in md

    def test_with_persona_quotes_renders_blockquotes(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, BacklogItem(
            id="B-001", title="Feature X", score=80.0, status="open",
            persona_quotes=[{"persona": "UXW-01", "quote": "I need this badly"}],
        ))
        md = render_backlog_markdown(path)
        assert "I need this badly" in md
        assert "UXW-01" in md

    def test_conftest_backlog_item(self, tmp_path, sample_backlog_item):
        """Use the conftest fixture to verify it round-trips through markdown."""
        path = tmp_path / "backlog.jsonl"
        add_item(path, sample_backlog_item)
        md = render_backlog_markdown(path)
        assert sample_backlog_item.title in md
        assert "78" in md


class TestItemDictRoundtrip:
    """_item_to_dict / _dict_to_item roundtrip preserves all fields."""

    def test_roundtrip_simple_item(self):
        item = BacklogItem(id="B-001", title="Test", score=50.0)
        d = _item_to_dict(item)
        restored = _dict_to_item(d)
        assert restored.id == item.id
        assert restored.title == item.title
        assert restored.score == item.score
        assert restored.status == item.status
        assert restored.effort == item.effort

    def test_roundtrip_full_item(self, sample_backlog_item):
        d = _item_to_dict(sample_backlog_item)
        restored = _dict_to_item(d)

        assert restored.id == sample_backlog_item.id
        assert restored.title == sample_backlog_item.title
        assert restored.description == sample_backlog_item.description
        assert restored.score == sample_backlog_item.score
        assert restored.finding_id == sample_backlog_item.finding_id
        assert restored.personas == sample_backlog_item.personas
        assert restored.pain_themes == sample_backlog_item.pain_themes
        assert restored.effort == sample_backlog_item.effort
        assert restored.status == sample_backlog_item.status
        assert restored.acceptance_criteria == sample_backlog_item.acceptance_criteria
        assert restored.persona_quotes == sample_backlog_item.persona_quotes
        assert restored.type == sample_backlog_item.type
        assert restored.coverage_score == sample_backlog_item.coverage_score
        assert restored.pain_score == sample_backlog_item.pain_score
        assert restored.revenue_score == sample_backlog_item.revenue_score
        assert restored.effort_score == sample_backlog_item.effort_score

    def test_dict_contains_all_fields(self):
        item = BacklogItem(
            id="B-X", title="T", description="D", score=10.0,
            finding_id="F-1", personas=["P1"], pain_themes=["A"],
            effort="small", status="open",
            acceptance_criteria=["AC1"],
            persona_quotes=[{"persona": "P1", "quote": "Q"}],
            type="fix",
            coverage_score=1.0, pain_score=2.0,
            revenue_score=3.0, effort_score=4.0,
        )
        d = _item_to_dict(item)
        expected_keys = {
            "id", "title", "description", "score", "finding_id",
            "personas", "pain_themes", "effort", "status",
            "acceptance_criteria", "persona_quotes", "type",
            "coverage_score", "pain_score", "revenue_score", "effort_score",
        }
        assert set(d.keys()) == expected_keys
