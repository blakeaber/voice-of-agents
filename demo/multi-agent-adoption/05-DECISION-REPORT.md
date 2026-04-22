# Decision Report

> This is the output you act on. Every finding is backed by the synthetic research.
> Validate the highest-risk items with 3 real user calls before committing resources.

## Build This First

Ship a per-handoff semantic validation layer with deterministic checkpoints and replayable, diff-able inter-agent messages — so every agent-to-agent transfer either passes an explicit correctness assertion or fails loudly with a reconstructable trace, before any side effect.

## Kill These Assumptions

- That a visual DAG with green checkmarks constitutes observability — for every segment interviewed, green checks over probabilistic handoffs are an anti-signal, not reassurance.
- That the conversational refine flow is the recovery path — it is read as symptom-patching that accumulates untestable debt and confirms a leaky abstraction.
- That more agents = more leverage — solo operators and small teams explicitly read N-agent decomposition as N-times-hallucination-surface and retreat to single-LLM scripts.
- That correctness is a prompt-engineering problem — responding to a wrong output with 'try a better prompt' is a permanent disqualifier for the reliability-engineer segment.
- That users abandon on loud failures — abandonment is almost always triggered by plausible-but-wrong output cosigned by a downstream agent, not by crashes.
- That integrations and pricing pages drive adoption — for pattern-matchers, the trust/failure-semantics story is missing at the landing-page level and nothing downstream matters until it exists.

## User Segments (Plain English)

- **Audit-Burdened Reliability Engineers**: Technical operators in regulated or ops-critical contexts who treat silent partial correctness as strictly worse than a crash and judge tools on verifiability primitives, not visual polish.
- **Solo Operators Retreating to Single-LLM Scripts**: One-person businesses with real reputational exposure who tried multi-agent orchestration, concluded it multiplies hallucination surface without leverage, and retreated to a single LLM call plus their own guardrails.
- **Pre-Refusal Pattern-Matchers**: Technically fluent practitioners who recognize the multi-agent silent-failure pattern from prior exposure and refuse to invest setup time when the landing page leads with a DAG and no correctness story.
- **Hedged Partial Adopters**: Users who neither adopt nor churn — they quarantine the tool to low-blast-radius workflows, keep paying, and never expand because no mechanism explains why a prior handoff went wrong.

## What Would Make Users Leave

- Audit-Burdened Reliability Engineers: a confidently-formatted output that passes the DAG but is subtly wrong on manual re-verification, especially if the vendor's suggested fix is prompt iteration.
- Solo Operators Retreating to Single-LLM Scripts: discovering a fabricated field was laundered through a downstream 'QA agent' and shipped to paying subscribers under their name.
- Pre-Refusal Pattern-Matchers: seeing the multi-agent DAG on the landing page with no upfront story about handoff contracts or failure semantics — they never start the trial.
- Hedged Partial Adopters: a second plausible-but-wrong output after using refine, with no diagnostic explaining why the handoff failed — they freeze scope permanently rather than churn.

## Pricing Signals

- Solo operators sit in a $29–$400/mo band, personal card, cancel mid-month without ceremony — price is not the blocker, perceived verification tax is.
- Small technical teams are happy to pay $100–$200/mo when debuggability is solved; budget is explicitly not the binding constraint.
- Mid-market/regulated: ~$500/mo is discretionary for a solo buyer; anything above routes through VP/procurement and requires SOC2 Type II minimum, with HIPAA/PCI/BAA/VPC for regulated subsegments.
- Across all segments, willingness to pay collapses to zero the moment the tool is perceived as shifting work from 'doing the task' to 'auditing the machine' — ROI is measured in verification-time saved, not features.

## Hypotheses: What the Research Supports

- Abandonment is driven by plausible-but-wrong outputs cosigned by downstream agents, not by loud coordination failures — the 70–85% correct zone is the kill zone.
- Visual DAG observability is insufficient and often anti-signal; users need semantic correctness guarantees at each handoff, not structural visualization.
- The conversational refine flow accelerates distrust rather than rebuilding it, because it patches symptoms without exposing root cause of handoff failure.

## Hypotheses: What the Research Refuted

- That successful automations eventually build enough trust to offset occasional coordination errors — they don't; one laundered hallucination permanently shrinks scope.
- That better prompt iteration / refinement UX is the primary lever for retention — users read prompt-level fixes as evidence the vendor misunderstands the problem.
- That pricing, integrations, or onboarding friction are material churn drivers at this stage — they are dominated by the correctness/trust axis and essentially irrelevant until it's solved.

## Open Questions (Requires Real User Validation)

- What specific per-handoff validation primitives (schema assertions, reference-grounded checks, deterministic gates) would actually convert a Pre-Refusal Pattern-Matcher into a trial start?
- For Hedged Partial Adopters, does a root-cause diagnostic layer measurably re-expand scope into previously-frozen workflows, or is the trust loss permanent per-workflow?
- What is the real price ceiling in regulated mid-market once SOC2/HIPAA/VPC and replayable audit logs are in place — does it move from ~$500/mo solo discretionary into five-figure annual contracts?
- Would Solo Operators accept a single-agent, deterministic-wrapper offering from the same vendor, or does the Rooben multi-agent brand itself poison that option?
- How do these abandonment patterns shift when the workflow owner is not the workflow author — i.e., when a non-author engineer has to debug a handoff on Tuesday morning?
