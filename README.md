# Voice of Agents

Research-grade rigor for developers who can't afford a research team.

```python
from voice_of_agents.research import quick_research_sync

result = quick_research_sync(
    what="a coding assistant that helps developers write tests",
    who="senior developers at startups",
    understand="why developers abandon AI coding tools after the first week",
)

print(result.build_this_first)   # "Ship a 'first win in 5 minutes' onboarding flow..."
print(result.validate_with)      # ["Walk me through the last time...", ...]
print(result.personas[0].would_pay_if)  # "It catches one bug I would have shipped..."
```

---

## What this is

Voice of Agents is a Python library that simulates user research using the Claude API. It runs a synthetic sampling frame — including adopters, abandoners, skeptics, and critics — and returns decision-oriented output: what to build first, what to validate with real users, and what would make each user type leave.

**It is not a replacement for real research.** It is a forcing function for better questions.

Every session emits a `SYNTHETIC-DATA-NOTICE.md` that tells you exactly what to ask real users to validate the highest-risk findings. The output is a map of the hypothesis space, not a conclusions report.

Read the [Manifesto](docs/MANIFESTO.md) for the full worldview.

---

## Quick start

```bash
pip install voice-of-agents  # or: git clone + pip install -e ".[dev]"
cp .env.example .env          # then paste your key into .env
```

### 60-second demo (no config required)

```bash
voa research demo
```

This runs a preset research question about developer tool adoption with 10 subjects and displays findings in your terminal. ~$0.30 with Opus, ~$0.02 with Haiku.

### Plain-English setup (3 questions, no methodology vocabulary)

```bash
voa research quickstart
```

Asks you 3 plain-English questions. Uses Claude to translate your answers into a valid research config. Then run:

```bash
voa research run --model-haiku  # low cost
```

### One-liner API (Python)

```python
from voice_of_agents.research import quick_research_sync

result = quick_research_sync(
    what="YOUR PRODUCT",
    who="YOUR USERS",
    understand="THE #1 THING YOU WANT TO UNDERSTAND",
)
```

---

## The research → eval bridge

The most unique workflow: use synthetic research personas to seed your LLM evaluation pipeline.

```bash
# Run research through Stage 2 (personas)
voa research run research-config.yaml

# Convert research personas to eval-ready Persona objects
voa research seed-eval research-sessions/my-research.yaml --output data/personas/

# Run eval with research-grounded personas
voa eval run --all
```

Research personas have constraint profiles, failure modes, and anti-models of success — exactly the signal you need to write eval rubrics that catch what your real users will complain about.

See [docs/BRIDGE-WORKFLOW.md](docs/BRIDGE-WORKFLOW.md) for the full workflow.

---

## Cost transparency

Before any API calls:

```bash
voa research run research-config.yaml --dry-run
# Estimated cost: $1.20–$2.10 | Estimated time: 8–15 minutes

voa research run research-config.yaml --dry-run --model-haiku
# Estimated cost: $0.06–$0.11 | Estimated time: 5–8 minutes
```

---

## CLI reference

### Research pipeline

```
voa research demo                          # 60-second preset demo, no config
voa research quickstart                    # 3-question plain-English setup
voa research init [slug]                   # create research-config.yaml interactively
voa research validate-config [config]      # pre-flight check, no API calls
voa research run [config] [--dry-run]      # run pipeline (all stages or one)
  --model-haiku                            # use Haiku (~1/20th the cost)
  --stage [all|product-research|personas|workflows|journey]
  --session path/to/session.yaml           # resume a partial run
voa research status session.yaml           # show completion state
voa research export session.yaml           # emit RESEARCH-SUMMARY.md
voa research seed-eval session.yaml        # convert personas to eval Personas
voa research list-sessions                 # list all sessions
```

### Eval pipeline

```
voa eval init --target http://localhost:3000 --api http://localhost:8420
voa eval run [--all]
voa eval status
voa eval backlog
voa eval capabilities
voa eval diff
```

The eval browser layer is LLM-driven — a Claude Sonnet 4.6 vision agent navigates the live app, selects elements, and decides when an exploration goal has succeeded or stalled. It is not a Playwright test runner.

### Design phase

```
voa design persona list|generate-prompt|import|validate
voa design workflow list|generate-prompt|import
voa design analyze gaps|coverage
```

### Bridge (cross-layer)

```
voa bridge status
voa bridge sync-gaps
```

---

## Programmatic API

```python
# Primary API — one function, plain-English inputs
from voice_of_agents.research import quick_research_sync
result = quick_research_sync(what=..., who=..., understand=...)

# Full pipeline — for complete research sessions
from voice_of_agents.research import run_full_pipeline_sync
from voice_of_agents.research.config import ResearchConfig
config = ResearchConfig.from_file(Path("research-config.yaml"))
session = run_full_pipeline_sync(config)

# Plain-English config — no methodology vocabulary required
import asyncio
config = asyncio.run(ResearchConfig.from_plain_english(
    what="a Slack bot that tracks action items",
    who="engineering managers at startups",
    understand="why teams stop using action item trackers",
))

# Real signal ingestion — augment synthetic research with real data
from voice_of_agents.research.signals import from_transcripts, from_csv
signals = from_transcripts(["interview1.txt", "interview2.txt"])
signals2 = from_csv("nps_responses.csv", text_column="comment")

# Research → eval bridge
from voice_of_agents.research.bridge import session_to_personas
personas = session_to_personas(session)  # list[Persona] ready for eval

# Cost estimation before any API calls
from voice_of_agents.research.cost import estimate_run_cost
estimate = estimate_run_cost(model="claude-opus-4-7", subject_count=12)
print(estimate.display())
```

---

## Examples

| Example | For | What it shows |
|---------|-----|---------------|
| [Solo founder](examples/solo-founder/) | Pre-PMF solo founders | quickstart → run → decision-report |
| [Product engineer](examples/product-engineer/) | Product engineers and PMs | `quick_research()` one-liner, output parsing |
| [DX practitioner](examples/dx-practitioner/) | Platform engineers, developer advocates | Full research → eval bridge |

### Worked example: full pipeline output

[`demo/multi-agent-adoption/`](demo/multi-agent-adoption/) captures a complete end-to-end run of the pipeline against a real product — research config, decision report, 4 seeded eval personas, browser exploration logs, per-persona evaluations, focus-group analysis, and prioritized backlog. Read it top-to-bottom before running your own.

---

## Data model

Everything is file-based and git-friendly:

- `research-sessions/*.yaml` — ResearchSession state (resumable after any stage)
- `research-sessions/SYNTHETIC-DATA-NOTICE.md` — Honest framing + validation questions
- `research-sessions/DECISION-REPORT.md` — What to build, kill, and validate
- `data/personas/P-*.yaml` — Canonical persona definitions (Pydantic-validated)
- `data/results/{id}-{name}/{timestamp}/` — Per-persona, timestamped eval results
- `data/backlog.jsonl` — Append-only backlog event log

---

## Design principles

- **Research is a forcing function, not a conclusion.** Every finding is a hypothesis until validated with a real user.
- **Include the users who left.** The sampling frame mandates a minimum of abandoners, rejecters, and critics.
- **Epistemic honesty is non-negotiable.** Every session writes `SYNTHETIC-DATA-NOTICE.md`. There is no option to suppress it.
- **Personas are explorers, not test scripts.** Objectives are fixed; journeys adapt.
- **Append-only persistence.** Nothing is ever deleted.

---

## Contributing

Read the [Manifesto](docs/MANIFESTO.md) to understand the worldview. Fork it, argue with it, open a PR.

```bash
git clone https://github.com/blakeaber/voice-of-agents
pip install -e ".[dev]"
pytest
```
