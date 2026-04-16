# Phase 2: Migrate Design Subpackage

## Goal
Move all Pro-package code into `src/voice_of_agents/design/`, update imports to use `core/` canonical models, replace `FeatureRecommendation` with `BacklogItem`, wire the design CLI, and delete `pro-package/`.

## Context
The Pro package lives at `pro-package/` as a separate pip-installable package. After this phase it is fully absorbed into the main package under the `design/` namespace. `FeatureRecommendation` is deleted — gap analysis now writes `BacklogItem(source="design")` directly.

## Dependencies
Phase 1 must be COMPLETE: `core/` models must exist before design code can import from them.

## Scope

### Files to Create
- `src/voice_of_agents/design/workflow.py` — Goal, Workflow, WorkflowStep, PersonaWorkflowMapping (no FeatureRecommendation)
- `src/voice_of_agents/design/gap_analysis.py` — GapAnalyzer, GapAnalysisReport (outputs BacklogItem)
- `src/voice_of_agents/design/prompts.py` — Jinja2 LLM prompt templates
- `src/voice_of_agents/design/persona_pipeline.py` — PersonaPipeline
- `src/voice_of_agents/design/workflow_pipeline.py` — WorkflowPipeline
- `src/voice_of_agents/design/validators.py` — validate_all(), ValidationResult
- `src/voice_of_agents/design/io.py` — save_workflow_mapping, load_workflow_mappings_dir
- `src/voice_of_agents/cli/design_cli.py` — `voa design *` Click commands
- `src/voice_of_agents/schemas/persona.yaml` — JSON Schema (copy from Pro)
- `src/voice_of_agents/schemas/capability.yaml` — JSON Schema (copy from Pro)
- `src/voice_of_agents/schemas/workflow.yaml` — JSON Schema (copy from Pro)
- `tests/unit/test_design_workflow.py` — ported from Pro's test_models.py
- `tests/unit/test_design_validators.py` — ported from Pro's test_validate.py
- `tests/fixtures/sample_registry.yaml` — copied from Pro's fixtures
- `tests/fixtures/sample_workflow.yaml` — copied from Pro's fixtures (updated: no FeatureRecommendation)

### Files to Modify
- `src/voice_of_agents/design/__init__.py` — update from empty stub to exports
- `src/voice_of_agents/cli/__init__.py` — no change needed yet (main.py not wired until Phase 3)

### Files to Delete
- `pro-package/` — entire directory, after verification

### Explicitly Out of Scope
- Wiring `design_cli` into the root `voa` group (that's Phase 3)
- Touching eval/ code
- Modifying `core/` models

## Implementation Notes

### Source files to copy and transform

**`pro-package/src/voice_of_agents/models/workflow.py` → `design/workflow.py`**
- Remove `FeatureRecommendation` class entirely
- Remove `PersonaWorkflowMapping.feature_recommendations` field (or change type to `list[BacklogItem]` from `core.backlog`)
- Update `Tier` import: `from voice_of_agents.core.enums import Tier, GoalCategory, GoalPriority`
- All other imports remain local to `design/`

**`pro-package/src/voice_of_agents/pipelines/gap_analysis.py` → `design/gap_analysis.py`**
- `GapAnalysisReport.feature_recommendations` changes type from `list[FeatureRecommendation]` to `list[BacklogItem]`
- In `analyze()`, when building recommendations: create `BacklogItem(source="design", extends_capability=..., value_statement=..., effort=..., title=..., description=..., id=...)` instead of `FeatureRecommendation`
- Complexity→effort mapping: trivial→"trivial", small→"small", medium→"medium" (large/epic not in Pro; default "medium")
- Import: `from voice_of_agents.core.backlog import BacklogItem`
- Import: `from voice_of_agents.core.capability import CapabilityRegistry` (instead of local model)

**`pro-package/src/voice_of_agents/pipelines/persona_pipeline.py` → `design/persona_pipeline.py`**
- `from voice_of_agents.core.persona import Persona` (instead of local model)
- `from voice_of_agents.core.io import save_persona, load_personas_dir` (defer persona I/O to core)
- Remove any local persona save/load logic

**`pro-package/src/voice_of_agents/pipelines/workflow_pipeline.py` → `design/workflow_pipeline.py`**
- `from voice_of_agents.core.capability import CapabilityRegistry` (instead of local model)
- `from voice_of_agents.core.io import load_capability_registry`

**`pro-package/src/voice_of_agents/validators/validate.py` → `design/validators.py`**
- Update all imports to use `voice_of_agents.core.*` and `voice_of_agents.design.*`
- No logic changes

**`pro-package/src/voice_of_agents/validators/io.py` → `design/io.py`**
- Keep: `save_workflow_mapping`, `load_workflow_mapping`, `load_workflow_mappings_dir`
- Remove: `save_persona`, `load_persona`, `load_personas_dir` (these now live in `core/io.py`)
- Remove: `load_capability_registry` (now in `core/io.py`)
- Update imports accordingly

**`pro-package/src/voice_of_agents/pipelines/prompts.py` → `design/prompts.py`**
- No logic changes; just update any imports

**`pro-package/src/voice_of_agents/cli/main.py` → `cli/design_cli.py`**
- Rename the Click group from `cli` to `design_cli`
- Update all imports to `voice_of_agents.design.*` and `voice_of_agents.core.*`
- The entry point is NOT changed yet (Phase 3 handles the root CLI)

### Unit tests to port
- `pro-package/tests/unit/test_models.py` → split into `tests/unit/test_design_workflow.py` (workflow/goal models) and update `test_core_persona.py`/`test_core_capability.py` for model tests already covered
- `pro-package/tests/unit/test_validate.py` → `tests/unit/test_design_validators.py`
- `pro-package/tests/unit/test_pipelines.py` → skip for now (pipeline tests require LLM mocking; deferred to Phase 6)
- `pro-package/tests/unit/test_io.py` → merge relevant parts into `test_design_workflow.py`

Update all imports in ported tests from `voice_of_agents.models.*` / `voice_of_agents.pipelines.*` / `voice_of_agents.validators.*` to `voice_of_agents.design.*` and `voice_of_agents.core.*`.

### Deletion
After verifying tests pass, delete `pro-package/` with `rm -rf pro-package/`.

## Acceptance Criteria
- [ ] `src/voice_of_agents/design/workflow.py` exists with `Goal`, `Workflow`, `WorkflowStep`, `PersonaWorkflowMapping` but NO `FeatureRecommendation`
- [ ] `src/voice_of_agents/design/gap_analysis.py` imports `BacklogItem` from `voice_of_agents.core.backlog` and `GapAnalysisReport.feature_recommendations` is typed `list[BacklogItem]`
- [ ] `src/voice_of_agents/design/persona_pipeline.py` imports `Persona` from `voice_of_agents.core.persona`
- [ ] `src/voice_of_agents/cli/design_cli.py` exists with `design_cli` Click group
- [ ] `pro-package/` directory no longer exists
- [ ] `pytest tests/unit/test_design_workflow.py tests/unit/test_design_validators.py -v` passes
- [ ] `python -c "from voice_of_agents.design.gap_analysis import GapAnalyzer; print('ok')"` succeeds
- [ ] `python -c "from voice_of_agents.design.workflow import Goal, PersonaWorkflowMapping; print('ok')"` succeeds
- [ ] No reference to `FeatureRecommendation` exists anywhere in `src/` (verify with grep)

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
python -c "from voice_of_agents.design.gap_analysis import GapAnalyzer; print('ok')"
python -c "from voice_of_agents.design.workflow import Goal, PersonaWorkflowMapping; print('ok')"
python -c "from voice_of_agents.design.validators import validate_all; print('ok')"
python -c "from voice_of_agents.cli.design_cli import design_cli; print('ok')"
grep -r "FeatureRecommendation" src/ && echo "FAIL: FeatureRecommendation still referenced" || echo "PASS: no FeatureRecommendation"
ls pro-package/ 2>/dev/null && echo "FAIL: pro-package still exists" || echo "PASS: pro-package deleted"
pytest tests/unit/test_design_workflow.py tests/unit/test_design_validators.py -v
```

## Status
PENDING
