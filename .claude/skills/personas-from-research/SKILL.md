---
name: personas-from-research
description: Synthesize evidence-backed persona cards from a /product-research run directory. Every field carries an inline citation to a source quote in the upstream evidence bank. On first run, archives existing UXW persona files to archived/v1-secondary/ before writing new ones. Use after /product-research to generate primary-research personas for the segments that emerged bottom-up.
---

# `/personas-from-research` Skill

Synthesizes primary-research persona cards from a `/product-research` run directory. Every persona sidecar field carries an inline citation to a source quote in the upstream evidence bank. Replaces secondary-research-derived UXW personas with evidence-backed ones that have full field-level provenance.

**Framework references:**
- `docs/methodology/product-discovery.md` §2 — Persona Synthesis from Primary Research: Holtzblatt contextual inquiry, Young behavioral personas, behavioral clustering rules, citation enforcement.
- `docs/methodology/product-discovery.md` §1 — Founder-Unique Problem Discovery: Mom Test behavioral-episode protocol (reused for top-up interview subjects).
- Input: `/product-research` run directory at `docs/research/product-research/{run-dir}/` (containing `hypotheses.md`, `verdicts.md`, `segments.md`, and `evidence/subject-NN.md` files).

---

## Operating Stance

Personas built from secondary research have no field-level provenance. When a persona card says "Maria values efficiency" with no source quote, that claim is an assumption — possibly correct, possibly a projection. This skill replaces assumption-based persona fields with evidence-backed ones, where every sidecar field traces to a specific quote from a specific subject in the upstream evidence bank.

**First-run archival is mandatory.** This skill will not write new persona files into `docs/research/ux-workflows/personas/` without first archiving the existing ones via `git mv`. Two sources of truth for downstream pipelines break the algorithm.

**Input contract:** This skill requires a `/product-research` run directory path. It refuses to run if `verdicts.md` is absent from that directory. A run without verdicts has not completed Stage 4 scoring — consuming it would produce personas from unscored evidence.

---

## Input Contract

```
/personas-from-research \
  --run-dir "docs/research/product-research/{YYYY-MM-DD}-{question-slug}"
```

**Rejection conditions:**
- Missing `--run-dir` → refused with: *"A `/product-research` run directory is required. Run `/product-research` first and pass the output directory path."*
- `verdicts.md` absent from `--run-dir` → refused with: *"Cannot synthesize personas from a run without `verdicts.md`. Stage 4 scoring must complete before persona synthesis. Re-run `/product-research` through Stage 4."*
- `segments.md` absent from `--run-dir` → refused with: *"Cannot synthesize personas: `segments.md` is absent. Stage 5 segmentation must complete before persona synthesis."*

---

## UXW Schema Gap

Existing UXW cards at `docs/research/ux-workflows/personas/UXW-##-*.md` (see `UXW-01-maria-gutierrez.md` as the reference structure) are **task-centric**: Intent · Trigger · Success · Today · Preconditions · Steps table · Success Criteria · Persona Evaluation Rubric. They do NOT carry `jtbd`, `adoption_trajectory`, `decision_topology`, `constraint_profile`, `failure_or_abandonment_mode`, or `anti_model_of_success` — the richer persona data captured by the `/product-research` upstream evidence bank. Merging the 8 fields into the task-centric card would break the downstream skill's input contract (which reads the task card). Therefore this skill emits a **persona-schema sidecar** at `docs/research/ux-workflows/personas/UXW-##-{name}-persona.md` carrying the 8 fields with inline `[source: evidence/subject-NN.md Q##]` citations, AND derives the task-centric UXW card from the sidecar. Downstream skills continue to read the task card unchanged.

---

## Ten-Phase Process

### Phase 1 — Load and Validate the Run Directory

Load the `/product-research` run directory. Reject if `verdicts.md` is absent (see Input Contract). Ingest:
- `segments.md` — the persona-ready behavioral segments with subject-to-segment assignments
- `verdicts.md` — the per-hypothesis rulings and representative quotes
- `evidence/subject-NN.md` files — the 8-field-per-subject records with verbatim quote banks

Confirm the run directory is complete before proceeding.

### Phase 2 — Confirm Coverage Per Segment

For each segment in `segments.md`, count how many subjects from the `evidence/` bank map to that segment. If **fewer than 3 subjects** map to a segment, mark it for top-up in Phase 4. Document:
- Segment name
- Subject count
- Top-up required (yes/no)
- If yes: how many additional subjects needed (target 3 per segment minimum, 6 preferred)

### Phase 3 — Draft Top-Up Interview Guide (if required)

If any segment needs top-up subjects, draft a behavioral interview guide targeting the under-covered segment(s). Use:
- JTBD framing: "What outcome were you trying to achieve?"
- Laddering: behavior → consequences → values
- Constraint probes: "What would have made this impossible?"
- Past-behavior anchoring (Mom Test): every question asks about a specific past episode — never "would you use" or "what do you think"

Draw subject profiles from the same 2D sampling-frame used in the upstream `/product-research` run:

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

### Phase 4 — Spawn Top-Up Researchers (if required)

If Phase 2 identified under-covered segments, dispatch **6–12 parallel researchers in a single message** — never sequentially. Each researcher is bound to one subject variant in the under-covered segment. Each researcher's prompt must be self-contained: inline subject profile, behavioral-episode interview protocol, and the mandatory 8-field response schema below.

**Behavioral-episode interview protocol** (included verbatim in every researcher prompt):

> Every researcher uses past-tense episodic questions. "Walk me through the last time you tried to use an AI tool for X. Start at the trigger event. What did you do first? What went wrong?" Never use "would you use", "what do you think about", or "would it help if". Subjects in the `abandoner`, `evaluated-and-rejected`, and `actively-anti` rows are expected to produce reasons adoption failed or was rejected — not pains Rooben Pro could solve. That is the correct output for those rows.

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

Each top-up researcher returns one `evidence/subject-NN.md` file (continuing the numbering from the upstream run) using the mandatory 8-field schema above.

### Phase 5 — Affinity-Map Combined Evidence

After all evidence is assembled (upstream `/product-research` subjects + any top-up subjects), affinity-map across the full subject set. Extract:
- JTBD candidates (the outcome subjects are hiring any tool to achieve)
- Adoption-trajectory shapes (adopter arc, abandonment arc, never-tried arc)
- Constraint clusters (regulation, data-sensitivity, time budget, autonomy level, trust threshold)
- Failure and abandonment modes (the exact moment and cause)
- Decision-topology patterns (who decides, who blocks, who pays)
- Anti-models of success (what "success theater" looks like to this segment)

Map each extracted item to its source: `[source: evidence/subject-NN.md Q##]`.

### Phase 6 — Cluster Subjects by Behavioral Axis

Group subjects according to behavioral differences, not demographics.

**Behavioral clustering rule** (mandatory):
> Personas MUST be differentiated by behavioral axes: JTBD (the job they're hiring the product for), adoption-trajectory shape, constraint profile, and failure/abandonment mode. Personas differentiated ONLY by age, gender, company size, or industry are rejected — demographic != behavioral.

When evaluating whether a cluster distinction is valid, ask: "If I swapped the demographic label but kept the behavior, would this persona still be meaningfully different from the others?" If yes, the behavioral axis is real. If no, merge the clusters.

Each cluster must contain at least 2 subjects. Name each cluster by its primary behavioral descriptor — never by a demographic label and never by a hypothesis label it happens to confirm.

Identify 1–3 personas per cluster (2–4 clusters expected per run).

### Phase 7 — Draft Persona Sidecar and UXW Card

For each persona:

**Step A — Write the persona-schema sidecar** (`UXW-##-{name}-persona.md`):

The sidecar carries the 8-field persona data schema synthesized from the behavioral cluster. Every field must include an inline citation:

Citation format: `[source: evidence/subject-NN.md Q##]`

Example: `jtbd: Retrieve a specific past decision, including its rationale and the constraints active at the time, within 2 minutes of need [source: evidence/subject-03.md Q2] [source: evidence/subject-07.md Q5]`

Required sidecar fields (all 8 required; no field may be left blank or cited as "N/A"):
```
jtbd:                         {synthesized from cluster — with inline citations}
adoption_trajectory:          {dominant arc for this cluster — with inline citations}
last_concrete_episode:        {composite or most representative episode — with inline citations}
constraint_profile:           {synthesized constraint cluster — with inline citations}
failure_or_abandonment_mode:  {dominant failure pattern for this cluster, if applicable — with inline citations}
decision_topology:            {synthesized decision structure — with inline citations}
anti_model_of_success:        {what "success theater" looks like to this cluster — with inline citations}
verbatim_quote_bank:          {5–8 representative quotes drawn from cluster subjects, keyed Q1..Q8}
```

**Step B — Derive the task-centric UXW card** (`UXW-##-{name}.md`):

Derive the task-centric UXW card from the sidecar. Match the existing UXW schema (Intent · Trigger · Success · Today · Preconditions · Steps table · Success Criteria · Persona Evaluation Rubric). Every UXW card field must trace back to a sidecar field — note the sidecar field in parentheses after each card field value. Do not add fields to the UXW card that do not map to sidecar fields.

### Phase 8 — Citation Audit

Before writing any persona files, run a field-level citation audit on every sidecar draft:

For each sidecar, grep for field lines without `[source: evidence/subject-NN.md Q##]` citations — zero tolerance. Any field missing a citation must be either:
- (a) Rewritten using evidence from the subject files, or
- (b) Removed from the sidecar entirely

Do not rationalize missing citations as "implied by the data." If it is not cited, it is not in the sidecar.

Confirm each UXW task card field traces back to a sidecar field before proceeding to Phase 9.

### Phase 9 — Archive Then Replace

Before writing any new persona files, run:

`git mv docs/research/ux-workflows/personas/UXW-*.md docs/research/ux-workflows/personas/archived/v1-secondary/`

Then create `docs/research/ux-workflows/personas/archived/v1-secondary/README.md` explaining:

> v1 = secondary-research-derived, no field-level provenance; v2 = primary-research-synthesized, every sidecar field cites a `[source: evidence/subject-NN.md Q##]` upstream evidence record.

After archival is confirmed via `git status`, write the new persona files:
- `docs/research/ux-workflows/personas/UXW-##-{name}-persona.md` — sidecar (8-field data schema with inline citations)
- `docs/research/ux-workflows/personas/UXW-##-{name}.md` — task-centric UXW card derived from sidecar

### Phase 10 — Emit Audit Trail

Write one `-evidence.md` sibling file per persona:

`docs/research/ux-workflows/personas/UXW-##-{name}-evidence.md`

Contents:
- All subject files from the upstream `evidence/` bank contributing to this persona cluster, indexed by citation ID
- Affinity-map excerpt showing how this behavioral cluster was formed
- List of subjects whose responses were NOT incorporated (with reason — e.g., insufficient episode detail, orthogonal JTBD, outlier failure mode)
- Pointer back to the upstream `/product-research` run directory

---

## Output Artifact Schema

Per persona:

- `docs/research/ux-workflows/personas/UXW-##-{name}-persona.md` — **sidecar**: 8-field persona data schema, every field with `[source: evidence/subject-NN.md Q##]` citations
- `docs/research/ux-workflows/personas/UXW-##-{name}.md` — task-centric UXW card (matches existing schema), every card field tracing to a sidecar field
- `docs/research/ux-workflows/personas/UXW-##-{name}-evidence.md` — audit trail: indexed citations pointing to the upstream `evidence/subject-NN.md` bank in the `/product-research` run directory

---

## Anti-Patterns

Per `docs/methodology/product-discovery.md` §2:

1. **Consuming a run without verdicts** — `verdicts.md` must exist in the run directory before this skill runs. Personas synthesized from unscored evidence inherit the confirmation biases of Stage 3 without the Stage 4 correction.

2. **Demographic clustering** — Do not group subjects by age, gender, company size, or industry and call the groups personas. These attributes may appear in a sidecar as context but must not be the organizing dimension.

3. **Single-subject persona** — Do not write a persona based on one subject. A cluster requires at least 2 subjects.

4. **Aspirational persona** — Do not write the persona as more tech-savvy, more willing to pay, or more patient than the actual subjects demonstrated. If subjects were resistant, the persona is resistant.

5. **Hypothesis-labeled segment** — A segment named "people who prove H2" is not acceptable. Segments are named for behavioral descriptors, not for hypotheses they confirm.

6. **Field without citation** — Any sidecar field without `[source: evidence/subject-NN.md Q##]` is rejected. There are no exceptions for fields that "seem obvious" from the data.

7. **UXW card field without sidecar trace** — Every UXW task card field must derive from a sidecar field. Fields that appear in the UXW card but have no sidecar origin are removed.

8. **Skipping archival** — Writing new persona files without first archiving existing ones creates two sources of truth. The `git mv` archival step is mandatory and non-skippable.

---

## Quality Bars

Per `docs/methodology/product-discovery.md` §2 checklist:

- Every sidecar field must cite at least one `[source: evidence/subject-NN.md Q##]` from the upstream evidence bank.
- Every UXW task card field must trace to a sidecar field (documented in-line).
- The `archived/v1-secondary/README.md` must distinguish v1 (secondary-research-derived) from v2 (primary-research-synthesized) provenance.
- A run where every `/product-research` hypothesis returned `supports` is flagged as high-risk before persona synthesis begins — require explicit acknowledgment before proceeding.
- Each top-up researcher prompt must be self-contained (no "see doc X" references).
