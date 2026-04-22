# Research → Eval Bridge

This document explains how to use synthetic research output to seed the eval pipeline.

## What the bridge does

The `voice_of_agents.research.bridge` module converts `UXWPersonaSidecar` objects
(research output) into canonical `Persona` objects (eval input). This closes the
loop between "what users need" (research) and "does our product serve them" (eval).

## Basic usage

```python
from voice_of_agents.research.session import ResearchSession
from voice_of_agents.research.bridge import session_to_personas
from pathlib import Path

# Load a completed research session
session = ResearchSession.load(Path("research-sessions/my-research.yaml"))

# Convert research personas to eval-ready Personas
personas = session_to_personas(session)

# Use in eval
from voice_of_agents.eval import run_eval
results = run_eval(personas=personas)
```

## CLI usage

```bash
# Seed the eval pipeline from a research session
voa research seed-eval research-sessions/my-research.yaml

# This writes personas to data/personas/ in the standard format
voa research seed-eval research-sessions/my-research.yaml --output data/personas/
```

## What gets mapped

| Research field | Eval field |
|---|---|
| `UXWPersonaSidecar.name` | `Persona.name` |
| `UXWPersonaSidecar.jtbd` | `Persona.mindset` |
| `UXWPersonaSidecar.constraint_profile` | `Persona.pain_points[0]` |
| `UXWPersonaSidecar.failure_or_abandonment_mode` | `Persona.pain_points[1]` |
| `UXWPersonaSidecar.anti_model_of_success` | `Persona.unmet_need` |
| `UXWPersonaSidecar.adoption_trajectory` | `Persona.ai_history` |
| `UXWPersonaSidecar.uxw_id` | `Persona.metadata.legacy_id` |

All bridged personas have `metadata.source="generated"` and `validation_status=DRAFT`.
Promote to `validated` after a real user confirms the archetype.
