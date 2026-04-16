"""Integration tests: Backlog JSONL append/replay roundtrip."""

import pytest

from voice_of_agents.contracts.backlog import (
    BacklogItem, add_item, update_score, change_status,
    load_events, materialize_backlog, save_backlog_markdown,
)


class TestBacklogIO:
    def test_append_and_load_events(self, tmp_data_dir):
        path = tmp_data_dir / "backlog.jsonl"
        item = BacklogItem(id="B-001", title="Test item", score=50.0, status="open")
        add_item(path, item)
        events = load_events(path)
        assert len(events) == 1
        assert events[0].type == "item_added"

    def test_multiple_events_in_order(self, tmp_data_dir):
        path = tmp_data_dir / "backlog.jsonl"
        add_item(path, BacklogItem(id="B-001", title="First", score=50.0))
        add_item(path, BacklogItem(id="B-002", title="Second", score=70.0))
        update_score(path, "B-001", 50.0, 60.0, "Updated")
        events = load_events(path)
        assert len(events) == 3
        assert events[0].type == "item_added"
        assert events[1].type == "item_added"
        assert events[2].type == "score_updated"

    def test_materialize_applies_updates(self, tmp_data_dir):
        path = tmp_data_dir / "backlog.jsonl"
        add_item(path, BacklogItem(id="B-001", title="Item", score=50.0))
        update_score(path, "B-001", 50.0, 75.0, "Re-scored")
        change_status(path, "B-001", "open", "resolved", by="human", note="Fixed")
        items = materialize_backlog(path)
        assert len(items) == 1
        assert items[0].score == 75.0
        assert items[0].status == "resolved"

    def test_materialize_sorts_by_score(self, tmp_data_dir):
        path = tmp_data_dir / "backlog.jsonl"
        add_item(path, BacklogItem(id="B-001", title="Low", score=30.0))
        add_item(path, BacklogItem(id="B-002", title="High", score=80.0))
        add_item(path, BacklogItem(id="B-003", title="Mid", score=55.0))
        items = materialize_backlog(path)
        assert [i.id for i in items] == ["B-002", "B-003", "B-001"]

    def test_save_backlog_markdown_creates_file(self, tmp_data_dir):
        jsonl = tmp_data_dir / "backlog.jsonl"
        md = tmp_data_dir / "backlog.md"
        add_item(jsonl, BacklogItem(id="B-001", title="Test", score=65.0, effort="small", status="open"))
        save_backlog_markdown(jsonl, md)
        assert md.exists()
        content = md.read_text()
        assert "# Backlog" in content
        assert "Test" in content
        assert "65" in content

    def test_empty_backlog_markdown(self, tmp_data_dir):
        jsonl = tmp_data_dir / "backlog.jsonl"
        md = tmp_data_dir / "backlog.md"
        # Don't add any items
        save_backlog_markdown(jsonl, md)
        content = md.read_text()
        assert "No items yet" in content
