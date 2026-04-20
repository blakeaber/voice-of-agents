---
name: workflows-from-interviews
description: Extract time-ordered workflow maps from 1:1 contextual-inquiry subagent episodes for a given persona. Explicitly refuses group mode. Emits PWM YAML schema-compatible with the existing 000-algorithm.md pipeline. Use after /personas-from-research to generate primary-research workflow maps.
---

# `/workflows-from-interviews` Skill

Extracts time-ordered workflow maps from 1:1 contextual-inquiry subagent episodes for a given UXW persona. Produces PWM YAML files compatible with the `docs/research/ux-workflows/000-algorithm.md` pipeline. Runs one persona at a time — group mode is explicitly refused.

**Framework references:**
- `docs/methodology/product-discovery.md` §3 — Workflow Extraction from 1:1 Interviews: episode anchoring, 1:1 rationale, step capture requirements.
- `docs/methodology/product-discovery.md` §4 — Focus Groups — When and When Not: full group-mode anti-pattern rationale.
- Input: a single UXW persona file from `docs/research/ux-workflows/personas/`.

---

## Operating Stance — Group Mode Refusal

This skill runs 1:1 interviews ONLY. Group mode is explicitly refused. Running multiple subjects simultaneously as a panel introduces groupthink, social-desirability bias, and vocal-minority dominance — documented anti-patterns for behavioral workflow discovery. See `docs/methodology/product-discovery.md` §3 for the full rationale. If you attempt to pass multiple personas as a group, this skill will stop and ask you to invoke it once per persona.

**Invocation:** Pass exactly one UXW persona file path per invocation. The skill will read the persona's role, constraints, data-sensitivity profile, and frustrations as the starting point for episode design.

---

## Seven-Phase Process

### Phase 1 — Load persona

Read the target UXW file. Extract:
- Role and sub-role
- Time/attention constraints (from the persona's efficiency baseline)
- Data-sensitivity profile (PII, confidential, or general)
- Primary frustrations and current workarounds
- Trust requirements (what the persona needs before acting on output)

These fields determine the episode types and the blocker probes in Phase 2.

### Phase 2 — Compose 3–5 episode prompts

Each episode prompt targets a distinct real-world episode type relevant to the persona's role. Episodes must be:
- **Distinct** — no two episodes should cover the same activity
- **Past-behavior anchored** — each prompt begins with "Tell me about the last time you..." or "Walk me through what happened the last time..."
- **Covering different time horizons** — mix routine episodes (daily/weekly) with acute episodes (urgent, unexpected, high-stakes)

Example episode types for a paralegal persona:
- "Monday morning case intake" (routine, scheduled)
- "Urgent deadline response" (acute, time-pressured)
- "New client onboarding" (periodic, relationship-critical)
- "Contradictory instructions from two partners" (acute, judgment-required)
- "Year-end file archival" (periodic, compliance-driven)

Document all 3–5 episode prompts before proceeding.

### Phase 3 — Spawn 3–5 parallel Explore subagents

Launch all episode subagents **in a single message** — one per episode prompt, no cross-talk. Each subagent:
- Plays the persona (uses the UXW persona file as its character brief)
- Responds to its assigned episode prompt only
- Uses the mandatory subagent episode schema for its response (all fields required)

```
EPISODE: {name, e.g. "Monday morning case intake"}
DATE: {relative, e.g. "last Monday"}
PRE-STATE: {what was true before the episode began}
STEPS:
  - step: {action taken}
    tool: {software/tool used, or "none"}
    input: {what they started with}
    output: {what they produced}
    time: {estimated minutes}
    blocker: {what slowed or stopped them, or "none"}
POST-STATE: {what was true after the episode}
WHAT I WISHED EXISTED: {one sentence}
```

Subagents must not consult or reference each other's episodes. Cross-episode synthesis happens in Phase 5, not during subagent execution.

### Phase 4 — Extract time-ordered narratives

From each subagent's response:
1. Validate that all schema fields are populated — reject any response with missing `PRE-STATE`, `STEPS`, or `POST-STATE` and re-prompt the subagent
2. Index every step by sequence number within the episode
3. Extract all tools and artifacts mentioned (software names, file types, handoff media)
4. Flag all blockers — these are the primary product gap candidates
5. Record `WHAT I WISHED EXISTED` verbatim — this is the unmet JTBD

### Phase 5 — Synthesize 2–3 workflow maps

Across all episode responses:
1. Identify step sequences that appear in multiple episodes — these are the core workflow paths
2. Identify where episodes diverge — these are decision branches; record the branch condition
3. Collapse redundant steps (same action, different episode context) into a single canonical step
4. Surface decision branches explicitly — a workflow map without branching is a happy-path illusion (per `docs/methodology/product-discovery.md` §3)
5. Derive 2–3 distinct workflow maps: primary (most common path), secondary (second most common or highest-friction path), edge (if the persona has compliance/trust constraints that produce a distinct path)

### Phase 6 — Emit PWM YAML

For each synthesized workflow map, emit a PWM YAML file matching the existing schema in `docs/research/ux-workflows/`. The canonical schema fields (read from existing PWM reference files in the personas directory) are:

```yaml
workflow:
  id: string               # UXW-{persona_id}-{sequence}, e.g. UXW-04-1
  persona: integer          # Persona number
  title: string             # Goal-oriented title (verb + outcome)

  intent:
    goal: string            # What the persona is trying to achieve
    trigger: string         # What event initiates this episode
    success_definition: string  # How the persona defines success (not how we define it)

  preconditions:
    account_tier: enum
    existing_data:
      - type: string        # e.g. case files, prior research, client records
        count: integer
        description: string

  steps:
    - number: integer
      action: string         # What the persona does (persona-language, not engineering-language)
      tool: string           # Software or medium used at this step
      input: string          # What they start with
      output: string         # What they produce
      time: string           # Estimated minutes
      blocker: string        # What slowed or stopped them, or "none"
      friction_risk: string  # What could go wrong or feel bad

  success_criteria:
    - criterion: string
      measurement: string    # How to verify (UI state, output artifact, persona self-report)

  persona_evaluation:
    satisfaction_drivers:
      - string               # What would make the persona rate this 9-10
    dealbreakers:
      - string               # What would make the persona rate this 1-3
    efficiency_baseline:
      method: string         # How they do this today (without Rooben)
      time: string           # e.g. "45 minutes across email and shared drive"
    value_delivered:
      time_saved: string
      errors_prevented: string
      knowledge_preserved: string
```

Validate the emitted YAML against this schema before writing. Any field mismatch must be corrected before archival.

### Phase 7 — Archive-then-replace

Before writing any new PWM YAML files:

`git mv` existing PWM files to `archived/v1-secondary/` before writing new ones.

The exact command pattern:
`git mv docs/research/ux-workflows/personas/PWM-{persona_id}-*.yaml docs/research/ux-workflows/personas/archived/v1-secondary/`

After archival:
1. Write new PWM YAML files to `docs/research/ux-workflows/personas/`
2. Write `-evidence.md` sibling file containing all raw subagent episode responses indexed by episode name and step number

---

## Mandatory Episode Schema

All subagent responses must use this schema exactly (no omitted fields):

```
EPISODE: {name, e.g. "Monday morning case intake"}
DATE: {relative, e.g. "last Monday"}
PRE-STATE: {what was true before the episode began}
STEPS:
  - step: {action taken}
    tool: {software/tool used, or "none"}
    input: {what they started with}
    output: {what they produced}
    time: {estimated minutes}
    blocker: {what slowed or stopped them, or "none"}
POST-STATE: {what was true after the episode}
WHAT I WISHED EXISTED: {one sentence}
```

Any subagent response missing `PRE-STATE`, `POST-STATE`, or any `STEPS` field must be re-prompted before synthesis proceeds.

---

## Archival Instruction

Before writing new workflow files, archive existing PWM files:

`git mv docs/research/ux-workflows/personas/PWM-{persona_id}-*.yaml docs/research/ux-workflows/personas/archived/v1-secondary/`

Create `docs/research/ux-workflows/personas/archived/v1-secondary/README.md` if it does not already exist, explaining: v1 = secondary-research-derived, abstracted from pain bullets; v2 = primary-research-synthesized, extracted from 1:1 episodic interviews with time-ordered steps, tool citations, and blocker records.

---

## Output Artifacts

At runtime, this skill writes per persona:

- `docs/research/ux-workflows/personas/UXW-{persona_id}-{seq}-workflow.yaml` — PWM YAML matching the schema above
- `docs/research/ux-workflows/personas/UXW-{persona_id}-{seq}-evidence.md` — raw subagent episode responses, indexed by episode name and step number

---

## Anti-Patterns

Per `docs/methodology/product-discovery.md` §3:

1. **Group workflow elicitation**: Passing multiple personas to this skill simultaneously — explicitly refused. Invoke once per persona.

2. **Happy-path recording**: Capturing only steps that succeed, omitting blockers, error-recovery paths, and abandoned attempts. Every `blocker` field must be populated honestly — "none" is a valid value only when the step genuinely had no friction.

3. **Abstracted steps**: Recording "reviewed the document" instead of "opened the PDF in Adobe, compared pages 3 and 7, pasted the discrepancy into Slack." Tool and artifact detail is required at every step.

4. **Frequency conflation**: Treating a single episode response as representative without asking "is this how it always goes?" The `DATE` field and the episode prompt design (past-behavior anchored) address this — use them.

5. **Missing post-state**: Every episode response must include `POST-STATE`. What the persona produced or experienced after the episode determines the downstream integration context.
