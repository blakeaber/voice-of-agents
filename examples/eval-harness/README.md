# Eval harness example — voa-config.json template

The eval pipeline (`voa eval *` commands) expects a `voa-config.json` file
in the current working directory of your project. This directory contains
a template you can copy as a starting point.

## Usage

```bash
# From the root of YOUR project (not this repo):
voa eval init --target http://your-app.local:3000 --api http://your-app.local:8420
```

That command writes a fresh `voa-config.json` with sensible defaults. If
you need to customize it further, copy `voa-config.example.json` from
this directory and edit the fields:

```bash
cp path/to/voice-of-agents/examples/eval-harness/voa-config.example.json \
   ./voa-config.json
```

## What the fields control

- `target_url` — the URL of the running web app that personas will
  navigate (the Playwright `browser.navigate(target_url)` target)
- `api_url` — the target app's API base URL, used for auth seeding if the
  app exposes a signup endpoint
- `data_dir` — where personas, results, and backlog artifacts are written
  (default `./data/`)
- `batch_size` — how many personas to explore in parallel during
  `voa eval run`
- `weight_*` — scoring weights for backlog prioritization; must sum to 1.0
- `pain_themes` — reference map of pain-theme codes (A–F) to human-readable
  labels; used only for display in the backlog report

## Further reading

- [CLI reference](../../README.md#cli-reference) in the main README
- [Bridge workflow](../../docs/BRIDGE-WORKFLOW.md) — research → eval loop
