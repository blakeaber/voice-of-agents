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

# Initialize project pointing at your running app
voa init --target http://localhost:3000 --api http://localhost:8420

# Import existing personas (e.g., from rooben-pro)
voa import personas ~/Documents/rooben-pro/docs/ux-workflows/personas/

# Run the full pipeline for a batch of 5 personas
voa run --batch 1

# Check status
voa status

# View the backlog
voa backlog
```

## CLI Reference

```
voa init          Initialize project config
voa import        Import personas or feature inventory
voa phase1        Generate or validate personas
voa phase2        Adaptive persona exploration (browser)
voa phase3        Synthetic focus group evaluations
voa phase4        Finding synthesis
voa phase5        Backlog scoring and prioritization
voa run           Full pipeline (phases 2-5)
voa status        Show evaluation progress
voa backlog       Pretty-print current backlog
voa inventory     Pretty-print feature inventory
voa diff          Generate diff report vs prior run
```

## Data model

Everything is file-based and git-friendly:
- `data/personas/*.yaml` — Persona definitions (stable)
- `data/results/UXW-{id}-{name}/{timestamp}/` — Per-persona, timestamped results (append-only)
- `data/backlog.jsonl` — Append-only event log (never overwritten)
- `data/005-backlog.md` — Human-readable view (generated from JSONL)
- `data/004-findings.md` — Synthesized findings (additive sections)
- `data/006-diff-report.md` — Run-over-run comparisons (additive)

## Design principles

- **Personas are explorers, not test scripts.** Objectives are fixed; journeys adapt.
- **Append-only persistence.** Nothing is ever deleted. Items are marked resolved, not removed.
- **Voice calibration.** Evaluations reflect authentic persona perspectives (skepticism, vocabulary, motivation).
- **Re-runnable.** Every run produces new timestamped data. Diff reports show progress over time.
