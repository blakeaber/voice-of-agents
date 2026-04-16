# Phase 4: Data and Persona Model Migration

## Goal
Replace Main's `contracts/personas.py` dataclasses with the canonical Pydantic `Persona` from `core/`, write a data migration script for existing `UXW-*.yaml` files, migrate `feature-inventory.yaml` to `capabilities.yaml`, and delete the now-obsolete `contracts/` directory.

## Context
This is the highest-risk phase. The eval layer still imports `Persona` from the legacy `contracts/personas.py` dataclass as of Phase 3. This phase simultaneously: (1) writes `eval/migrate.py` to convert existing data files, (2) updates all eval code to use the canonical Pydantic model, (3) deletes the old model file, and (4) runs the migration on the actual `data/` directory.

## Dependencies
Phase 3 must be COMPLETE: all eval code must be in `eval/`, all legacy directories deleted, CLI wired.

## Scope

### Files to Create
- `src/voice_of_agents/eval/migrate.py` — migration script with `migrate_persona_yaml`, `migrate_objectives_to_workflow`, `migrate_feature_inventory`, `migrate_all`
- `tests/unit/test_eval_migrate.py` — unit tests using `sample_persona_legacy.yaml`
- `tests/fixtures/sample_persona_legacy.yaml` — a UXW-format persona fixture (Maria Gutierrez)

### Files to Modify
- `src/voice_of_agents/eval/config.py` — add `resolve_result_slug(persona)` helper
- `src/voice_of_agents/eval/phase2_explore.py` — load goals from PersonaWorkflowMapping; update Persona field access
- `src/voice_of_agents/eval/phase3_evaluate.py` — update all Persona field access; voice calibration uses `persona.voice.*` unconditionally
- `src/voice_of_agents/eval/phase4_synthesize.py` — update Persona field access
- `src/voice_of_agents/eval/phase5_prioritize.py` — update Persona field access; `persona.tier` is now an enum
- `src/voice_of_agents/eval/phase1_generate.py` — update Persona construction
- `src/voice_of_agents/eval/seed.py` — `_derive_goals()` uses `persona.pain_themes` instead of `persona.pain_points[].theme`
- `src/voice_of_agents/eval/browser.py` — update Persona field access
- `src/voice_of_agents/cli/eval_cli.py` — add `migrate` command; update Persona loading to use `core/io.py`
- `data/personas/` — migration writes `P-*.yaml` files here, backs up originals to `_legacy/`
- `data/capabilities.yaml` — created by migrating `data/feature-inventory.yaml`

### Files to Delete
- `src/voice_of_agents/contracts/personas.py`
- `src/voice_of_agents/contracts/` — directory (now empty)

### Explicitly Out of Scope
- Bridge layer (`eval/bridge.py`) — Phase 5
- Renaming existing `data/results/UXW-*/` directories (leave untouched)

## Implementation Notes

### `eval/migrate.py`

```python
from pathlib import Path
from typing import Optional
import yaml
import shutil
import re
from datetime import datetime

from voice_of_agents.core.persona import Persona, VoiceProfile, PersonaMetadata
from voice_of_agents.core.enums import ThemeCode, Intensity, Segment, Tier
from voice_of_agents.core.capability import Capability, CapabilityRegistry, TestResult
from voice_of_agents.core.io import save_persona, save_capability_registry

SEVERITY_TO_INTENSITY = {
    range(1, 5): "LOW",
    range(5, 7): "MEDIUM",
    range(7, 9): "HIGH",
    range(9, 11): "CRITICAL",
}

def _severity_to_intensity(severity: int) -> str:
    for r, intensity in SEVERITY_TO_INTENSITY.items():
        if severity in r:
            return intensity
    return "MEDIUM"

def migrate_persona_yaml(path: Path) -> dict:
    """Convert UXW-format YAML dict to canonical Persona dict."""
    with open(path) as f:
        data = yaml.safe_load(f)

    legacy_id = data.get("id", "")  # e.g. "UXW-01"
    # Parse integer from legacy ID
    id_int = int(re.search(r'\d+', str(legacy_id)).group())

    org_size = data.get("team_size", data.get("org_size", 1))
    segment = "b2c" if org_size <= 1 else "b2b"

    # Migrate pain_points
    new_pain_points = []
    raw_themes: dict[str, int] = {}  # theme_code -> max_severity
    for pp in data.get("pain_points", []):
        desc = pp.get("description", "")
        severity = pp.get("severity", 5)
        frequency = pp.get("frequency", "")
        theme = pp.get("theme", "")
        impact = f"severity {severity}/10"
        if frequency:
            impact += f", {frequency}"
        new_pain_points.append({
            "description": desc,
            "impact": impact,
            "current_workaround": None,
        })
        if theme:
            raw_themes[theme] = max(raw_themes.get(theme, 0), severity)

    # Build pain_themes from deduplicated themes
    new_pain_themes = []
    for theme_code, max_sev in raw_themes.items():
        new_pain_themes.append({
            "theme": theme_code,
            "intensity": _severity_to_intensity(max_sev),
        })

    # Migrate voice
    old_voice = data.get("voice", {})
    new_voice = {
        "skepticism": old_voice.get("skepticism", "moderate"),
        "vocabulary": old_voice.get("vocabulary", "general"),
        "motivation": old_voice.get("motivation", "efficiency"),
        "price_sensitivity": old_voice.get("price_sensitivity", "moderate"),
    }

    canonical = {
        "id": id_int,
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "industry": data.get("industry", ""),
        "segment": segment,
        "tier": data.get("tier", "FREE"),
        "age": data.get("age"),
        "income": data.get("income"),
        "org_size": org_size,
        "experience_years": data.get("experience_years"),
        "ai_history": data.get("ai_history"),
        "mindset": data.get("mindset"),
        "pain_points": new_pain_points,
        "pain_themes": new_pain_themes,
        "unmet_need": data.get("unmet_need"),
        "proof_point": data.get("proof_point"),
        "trust_requirements": data.get("trust_requirements", []),
        "voice": new_voice,
        "metadata": {
            "source": "manual",
            "validation_status": "draft",
            "legacy_id": str(legacy_id),
        },
    }
    return canonical, data.get("objectives", [])

def migrate_objectives_to_workflow(persona_id: int, persona_name: str, objectives: list) -> dict:
    """Wrap legacy objectives as PersonaWorkflowMapping Goals."""
    goals = []
    for i, obj in enumerate(objectives, 1):
        goals.append({
            "id": f"G-{persona_id:02d}-{i}",
            "title": obj.get("goal", f"Goal {i}"),
            "category": "knowledge",
            "priority": "primary",
            "trigger": obj.get("trigger", ""),
            "success_statement": obj.get("success_definition", ""),
            "value_metrics": {
                "time_saved": obj.get("efficiency_baseline", ""),
                "error_reduction": "",
                "cost_impact": "",
            },
            "workflows": [],
        })
    return {
        "persona_id": persona_id,
        "persona_name": persona_name,
        "persona_tier": "FREE",
        "goals": goals,
        "feature_recommendations": [],
    }

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def migrate_feature_inventory(path: Path) -> Optional[CapabilityRegistry]:
    """Convert feature-inventory.yaml to CapabilityRegistry."""
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    features = data.get("features", [])
    capabilities = []
    for feat in features:
        raw_id = feat.get("id", "unknown")
        # Convert slug to CAP-* format
        parts = raw_id.upper().replace("-", "_").split("_")
        if len(parts) >= 2:
            cap_id = f"CAP-{parts[0]}-{'_'.join(parts[1:])}"
        else:
            cap_id = f"CAP-MISC-{raw_id.upper()}"

        # Map status literals
        status_map = {"implemented": "complete", "partial": "partial",
                      "missing": "planned", "planned": "planned", "future": "future"}
        raw_status = feat.get("status", "planned")
        status = status_map.get(raw_status, "planned")

        test_results = []
        for tr in feat.get("test_results", []):
            test_results.append({
                "run_date": tr.get("run_date", ""),
                "status": tr.get("status", "not_tested"),
                "personas_tested": tr.get("personas_tested", []),
            })

        capabilities.append(Capability(
            id=cap_id,
            name=feat.get("name", raw_id),
            description=feat.get("description", ""),
            status=status,
            feature_area=feat.get("area", "General"),
            api_endpoint=None,
            ui_page=feat.get("pages", [None])[0] if feat.get("pages") else None,
            dependencies=[],
            test_results=[TestResult(**tr) for tr in test_results],
            requested_by=feat.get("requested_by", []),
            first_reported=feat.get("first_reported"),
        ))
    return CapabilityRegistry(
        product=data.get("product", "unknown"),
        version="1.0.0",
        capabilities=capabilities,
    )

def migrate_all(personas_dir: Path, workflows_dir: Path, data_dir: Path, backup: bool = True) -> dict:
    """Run full migration: personas + feature inventory."""
    legacy_dir = personas_dir / "_legacy"
    results = {"personas": [], "workflows": [], "capabilities": None, "errors": []}

    # Migrate personas
    for path in sorted(personas_dir.glob("UXW-*.yaml")):
        try:
            canonical_dict, objectives = migrate_persona_yaml(path)
            persona = Persona(**canonical_dict)

            if backup:
                legacy_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, legacy_dir / path.name)

            saved = save_persona(persona, personas_dir)
            results["personas"].append(str(saved))

            if objectives:
                workflows_dir.mkdir(parents=True, exist_ok=True)
                wf = migrate_objectives_to_workflow(persona.id, persona.name, objectives)
                wf_path = workflows_dir / f"PWM-{persona.id:02d}-{_slugify(persona.name)}.yaml"
                with open(wf_path, "w") as f:
                    yaml.dump(wf, f, default_flow_style=False, allow_unicode=True)
                results["workflows"].append(str(wf_path))

            path.unlink()  # remove old UXW-*.yaml
        except Exception as e:
            results["errors"].append(f"{path.name}: {e}")

    # Migrate feature inventory
    inventory_path = data_dir / "feature-inventory.yaml"
    registry = migrate_feature_inventory(inventory_path)
    if registry:
        cap_path = data_dir / "capabilities.yaml"
        save_capability_registry(registry, cap_path)
        results["capabilities"] = str(cap_path)
        if backup and inventory_path.exists():
            shutil.copy2(inventory_path, data_dir / "feature-inventory.yaml.bak")

    return results
```

### `eval/config.py` — add slug resolution
```python
def resolve_result_slug(persona) -> str:
    """Return the result directory slug, checking both UXW-* and new formats."""
    from voice_of_agents.eval.config import VoAConfig
    # New format: 01-maria-gutierrez
    new_slug = persona.slug  # from Persona.slug property
    # Legacy format: UXW-01-maria-gutierrez (stored in metadata.legacy_id)
    legacy_id = getattr(getattr(persona, 'metadata', None), 'legacy_id', None)
    return new_slug  # caller checks both paths
```

### Eval code field access changes
Go through each `eval/*.py` file and update:

| Old (dataclass) | New (Pydantic) |
|-----------------|----------------|
| `persona.id` (str "UXW-01") | `persona.id` (int 1) |
| `persona.team_size` | `persona.org_size` |
| `persona.voice.skepticism` | `persona.voice.skepticism` (unchanged — no None guard needed) |
| `persona.objectives` | load from `PersonaWorkflowMapping.goals` (see phase2_explore update) |
| `persona.pain_points[i].theme` | `persona.pain_themes[i].theme.value` |
| `persona.tier` (str) | `persona.tier.value` (enum) |
| `f"{persona.slug}"` | `f"{persona.slug}"` (property unchanged, but now `int`-based) |

### `eval/seed.py` update
```python
# Old:
for pp in persona.pain_points:
    theme = pp.theme
# New:
for pt in persona.pain_themes:
    theme = pt.theme.value
```

### `voa eval migrate` CLI command
Add to `cli/eval_cli.py`:
```python
@eval_cli.command("migrate")
@click.option("--dry-run", is_flag=True, help="Show planned changes without writing")
@click.option("--no-backup", is_flag=True, help="Skip backing up original files")
def migrate_cmd(dry_run, no_backup):
    """Migrate UXW-format persona YAMLs and feature-inventory to canonical format."""
    from voice_of_agents.eval.migrate import migrate_persona_yaml, migrate_feature_inventory
    from voice_of_agents.eval.config import VoAConfig
    config = VoAConfig.load()
    # ... dry-run: show what would change; otherwise call migrate_all()
```

## Acceptance Criteria
- [ ] `src/voice_of_agents/eval/migrate.py` exists with `migrate_persona_yaml`, `migrate_objectives_to_workflow`, `migrate_feature_inventory`, `migrate_all`
- [ ] `voa eval migrate --dry-run` runs without error and prints a summary of planned changes
- [ ] `voa eval migrate` converts all `UXW-*.yaml` to `P-*.yaml` in `data/personas/`
- [ ] `data/personas/_legacy/UXW-*.yaml` files exist (originals backed up)
- [ ] `data/capabilities.yaml` exists (migrated from feature-inventory.yaml if present)
- [ ] No `UXW-*.yaml` files remain in `data/personas/` after migration
- [ ] `src/voice_of_agents/contracts/personas.py` is deleted
- [ ] `src/voice_of_agents/contracts/` directory is deleted
- [ ] `voa eval status` runs without ImportError after migration
- [ ] `python -c "from voice_of_agents.core.persona import Persona; from voice_of_agents.core.io import load_personas_dir; from pathlib import Path; ps = load_personas_dir(Path('data/personas')); print(len(ps), 'personas loaded')"` succeeds
- [ ] `pytest tests/unit/test_eval_migrate.py -v` passes

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
# Test migrate dry-run
voa eval migrate --dry-run

# Run migration
voa eval migrate

# Verify output
ls data/personas/P-*.yaml | head -5
ls data/personas/_legacy/ | head -5
ls data/capabilities.yaml 2>/dev/null && echo "capabilities.yaml created" || echo "skipped (no feature-inventory.yaml)"
ls src/voice_of_agents/contracts/ 2>/dev/null && echo "FAIL: contracts/ still exists" || echo "PASS: contracts deleted"

# Load migrated personas
python -c "
from voice_of_agents.core.io import load_personas_dir
from pathlib import Path
ps = load_personas_dir(Path('data/personas'))
print(f'{len(ps)} personas loaded')
print(f'First: {ps[0].name}, id={ps[0].id}, voice={ps[0].voice.skepticism}')
"

# Run status
voa eval status

# Run migrate tests
pytest tests/unit/test_eval_migrate.py -v
```

## Status
PENDING
