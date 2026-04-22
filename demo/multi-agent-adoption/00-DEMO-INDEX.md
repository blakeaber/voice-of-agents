# Demo: Multi-Agent Adoption Research → Eval
**Product:** Rooben Pro  
**Research question:** Do early adopters of multi-agent workflow tools abandon after initial setup because agent coordination failures erode trust faster than successful automations build it?  
**Date:** 2026-04-20

---

## Artifact Map

```
01-research-config.yaml          ← Inputs: research question, scope, model
multi-agent-adoption.yaml        ← Session state (4 stages complete, resumable)
SYNTHETIC-DATA-NOTICE.md         ← Auto-generated epistemic honesty notice
03-RESEARCH-SUMMARY.md           ← Stage 1+2 summary: hypotheses, segments, personas
05-DECISION-REPORT.md            ← Actionable decision output: build this first, kill these assumptions
06-seeded-personas/              ← 4 canonical Persona YAMLs (research → eval bridge)
  100-priya.yaml                 ← Early adopter who needs proof-of-value fast
  101-maya.yaml                  ← Partial adopter who froze at first coordination failure
  102-maya.yaml                  ← Abandoner who lost trust after plausible-but-wrong output
  103-maya.yaml                  ← Evaluator who rejected after onboarding friction
  BRIDGE-WORKFLOW.md             ← Field mapping: UXW sidecar → canonical Persona
07-eval-results/                 ← Eval pipeline outputs (Phases 2–5 against localhost:3000)
  003-focus-group-analysis.md    ← Cross-persona score summary + unmet needs themes
  005-backlog.md                 ← Prioritized backlog (12 items, scored)
  per-persona/                   ← Per-persona exploration + evaluation YAMLs
    100-priya-exploration.yaml
    100-priya-evaluation.yaml
    101-maya-exploration.yaml
    101-maya-evaluation.yaml
    102-maya-exploration.yaml
    102-maya-evaluation.yaml
    103-maya-exploration.yaml
    103-maya-evaluation.yaml
```

---

## Pipeline Summary

| Stage | Output | Key Finding |
|-------|--------|-------------|
| Stage 1: Product Research | 12 synthetic subjects, 4 segments | Trust erodes at the first plausible-but-wrong inter-agent output |
| Stage 2: Personas from Research | 4 archetypes (UXW-01–04) | Adopters need per-handoff observability; abandoners walk at silent failure |
| Stage 3: Workflows from Interviews | 4 episode maps | The inflection point is always a coordination failure, not a crash |
| Stage 4: Journey Redesign | Avg score 4.3/10 | Fix: replayable, diff-able inter-agent messages with semantic validation |
| Research → Eval Bridge | 4 canonical Personas seeded | Lineage preserved via `metadata.legacy_id = uxw_id` |
| Eval Phase 2: Exploration | 2 objectives per persona | Personas navigated the dashboard; blocked by missing onboarding and no product overview |
| Eval Phase 3: Evaluation | All 4 personas scored | Overall 2–4/10; trust 1–2/10; 0/4 would pay |
| Eval Phase 4: Synthesis | 15 findings | Top themes: Trust Deficit (D), Contextual Failure (C) |
| Eval Phase 5: Backlog | 15 backlog items | #1: Demonstrate product performance before asking for commitment |

---

## The Meta-Finding

All 4 personas got inside the product and explored the dashboard. What they found confirmed the research hypothesis from a different angle: **trust is lost before the first agent runs, but not because of a technical failure — because there's no onboarding that explains what the product does.**

The research predicted:
> *"Do early adopters abandon because agent coordination failures erode trust faster than successful automations build it?"*

The eval found the trust gap arrives even before the first agent: personas navigated a working product but couldn't determine whether it solved their problem. No product overview, no demo mode, no "here's what you can do." They were asked to create a workflow before they understood the value.

The top backlog item: **Demonstrate actual product performance before asking for commitment** — not a technical fix, a positioning fix.

---

## How to Use These Artifacts

- **Share `05-DECISION-REPORT.md`** with your engineering lead as the sprint anchor
- **Share `07-eval-results/005-backlog.md`** to prioritize your next 2 weeks
- **Recruit users matching archetypes** in `06-seeded-personas/` for validation interviews
- **Promote validated archetypes** by setting `metadata.validation_status: validated` in the persona YAML
