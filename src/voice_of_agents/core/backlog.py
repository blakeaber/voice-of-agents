"""Unified BacklogItem with append-only JSONL event sourcing.

Items are never edited in-place; all mutations are new events replayed via
materialize_backlog() to produce current state. source field distinguishes origin:
eval (runtime), design (planning), or bridge (cross-layer integration).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BacklogItem(BaseModel):
    id: str
    title: str
    description: str = ""
    source: Literal["eval", "design", "bridge"]

    # Scoring (eval-originated items compute these; design-originated items may estimate)
    score: float = 0.0
    coverage_score: float = 0.0
    pain_score: float = 0.0
    revenue_score: float = 0.0
    effort_score: float = 0.0

    # Classification
    effort: Literal["trivial", "small", "medium", "large", "epic"] = "medium"
    status: Literal["open", "in_progress", "resolved", "deprioritized"] = "open"
    pain_themes: list[str] = Field(default_factory=list)

    # Evidence (eval layer)
    finding_id: Optional[str] = None
    personas: list[int] = Field(default_factory=list)
    persona_quotes: list[dict] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)

    # Design layer fields
    extends_capability: Optional[str] = None
    value_statement: Optional[str] = None


class BacklogEvent(BaseModel):
    ts: str
    type: Literal["item_added", "score_updated", "status_changed"]
    data: dict = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_raw(path: Path, event_type: str, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": _now_iso(), "type": event_type, **data}
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")


def add_item(path: Path, item: BacklogItem) -> None:
    _append_raw(path, "item_added", {"item": item.model_dump()})


def update_score(
    path: Path, item_id: str, prev_score: float, new_score: float, reason: str = ""
) -> None:
    _append_raw(
        path,
        "score_updated",
        {
            "item_id": item_id,
            "prev_score": prev_score,
            "new_score": new_score,
            "reason": reason,
        },
    )


def change_status(
    path: Path, item_id: str, prev_status: str, new_status: str, by: str = "system", note: str = ""
) -> None:
    _append_raw(
        path,
        "status_changed",
        {
            "item_id": item_id,
            "prev_status": prev_status,
            "new_status": new_status,
            "by": by,
            "note": note,
        },
    )


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text().strip().split("\n"):
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSONL line: %s", line[:100])
    return events


def materialize_backlog(path: Path) -> list[BacklogItem]:
    """Replay all JSONL events to produce current backlog state."""
    items: dict[str, dict] = {}

    for event in load_events(path):
        etype = event.get("type", "")

        if etype == "item_added":
            item_data = event.get("item", {})
            # Default source to "eval" for events written before unified model
            item_data.setdefault("source", "eval")
            # personas may be strings in legacy data; coerce to ints where possible
            raw_personas = item_data.get("personas", [])
            coerced = []
            for p in raw_personas:
                try:
                    coerced.append(int(p) if not isinstance(p, int) else p)
                except (ValueError, TypeError):
                    pass  # drop non-convertible legacy string IDs
            item_data["personas"] = coerced
            items[item_data["id"]] = item_data

        elif etype == "score_updated":
            item_id = event.get("item_id", "")
            if item_id in items:
                items[item_id]["score"] = event.get("new_score", items[item_id].get("score", 0.0))

        elif etype == "status_changed":
            item_id = event.get("item_id", "")
            if item_id in items:
                items[item_id]["status"] = event.get(
                    "new_status", items[item_id].get("status", "open")
                )

    result = []
    for data in items.values():
        try:
            result.append(BacklogItem(**data))
        except Exception as e:
            logger.warning("Skipping malformed backlog item %s: %s", data.get("id"), e)
    return sorted(result, key=lambda x: x.score, reverse=True)


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
        "| Rank | Score | Title | Effort | Status | Source | Personas | Themes |",
        "|------|-------|-------|--------|--------|--------|----------|--------|",
    ]

    for i, item in enumerate(items, 1):
        personas = ", ".join(str(p) for p in item.personas[:3])
        if len(item.personas) > 3:
            personas += f" +{len(item.personas) - 3}"
        themes = ", ".join(item.pain_themes[:2])
        lines.append(
            f"| {i} | {item.score:.0f} | {item.title} | {item.effort} "
            f"| {item.status} | {item.source} | {personas} | {themes} |"
        )

    quick_wins = [
        i for i in items if i.score > 60 and i.effort in ("trivial", "small") and i.status == "open"
    ]
    if quick_wins:
        lines.extend(["", "## Quick Wins", ""])
        for item in quick_wins:
            lines.append(f"- **{item.title}** (score: {item.score:.0f}) — {item.description}")

    top_items = [i for i in items if i.status == "open"][:5]
    if top_items:
        lines.extend(["", "## Top Priority Items", ""])
        for item in top_items:
            lines.append(f"### {item.title} (Score: {item.score:.0f})")
            lines.append(f"*{item.description}*")
            if item.value_statement:
                lines.append(f"> {item.value_statement}")
            if item.extends_capability:
                lines.append(f"*Extends: {item.extends_capability}*")
            if item.acceptance_criteria:
                lines.extend(["", "**Acceptance Criteria:**"])
                for ac in item.acceptance_criteria:
                    lines.append(f"- [ ] {ac}")
            if item.persona_quotes:
                lines.extend(["", "**Persona Voices:**"])
                for pq in item.persona_quotes:
                    lines.append(f'> "{pq.get("quote", pq)}" — {pq.get("persona", "")}')
            lines.append("")

    return "\n".join(lines) + "\n"


def save_backlog_markdown(jsonl_path: Path, md_path: Path) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_backlog_markdown(jsonl_path))
