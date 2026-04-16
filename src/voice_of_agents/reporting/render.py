"""Markdown rendering utilities for YAML/JSONL data."""

from __future__ import annotations

from pathlib import Path

from voice_of_agents.contracts.backlog import render_backlog_markdown


def render_backlog(jsonl_path: Path) -> str:
    """Render the current backlog as markdown."""
    return render_backlog_markdown(jsonl_path)
