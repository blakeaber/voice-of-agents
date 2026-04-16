# Phase 1: Extract Canonical Core Models

## Goal
Create the `core/` package containing canonical Pydantic models for Persona, Capability, BacklogItem, and shared enums — the single source of truth that both design and eval layers will import from.

## Context
Both packages define their own Persona, pain themes, and partial backlog/feature models. This phase establishes the unified versions in `core/` without touching either existing package. All other phases import from here. Getting the field shapes right — especially `VoiceProfile` defaults and `BacklogItem.source` — is the most consequential decision in the entire refactoring.

## Dependencies
Phase 0 must be COMPLETE: `core/`, `design/`, `eval/`, `cli/` stub directories must exist.

## Scope

### Files to Create
- `src/voice_of_agents/core/enums.py` — `Tier`, `ThemeCode`, `Segment`, `Intensity`, `ValidationStatus`, `GoalCategory`, `GoalPriority`
- `src/voice_of_agents/core/pain.py` — `PainPoint`, `PainTheme`
- `src/voice_of_agents/core/persona.py` — `VoiceProfile`, `PersonaMetadata`, `Persona`
- `src/voice_of_agents/core/capability.py` — `TestResult`, `Capability`, `CapabilityRegistry`
- `src/voice_of_agents/core/backlog.py` — `BacklogItem`, `BacklogEvent`, JSONL functions
- `src/voice_of_agents/core/io.py` — `load_persona`, `save_persona`, `load_personas_dir`, `load_capability_registry`, `save_capability_registry`, `LoadError`
- `src/voice_of_agents/core/__init__.py` — re-export key names
- `tests/unit/test_core_persona.py` — Pydantic validation tests for Persona + VoiceProfile
- `tests/unit/test_core_capability.py` — Capability + CapabilityRegistry tests
- `tests/unit/test_core_backlog.py` — BacklogItem + JSONL event sourcing tests
- `tests/fixtures/sample_persona.yaml` — canonical Pydantic-format persona fixture

### Files to Modify
- `src/voice_of_agents/core/__init__.py` — update from empty stub to export key symbols

### Explicitly Out of Scope
- Touching `pro-package/` code
- Touching `contracts/personas.py` (still used by Main — don't break it)
- Moving any existing files

## Implementation Notes

### `core/enums.py`
Source: copy from `pro-package/src/voice_of_agents/models/persona.py` and `models/workflow.py`.

```python
from enum import Enum

class Tier(str, Enum):
    FREE = "FREE"
    DEVELOPER = "DEVELOPER"
    TEAM = "TEAM"
    ENTERPRISE = "ENTERPRISE"

class ThemeCode(str, Enum):
    A = "A"  # Knowledge Retrieval Failure
    B = "B"  # Bus Factor / SPOF
    C = "C"  # Contextual Failure
    D = "D"  # Trust Deficit
    E = "E"  # Governance Vacuum
    F = "F"  # Integration Failure

class Segment(str, Enum):
    B2C = "b2c"
    B2B = "b2b"

class Intensity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ValidationStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    STALE = "stale"

class GoalCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    DELEGATION = "delegation"
    GOVERNANCE = "governance"
    MARKETPLACE = "marketplace"
    AUTOMATION = "automation"
    COLLABORATION = "collaboration"

class GoalPriority(str, Enum):
    PRIMARY = "primary"       # Day-1 use case
    SECONDARY = "secondary"   # Month-1 use case
    ASPIRATIONAL = "aspirational"  # Quarter-1 use case
```

### `core/pain.py`
```python
from pydantic import BaseModel
from typing import Optional
from voice_of_agents.core.enums import ThemeCode, Intensity

class PainPoint(BaseModel):
    description: str
    impact: str  # quantified, e.g. "45 min lost per incident"
    current_workaround: Optional[str] = None

class PainTheme(BaseModel):
    theme: ThemeCode
    intensity: Intensity
```

### `core/persona.py`
Key decisions:
- `VoiceProfile` has all-defaulted fields — never None, never needs guarding
- `Persona.voice` uses `default_factory=VoiceProfile` so it's always present
- `slug` property derives from `id` (int) + name
- `legacy_id` in metadata is only for migration tracing

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date
import re
from voice_of_agents.core.enums import Tier, Segment, ValidationStatus
from voice_of_agents.core.pain import PainPoint, PainTheme

class VoiceProfile(BaseModel):
    skepticism: Literal["low", "moderate", "high"] = "moderate"
    vocabulary: Literal["legal", "medical", "financial", "technical", "general"] = "general"
    motivation: Literal["fear", "ambition", "efficiency", "legacy", "compliance"] = "efficiency"
    price_sensitivity: Literal["low", "moderate", "high"] = "moderate"

class PersonaMetadata(BaseModel):
    source: Literal["manual", "generated", "hybrid"] = "manual"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    research_basis: Optional[str] = None
    validation_status: ValidationStatus = ValidationStatus.DRAFT
    legacy_id: Optional[str] = None  # e.g. "UXW-01" — for migration tracing only

class Persona(BaseModel):
    id: int
    name: str
    role: str
    industry: str
    segment: Segment
    tier: Tier
    age: Optional[int] = None
    income: Optional[int] = None
    org_size: int = 1
    experience_years: Optional[int] = None
    ai_history: Optional[str] = None
    mindset: Optional[str] = None
    pain_points: list[PainPoint] = []
    pain_themes: list[PainTheme] = []
    unmet_need: Optional[str] = None
    proof_point: Optional[str] = None
    trust_requirements: list[str] = []
    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    metadata: PersonaMetadata = Field(default_factory=PersonaMetadata)

    @property
    def slug(self) -> str:
        name_slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"{self.id:02d}-{name_slug}"

    def theme_intensity(self, theme_code: str):
        for pt in self.pain_themes:
            if pt.theme.value == theme_code:
                return pt.intensity
        return None

    def is_regulated(self) -> bool:
        from voice_of_agents.core.enums import Intensity
        intensity = self.theme_intensity("D")
        return intensity in (Intensity.HIGH, Intensity.CRITICAL)
```

### `core/capability.py`
```python
from pydantic import BaseModel, field_validator
from typing import Literal, Optional
import re

class TestResult(BaseModel):
    run_date: str
    status: Literal["pass", "fail", "skip", "not_tested"]
    personas_tested: list[int] = []

class Capability(BaseModel):
    id: str  # CAP-AREA-NAME format
    name: str
    description: str
    status: Literal["complete", "partial", "planned", "future"]
    feature_area: str
    api_endpoint: Optional[str] = None
    ui_page: Optional[str] = None
    dependencies: list[str] = []
    test_results: list[TestResult] = []
    requested_by: list[int] = []
    first_reported: Optional[str] = None

    def is_available(self) -> bool:
        return self.status in ("complete", "partial")

    def latest_test(self) -> Optional[TestResult]:
        return self.test_results[-1] if self.test_results else None

class CapabilityRegistry(BaseModel):
    product: str
    version: str
    capabilities: list[Capability]

    def get(self, capability_id: str) -> Optional[Capability]:
        for c in self.capabilities:
            if c.id == capability_id:
                return c
        return None

    def available(self) -> list[Capability]:
        return [c for c in self.capabilities if c.is_available()]

    def by_feature_area(self, area: str) -> list[Capability]:
        return [c for c in self.capabilities if c.feature_area == area]

    def by_status(self, status: str) -> list[Capability]:
        return [c for c in self.capabilities if c.status == status]

    def feature_areas(self) -> list[str]:
        return sorted(set(c.feature_area for c in self.capabilities))
```

### `core/backlog.py`
Unifies Main's `BacklogItem` + Pro's `FeatureRecommendation`. The JSONL event-sourcing functions from `contracts/backlog.py` are reproduced here (same logic, new imports).

```python
from pydantic import BaseModel
from typing import Literal, Optional
import json
from pathlib import Path
from datetime import datetime, timezone

class BacklogItem(BaseModel):
    id: str
    title: str
    description: str
    source: Literal["eval", "design", "bridge"]
    score: float = 0.0
    coverage_score: float = 0.0
    pain_score: float = 0.0
    revenue_score: float = 0.0
    effort_score: float = 0.0
    effort: Literal["trivial", "small", "medium", "large", "epic"] = "medium"
    status: Literal["open", "in_progress", "resolved", "deprioritized"] = "open"
    pain_themes: list[str] = []
    finding_id: Optional[str] = None
    personas: list[int] = []
    persona_quotes: list[str] = []
    acceptance_criteria: list[str] = []
    extends_capability: Optional[str] = None
    value_statement: Optional[str] = None

class BacklogEvent(BaseModel):
    ts: str
    type: Literal["item_added", "score_updated", "status_changed"]
    data: dict

# JSONL functions — append-only event log
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def add_item(path: Path, item: BacklogItem) -> None:
    event = BacklogEvent(ts=_now(), type="item_added", data=item.model_dump())
    with open(path, "a") as f:
        f.write(json.dumps(event.model_dump()) + "\n")

def update_score(path: Path, item_id: str, prev_score: float, new_score: float, reason: str) -> None:
    event = BacklogEvent(ts=_now(), type="score_updated",
                         data={"item_id": item_id, "prev_score": prev_score,
                               "new_score": new_score, "reason": reason})
    with open(path, "a") as f:
        f.write(json.dumps(event.model_dump()) + "\n")

def change_status(path: Path, item_id: str, prev_status: str, new_status: str, by: str, note: str) -> None:
    event = BacklogEvent(ts=_now(), type="status_changed",
                         data={"item_id": item_id, "prev_status": prev_status,
                               "new_status": new_status, "by": by, "note": note})
    with open(path, "a") as f:
        f.write(json.dumps(event.model_dump()) + "\n")

def materialize_backlog(path: Path) -> list[BacklogItem]:
    if not path.exists():
        return []
    items: dict[str, BacklogItem] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event["type"] == "item_added":
                item = BacklogItem(**event["data"])
                items[item.id] = item
            elif event["type"] == "score_updated":
                d = event["data"]
                if d["item_id"] in items:
                    items[d["item_id"]].score = d["new_score"]
            elif event["type"] == "status_changed":
                d = event["data"]
                if d["item_id"] in items:
                    items[d["item_id"]].status = d["new_status"]
    return sorted(items.values(), key=lambda x: x.score, reverse=True)
```

### `core/io.py`
```python
import yaml
from pathlib import Path
from voice_of_agents.core.persona import Persona
from voice_of_agents.core.capability import CapabilityRegistry

class LoadError(Exception):
    def __init__(self, path: Path, errors: list[str]):
        self.path = path
        self.errors = errors
        super().__init__(f"Failed to load {path}: {errors}")

def load_persona(path: Path) -> Persona:
    with open(path) as f:
        data = yaml.safe_load(f)
    try:
        return Persona(**data)
    except Exception as e:
        raise LoadError(path, [str(e)])

def load_personas_dir(directory: Path) -> list[Persona]:
    personas = []
    for p in sorted(directory.glob("P-*.yaml")):
        personas.append(load_persona(p))
    return sorted(personas, key=lambda x: x.id)

def save_persona(persona: Persona, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"P-{persona.id:02d}-{persona.slug.split('-', 1)[1]}.yaml"
    with open(path, "w") as f:
        yaml.dump(persona.model_dump(), f, default_flow_style=False, allow_unicode=True)
    return path

def load_capability_registry(path: Path) -> CapabilityRegistry:
    with open(path) as f:
        data = yaml.safe_load(f)
    try:
        return CapabilityRegistry(**data)
    except Exception as e:
        raise LoadError(path, [str(e)])

def save_capability_registry(registry: CapabilityRegistry, path: Path) -> None:
    with open(path, "w") as f:
        yaml.dump(registry.model_dump(), f, default_flow_style=False, allow_unicode=True)
```

### Test fixtures
`tests/fixtures/sample_persona.yaml` — use the Maria Gutierrez archetype in canonical Pydantic format (id: 1, not "UXW-01").

### Unit tests
- `test_core_persona.py`: test VoiceProfile defaults, Persona required fields, slug property, theme_intensity(), is_regulated()
- `test_core_capability.py`: test is_available(), latest_test(), registry.get(), available(), by_feature_area()
- `test_core_backlog.py`: test add_item, materialize_backlog replay, update_score accumulation, source field enforcement

## Acceptance Criteria
- [x] `src/voice_of_agents/core/enums.py` exists with all 7 enum classes
- [x] `src/voice_of_agents/core/pain.py` exists with `PainPoint` and `PainTheme`
- [x] `src/voice_of_agents/core/persona.py` exists with `VoiceProfile`, `PersonaMetadata`, `Persona`
- [x] `src/voice_of_agents/core/capability.py` exists with `TestResult`, `Capability`, `CapabilityRegistry`
- [x] `src/voice_of_agents/core/backlog.py` exists with `BacklogItem`, `BacklogEvent`, and JSONL functions
- [x] `src/voice_of_agents/core/io.py` exists with all 5 I/O functions
- [x] `VoiceProfile` instantiates with no arguments and all fields have defaults: `python -c "from voice_of_agents.core.persona import VoiceProfile; v = VoiceProfile(); assert v.skepticism == 'moderate'"`
- [x] `Persona` instantiates without providing `voice`: `python -c "from voice_of_agents.core.persona import Persona; p = Persona(id=1, name='Test', role='Dev', industry='Tech', segment='b2c', tier='FREE'); assert p.voice.motivation == 'efficiency'"`
- [x] `BacklogItem` requires `source` field: `python -c "from voice_of_agents.core.backlog import BacklogItem; BacklogItem(id='B-001', title='T', description='D', source='eval')"` succeeds; omitting `source` raises `ValidationError`
- [x] Existing `src/voice_of_agents/contracts/personas.py` is untouched and still importable
- [x] `pytest tests/unit/test_core_persona.py tests/unit/test_core_capability.py tests/unit/test_core_backlog.py -v` passes (56 tests, 0 failures)

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
python -c "from voice_of_agents.core.persona import Persona, VoiceProfile; p = Persona(id=1, name='Test', role='Dev', industry='Tech', segment='b2c', tier='FREE'); print(p.voice.skepticism, p.slug)"
python -c "from voice_of_agents.core.backlog import BacklogItem; b = BacklogItem(id='B-001', title='T', description='D', source='eval'); print(b.source)"
python -c "from voice_of_agents.core.capability import CapabilityRegistry; print('ok')"
# Verify existing code not broken:
python -c "from voice_of_agents.contracts.personas import Persona; print('legacy ok')"
pytest tests/unit/test_core_persona.py tests/unit/test_core_capability.py tests/unit/test_core_backlog.py -v
```

## Status
COMPLETE
