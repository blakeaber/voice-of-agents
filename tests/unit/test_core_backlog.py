"""Unit tests for core/backlog.py — BacklogItem, event sourcing, materialize_backlog."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from voice_of_agents.core.backlog import (
    BacklogItem,
    add_item,
    change_status,
    materialize_backlog,
    render_backlog_markdown,
    update_score,
)


def _item(**kwargs) -> BacklogItem:
    defaults = dict(id="B-001", title="Fix empty state", description="Add helpful copy", source="eval")
    defaults.update(kwargs)
    return BacklogItem(**defaults)


class TestBacklogItem:
    def test_basic_creation(self):
        b = _item()
        assert b.id == "B-001"
        assert b.source == "eval"

    def test_source_required(self):
        with pytest.raises(ValidationError):
            BacklogItem(id="B-001", title="T", description="D")

    def test_all_source_values(self):
        for source in ("eval", "design", "bridge"):
            b = _item(source=source)
            assert b.source == source

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            _item(source="manual")

    def test_default_score_zero(self):
        assert _item().score == 0.0

    def test_default_status_open(self):
        assert _item().status == "open"

    def test_design_layer_fields(self):
        b = _item(source="design", extends_capability="CAP-LEARN-SEARCH",
                  value_statement="I need to find past work instantly.")
        assert b.extends_capability == "CAP-LEARN-SEARCH"
        assert b.value_statement == "I need to find past work instantly."

    def test_eval_layer_fields(self):
        b = _item(personas=[1, 2, 3], finding_id="F-001",
                  acceptance_criteria=["Returns results in <2s"])
        assert b.personas == [1, 2, 3]
        assert b.finding_id == "F-001"

    def test_invalid_effort(self):
        with pytest.raises(ValidationError):
            _item(effort="enormous")

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            _item(status="wontfix")


class TestJSONLEventSourcing:
    def test_add_and_materialize(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        item = _item(id="B-001", score=75.0)
        add_item(path, item)
        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].id == "B-001"
        assert result[0].score == 75.0

    def test_materialize_empty(self, tmp_path):
        assert materialize_backlog(tmp_path / "backlog.jsonl") == []

    def test_update_score(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(id="B-001", score=50.0))
        update_score(path, "B-001", 50.0, 80.0, reason="More personas affected")
        result = materialize_backlog(path)
        assert result[0].score == 80.0

    def test_change_status(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(id="B-001"))
        change_status(path, "B-001", "open", "in_progress", by="dev", note="started")
        result = materialize_backlog(path)
        assert result[0].status == "in_progress"

    def test_multiple_items_sorted_by_score(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(id="B-001", score=30.0))
        add_item(path, _item(id="B-002", score=90.0))
        add_item(path, _item(id="B-003", score=60.0))
        result = materialize_backlog(path)
        assert [r.id for r in result] == ["B-002", "B-003", "B-001"]

    def test_score_update_accumulates(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(id="B-001", score=50.0))
        update_score(path, "B-001", 50.0, 70.0, reason="first update")
        update_score(path, "B-001", 70.0, 85.0, reason="second update")
        result = materialize_backlog(path)
        assert result[0].score == 85.0

    def test_source_preserved_in_roundtrip(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(source="design", extends_capability="CAP-LEARN-SEARCH"))
        result = materialize_backlog(path)
        assert result[0].source == "design"
        assert result[0].extends_capability == "CAP-LEARN-SEARCH"

    def test_legacy_events_default_source_eval(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        # Write a legacy-format event without 'source' field
        legacy_event = {
            "ts": "2026-01-01T00:00:00Z",
            "type": "item_added",
            "item": {"id": "B-999", "title": "Legacy", "description": "Old item",
                     "score": 40.0, "effort": "medium", "status": "open",
                     "pain_themes": [], "personas": [], "persona_quotes": [],
                     "acceptance_criteria": [], "finding_id": None,
                     "coverage_score": 0.0, "pain_score": 0.0,
                     "revenue_score": 0.0, "effort_score": 0.0}
        }
        with open(path, "w") as f:
            f.write(json.dumps(legacy_event) + "\n")
        result = materialize_backlog(path)
        assert len(result) == 1
        assert result[0].source == "eval"

    def test_render_markdown(self, tmp_path):
        path = tmp_path / "backlog.jsonl"
        add_item(path, _item(id="B-001", score=80.0, source="eval"))
        add_item(path, _item(id="B-002", score=90.0, source="design",
                              extends_capability="CAP-LEARN", value_statement="Need this."))
        md = render_backlog_markdown(path)
        assert "# Backlog" in md
        assert "B-001" in md or "Fix empty state" in md
        assert "design" in md
