"""Backlog contract — append-only JSONL event log with markdown rendering."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BacklogItem:
    id: str
    title: str
    description: str = ""
    score: float = 0.0
    finding_id: str = ""
    personas: list[str] = field(default_factory=list)
    pain_themes: list[str] = field(default_factory=list)
    effort: str = "medium"  # trivial, small, medium, large, epic
    status: str = "open"  # open, in_progress, resolved, deprioritized
    acceptance_criteria: list[str] = field(default_factory=list)
    persona_quotes: list[dict[str, str]] = field(default_factory=list)
    type: str = "enhancement"  # new_feature, enhancement, fix, ux_improvement

    # Scoring breakdown
    coverage_score: float = 0.0
    pain_score: float = 0.0
    revenue_score: float = 0.0
    effort_score: float = 0.0


@dataclass
class BacklogEvent:
    ts: str
    type: str  # item_added, score_updated, status_changed
    data: dict = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(path: Path, event_type: str, data: dict) -> None:
    """Append a single event to the JSONL log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": _now_iso(), "type": event_type, **data}
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")


def add_item(path: Path, item: BacklogItem) -> None:
    """Append an item_added event."""
    append_event(path, "item_added", {"item": _item_to_dict(item)})


def update_score(path: Path, item_id: str, prev_score: float, new_score: float, reason: str = "") -> None:
    """Append a score_updated event."""
    append_event(path, "score_updated", {
        "item_id": item_id,
        "prev_score": prev_score,
        "new_score": new_score,
        "reason": reason,
    })


def change_status(path: Path, item_id: str, prev_status: str, new_status: str, by: str = "system", note: str = "") -> None:
    """Append a status_changed event."""
    append_event(path, "status_changed", {
        "item_id": item_id,
        "prev_status": prev_status,
        "new_status": new_status,
        "by": by,
        "note": note,
    })


def load_events(path: Path) -> list[BacklogEvent]:
    """Load all events from the JSONL log."""
    if not path.exists():
        return []
    events = []
    for line in path.read_text().strip().split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                events.append(BacklogEvent(
                    ts=data.get("ts", ""),
                    type=data.get("type", ""),
                    data=data,
                ))
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSONL line: %s", line[:100])
    return events


def materialize_backlog(path: Path) -> list[BacklogItem]:
    """Replay events to produce the current backlog state.

    Applies events in order: item_added creates items, score_updated
    changes scores, status_changed changes status. Returns the final
    state of all items.
    """
    items: dict[str, BacklogItem] = {}

    for event in load_events(path):
        if event.type == "item_added":
            item_data = event.data.get("item", {})
            item = _dict_to_item(item_data)
            items[item.id] = item

        elif event.type == "score_updated":
            item_id = event.data.get("item_id", "")
            if item_id in items:
                items[item_id].score = event.data.get("new_score", items[item_id].score)

        elif event.type == "status_changed":
            item_id = event.data.get("item_id", "")
            if item_id in items:
                items[item_id].status = event.data.get("new_status", items[item_id].status)

    # Sort by score descending
    return sorted(items.values(), key=lambda x: x.score, reverse=True)


def render_backlog_markdown(path: Path) -> str:
    """Generate human-readable markdown from the JSONL backlog."""
    items = materialize_backlog(path)
    if not items:
        return "# Backlog\n\nNo items yet.\n"

    lines = [
        "# Backlog",
        "",
        f"*Generated from backlog.jsonl — {len(items)} items*",
        "",
        "| Rank | Score | Title | Effort | Status | Personas | Themes |",
        "|------|-------|-------|--------|--------|----------|--------|",
    ]

    for i, item in enumerate(items, 1):
        personas = ", ".join(item.personas[:3])
        if len(item.personas) > 3:
            personas += f" +{len(item.personas) - 3}"
        themes = ", ".join(item.pain_themes[:2])
        lines.append(
            f"| {i} | {item.score:.0f} | {item.title} | {item.effort} "
            f"| {item.status} | {personas} | {themes} |"
        )

    # Quick wins section
    quick_wins = [i for i in items if i.score > 60 and i.effort in ("trivial", "small") and i.status == "open"]
    if quick_wins:
        lines.extend(["", "## Quick Wins", ""])
        for item in quick_wins:
            lines.append(f"- **{item.title}** (score: {item.score:.0f}) — {item.description}")

    # High-value items with acceptance criteria
    top_items = [i for i in items if i.status == "open"][:5]
    if top_items:
        lines.extend(["", "## Top Priority Items", ""])
        for item in top_items:
            lines.append(f"### {item.title} (Score: {item.score:.0f})")
            lines.append(f"*{item.description}*")
            if item.acceptance_criteria:
                lines.append("")
                lines.append("**Acceptance Criteria:**")
                for ac in item.acceptance_criteria:
                    lines.append(f"- [ ] {ac}")
            if item.persona_quotes:
                lines.append("")
                lines.append("**Persona Voices:**")
                for pq in item.persona_quotes:
                    lines.append(f'> "{pq.get("quote", "")}" — {pq.get("persona", "")}')
            lines.append("")

    return "\n".join(lines) + "\n"


def save_backlog_markdown(jsonl_path: Path, md_path: Path) -> None:
    """Generate and save the human-readable backlog markdown."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_backlog_markdown(jsonl_path))


def _item_to_dict(item: BacklogItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "score": item.score,
        "finding_id": item.finding_id,
        "personas": item.personas,
        "pain_themes": item.pain_themes,
        "effort": item.effort,
        "status": item.status,
        "acceptance_criteria": item.acceptance_criteria,
        "persona_quotes": item.persona_quotes,
        "type": item.type,
        "coverage_score": item.coverage_score,
        "pain_score": item.pain_score,
        "revenue_score": item.revenue_score,
        "effort_score": item.effort_score,
    }


def _dict_to_item(data: dict) -> BacklogItem:
    return BacklogItem(
        id=data.get("id", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        score=data.get("score", 0.0),
        finding_id=data.get("finding_id", ""),
        personas=data.get("personas", []),
        pain_themes=data.get("pain_themes", []),
        effort=data.get("effort", "medium"),
        status=data.get("status", "open"),
        acceptance_criteria=data.get("acceptance_criteria", []),
        persona_quotes=data.get("persona_quotes", []),
        type=data.get("type", "enhancement"),
        coverage_score=data.get("coverage_score", 0.0),
        pain_score=data.get("pain_score", 0.0),
        revenue_score=data.get("revenue_score", 0.0),
        effort_score=data.get("effort_score", 0.0),
    )
