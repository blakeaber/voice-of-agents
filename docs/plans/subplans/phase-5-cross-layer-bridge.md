# Phase 5: Cross-Layer Bridge

## Goal
Add the integration layer that makes the tool a coherent end-to-end system: `eval/phase2_explore.py` reads objectives from `PersonaWorkflowMapping.goals` when available, and `voa bridge sync-gaps` converts gap analysis findings into `backlog.jsonl` entries.

## Context
After Phase 4, both layers share the canonical `Persona` model. The bridge makes the design→eval handoff explicit: personas designed with Pro workflows now drive the eval exploration directly, and gap-analysis findings from the design layer can flow into the same scored backlog as runtime evaluation findings.

## Dependencies
Phase 4 must be COMPLETE: canonical Persona model in use, contracts/ deleted, data migrated.

## Scope

### Files to Create
- `src/voice_of_agents/eval/bridge.py` — `sync_gap_analysis_to_backlog`, `bridge_status`
- `src/voice_of_agents/cli/bridge_cli.py` — `voa bridge *` Click commands

### Files to Modify
- `src/voice_of_agents/eval/phase2_explore.py` — accept optional `PersonaWorkflowMapping`; map goals → objectives
- `src/voice_of_agents/cli/eval_cli.py` — in `phase2` command, try to load workflow mapping for each persona
- `src/voice_of_agents/cli/main.py` — add `bridge_cli` as `bridge` subgroup

### Explicitly Out of Scope
- Test coverage (Phase 6)
- Changing any existing phase logic for personas without mappings (must work identically)

## Implementation Notes

### `eval/phase2_explore.py` update
The `explore_personas()` function gains an optional `workflow_mapping` parameter per persona:

```python
# In explore_personas() or in the per-persona loop:
from voice_of_agents.design.io import load_workflow_mapping
from pathlib import Path

def _load_mapping_for_persona(persona, workflows_dir: Path):
    """Try to find a PWM-*.yaml for this persona."""
    candidates = list(workflows_dir.glob(f"PWM-{persona.id:02d}-*.yaml"))
    if candidates:
        try:
            from voice_of_agents.design.io import load_workflow_mapping
            return load_workflow_mapping(candidates[0])
        except Exception:
            return None
    return None

def _goals_to_objectives(goals: list) -> list:
    """Convert design-layer Goals to the objective dict shape phase2 expects."""
    objectives = []
    for g in goals:
        objectives.append({
            "goal": g.title,
            "trigger": g.trigger,
            "success_definition": g.success_statement,
            "efficiency_baseline": g.value_metrics.time_saved if g.value_metrics else "",
            "target_efficiency": "",
        })
    return objectives
```

In `phase2_explore.py`, after loading each persona, attempt to load its workflow mapping and use those goals as objectives. If no mapping exists, fall back to empty objectives list (current behavior).

### `eval/bridge.py`
```python
from pathlib import Path
from voice_of_agents.design.gap_analysis import GapAnalysisReport
from voice_of_agents.core.backlog import BacklogItem, add_item
from voice_of_agents.eval.config import VoAConfig

def sync_gap_analysis_to_backlog(report: GapAnalysisReport, config: VoAConfig) -> int:
    """Write design-layer BacklogItems from gap analysis into backlog.jsonl.
    Returns count of items written.
    """
    backlog_path = config.backlog_jsonl_path
    existing = {item.id for item in _load_existing_ids(backlog_path)}
    written = 0
    for item in report.feature_recommendations:
        if item.id not in existing:
            add_item(backlog_path, item)
            written += 1
    return written

def _load_existing_ids(path: Path) -> list:
    from voice_of_agents.core.backlog import materialize_backlog
    if not path.exists():
        return []
    return materialize_backlog(path)

def bridge_status(config: VoAConfig) -> dict:
    """Return per-persona summary of design vs eval coverage."""
    from voice_of_agents.core.io import load_personas_dir
    from voice_of_agents.design.io import load_workflow_mappings_dir
    personas_dir = config.personas_path
    workflows_dir = config.data_path / "workflows"
    results_dir = config.results_path

    personas = load_personas_dir(personas_dir) if personas_dir.exists() else []
    mappings = {m.persona_id: m for m in (load_workflow_mappings_dir(workflows_dir)
                                           if workflows_dir.exists() else [])}

    status = []
    for p in personas:
        has_mapping = p.id in mappings
        has_results = any(results_dir.glob(f"{p.slug}*/")) if results_dir.exists() else False
        status.append({
            "id": p.id,
            "name": p.name,
            "has_design_mapping": has_mapping,
            "has_eval_results": has_results,
            "goals": len(mappings[p.id].goals) if has_mapping else 0,
        })
    return {"personas": status}
```

### `cli/bridge_cli.py`
```python
import click
from rich.table import Table
from rich.console import Console

@click.group("bridge")
def bridge_cli():
    """Cross-layer integration between design and eval."""
    pass

@bridge_cli.command("status")
def bridge_status_cmd():
    """Show per-persona design vs eval coverage."""
    from voice_of_agents.eval.bridge import bridge_status
    from voice_of_agents.eval.config import VoAConfig
    config = VoAConfig.load()
    result = bridge_status(config)
    console = Console()
    table = Table(title="Bridge Status")
    table.add_column("ID"); table.add_column("Name"); table.add_column("Design Mapping")
    table.add_column("Eval Results"); table.add_column("Goals")
    for p in result["personas"]:
        table.add_row(str(p["id"]), p["name"],
                      "✓" if p["has_design_mapping"] else "—",
                      "✓" if p["has_eval_results"] else "—",
                      str(p["goals"]))
    console.print(table)

@bridge_cli.command("sync-gaps")
@click.option("--dir", "project_dir", default=".", help="Design project directory")
def sync_gaps_cmd(project_dir):
    """Sync gap analysis findings into backlog.jsonl."""
    from voice_of_agents.design.gap_analysis import GapAnalyzer
    from voice_of_agents.design.io import load_workflow_mappings_dir
    from voice_of_agents.core.io import load_capability_registry
    from voice_of_agents.eval.bridge import sync_gap_analysis_to_backlog
    from voice_of_agents.eval.config import VoAConfig
    from pathlib import Path
    p = Path(project_dir)
    registry = load_capability_registry(p / "capabilities.yaml")
    mappings = load_workflow_mappings_dir(p / "workflows")
    analyzer = GapAnalyzer(registry)
    report = analyzer.analyze(mappings)
    config = VoAConfig.load()
    n = sync_gap_analysis_to_backlog(report, config)
    click.echo(f"Synced {n} new backlog items from gap analysis.")
```

### `cli/main.py` update
```python
from voice_of_agents.cli.bridge_cli import bridge_cli
cli.add_command(bridge_cli, name="bridge")
```

### `VoAConfig` additions needed
`config.data_path` / `config.personas_path` / `config.results_path` / `config.backlog_jsonl_path` — these should already exist from the moved `eval/config.py`. Verify they're accessible.

## Acceptance Criteria
- [x] `src/voice_of_agents/eval/bridge.py` exists with `sync_gap_analysis_to_backlog` and `bridge_status`
- [x] `src/voice_of_agents/cli/bridge_cli.py` exists with `bridge_cli` group
- [x] `voa bridge --help` shows `status` and `sync-gaps` subcommands
- [x] `voa bridge status` runs without error (shows table, even if empty)
- [x] `voa eval phase2 --all` still works when NO workflow mappings exist (fall-back to empty objectives)
- [x] `voa eval phase2 --all` uses workflow goals when `data/workflows/PWM-*.yaml` files exist
- [x] `python -c "from voice_of_agents.eval.bridge import bridge_status; print('ok')"` succeeds
- [x] `python -c "from voice_of_agents.cli.bridge_cli import bridge_cli; print('ok')"` succeeds

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
pip install -e . -q
python -c "from voice_of_agents.eval.bridge import bridge_status, sync_gap_analysis_to_backlog; print('ok')"
python -c "from voice_of_agents.cli.bridge_cli import bridge_cli; print('ok')"
voa --help       # should show design, eval, bridge
voa bridge --help
voa bridge status
# Test that phase2 still works without mappings (no ImportError):
voa eval phase2 --all 2>&1 | grep -i "error" | grep -iv "connection" | head -5
```

## Status
COMPLETE
