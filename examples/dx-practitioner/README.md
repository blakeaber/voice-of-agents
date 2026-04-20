# DX Practitioner Example

**Who this is for:** Developer experience practitioners, platform engineers, and developer advocates building AI-assisted tools for engineering teams.

**What you'll do:** Run the full research → eval bridge workflow: synthetic research identifies behavioral archetypes, which are converted into canonical eval Personas for your LLM evaluation pipeline.

**Cost:** ~$0.08 with Haiku | **Time:** 10-15 minutes

## Why this workflow matters

If you're building an AI product and using LLM-as-judge evaluation, your eval personas should represent the actual users you're building for — not generic "power user" and "novice user" abstractions.

This example:
1. Runs synthetic research on DX tool adoption (adopters, abandoners, skeptics, critics)
2. Extracts behavioral archetypes from the research output
3. Converts them into canonical `Persona` objects with constraint profiles, failure modes, and behavioral signals
4. Seeds your eval pipeline with research-grounded personas

## Setup

```bash
export ANTHROPIC_API_KEY=sk-...
cd examples/dx-practitioner
```

## Run

```bash
chmod +x run.sh
./run.sh
```

## What you'll see

The script runs in 4 steps:
1. Config validation
2. Cost estimate with confirmation
3. Research pipeline (Stages 1 + 2 for personas)
4. Eval seeding: personas written to `data/personas/`

## What you get

**`data/personas/`** — Research-grounded Persona YAML files, one per archetype:
- `100-alice.yaml` — The early adopter who champions it internally
- `101-bob.yaml` — The abandoner who lost trust after one bad suggestion
- `102-carol.yaml` — The skeptic who never got past the setup step

Each persona has:
- `metadata.source = "generated"` — clearly labeled as synthetic
- `metadata.validation_status = "draft"` — promotes to "validated" after real confirmation
- `metadata.legacy_id = "UXW-01"` — traces back to the research session

**`data/personas/BRIDGE-WORKFLOW.md`** — Full documentation of the research → eval mapping.

## Use the seeded personas in eval

```python
from pathlib import Path
from voice_of_agents.core.persona import Persona
import yaml

persona_files = list(Path("data/personas").glob("*.yaml"))
personas = []
for f in persona_files:
    if f.name != "BRIDGE-WORKFLOW.md":
        data = yaml.safe_load(f.read_text())
        personas.append(Persona(**data))

# Use in your eval suite
from voice_of_agents.eval import run_eval
results = run_eval(personas=personas)
```

## Promote to validated

After a real user confirms an archetype:

```python
import yaml
from pathlib import Path
from voice_of_agents.core.enums import ValidationStatus

path = Path("data/personas/100-alice.yaml")
data = yaml.safe_load(path.read_text())
data["metadata"]["validation_status"] = ValidationStatus.VALIDATED.value
path.write_text(yaml.dump(data))
```

## What to do after the run

1. Read `data/personas/BRIDGE-WORKFLOW.md`
2. Recruit 1-2 real users who match each archetype profile
3. Confirm or refute the archetype in a 30-minute call
4. Promote confirmed archetypes to `validated`
5. Run your eval suite with the research-grounded personas

## See also

- [Solo founder example](../solo-founder/) — Full pipeline with CLI and decision report
- [Product engineer example](../product-engineer/) — `quick_research()` one-liner
- [docs/BRIDGE-WORKFLOW.md](../../docs/BRIDGE-WORKFLOW.md) — Full bridge reference documentation
- [MANIFESTO.md](../../docs/MANIFESTO.md) — The worldview behind this library
