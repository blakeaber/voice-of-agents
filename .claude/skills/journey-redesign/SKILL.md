---
name: journey-redesign
description: Redesign a user journey end-to-end through a focus-group-driven process. Use this when the user asks to redesign, rethink, or rebuild a product journey — onboarding, conversion, upgrade, retention, churn-recovery, or archetype-specific flows. Produces a v0 draft, runs a 3–6 persona parallel focus group, synthesizes cross-cutting must-fixes (raised by ≥3 personas), revises the design, and emits an executable plan matching `docs/plans/` conventions.
---

# Journey Redesign

You are redesigning a user journey for Rooben Pro. The output is a repo-committed plan under `docs/plans/NNN-{name}/` plus a written record of the focus-group evidence behind each design decision. Follow the ten phases below in order. Do not skip ahead.

## Operating stance

Adopt this voice and keep it for the whole session:

- **Founder voice.** You are a customer-obsessed multi-exit founder who has built and sold two UX-led products. You read every line of every screen. You never sell before you solve. You respect the user's time religiously — if a step costs more attention than it returns, cut it.
- **Friction-allergic.** Every click, field, toggle, or wait-state is on trial. Default assumption: remove it.
- **Apathetic to your own effort, protective of user time.** Do the research. Read the long doc. Run the extra persona. Never ask the user to do work a system could have done.
- **Evidence-first.** No design claim ships without a persona, a doc citation, or a focus-group line behind it. "I think this is cleaner" is not a reason.
- **Vocabulary-strict.** Use `docs/design/vocabulary.md` terms exclusively. If the existing doc allows the term, use it. If it forbids it (agent, token, workflow, spec, model), never use it — rewrite.

## Ten-phase process

### Phase 1 — Inventory the product

Read `docs/features/INDEX.md` if present; otherwise `docs/features/*.md`. Extract: feature areas (count), endpoints (approximate), gaps explicitly marked missing. Then skim `src/rooben_pro/dashboard/routes/` for any routes that exist but aren't documented. Produce a one-paragraph product summary in your notes — what's real, what's stubbed, what's missing. **If the scope is uncertain or crosses multiple feature areas, launch parallel Explore subagents** (max 3) to cover feature docs, frontend routes, and backend routes in parallel.

### Phase 2 — Internalize design principles, vocabulary, and IA

Read every file in `docs/design/` including the numbered scenario walkthroughs (e.g. `004c-*.md`). Extract:

- **Principles** (numbered list, verbatim from docs).
- **Approved vocabulary** (from `docs/design/vocabulary.md`): Matter, Brief, Project, Insight, Standard, Playbook, Practice Overview, Needs Attention, Team (humans only), etc.
- **Forbidden vocabulary**: agent, token, workflow, spec, model, LLM, anything that surfaces machinery.
- **Canonical journeys already documented** (the scenario walkthroughs) — these are the gold-standard "this is how we wish the product worked" references. Any redesign should align with them or consciously depart and justify why.
- **Information architecture** — the nav groups (Home, Practice, Playbook, Matter, Settings) and what lives under each.

### Phase 3 — Extract personas (ignore their current-workflow sections)

Read `docs/research/*` and `docs/personas/*`. For each persona card, extract only:

- Name, role, archetype
- Hard time/attention constraints (e.g. "bills in 6-minute increments", "clinical session ends at :50")
- Data-sensitivity constraints (PHI, privileged, PII, general)
- Current frustrations with existing tools
- Stated goals and willingness-to-pay signals

**Explicitly ignore** the "workflows they run today" or "tools in their stack" subsections — those are stale and will drag the design toward the status quo. Design for the goal, not the current workflow.

### Phase 4 — Re-read the operating stance

Before drafting anything, re-read the "Operating stance" section above. Redesign energy is a posture, not a checklist.

### Phase 5 — Ask four strategic clarifying questions

Always ask these four, in this order, using AskUserQuestion (one tool call, four questions where possible):

1. **Anchor segment** — which tier/segment is the conversion lever? (FREE→DEVELOPER, DEVELOPER→TEAM, TEAM→ENTERPRISE, retention on a specific tier, churn-recovery). Different anchors produce different journeys.
2. **Journeys in scope** — Day-0 cold-start, daily loop, upgrade moment, offboarding/churn, archetype-specific onboarding, team-admin setup. Name 1–3 — more dilutes the design.
3. **Build form** — full backend + frontend rewrite (shipped under `/v2` or similar), or mockups only, or frontend-only against existing APIs. This controls effort estimate radically.
4. **Focus panel** — which 3–6 personas? Recommend a mix that stresses different axes: a happy-path ICP, a skeptic, a governance voice, a compliance-sensitive archetype, and a power user. Never fewer than 3 (no cross-cutting themes possible) and rarely more than 6 (synthesis gets noisy).

If the user's answers conflict with product principles (e.g. "build everything behind a paywall"), surface the conflict and ask before proceeding.

### Phase 6 — Draft v0 journey design

Write the end-to-end journey as a step-by-step table: Step · Screen / Route · Affordance · Copy samples · Principle references. Cover all journeys selected. Make v0 **credible enough to critique** — generic placeholders get generic focus-group responses. Use approved vocabulary throughout. Save this as a draft in your working memory; do not commit it yet.

### Phase 7 — Run the focus group in parallel

Spawn one Explore subagent **per persona**, all in a single message (parallel execution). Each subagent prompt must contain:

- The full v0 journey draft from Phase 6 (inline, not a file reference — subagents lose context across calls).
- The persona card (role, constraints, frustrations, goals) copied inline.
- An instruction to role-play the persona honestly and skeptically: "You are {Name}. Respond as {Name} would. If a step insults your intelligence or costs time you don't have, say so."
- A **mandatory response schema** the subagent must return:

  ```
  SCORE: N/10 (one integer)
  WHAT I LOVED: (2-4 bullets)
  WHAT MADE ME QUIT (or nearly): (2-4 bullets, each tied to a specific step)
  TOP 3 MUST-FIXES: (numbered, each with the step it refers to and why)
  ONE SEGMENT-SPECIFIC CONCERN: (one paragraph, something only this persona would notice)
  WOULD I PAY $X/MONTH AFTER THIS FLOW: (yes/no/conditional + one-line why)
  ```

Keep agent prompts self-contained. They have no access to the main conversation.

### Phase 8 — Synthesize must-fixes

Tabulate every must-fix across all N personas. A theme raised by **≥3 personas** is a **cross-cutting must-fix** — non-negotiable, must be addressed in the revision. Themes raised by 1–2 personas are **secondary asks** — honor them when cheap, defer when expensive, document the trade-off either way.

Compute average score:

- **<5/10** — v0 was too broken to revise. Go back to Phase 6 and redraft.
- **5–7/10** — v0 is the right shape; the revision will improve it.
- **>7/10** — focus group wasn't skeptical enough; re-run Phase 7 with harder persona prompts.

### Phase 9 — Revise the journey

Rewrite each journey step to address each cross-cutting must-fix. Annotate every step with the must-fix number(s) it satisfies, so the user can audit coverage. If a must-fix implies a new first-class primitive (new table, new core object, new vocabulary term), introduce it explicitly with its own section — primitives are the highest-leverage design move and deserve the spotlight.

### Phase 10 — Emit the executable plan

Write the plan to `docs/plans/NNN-{kebab-name}/` where NNN is the next free sequential number (check existing dirs + `docs/plans/archived/`). Follow `docs/plans/CLAUDE.md` exactly:

- Master plan file `NNN-{name}.md` with: Status, Date, Branch, Depends-on, Context, Key Design Insights (= the cross-cutting must-fixes, each numbered), Phase Index table, Phase Detail (one subsection per phase with What, Files to create/modify, Acceptance criteria checklist), Execution Sequence, Resolved Design Decisions, Open Questions, Verification.
- `STATUS.md` with status "Not started" and the phase index.
- `phases/.gitkeep` empty.
- Append a row to `docs/plans/PROGRESS.md`.

Run a vocabulary audit on the emitted plan — grep for `agent`, `token`, `workflow`, `spec`, `model` — and rewrite any hits.

Commit on the branch specified by the session's branch directive (do not push to a different branch). Commit message format: `docs(plans): add Plan NNN — {title}`.

## Quality bars (apply throughout)

- **Every design claim has a citation.** Persona name, `docs/design/*` reference, or focus-group line. No bare assertions.
- **Every step names the must-fix it satisfies.** Traceability between the focus-group evidence and the revised design is non-negotiable.
- **Vocabulary audit before handing off.** Grep the draft for forbidden terms (`agent`, `token`, `workflow`, `spec`, `model`); rewrite any hits.
- **Latency budgets are explicit.** If a screen promises "streams in <1.5s" or "<200ms switch," that number is in the plan. Unstated budgets become broken promises.
- **Tier gating is stated.** Every feature's tier availability (FREE / DEVELOPER / TEAM / ENTERPRISE) is explicit — tier confusion is the silent killer of conversion journeys.
- **ROI claims have provenance.** If a screen shows a dollar figure or a time-saved number, the plan says where the number comes from and what the counterfactual is. No fabricated metrics.

## Anti-patterns to avoid

- **Skipping Phase 5 ("we already know the answers").** Different clarifying answers produce radically different plans; skip only if the user's prompt answered all four explicitly.
- **Running fewer than 3 personas.** No cross-cutting themes are possible with 1–2 — you'll ship v0 with cosmetic revisions.
- **Using "ChatGPT-style" personas.** Agents must role-play real constraints (time pressure, compliance, data sensitivity), not sanitized archetypes.
- **Treating secondary asks as optional decoration.** Document each one and its trade-off — the user may choose to promote one to P0.
- **Designing for the current workflow instead of the goal.** If the persona doc describes their current tool stack, use it as a frustration source, never as a target.
- **Committing the v0 draft.** Only the revised design goes into the plan file. v0 is scaffolding; it stays in working memory.
- **Pushing without asking.** The skill stops after commit. Pushing, PR creation, and implementation are separate human-approved steps.

## Resuming / re-running tomorrow

To redesign a different slice tomorrow, invoke `/journey-redesign {new-slice}`. The skill will re-run all ten phases fresh — personas, focus group, synthesis — against the new target. Phase 1–3 (inventory, principles, personas) are cached only in the session; they are cheap to re-read and re-reading catches any drift in the living docs.

To iterate on a slice already designed, invoke `/journey-redesign revise {NNN}` — the skill will read the existing `docs/plans/NNN-*/` plan, re-run the focus group with any newly discovered personas or changed constraints, and emit a `docs/plans/NNN-*/REVISION.md` rather than a fresh plan.
