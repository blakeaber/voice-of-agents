# Voice of Agents

Persona-driven UX evaluation pipeline. Adaptive exploration, synthetic focus groups, and prioritized backlogs.

## What it does

Voice of Agents (VoA) runs personas through your product to discover what works, what's broken, and what's missing. Each persona has fixed objectives and perspectives but adaptive journeys — they explore the app as a real user would, discovering new features and hitting real friction points.

The pipeline:
1. **Phase 1** — Define personas (or generate them from app analysis)
2. **Phase 2** — Explore the app as each persona via Playwright
3. **Phase 3** — Generate in-character evaluations (synthetic focus group)
4. **Phase 4** — Synthesize findings across all personas
5. **Phase 5** — Score and prioritize the backlog

All data is append-only. Nothing is ever overwritten. Re-runs produce new timestamped results and diff reports.

## Quick start

```bash
pip install -e ".[dev]"
playwright install chromium

# Initialize eval project pointing at your running app
voa eval init --target http://localhost:3000 --api http://localhost:8420

# Migrate existing UXW-format personas to canonical format
voa eval migrate

# Run the full eval pipeline
voa eval run --all

# Check status
voa eval status

# View the backlog
voa eval backlog
```

## CLI Reference

### Design phase
```
voa design persona list --dir .
voa design persona generate-prompt --product X --description Y --industry Z --roles A,B
voa design persona import FILE --dir .
voa design persona validate --dir .
voa design workflow list --dir .
voa design workflow generate-prompt PERSONA_ID --dir .
voa design workflow import FILE PERSONA_ID --dir .
voa design analyze gaps --dir .
voa design analyze coverage --dir .
voa design validate --dir .
```

### Eval phase
```
voa eval init --target http://localhost:3000 --api http://localhost:8420
voa eval migrate [--dry-run] [--no-backup]   # convert UXW-format personas to canonical format
voa eval phase1                              # generate or validate personas
voa eval phase2 [--personas X,Y | --batch N | --all]
voa eval phase3 [--personas X,Y | --batch N | --all]
voa eval phase4
voa eval phase5
voa eval run [--all]                         # full pipeline (phases 2-5)
voa eval status                              # evaluation progress
voa eval backlog                             # pretty-print current backlog
voa eval capabilities                        # pretty-print capability registry
voa eval diff                                # generate diff report vs prior run
```

### Bridge (cross-layer)
```
voa bridge status                            # per-persona design + eval coverage
voa bridge sync-gaps [--dir .]              # push gap analysis findings into backlog.jsonl
```

## Data model

Everything is file-based and git-friendly:
- `data/personas/P-*.yaml` — Canonical persona definitions (Pydantic-validated)
- `data/personas/_legacy/` — Original UXW-format backups (migration artifacts)
- `data/workflows/PWM-*.yaml` — Persona workflow mappings (design layer)
- `data/capabilities.yaml` — Unified capability registry
- `data/results/{id}-{name}/{timestamp}/` — Per-persona, timestamped results (append-only)
- `data/backlog.jsonl` — Append-only event log (never overwritten)
- `data/005-backlog.md` — Human-readable view (generated from JSONL)
- `data/004-findings.md` — Synthesized findings (additive sections)
- `data/006-diff-report.md` — Run-over-run comparisons (additive)

## Design principles

- **Personas are explorers, not test scripts.** Objectives are fixed; journeys adapt.
- **Append-only persistence.** Nothing is ever deleted. Items are marked resolved, not removed.
- **Voice calibration.** Evaluations reflect authentic persona perspectives (skepticism, vocabulary, motivation).
- **Re-runnable.** Every run produces new timestamped data. Diff reports show progress over time.
