# Voice of Agents

[![PyPI version](https://img.shields.io/pypi/v/voice-of-agents.svg)](https://pypi.org/project/voice-of-agents/)
[![Python versions](https://img.shields.io/pypi/pyversions/voice-of-agents.svg)](https://pypi.org/project/voice-of-agents/)
[![CI](https://github.com/blakeaber/voice-of-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/blakeaber/voice-of-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [**Beta users lie.**](https://www.predicate.ventures/writing/beta-users-are-lying) Simulate them honestly, then validate the risky findings with the users you still need to talk to.

<p align="center">
  <img src="assets/demo.gif" alt="voa research demo running in a terminal" width="720">
</p>

---

## Why this exists

- **The problem:** Pre-PMF user research is too slow and expensive, so founders ship by vibe and learn why users churn only *after* they've churned.
- **The approach:** A 4-stage synthetic research pipeline (subjects → personas → workflows → journey) with mandatory epistemic framing — synthetic data is marked as hypothesis, not finding.
- **The twist:** Synthetic personas feed directly into a live browser-based eval harness that navigates your actual product. The loop goes from *"I don't know my users"* to *"here are typed personas failing to adopt my product"* in under 15 minutes.

---

## Quick start

```bash
pip install voice-of-agents
cp .env.example .env          # then paste your key into .env
voa doctor                    # pre-flight check — recommended first command
```

### 60-second demo — zero API key required

```bash
voa research demo --offline
```

Uses a bundled cassette of a real pipeline run. Prints findings to your terminal in under 10 seconds. No Anthropic account needed.

### Live demo (requires `ANTHROPIC_API_KEY`)

```bash
voa research demo
```

Runs a preset research question with 10 subjects. ~$0.30 with Opus, ~$0.02 with Haiku.

### Plain-English setup

```bash
voa research quickstart        # 3 plain-English questions; no methodology vocabulary
voa research run --model-haiku # low-cost exploration run
```

### One-liner Python API

```python
from voice_of_agents.research import quick_research_sync

result = quick_research_sync(
    what="a coding assistant that helps developers write tests",
    who="senior developers at startups",
    understand="why developers abandon AI coding tools after the first week",
)

print(result.build_this_first)            # "Ship a 'first win in 5 minutes' onboarding flow..."
print(result.validate_with)               # ["Walk me through the last time...", ...]
print(result.personas[0].would_pay_if)    # "It catches one bug I would have shipped..."
```

---

## Who is this for?

- **Pre-PMF solo founders** — you need decisions, not just findings. Start with [`examples/solo-founder/`](examples/solo-founder/).
- **Product engineers owning a roadmap** — you want a one-liner Python API to seed user-archetype hypotheses. Start with [`examples/product-engineer/`](examples/product-engineer/).
- **DX practitioners / platform leads** — you want the full research → eval bridge: synthetic personas navigating your actual product. Start with [`examples/dx-practitioner/`](examples/dx-practitioner/).

---

## Proof, not claims

[`demo/multi-agent-adoption/`](demo/multi-agent-adoption/00-DEMO-INDEX.md) is a complete end-to-end run of the pipeline against a real product: research config → decision report → 4 seeded eval personas → browser exploration logs → per-persona evaluations → focus-group analysis → prioritized backlog.

Read it top-to-bottom before running your own. It shows what "good" output looks like, so you can calibrate your expectations before spending API budget.

---

## What this is (and is not)

Voice of Agents is a Python library that simulates user research using the Claude API. It runs a synthetic sampling frame — including adopters, abandoners, skeptics, and critics — and returns decision-oriented output: what to build first, what to validate with real users, and what would make each user type leave.

**It is not a replacement for real research.** It is a forcing function for better questions.

Every session emits a `SYNTHETIC-DATA-NOTICE.md` that tells you exactly what to ask real users to validate the highest-risk findings. The output is a map of the hypothesis space, not a conclusions report.

Read the [Manifesto](docs/MANIFESTO.md) for the full worldview.

---

## The research → eval bridge

The workflow that differentiates this library: use synthetic research personas to seed your LLM evaluation pipeline.

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
voa research demo [--offline]              # preset demo; --offline uses bundled cassette (no API key)
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

### Diagnostic

```
voa doctor [--offline]                     # pre-flight check of Python, API key, Playwright, disk
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

## Data model

Everything is file-based and git-friendly:

- `research-sessions/*.yaml` — ResearchSession state (resumable after any stage)
- `research-sessions/SYNTHETIC-DATA-NOTICE.md` — honest framing + validation questions
- `research-sessions/DECISION-REPORT.md` — what to build, kill, and validate
- `data/personas/P-*.yaml` — canonical persona definitions (Pydantic-validated)
- `data/results/{id}-{name}/{timestamp}/` — per-persona, timestamped eval results
- `data/backlog.jsonl` — append-only backlog event log

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
git clone https://github.com/blakeaber/voice-of-agents.git
pip install -e ".[dev]"
pre-commit install
pytest
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for branch conventions and PR guidelines. Security issues go to [`SECURITY.md`](SECURITY.md) (not public GitHub issues).

---

## License

MIT © 2026 Blake Aber. See [`LICENSE`](LICENSE).
