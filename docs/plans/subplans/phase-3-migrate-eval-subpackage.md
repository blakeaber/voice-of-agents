# Phase 3: Migrate Eval Subpackage

## Goal
Restructure Main's pipeline code into `src/voice_of_agents/eval/`, update all imports to use `core/` models, wire the unified `voa` CLI root, and delete all legacy source directories. No backward-compat aliases.

## Context
Main's code currently lives in flat directories: `contracts/`, `explorer/`, `phases/`, `reporting/`, and `cli.py`. This phase reorganizes them into `eval/` and establishes `cli/main.py` as the new root CLI that dispatches to `design_cli` and `eval_cli`. The old `voa phase2` flat commands cease to exist — no shimming.

## Dependencies
Phase 2 must be COMPLETE: `design_cli` must exist before `cli/main.py` can import it.

## Scope

### Files to Create
- `src/voice_of_agents/eval/config.py` — VoAConfig (moved from root)
- `src/voice_of_agents/eval/browser.py` — Playwright explorer (moved from explorer/)
- `src/voice_of_agents/eval/api.py` — TargetAPI HTTP client (moved from explorer/)
- `src/voice_of_agents/eval/seed.py` — seed_persona() (moved from explorer/)
- `src/voice_of_agents/eval/phase1_generate.py` — (moved from phases/)
- `src/voice_of_agents/eval/phase2_explore.py` — (moved from phases/)
- `src/voice_of_agents/eval/phase3_evaluate.py` — (moved from phases/)
- `src/voice_of_agents/eval/phase4_synthesize.py` — (moved from phases/)
- `src/voice_of_agents/eval/phase5_prioritize.py` — (moved from phases/)
- `src/voice_of_agents/eval/render.py` — backlog markdown rendering (moved from reporting/)
- `src/voice_of_agents/eval/diff.py` — run-over-run diff (moved from reporting/)
- `src/voice_of_agents/cli/eval_cli.py` — `voa eval *` Click commands
- `src/voice_of_agents/cli/main.py` — root `voa` group with design/eval/bridge subgroups

### Files to Delete (after successful move)
- `src/voice_of_agents/config.py`
- `src/voice_of_agents/contracts/backlog.py` — replaced by `core/backlog.py`
- `src/voice_of_agents/contracts/inventory.py` — replaced by `core/capability.py`
- `src/voice_of_agents/contracts/personas.py` — NOTE: keep until Phase 4
- `src/voice_of_agents/contracts/` — directory (after personas.py removal in Phase 4)
- `src/voice_of_agents/explorer/` — entire directory
- `src/voice_of_agents/phases/` — entire directory
- `src/voice_of_agents/reporting/` — entire directory
- `src/voice_of_agents/cli.py` — replaced by `cli/eval_cli.py`

### Explicitly Out of Scope
- Replacing `contracts/personas.py` with Pydantic Persona (that's Phase 4)
- Running data migration (Phase 4)
- `eval/migrate.py` and `eval/bridge.py` (Phases 4 and 5)

## Implementation Notes

### Import updates in moved files

Every moved file needs these import changes:

| Old import | New import |
|-----------|-----------|
| `from voice_of_agents.config import VoAConfig` | `from voice_of_agents.eval.config import VoAConfig` |
| `from voice_of_agents.contracts.backlog import BacklogItem, ...` | `from voice_of_agents.core.backlog import BacklogItem, ...` |
| `from voice_of_agents.contracts.inventory import Feature, FeatureInventory` | `from voice_of_agents.core.capability import Capability, CapabilityRegistry` |
| `from voice_of_agents.contracts.personas import Persona` | Keep as-is for Phase 3 — persona model swap is Phase 4 |
| `from voice_of_agents.explorer.browser import ...` | `from voice_of_agents.eval.browser import ...` |
| `from voice_of_agents.explorer.api import ...` | `from voice_of_agents.eval.api import ...` |
| `from voice_of_agents.explorer.seed import ...` | `from voice_of_agents.eval.seed import ...` |
| `from voice_of_agents.phases.phase2_explore import ...` | `from voice_of_agents.eval.phase2_explore import ...` |
| (etc. for all phases) | |
| `from voice_of_agents.reporting.render import ...` | `from voice_of_agents.eval.render import ...` |
| `from voice_of_agents.reporting.diff import ...` | `from voice_of_agents.eval.diff import ...` |

**Important:** `contracts/personas.py` is intentionally NOT changed in this phase. The eval modules still import `Persona` from the legacy location until Phase 4.

### `eval/render.py` updates
The markdown templates for backlog rendering should display the new `source` and `value_statement` fields from `BacklogItem` when present:
```python
# In the table row: add source column
# In the detail section: if item.value_statement, render it
# if item.extends_capability, show which capability it extends
```

### `cli/eval_cli.py`
Copy all commands from `src/voice_of_agents/cli.py`. Rename the Click group to `eval_cli`. Key command renames:
- `voa inventory` → `voa eval capabilities` (points at `CapabilityRegistry.load()`)
- All other commands keep their names under the `eval` namespace

### `cli/main.py`
```python
import click
from voice_of_agents.cli.design_cli import design_cli
from voice_of_agents.cli.eval_cli import eval_cli

@click.group()
def cli():
    """Voice of Agents — unified persona research pipeline."""
    pass

cli.add_command(design_cli, name="design")
cli.add_command(eval_cli, name="eval")
# bridge_cli added in Phase 5
```

### `pyproject.toml` entry point update
```toml
[project.scripts]
voa = "voice_of_agents.cli.main:cli"
```

### Deletion order
1. Delete `src/voice_of_agents/contracts/backlog.py`
2. Delete `src/voice_of_agents/contracts/inventory.py`
3. (Keep `contracts/personas.py` — Phase 4 handles it)
4. Delete `src/voice_of_agents/explorer/` directory
5. Delete `src/voice_of_agents/phases/` directory
6. Delete `src/voice_of_agents/reporting/` directory
7. Delete `src/voice_of_agents/cli.py`
8. Delete `src/voice_of_agents/config.py`

## Acceptance Criteria
- [x] `src/voice_of_agents/eval/config.py` exists
- [x] `src/voice_of_agents/eval/phase2_explore.py` exists
- [x] `src/voice_of_agents/eval/phase3_evaluate.py` exists
- [x] `src/voice_of_agents/eval/phase5_prioritize.py` exists
- [x] `src/voice_of_agents/cli/eval_cli.py` exists with `eval_cli` Click group
- [x] `src/voice_of_agents/cli/main.py` exists with `cli` group containing `design` and `eval` subgroups
- [x] `pyproject.toml` entry point is `voice_of_agents.cli.main:cli`
- [x] `src/voice_of_agents/explorer/` directory does NOT exist
- [x] `src/voice_of_agents/phases/` directory does NOT exist
- [x] `src/voice_of_agents/reporting/` directory does NOT exist
- [x] `src/voice_of_agents/cli.py` does NOT exist (cli/ package __init__.py re-exports)
- [x] `python -c "from voice_of_agents.cli.main import cli; print('ok')"` succeeds
- [x] `voa --help` shows `design` and `eval` subgroups
- [x] `voa eval status` runs without ImportError — shows 35 personas loaded
- [x] `voa design --help` shows persona/workflow/analyze subgroups

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
pip install -e . -q
python -c "from voice_of_agents.cli.main import cli; print('ok')"
voa --help
voa eval --help
voa design --help
voa eval status 2>&1 | head -5  # may show "no personas" — OK, not ImportError
ls src/voice_of_agents/explorer/ 2>/dev/null && echo "FAIL" || echo "PASS: explorer deleted"
ls src/voice_of_agents/phases/ 2>/dev/null && echo "FAIL" || echo "PASS: phases deleted"
ls src/voice_of_agents/reporting/ 2>/dev/null && echo "FAIL" || echo "PASS: reporting deleted"
ls src/voice_of_agents/cli.py 2>/dev/null && echo "FAIL" || echo "PASS: cli.py deleted"
```

## Status
COMPLETE
