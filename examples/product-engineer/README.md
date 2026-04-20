# Product Engineer Example

**Who this is for:** Product engineers and PMs who own the roadmap and need behavioral signal before the next sprint.

**What you'll do:** Use the `quick_research()` one-liner API to get decision-oriented findings in under 10 minutes, with no config files.

**Cost:** ~$0.30 with Opus | **Time:** 5-10 minutes

## Setup

```bash
export ANTHROPIC_API_KEY=sk-...
cd examples/product-engineer
pip install voice-of-agents  # or: pip install -e ../../
```

## Run

```bash
python run.py
```

## What you'll see

```
BUILD THIS FIRST:
  Ship a "first win in 5 minutes" onboarding flow...

TOP FINDINGS:
  1. Product engineers abandon tools when the import step takes >10 minutes
  2. ...

USER ARCHETYPES:
  [UXW-01] The Pragmatic Engineer
    Top concern: I need this to integrate with Jira or I can't use it
    Would pay if: it saves me one stakeholder meeting per sprint

VALIDATE WITH REAL USERS:
  1. Walk me through the last time you had to justify a roadmap decision to...
  2. ...
```

## Customize

Edit `run.py` to change `what`, `who`, and `understand` to match your product.

```python
result = quick_research_sync(
    what="YOUR PRODUCT DESCRIPTION",
    who="YOUR TARGET USER",
    understand="THE #1 THING YOU WANT TO UNDERSTAND",
)
```

## Access full session data

The `result.session` field gives you the full typed `ResearchSession`:

```python
# Full hypothesis verdicts
for score in result.session.product_research_output.hypothesis_scores:
    print(f"{score.hypothesis_id}: {score.verdict}")

# Full persona sidecars with verbatim quotes
for sidecar in result.session.persona_research_output.persona_sidecars:
    for quote in sidecar.verbatim_quote_bank:
        print(f"[{sidecar.name}] {quote.text}")
```

## What to do with the output

1. Share `build_this_first` with your engineering lead — this is your next sprint anchor
2. Use `validate_with` questions in your next user interview
3. Cross-reference `churn_triggers` with your current activation metrics
4. If a finding contradicts your existing data, trust your data — not the synthetic output

## See also

- [Solo founder example](../solo-founder/) — Full pipeline with CLI, decision report, config file
- [DX practitioner example](../dx-practitioner/) — Research → eval bridge workflow
- [MANIFESTO.md](../../docs/MANIFESTO.md) — Why synthetic research is a forcing function, not a conclusion
