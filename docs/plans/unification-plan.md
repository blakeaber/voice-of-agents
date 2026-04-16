# Voice of Agents — Unified Codebase Refactoring Plan

## Context

Two packages share the name "Voice of Agents," the same `voa` CLI entry point, and overlapping domain concepts, but serve entirely different purposes at different stages of the product lifecycle:

- **Main** (`/voice-of-agents/`): A **runtime evaluation pipeline** — runs Playwright browser sessions as LLM-backed personas against a live product to discover friction and produce a scored, event-sourced backlog.
- **Pro** (`/voice-of-agents/pro-package/`): A **design-time planning framework** — generates personas, maps Goal→Workflow→Step hierarchies against a capability registry, and performs static gap analysis.

These are complementary halves of a complete product research lifecycle. Pro generates validated personas and maps what they need; Main runs those personas through the live product to measure how well those needs are actually met. The unified package makes this handoff explicit and seamless.

**Approach:** No backward compatibility shims. This is a research package with no external users. All legacy code is deleted, not shimmed.

---

## Canonical Package Structure

```
voice-of-agents/
├── pyproject.toml                     # Single package, all dependencies
├── voa-config.json                    # Runtime evaluation config (eval layer)
├── README.md
│
├── src/
│   └── voice_of_agents/
│       ├── __init__.py
│       │
│       ├── core/                      # SHARED — canonical data models
│       │   ├── __init__.py
│       │   ├── enums.py               # Tier, ThemeCode, Segment, Intensity (Pydantic enums)
│       │   ├── persona.py             # Canonical Persona (Pydantic BaseModel)
│       │   ├── pain.py                # PainPoint, PainTheme (Pydantic)
│       │   ├── capability.py          # Unified Capability + CapabilityRegistry (absorbs FeatureInventory)
│       │   ├── backlog.py             # Unified BacklogItem (absorbs FeatureRecommendation) + JSONL sourcing
│       │   └── io.py                  # Shared YAML load/save with Pydantic
│       │
│       ├── design/                    # Design-time planning tools (from Pro)
│       │   ├── __init__.py
│       │   ├── workflow.py            # Goal, Workflow, WorkflowStep, PersonaWorkflowMapping
│       │   ├── gap_analysis.py        # GapAnalyzer, GapAnalysisReport
│       │   ├── prompts.py             # Jinja2 templates
│       │   ├── persona_pipeline.py    # PersonaPipeline (generate-prompt + parse)
│       │   ├── workflow_pipeline.py   # WorkflowPipeline
│       │   ├── io.py                  # Design-specific YAML I/O (workflow mappings)
│       │   └── validators.py          # validate_all(), ValidationResult
│       │
│       ├── eval/                      # Runtime evaluation pipeline (from Main)
│       │   ├── __init__.py
│       │   ├── config.py              # VoAConfig dataclass
│       │   ├── browser.py             # Playwright explorer (explore_as_persona)
│       │   ├── api.py                 # TargetAPI HTTP client
│       │   ├── seed.py                # seed_persona()
│       │   ├── migrate.py             # UXW-format → canonical Persona migration script
│       │   ├── bridge.py              # Design↔Eval integration (gap analysis → backlog)
│       │   ├── phase1_generate.py
│       │   ├── phase2_explore.py
│       │   ├── phase3_evaluate.py
│       │   ├── phase4_synthesize.py
│       │   ├── phase5_prioritize.py
│       │   ├── render.py              # Backlog markdown rendering
│       │   └── diff.py                # Run-over-run diff
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py                # Root `voa` group — dispatches to sub-CLIs
│       │   ├── design_cli.py          # `voa design *` commands
│       │   └── eval_cli.py            # `voa eval *` commands
│       │
│       └── schemas/                   # JSON Schema YAML files (from Pro)
│           ├── persona.yaml
│           ├── capability.yaml
│           └── workflow.yaml
│
├── data/                              # Runtime data (eval layer)
│   ├── personas/                      # Canonical persona YAMLs (P-*.yaml)
│   │   └── _legacy/                   # Backed-up UXW-*.yaml originals after migration
│   ├── workflows/                     # Persona workflow mappings (PWM-*.yaml)
│   ├── capabilities.yaml              # Unified capability registry
│   ├── results/                       # Per-run exploration/evaluation
│   ├── backlog.jsonl
│   ├── 004-findings.md
│   ├── 005-backlog.md
│   └── 006-diff-report.md
│
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── sample_persona.yaml
    │   ├── sample_persona_legacy.yaml
    │   ├── sample_registry.yaml
    │   ├── sample_workflow.yaml
    │   ├── sample_exploration.yaml
    │   ├── sample_evaluation.yaml
    │   └── sample_findings.md
    ├── unit/
    │   ├── test_core_persona.py
    │   ├── test_core_capability.py
    │   ├── test_core_backlog.py
    │   ├── test_design_workflow.py
    │   ├── test_design_validators.py
    │   ├── test_eval_migrate.py
    │   ├── test_eval_prioritize.py
    │   └── test_eval_evaluate.py
    └── integration/
        └── test_cli_design.py
```

---

## Data Model Reconciliation

### Persona: Canonical Model

Adopt Pro's Pydantic model as the canonical `Persona`. Additions from Main:
- `voice: VoiceProfile` — behavioral calibration needed by `phase3_evaluate`; **optional with sensible defaults** (see VoiceProfile below)
- `metadata.legacy_id: Optional[str]` — preserves "UXW-01" for result directory backward-compat during migration only

**ID:** `int` (sequential). Legacy string IDs ("UXW-01") stored in `metadata.legacy_id` only.

### VoiceProfile (Shared, with Defaults)

```python
class VoiceProfile(BaseModel):
    skepticism: Literal["low", "moderate", "high"] = "moderate"
    vocabulary: Literal["legal", "medical", "financial", "technical", "general"] = "general"
    motivation: Literal["fear", "ambition", "efficiency", "legacy", "compliance"] = "efficiency"
    price_sensitivity: Literal["low", "moderate", "high"] = "moderate"
```

Added to canonical `Persona` as `voice: VoiceProfile = Field(default_factory=VoiceProfile)` — always present, always valid, no optional check needed anywhere. Eval code can safely access `persona.voice.skepticism` unconditionally.

### PainPoint Reconciliation

Canonical `PainPoint` = Pro's shape:
- `description: str`
- `impact: str` — quantified (e.g., "45 min lost per incident")
- `current_workaround: Optional[str]`

Theme classification lives at the persona level in `pain_themes: list[PainTheme]` (Pro's model). Main's per-pain-point `theme: str` and `severity: int` are migrated during Phase 4.

### Unified BacklogItem (absorbs FeatureRecommendation)

Main's `BacklogItem` and Pro's `FeatureRecommendation` are consolidated into a single `BacklogItem` in `core/backlog.py`. The unified model:

```python
class BacklogItem(BaseModel):
    id: str                          # B-001 (eval) or FR-01-1 (design) or bridge-assigned
    title: str
    description: str
    source: Literal["eval", "design", "bridge"]   # origin of this item

    # Scoring (eval-originated items compute these; design-originated items may estimate)
    score: float = 0.0
    coverage_score: float = 0.0
    pain_score: float = 0.0
    revenue_score: float = 0.0
    effort_score: float = 0.0

    # Classification
    effort: Literal["trivial", "small", "medium", "large", "epic"] = "medium"
    status: Literal["open", "in_progress", "resolved", "deprioritized"] = "open"
    pain_themes: list[str] = []      # ThemeCode values (A-F)

    # Evidence (from eval)
    finding_id: Optional[str] = None
    personas: list[int] = []         # Persona IDs affected
    persona_quotes: list[str] = []
    acceptance_criteria: list[str] = []

    # Design-layer fields (from FeatureRecommendation)
    extends_capability: Optional[str] = None   # CAP-* ID this item extends
    value_statement: Optional[str] = None      # Persona-voice statement
```

`FeatureRecommendation` is deleted. Design-layer gap analysis writes `BacklogItem` objects with `source="design"` directly to `backlog.jsonl`. `BacklogEvent` and JSONL event sourcing are retained as-is.

`complexity` (Pro's FeatureRecommendation) maps to `effort`: trivial→trivial, small→small, medium→medium.

### Unified Capability + CapabilityRegistry (absorbs FeatureInventory)

Main's `Feature`/`FeatureInventory` and Pro's `Capability`/`CapabilityRegistry` are consolidated into a single `Capability` model in `core/capability.py`:

```python
class TestResult(BaseModel):          # From Main's FeatureInventory
    run_date: str
    status: Literal["pass", "fail", "skip", "not_tested"]
    personas_tested: list[int] = []

class Capability(BaseModel):
    id: str                           # CAP-LEARN-SEARCH (Pro format; required)
    name: str
    description: str
    status: Literal["complete", "partial", "planned", "future"]
    feature_area: str

    # Structural (from Pro)
    api_endpoint: Optional[str] = None
    ui_page: Optional[str] = None
    dependencies: list[str] = []     # Other CAP-* IDs

    # Runtime tracking (from Main's Feature)
    test_results: list[TestResult] = []
    requested_by: list[int] = []     # Persona IDs that surfaced this need
    first_reported: Optional[str] = None

    # Computed
    def is_available(self) -> bool: ...
    def latest_test(self) -> Optional[TestResult]: ...

class CapabilityRegistry(BaseModel):
    product: str
    version: str
    capabilities: list[Capability]

    def get(self, capability_id: str) -> Optional[Capability]: ...
    def available(self) -> list[Capability]: ...
    def by_feature_area(self, area: str) -> list[Capability]: ...
    def by_status(self, status: str) -> list[Capability]: ...
```

Main's `Feature` (with free-form `id`, `pages`, `endpoints`, `status` as different literals) is migrated to `Capability` format during Phase 4. The `feature-inventory.yaml` file is renamed to `capabilities.yaml`.

`FeatureInventory` class is deleted. All eval code that referenced `FeatureInventory` uses `CapabilityRegistry` directly.

---

## CLI Structure

```
voa
  design                         # design-time commands (from Pro)
    init [project_dir] --product
    persona
      list --dir
      generate-prompt --product --description --industry --roles
      import YAML_FILE --dir
      validate --dir
    workflow
      list --dir
      generate-prompt PERSONA_ID --dir
      import YAML_FILE PERSONA_ID --dir
    analyze
      gaps --dir
      coverage --dir
    validate --dir
  eval                           # eval-time commands (from Main)
    init --target --api --data
    import
      personas DIR
      inventory FILE
    phase1
    phase2 [--personas|--batch|--all]
    phase3 [--personas|--batch|--all]
    phase4
    phase5
    migrate [--dry-run] [--no-backup]
    status
    backlog
    capabilities
    diff
  bridge                         # cross-layer integration
    status
    sync-gaps
```

No backward-compat aliases. Old `voa phase2`-style commands are deleted entirely.

---

## Migration Notes for Existing Data Files

### Main's Persona Files (`data/personas/UXW-*.yaml`)
- `id: str` ("UXW-01") → `id: int` (1) + `metadata.legacy_id: "UXW-01"`
- `team_size` → `org_size`
- `segment`: infer from `org_size` (1 → "b2c", >1 → "b2b")
- `pain_points[].theme` + `severity` → migrate to `pain_themes` list on persona
- `pain_points[].frequency` → folded into `impact` string
- `voice` → `VoiceProfile` (field names unchanged, defaults fill gaps)
- `objectives` → written as `Goals` in companion `PersonaWorkflowMapping` YAML
- Missing fields (`ai_history`, `mindset`, `unmet_need`, `proof_point`) → `null`

Original files backed up to `data/personas/_legacy/` before overwrite.

### Feature Inventory (`data/feature-inventory.yaml`)
Migrated to `Capability` format and saved as `data/capabilities.yaml`. Main's `Feature.id` (free-form slug) gets a `CAP-` prefix and area suffix (e.g., `"learning-search"` → `"CAP-LEARN-SEARCH"`). Existing test history is preserved in `test_results`.

### Result Directories (`data/results/{slug}/{timestamp}/`)
Slug format changes: `UXW-01-maria-gutierrez` → `01-maria-gutierrez`. Existing directories left untouched. New runs use the new format. A slug-resolution helper checks both formats.

### Backlog (`data/backlog.jsonl`)
Append-only. No migration needed for existing events. New events use `persona_id: int`.

---

## Phases

---

### Phase 0: Repository Preparation

**Motivation:** Establish the structural scaffolding so both packages can coexist temporarily and the unified landing zone is ready to receive code.

**Acceptance Criteria:**
- Both packages still import and run independently
- Empty module stubs exist for `core/`, `design/`, `eval/`, `cli/`
- `pydantic>=2.0`, `rich>=13.0`, and `jinja2>=3.1` declared in root `pyproject.toml`
- No existing import paths changed

**Specifications:**
1. Add to root `pyproject.toml` dependencies: `pydantic>=2.0`, `rich>=13.0`, `jinja2>=3.1`
2. Create stub `__init__.py` in: `src/voice_of_agents/core/`, `design/`, `eval/`, `cli/`
3. Tag git repo as `v0.1.0-pre-unification` before any further changes
4. Update `.gitignore` to exclude `pro-package/` build artifacts

**Constraints:** Do not rename or move any existing files. Do not change any import paths.

**Open Questions:**
- Is there a CI pipeline that needs updating?

**Dependencies:** None

---

### Phase 1: Extract Canonical Core Models

**Motivation:** Establishing the canonical `Persona`, `Capability`, and `BacklogItem` in `core/` eliminates duplication at the foundation. Both packages eventually import from here.

**Acceptance Criteria:**
- `core/enums.py`, `core/pain.py`, `core/persona.py`, `core/capability.py`, `core/backlog.py`, `core/io.py` exist
- All Pro unit tests pass against core models (after import path updates)
- Main package is untouched and functional
- `VoiceProfile` defaults work correctly (no `None` checks needed downstream)

**Specifications:**

1. **`core/enums.py`** — From Pro's `models/persona.py` and `models/workflow.py`:
   - `Tier`, `ThemeCode`, `Segment`, `Intensity`, `ValidationStatus`
   - `GoalCategory`, `GoalPriority`

2. **`core/pain.py`** — Pydantic models:
   - `PainPoint(description, impact, current_workaround=None)`
   - `PainTheme(theme: ThemeCode, intensity: Intensity)`

3. **`core/persona.py`** — Canonical Persona:
   - `VoiceProfile` with all fields defaulted (see model above)
   - `PersonaMetadata(source, created_at, updated_at, research_basis, validation_status, legacy_id: Optional[str])`
   - `Persona`: all Pro fields + `voice: VoiceProfile = Field(default_factory=VoiceProfile)`
   - `slug` property: `f"{self.id:02d}-{slugify(self.name)}"`

4. **`core/capability.py`** — Unified capability model:
   - `TestResult(run_date, status, personas_tested=[])`
   - `Capability` (see full model above)
   - `CapabilityRegistry(product, version, capabilities)`

5. **`core/backlog.py`** — Unified backlog model:
   - `BacklogItem` (see full model above; `source` field required)
   - `BacklogEvent(ts, type, data)` — event envelope unchanged
   - All existing JSONL functions: `add_item`, `update_score`, `change_status`, `materialize_backlog`, `render_backlog_markdown`

6. **`core/io.py`** — Shared I/O:
   - `load_persona(path) -> Persona`
   - `load_personas_dir(directory) -> list[Persona]`
   - `save_persona(persona, directory) -> Path` — `P-{id:02d}-{slug}.yaml`
   - `load_capability_registry(path) -> CapabilityRegistry`
   - `save_capability_registry(registry, path)`
   - `LoadError(path, errors)`

7. **`tests/unit/test_core_persona.py`**, **`test_core_capability.py`**, **`test_core_backlog.py`**

**Constraints:**
- Do not touch `pro-package/` code yet
- Do not change `contracts/personas.py` yet
- All new code must have unit tests

**Open Questions:**
- What `VoiceProfile.vocabulary` default best represents "average person"? **Recommended: `"general"`.**
- What `VoiceProfile.motivation` default? **Recommended: `"efficiency"` — the most neutral/universal motivation.**

**Dependencies:** Phase 0

---

### Phase 2: Migrate Design Subpackage

**Motivation:** Move all Pro-only code into `src/voice_of_agents/design/` so it lives inside the main package source tree and `pro-package/` can be deleted.

**Acceptance Criteria:**
- `voa design persona list` works
- `voa design analyze gaps` works
- `voa design validate` works
- All Pro unit tests pass with updated import paths
- `pro-package/` directory is deleted

**Specifications:**

1. Copy into `src/voice_of_agents/design/`:
   - `pro-package/.../models/workflow.py` → `design/workflow.py` (update `Tier` import → `core.enums`; remove `FeatureRecommendation` — replaced by `core.backlog.BacklogItem`)
   - `pro-package/.../pipelines/gap_analysis.py` → `design/gap_analysis.py` (update gap output to write `BacklogItem` with `source="design"` instead of `FeatureRecommendation`)
   - `pro-package/.../pipelines/prompts.py` → `design/prompts.py`
   - `pro-package/.../pipelines/persona_pipeline.py` → `design/persona_pipeline.py` (import `Persona` from `core.persona`)
   - `pro-package/.../pipelines/workflow_pipeline.py` → `design/workflow_pipeline.py` (import `CapabilityRegistry` from `core.capability`)
   - `pro-package/.../validators/validate.py` → `design/validators.py`
   - `pro-package/.../validators/io.py` → `design/io.py` (keep `save_workflow_mapping`, `load_workflow_mappings_dir`; persona I/O defers to `core/io.py`; capability I/O defers to `core/io.py`)

2. **Update `design/gap_analysis.py`**:
   - Replace `FeatureRecommendation` output with `BacklogItem(source="design", extends_capability=..., value_statement=..., effort=...)`
   - `GapAnalysisReport.feature_recommendations: list[BacklogItem]` (renamed field, same semantics)

3. **`cli/design_cli.py`**: Copy Pro CLI, update all imports to `voice_of_agents.design.*` and `voice_of_agents.core.*`

4. Copy Pro schemas → `src/voice_of_agents/schemas/`

5. Port Pro unit tests → `tests/unit/` with updated import paths

6. Delete `pro-package/` directory

**Constraints:**
- `design/workflow.py` must NOT import `FeatureRecommendation` from anywhere — it is deleted
- All Pro tests must pass with only import path changes (no logic changes)

**Open Questions:**
- Should `WorkflowPipeline.parse_response()` return `BacklogItem` objects directly from LLM response, or convert after? **Recommended: convert after — keep LLM parsing isolated from model changes.**

**Dependencies:** Phase 1

---

### Phase 3: Migrate Eval Subpackage

**Motivation:** Restructure Main's pipeline code into `src/voice_of_agents/eval/` and wire the unified CLI. All old flat-namespace code is deleted — no aliases.

**Acceptance Criteria:**
- `voa eval phase2 --all` works end-to-end
- `voa eval status` shows correct status
- `voa eval run --all` completes
- All existing `data/` files load correctly
- Old `voa phase2`-style commands are gone (no aliases)

**Specifications:**

1. **Move** (with import updates) into `src/voice_of_agents/eval/`:
   - `config.py`, `contracts/backlog.py` (now replaced by `core/backlog.py` — delete this file), `contracts/inventory.py` (now replaced by `core/capability.py` — delete this file), `explorer/browser.py`, `explorer/api.py`, `explorer/seed.py`, `phases/phase{1-5}_*.py`, `reporting/render.py`, `reporting/diff.py`

2. **Update all imports** in moved files:
   - `BacklogItem`, `BacklogEvent`, `materialize_backlog` etc. → `from voice_of_agents.core.backlog import ...`
   - `Feature`, `FeatureInventory` → `from voice_of_agents.core.capability import Capability, CapabilityRegistry`
   - `Persona` → `from voice_of_agents.core.persona import Persona`

3. **`cli/eval_cli.py`**: All commands from `src/voice_of_agents/cli.py`, updated imports, renamed group to `eval_cli`. The `inventory` command becomes `capabilities` (pointing at `CapabilityRegistry`).

4. **`cli/main.py`** (new root):
   ```python
   @click.group()
   def cli(): ...
   cli.add_command(design_cli, name="design")
   cli.add_command(eval_cli, name="eval")
   cli.add_command(bridge_cli, name="bridge")
   ```

5. Update `pyproject.toml` entry point: `voa = "voice_of_agents.cli.main:cli"`

6. Delete: `src/voice_of_agents/contracts/`, `src/voice_of_agents/explorer/`, `src/voice_of_agents/phases/`, `src/voice_of_agents/reporting/`, `src/voice_of_agents/cli.py`

**Constraints:**
- No backward-compat aliases — old commands simply no longer exist
- `data/` files must remain readable without migration
- `playwright` and `httpx` remain in main dependencies

**Open Questions:**
- Should `eval/render.py` be updated to render the unified `BacklogItem` (with new `source` and `extends_capability` fields)? **Yes — update the markdown templates to show source and value_statement when present.**

**Dependencies:** Phase 2

---

### Phase 4: Migrate Existing Data and Persona Model

**Motivation:** Replace Main's `contracts/personas.py` dataclasses with the canonical Pydantic model and migrate existing YAML files to the canonical format. Migrate `feature-inventory.yaml` to `capabilities.yaml`.

**Acceptance Criteria:**
- `voa eval migrate --dry-run` shows planned changes
- `voa eval migrate` converts all `UXW-*.yaml` to `P-*.yaml` without data loss
- `voa eval migrate` converts `feature-inventory.yaml` → `capabilities.yaml`
- `voa eval phase2 --all` works with migrated files
- `voa eval phase3 --all` generates correct evaluations (voice calibration uses defaults where missing)
- `contracts/personas.py` is deleted

**Specifications:**

1. **`eval/migrate.py`**:
   - `migrate_persona_yaml(path: Path) -> dict`:
     - `id`: parse int from "UXW-01" → 1; `metadata.legacy_id = "UXW-01"`
     - `org_size`: from `team_size`
     - `segment`: infer from `org_size` (1 → "b2c", >1 → "b2b")
     - `pain_points`: `{description, impact: "severity {n}/10, {frequency}", current_workaround: null}`
     - `pain_themes`: deduplicate themes; map severity → intensity (1-4→LOW, 5-6→MEDIUM, 7-8→HIGH, 9-10→CRITICAL)
     - `voice`: copy fields to `VoiceProfile` (missing fields get model defaults)
     - `objectives`: extracted for workflow migration
     - Missing (`ai_history`, `mindset`, `unmet_need`, `proof_point`): `null`
   - `migrate_objectives_to_workflow(persona_id: int, objectives: list) -> dict`: wraps objectives as Goals with `category="knowledge"`, `priority="primary"`, empty workflows
   - `migrate_feature_inventory(path: Path) -> CapabilityRegistry`: converts `Feature` records to `Capability` records; prefixes IDs with `CAP-`; preserves test history
   - `migrate_all(config: VoAConfig)`: runs all migrations, backs up originals

2. **`voa eval migrate` CLI command**:
   - `--dry-run`: show changes, no writes
   - `--no-backup`: skip backup (default: backup enabled)

3. **Update all `eval/` code** that referenced `contracts.personas`:
   - Import `Persona` from `voice_of_agents.core.persona`
   - `persona.team_size` → `persona.org_size`
   - `persona.voice.*` — always safe to access (no `None` check needed; defaults present)
   - `persona.objectives` → load from companion `PersonaWorkflowMapping`
   - `persona.pain_points[].theme` → `persona.pain_themes[].theme.value`
   - `persona.id` (was str) → `int`; slug: `f"{persona.id:02d}-{slugify(persona.name)}"`

4. **Update `eval/phase2_explore.py`**: load goals from `PersonaWorkflowMapping` (fall back to empty list if no mapping exists)

5. **Update `eval/seed.py`**: `_derive_goals()` uses `persona.pain_themes` instead of `persona.pain_points[].theme`

6. **Slug resolution helper** in `eval/config.py`: `resolve_result_slug(persona)` checks both `UXW-01-*` and `01-*` formats in `data/results/`

7. Delete `src/voice_of_agents/contracts/` directory entirely

8. **`tests/unit/test_eval_migrate.py`**: migration function tests using `sample_persona_legacy.yaml` fixture

**Constraints:**
- Migration is non-destructive: originals backed up before overwrite
- Existing `data/results/UXW-*/` directories remain untouched
- Run `--dry-run` documented as recommended pre-flight step in README

**Open Questions:**
- How should Feature IDs (e.g., `"learning-search"`) map to CAP-* format? **Recommended: uppercase, replace hyphens with area separator: `"learning-search"` → `"CAP-LEARN-SEARCH"`. Non-conforming IDs get `CAP-MISC-` prefix.**

**Dependencies:** Phase 3

---

### Phase 5: Add Cross-Layer Bridge

**Motivation:** With both layers sharing the canonical models, add the integration that makes the tool a coherent end-to-end system: design-layer gap analysis writes directly to the backlog; eval-layer reads workflow goals as objectives.

**Acceptance Criteria:**
- `voa eval phase2` reads objectives from `PersonaWorkflowMapping.goals` when a mapping exists
- `voa bridge sync-gaps` converts gap analysis findings to backlog items with `source="bridge"`
- `voa bridge status` shows per-persona design-vs-eval coverage

**Specifications:**

1. **`eval/phase2_explore.py`**: accept `mapping: PersonaWorkflowMapping | None`; map `Goal` → objective fields; fall back to empty

2. **`eval/bridge.py`**:
   - `sync_gap_analysis_to_backlog(report: GapAnalysisReport, config: VoAConfig)`: writes `BacklogItem(source="bridge")` for each gap to `backlog.jsonl`
   - `bridge_status(config: VoAConfig) -> dict`: per-persona summary (has design mapping? has eval results?)

3. **`cli/main.py`**: add `bridge` subgroup:
   - `voa bridge status`
   - `voa bridge sync-gaps`

**Constraints:**
- Additive only — no changes to existing phase logic
- `voa eval run --all` works identically whether or not workflow mappings exist

**Dependencies:** Phase 4

---

### Phase 6: Test Coverage and Cleanup

**Motivation:** Main's package has zero unit tests. This phase adds baseline coverage and finalizes the directory cleanup.

**Acceptance Criteria:**
- `pytest tests/` passes with zero failures
- `core/backlog.py` coverage ≥ 80%
- `eval/phase5_prioritize.py` coverage ≥ 60%
- `eval/phase3_evaluate.py` template scoring coverage ≥ 60%
- `core/persona.py` coverage ≥ 90%
- All migrated Pro tests pass

**Specifications:**

1. **`tests/unit/test_core_backlog.py`**: `add_item`, `materialize_backlog`, `update_score`, `change_status`, event replay, unified `BacklogItem` with all sources

2. **`tests/unit/test_core_capability.py`**: `is_available()`, `latest_test()`, registry lookups, `by_feature_area()`

3. **`tests/unit/test_eval_prioritize.py`**: `_load_findings()`, `_revenue_score()`, `_estimate_effort()`

4. **`tests/unit/test_eval_evaluate.py`**: voice calibration with defaults, `_validate_evaluation()`, `_fix_consistency()`, template scoring

5. **Test fixtures**: add `sample_exploration.yaml`, `sample_evaluation.yaml`, `sample_findings.md`, `sample_persona_legacy.yaml`

6. **Final cleanup**:
   - Confirm `pro-package/` is deleted
   - Confirm `contracts/`, `explorer/`, `phases/`, `reporting/` are deleted
   - Confirm `src/voice_of_agents/cli.py` is deleted
   - Remove any stale `__pycache__` or `.egg-info` artifacts
   - Update README with unified CLI reference

**Constraints:**
- `eval/browser.py` and `eval/api.py` excluded from unit tests (require live infrastructure)

**Dependencies:** Phase 5

---

## Summary

| Phase | Name | Key Output | Risk | Breaking Changes |
|-------|------|------------|------|-----------------|
| 0 | Repository Preparation | Module stubs, pyproject.toml updates | Low | None |
| 1 | Extract Core Models | `core/` — Persona, Capability, BacklogItem | Medium | None (additive) |
| 2 | Migrate Design Subpackage | `design/` modules, delete `pro-package/` | Medium | Pro import paths (internal only) |
| 3 | Migrate Eval Subpackage | `eval/` modules, new CLI root | Medium | All old `voa phase*` commands deleted |
| 4 | Data + Persona Migration | `eval/migrate.py`, dataclass→Pydantic | High | Field names change throughout eval layer |
| 5 | Cross-Layer Bridge | `eval/bridge.py`, `voa bridge` commands | Low | None (additive) |
| 6 | Test Coverage & Cleanup | Unit tests, final deletions | Low | None |

---

## Critical Files

| File | Why It Matters |
|------|---------------|
| `src/voice_of_agents/core/persona.py` | Canonical Persona — most consequential field-set decision; `VoiceProfile` defaults must be correct |
| `src/voice_of_agents/core/backlog.py` | Unified BacklogItem — must satisfy both eval scoring requirements and design recommendation fields |
| `src/voice_of_agents/core/capability.py` | Unified Capability — must preserve Pro's structural IDs and Main's test history |
| `src/voice_of_agents/eval/phase3_evaluate.py` | Most complex eval file; voice calibration must work correctly with defaulted `VoiceProfile` |
| `src/voice_of_agents/eval/migrate.py` | Converts 35 existing YAMLs + feature inventory — data fidelity here determines Phase 4 success |
| `pyproject.toml` | Dependency unification and entry point change |

---

## Verification

After each phase:

1. **Phase 0–1**: `python -c "from voice_of_agents.core.persona import Persona; p = Persona(id=1, name='Test', role='Tester', industry='Tech', segment='b2c', tier='FREE'); print(p.voice.skepticism)"`
2. **Phase 2**: `voa design persona list --dir ./tests/fixtures/`
3. **Phase 3**: `voa eval status` (no backward-compat check — old commands are gone)
4. **Phase 4**: `voa eval migrate --dry-run` → `voa eval migrate` → `voa eval status`
5. **Phase 5**: `voa bridge status`
6. **Phase 6**: `pytest tests/ -v --tb=short`
