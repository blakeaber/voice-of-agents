---
name: product-research
description: Answer a specific research question by decomposing it into falsifiable hypotheses, building a sampling frame that structurally includes abandoners and refusers, spawning 10–16 parallel interview subjects across the frame, scoring transcripts against each hypothesis, and deriving behavioral segments bottom-up. Emits hypothesis verdicts before segments. Use to decide whether a segment framing is even correct — not to validate a pre-chosen market.
---

# `/product-research` Skill

Answers a specific research question through a five-stage, question-driven process. Refuses to accept a target-market string as input — that framing pre-biases sampling toward solution-affine subjects and hides segment-framing errors. The output is a per-run evidence directory with hypothesis verdicts written before behavioral segments, and a per-subject evidence bank feeding `/personas-from-research`.

**Framework references:**
- `docs/methodology/product-discovery.md` §1 — Founder-Unique Problem Discovery: Mom Test behavioral-episode protocol, Ulwick Outcome-Driven Innovation, Christensen Jobs-To-Be-Done, the world-class founder checklist.
- `docs/methodology/product-discovery.md` §2 — Persona Synthesis from Primary Research: Holtzblatt contextual inquiry, Young behavioral personas, behavioral clustering rules.

---

## Operating Stance

Research answers a research question, not a target market. Accepting a segment as input (e.g. `--market "US small business owners"`) pre-biases sampling toward solution-affine subjects: abandoners, evaluated-and-rejected subjects, and actively-anti subjects — the population that most clearly answers an adoption-friction question — become structurally invisible. A question-driven contract lets the skill surface whether the segment framing itself is wrong.

**This skill rejects the following inputs with an explicit refusal:**
- `--market`, `--target-market`, or any segment-name string in place of `--question`
- Any invocation without a `--slug` of ≤6 words kebab-case
- A sampling frame with fewer than the required minimums per row (see row-count gate below)

The "Gaps between findings and Rooben Pro's current positioning" callout in `segments.md` is not optional — it is the skill's primary deliverable for the founder. If every hypothesis returns `supports`, the skill has failed, not succeeded.

---

## Input Contract

```
/product-research \
  --question "<research question>"  \   # required — a falsifiable question about a customer population
  --scope    "<scope description>"  \   # required — population boundary: region, firm-size, time window
  --slug     "<kebab-case-slug>"        # required — ≤6 words; used in the artifact directory name
```

**Rejected inputs (with explicit refusal messages):**
- `--market` / `--target-market` → refused with: *"This skill requires a research question (`--question`), not a target-market name. See Key Design Insight #1 in `docs/plans/014-product-discovery-skills/014-product-discovery-skills.md`: accepting a segment pre-biases sampling toward solution-affine subjects and hides segment-framing errors."*
- Missing `--slug` → refused with: *"A `--slug` of ≤6 words kebab-case is required to name the artifact directory."*
- `--slug` longer than 6 words → refused with: *"Slug must be ≤6 words. Shorten it."*

---

## Five-Stage Process

### Stage 1 — Question Decomposition

Draft 4–7 falsifiable hypotheses that decompose the research question. Each hypothesis must make a claim the evidence could disprove — not a description of a pain, but a testable causal or structural assertion.

Good hypothesis form: *"H1: Abandoners quit because cost-per-outcome is invisible to them, not because the outcomes themselves are bad."*
Bad hypothesis form: *"H1: Users find AI tools confusing."* (non-falsifiable — no evidence could refute it)

Write the hypotheses to `hypotheses.md` in the run directory. Block until the founder ratifies the hypothesis set before proceeding to Stage 2. Do not spawn any subjects before ratification.

`hypotheses.md` format:
```markdown
# Hypotheses — {question-slug}

Research question: {--question value}
Scope: {--scope value}
Ratified: {yes | pending}

| ID | Hypothesis | Falsification condition |
|----|-----------|------------------------|
| H1 | ... | ... |
| H2 | ... | ... |
...
```

### Stage 2 — Sampling-Frame Construction

Construct the 2D matrix crossing adoption-status (6 rows) × context (5 columns). Assign subjects to cells — each filled cell will produce one interview subject in Stage 3.

**Sampling-frame 2D matrix** (appears verbatim in every run's `sampling-frame.md`):

```
                               | B2B-small | B2B-mid | B2B-large-regulated | B2C-high-autonomy | B2C-low-autonomy
-------------------------------|-----------|---------|---------------------|-------------------|------------------
Adopter                  (≥1)  |           |         |                     |                   |
Partial-adopter          (≥1)  |           |         |                     |                   |
Abandoner                (≥2)  |           |         |                     |                   |
Evaluated-and-rejected   (≥2)  |           |         |                     |                   |
Never-tried-aware        (≥1)  |           |         |                     |                   |
Actively-anti            (≥2)  |           |         |                     |                   |
```

**Row-count refusal gate:**

> Before any subject is spawned, count the filled cells per row. If `abandoner`, `evaluated-and-rejected`, or `actively-anti` has fewer than 2 filled cells, HALT with `"expand recruitment in row X"`. If any of `adopter`, `partial-adopter`, `never-tried-aware` has fewer than 1 filled cell, HALT with the same message. Refusers and abandoners are structurally required — they are the population that answers an adoption-friction question.

Write the filled matrix to `sampling-frame.md` with a column showing each cell's assigned subject role/context before proceeding to Stage 3.

### Stage 3 — Parallel Interview Spawn

Dispatch **10–16 parallel researchers in a single message** — never sequentially. Each researcher is bound to one filled cell from the sampling frame. Do not launch researchers one at a time; the parallel constraint is a research-integrity requirement (no researcher sees another's output).

Each researcher's prompt must be **self-contained**: the prompt inlines the cell-specific subject profile (adoption status, context, industry, tenure), the behavioral-episode interview protocol below, and the mandatory 8-field response schema below. No "see doc X" references — researchers do not carry doc context.

**Behavioral-episode interview protocol** (included verbatim in every researcher prompt):

> Every researcher uses past-tense episodic questions. "Walk me through the last time you tried to use an AI tool for X. Start at the trigger event. What did you do first? What went wrong?" Never use "would you use", "what do you think about", or "would it help if". Subjects in the `abandoner`, `evaluated-and-rejected`, and `actively-anti` rows are expected to produce reasons adoption failed or was rejected — not pains Rooben Pro could solve. That is the correct output for those rows.

Each researcher returns one `evidence/subject-NN.md` file (zero-padded, e.g. `subject-01.md` through `subject-16.md`) using the mandatory 8-field schema below.

**Mandatory 8-field subject response schema** (appears verbatim in every researcher prompt; all eight fields are required; no field may be omitted or marked "N/A"):

```
jtbd:                         {The outcome the subject is hiring any tool (or none) to achieve — the progress they're trying to make.}
adoption_trajectory:          {Timeline: first-heard → evaluated → used → current-state, with approximate dates.}
last_concrete_episode:        {One specific past event, time-ordered. Tools touched. Outcome. No hypotheticals. Start with a date or relative anchor ("Last Tuesday", "Three months ago").}
constraint_profile:           {Regulation, data-sensitivity, time budget, autonomy level, trust threshold.}
failure_or_abandonment_mode:  {If partial-adopter / abandoner / evaluated-and-rejected / actively-anti: the exact failure + the moment it happened. If adopter: leave blank.}
decision_topology:            {Who chose / who blocked / who paid. Approval path. Budget authority.}
anti_model_of_success:        {What "it worked" looks like in the subject's own words. What "success theater" they distrust — outputs that look impressive but don't help.}
verbatim_quote_bank:          {5–8 quotes keyed Q1..Q8, each ≤2 sentences, suitable for downstream [source: evidence/subject-NN.md Q##] citations.}
```

### Stage 4 — Hypothesis Scoring

After all researcher `evidence/subject-NN.md` files are returned, score every subject transcript against every hypothesis from Stage 1. This stage completes before Stage 5 begins — verdicts.md is written before segments.md.

For each hypothesis, assign one verdict:
- `supports` — the subject's evidence clearly backs the hypothesis
- `refutes` — the subject's evidence clearly contradicts the hypothesis
- `orthogonal` — the subject's evidence is relevant to the question but doesn't touch this hypothesis
- `insufficient-evidence` — the subject's episode didn't generate enough detail to score this hypothesis

Include representative quotes (keyed to the verbatim_quote_bank) for every non-`insufficient-evidence` verdict.

Write `verdicts.md` with the full scoring matrix before proceeding.

`verdicts.md` format:
```markdown
# Verdicts — {question-slug}

| Hypothesis | Verdict | Supporting subjects | Refuting subjects | Key quotes |
|-----------|---------|-------------------|------------------|-----------|
| H1: ... | refutes | subject-03, subject-11 | subject-01, subject-07 | S03/Q4: "..." |
...

## Cross-cutting findings
{Observations that emerged across hypotheses — unexpected patterns not captured by any single hypothesis}
```

If every hypothesis returns `supports`, flag this explicitly: *"All hypotheses supported — high risk of confirmation bias. Review sampling frame for solution-affine overrepresentation before accepting these verdicts."*

### Stage 5 — Bottom-Up Segmentation

After `verdicts.md` is written, affinity-map subjects on behavioral axes (jobs-to-be-done, adoption-trajectory shape, constraint profile). Segments are derived bottom-up from the evidence — they are never named for a hypothesis they absorb. A segment named "cost-sensitive abandoners" is acceptable; a segment named "people who prove H2" is not.

Clustering rules:
- Differentiate on JTBD, adoption-trajectory shape, constraint profile, and failure/abandonment mode
- Explicitly refuse demographic-only differentiation (age, gender, company size, industry alone)
- Label each segment with a behavioral descriptor, not a demographic label

Write `segments.md` as a persona-ready bank for `/personas-from-research`.

`segments.md` must include a mandatory final section:

**"Gaps between findings and Rooben Pro's current positioning"** — for each top segment, compare the behavioral evidence against Rooben Pro's current feature set and positioning. Flag explicitly where Rooben Pro: (a) does not address the finding, (b) partially addresses it, or (c) addresses it but subjects were unaware. Ground every gap callout in a specific verdict from `verdicts.md`. If no gaps exist, this is a red flag — either the research was contaminated or the positioning is accidentally correct; document which and explain the evidence.

---

## Output Artifact Tree

The skill emits this directory at runtime (not during the phase that writes this SKILL.md):

```
docs/research/product-research/{YYYY-MM-DD}-{question-slug}/
  hypotheses.md        # 4–7 falsifiable hypotheses, founder-ratified (Stage 1)
  sampling-frame.md    # 2D matrix with subject assignments per cell (Stage 2)
  evidence/
    subject-01.md      # one file per researcher, 8-field schema (Stage 3)
    subject-02.md
    ...
  verdicts.md          # per-hypothesis ruling + representative quotes (Stage 4 — written before segments.md)
  segments.md          # bottom-up behavioral segments + "Gaps vs. Rooben Pro positioning" section (Stage 5)
```

The `{question-slug}` comes from `--slug`. The `{YYYY-MM-DD}` is today's date at invocation time.

---

## Anti-Patterns

This skill calls out and refuses the following failure modes:

1. **Accepting a segment name as input** (`--market "..."`) instead of `--question` — pre-biases sampling toward solution-affine subjects. Refusals are mandatory.
2. **Leading questions** — phrasing that implies the answer or hints at the product being built ("Would it help if you had X?"). All researcher prompts use past-tense behavioral-episode questions only.
3. **Selling during discovery** — pivoting a researcher prompt from listening to pitching Rooben Pro features. Researcher prompts contain no product descriptions.
4. **Accepting future intent over past behavior** — "I would use..." or "I think I'd..." instead of "I did..." or "Last time this happened...". Researcher prompts flag this explicitly as invalid data.
5. **Sampling only adopters** — the row-count gate is the mechanical enforcement. Any run missing required minimums in the `abandoner`, `evaluated-and-rejected`, or `actively-anti` rows is halted before subjects are spawned.
6. **Clustering before scoring hypotheses** — `segments.md` is written after `verdicts.md` in every run. Stage 4 precedes Stage 5. No exceptions.
7. **Treating `actively-anti` subjects as noise** — they are high-signal. A subject who has evaluated and rejected agentic AI is the most informative data point for an adoption-friction question. Their `failure_or_abandonment_mode` field is mandatory.
8. **Running fewer than 10 subjects** — no cross-cutting patterns are defensible from fewer than 10 independent subjects. The sampling-frame gate (≥2 in three rows, ≥1 in three rows) enforces a minimum of 9; the spawn instruction requires 10–16.

---

## Quality Bars

Per `docs/methodology/product-discovery.md` §1 checklist:

- Every hypothesis in `hypotheses.md` must have an explicit falsification condition — a statement of what evidence would force a `refutes` verdict.
- Every `verdicts.md` row must cite at least one verbatim quote from the subject's `verbatim_quote_bank`.
- `segments.md` must not reuse hypothesis labels as segment names.
- The "Gaps vs. Rooben Pro positioning" section must cite specific verdict rows — not general impressions.
- A run where every hypothesis returns `supports` is flagged as high-risk and requires explicit acknowledgment before `/personas-from-research` can consume the run directory.
