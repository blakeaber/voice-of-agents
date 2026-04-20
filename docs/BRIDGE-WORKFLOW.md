# Research → Eval Bridge

This document explains how to use synthetic research output to seed the eval pipeline.
The bridge is the most unique workflow in Voice of Agents — it closes the loop between
"what users need" (research) and "does our product serve them" (eval).

## Why this matters

If you're building an AI product and using LLM-as-judge evaluation, your eval personas
should represent the actual users you're building for — not generic "power user" and
"novice user" abstractions.

Research personas include:
- **Constraint profiles** — what's limiting these users (time, trust, budget, org politics)
- **Failure modes** — what caused abandonment or rejection
- **Anti-models of success** — what they're actively trying to avoid
- **Verbatim quote banks** — exact language patterns from their segment

These map directly to the behavioral signals you need in eval rubrics.

## CLI workflow (recommended)

```bash
# Step 1: Run research through at least Stage 2 (personas)
voa research run research-config.yaml

# Step 2: Convert research personas to eval-ready Persona YAML files
voa research seed-eval research-sessions/my-research.yaml --output data/personas/

# Step 3: Run eval with research-grounded personas
voa eval run --all
```

## Python workflow

```python
from pathlib import Path
from voice_of_agents.research.session import ResearchSession
from voice_of_agents.research.bridge import session_to_personas

# Load a completed research session
session = ResearchSession.load(Path("research-sessions/my-research.yaml"))

# Convert research personas to eval-ready Persona objects
personas = session_to_personas(session, starting_id=100)

# All personas have metadata.source="generated", validation_status="draft"
for p in personas:
    print(f"{p.slug}: {p.mindset}")
    print(f"  Pain: {p.pain_points[0].description}")
    print(f"  Legacy ID: {p.metadata.legacy_id}")  # traces back to UXW-01, etc.
```

## What gets mapped

| Research field | Eval field | Notes |
|---|---|---|
| `UXWPersonaSidecar.name` | `Persona.name` | |
| `UXWPersonaSidecar.jtbd` | `Persona.mindset` | |
| `UXWPersonaSidecar.constraint_profile` | `Persona.pain_points[0].description` | |
| `UXWPersonaSidecar.failure_or_abandonment_mode` | `Persona.pain_points[1].description` | Only if non-empty |
| `UXWPersonaSidecar.anti_model_of_success` | `Persona.unmet_need` | |
| `UXWPersonaSidecar.adoption_trajectory` | `Persona.ai_history` | |
| `UXWPersonaSidecar.uxw_id` | `Persona.metadata.legacy_id` | Preserves lineage |
| Context segment (B2B/B2C) | `Persona.segment` | Inferred from segment_source |
| Adoption status (abandoner → high) | `Persona.voice.price_sensitivity` | |

## Validation status lifecycle

All bridged personas start with `validation_status = "draft"`.

Promote to `"validated"` after a real user confirms the archetype:

```python
import yaml
from pathlib import Path
from voice_of_agents.core.enums import ValidationStatus

path = Path("data/personas/100-alice.yaml")
data = yaml.safe_load(path.read_text())
data["metadata"]["validation_status"] = ValidationStatus.VALIDATED.value
path.write_text(yaml.dump(data))
```

## Single-persona conversion

For fine-grained control, convert one sidecar at a time:

```python
from voice_of_agents.research.bridge import sidecar_to_canonical_persona
from voice_of_agents.research.models import ContextSegment, AdoptionStatus

persona = sidecar_to_canonical_persona(
    sidecar=sidecar,
    persona_id=101,
    role="Senior Product Engineer",
    industry="B2B SaaS",
    context_segment=ContextSegment.B2B_MID,
    adoption_status=AdoptionStatus.ABANDONER,
    session_slug="my-research",
)
```

## See also

- [DX Practitioner Example](../examples/dx-practitioner/) — Full end-to-end walkthrough
- [Research Module API](../src/voice_of_agents/research/__init__.py) — Full public API
- [MANIFESTO.md](MANIFESTO.md) — Why this workflow exists
