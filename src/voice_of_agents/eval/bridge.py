"""Cross-layer bridge: syncs design-layer gap analysis into the eval backlog."""

from __future__ import annotations

from pathlib import Path

from voice_of_agents.core.backlog import add_item, materialize_backlog
from voice_of_agents.eval.config import VoAConfig


def _load_existing_ids(path: Path) -> list:
    if not path.exists():
        return []
    return materialize_backlog(path)


def sync_gap_analysis_to_backlog(report, config: VoAConfig) -> int:
    """Write design-layer BacklogItems from gap analysis into backlog.jsonl.

    Returns count of items written (skips items whose ID already exists).
    """
    backlog_path = config.backlog_jsonl_path
    existing_ids = {item.id for item in _load_existing_ids(backlog_path)}
    written = 0
    for item in report.feature_recommendations:
        if item.id not in existing_ids:
            add_item(backlog_path, item)
            written += 1
    return written


def bridge_status(config: VoAConfig) -> dict:
    """Return per-persona summary of design vs eval coverage."""
    from voice_of_agents.core.io import load_personas_dir
    from voice_of_agents.design.io import load_workflow_mappings_dir

    personas_dir = config.personas_path
    workflows_dir = config.workflows_path
    results_dir = config.results_path

    personas = load_personas_dir(personas_dir) if personas_dir.exists() else []
    raw_mappings = (
        load_workflow_mappings_dir(workflows_dir) if workflows_dir.exists() else []
    )
    mappings = {m.persona_id: m for m in raw_mappings}

    status = []
    for p in personas:
        has_mapping = p.id in mappings
        has_results = (
            bool(list(results_dir.glob(f"{p.slug}*/")))
            if results_dir.exists()
            else False
        )
        if not has_results and results_dir.exists():
            legacy_prefix = f"UXW-{p.id:02d}-"
            has_results = bool(list(results_dir.glob(f"{legacy_prefix}*/")))
        status.append(
            {
                "id": p.id,
                "name": p.name,
                "has_design_mapping": has_mapping,
                "has_eval_results": has_results,
                "goals": len(mappings[p.id].goals) if has_mapping else 0,
            }
        )
    return {"personas": status}
