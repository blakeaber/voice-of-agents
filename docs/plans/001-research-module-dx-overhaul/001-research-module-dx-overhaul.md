# Plan 001: Research Module DX Overhaul

## Context

The `voice_of_agents.research` module was built with the right internal architecture — 4-stage pipeline, typed Pydantic contracts, parallel async Claude calls, `ResearchSession` persistence — but organized around research methodology rather than developer decisions. A founder assessment (see `docs/research/founder-assessment-2026-04-20.md`) identified three critical failure modes that will kill organic adoption:

1. **Time-to-value is catastrophically long.** Three commands before any output. No demo mode. No cost estimate. First-time users pay real money, get a YAML file, and never return.
2. **Entry is expert-gated.** "Falsifiable question," "population scope," "adoption status" — this is UX research vocabulary that excludes the exact developers this tool should serve.
3. **Outputs don't connect to decisions.** The pipeline ends at `ResearchSession`. There's no "build this first," no ranked actionable finding, no path from analysis to action.

Beyond these three, the assessment identified five additional gaps: the epistemic danger of treating synthetic data as real research; the invisibility of cost and time; the absence of the `research → eval` bridge (the most unique workflow nobody knows about); zero integration with real signals; and no strategic positioning or manifesto to make the worldview legible.

**Intended outcome:** The three target personas — pre-PMF solo founder, product engineer who owns the roadmap, DX practitioner building dev tools — reach "ecstatic" from the first `voa research` command. Organic adoption happens because the first experience is surprising and delightful, not because the architecture is sound.

**Source:** `docs/research/founder-assessment-2026-04-20.md`

---

## Phase Index

| Phase | Title | Effort | Risk | Priority | Status |
|-------|-------|--------|------|----------|--------|
| 001-A | Epistemic Honesty Layer | Small | Low | Critical | Complete |
| 001-B | `quick_research()` One-Liner API | Medium | Low | Critical | Complete |
| 001-C | `voa research demo` — 60-Second Wow Moment | Small | Low | Critical | Complete |
| 001-D | `voa research quickstart` — Plain-English Entry | Medium | Low | High | Complete |
| 001-E | Cost + Time Transparency | Small | Low | High | Complete |
| 001-F | Decision-Oriented Output Layer | Medium | Medium | High | Complete |
| 001-G | Research → Eval Bridge | Medium | Medium | High | Complete |
| 001-H | Real Signal Ingestion | Medium | Medium | Medium | Complete |
| 001-I | Manifesto, README, and Examples | Medium | Low | High | Complete |

**Execution Sequence:** 001-A → 001-B → 001-C → 001-D → 001-E → 001-F → 001-G → 001-H → 001-I

001-A has no dependencies and can be done immediately.
001-B depends on 001-A (honest framing should be built in from the start of the new API).
001-C and 001-D can run in parallel after 001-B.
001-E can run in parallel with 001-C and 001-D.
001-F depends on 001-B (builds on the quick_research output model).
001-G depends on 001-F (uses the decision output in the eval bridge).
001-H can run after 001-B independently.
001-I depends on all prior phases (documents what was built).

---

## Phase Detail Sections

---

### Phase 001-A — Epistemic Honesty Layer

**What:**
Add a `SYNTHETIC-DATA-NOTICE.md` artifact to every research run output. Embed honest synthetic framing in `ResearchSession.export_summary()`. Add a `SyntheticDataNotice` model that serves as a **workflow guide** (not legal boilerplate) telling developers what to do next with their synthetic output.

The notice must answer three questions:
1. What is this? (synthetic personas generated from a language model)
2. What it is NOT? (observed human behavior)
3. What to do next? (3 concrete validation questions to ask a real user)

The notice is generated once per session and auto-appended to every output directory. It also appears as a highlighted block at the top of `RESEARCH-SUMMARY.md`.

**Files to create:**
- `src/voice_of_agents/research/notice.py` — `SyntheticDataNotice` model + `generate_notice()` function

**Files to modify:**
- `src/voice_of_agents/research/session.py` — call `generate_notice()` in `export_summary()` and `save()`
- `src/voice_of_agents/research/pipeline.py` — emit `SYNTHETIC-DATA-NOTICE.md` alongside session YAML on every save
- `tests/unit/research/test_session.py` — add tests for notice presence in summary output

**Acceptance Criteria:**
- [ ] `ResearchSession.export_summary()` includes a `⚠️ Synthetic Data` section at the top with "treat as hypothesis" language
- [ ] Every `session.save(path)` call also writes `SYNTHETIC-DATA-NOTICE.md` to `path.parent/`
- [ ] `SYNTHETIC-DATA-NOTICE.md` includes: what it is, what it is not, and 3 validation questions derived from the research question
- [ ] `pytest tests/unit/research/test_session.py` passes with new notice tests
- [ ] Notice language uses plain English, not research jargon

---

### Phase 001-B — `quick_research()` One-Liner API

**What:**
Add a `quick_research()` function as the **primary public API** for the library. This is the single function a developer needs to understand. It accepts plain-English strings (no methodology vocabulary), runs an abbreviated 3-stage pipeline (skips journey redesign by default), and returns a `QuickResearchResult` with decision-oriented fields.

The function hides the 4-stage pipeline entirely. Internally it translates plain-English input into a `ProductResearchInput` (using a Claude call to generate a falsifiable hypothesis from the plain description), runs with a reduced subject count (default 6 for speed), and synthesizes a `QuickResearchResult`.

```python
from voice_of_agents.research import quick_research

result = quick_research(
    what="a coding assistant that helps developers write tests",
    who="senior developers at startups",
    understand="why developers abandon AI coding tools after the first week",
)

result.top_findings       # list[str] — 3-5 ranked behavioral findings
result.personas           # list[QuickPersona] — 2-3 user archetypes, plain English
result.build_this_first   # str — single highest-signal recommendation
result.churn_triggers     # list[str] — what would cause each archetype to leave
result.validate_with      # list[str] — 3 questions to ask a real user
result.session            # ResearchSession — full typed data for power users
```

**Files to create:**
- `src/voice_of_agents/research/quick.py` — `quick_research()`, `quick_research_sync()`, `QuickResearchResult`, `QuickPersona`

**Files to modify:**
- `src/voice_of_agents/research/__init__.py` — export `quick_research`, `quick_research_sync`, `QuickResearchResult`
- `src/voice_of_agents/research/prompts/quick/` — new prompt subdirectory
- `src/voice_of_agents/research/prompts/quick/translate_to_question.j2` — translates plain-English → falsifiable question
- `src/voice_of_agents/research/prompts/quick/synthesize_result.j2` — synthesizes session into QuickResearchResult fields
- `tests/unit/research/test_quick.py` — new test file

**Acceptance Criteria:**
- [ ] `quick_research(what=..., who=..., understand=...)` runs without error with a mocked Anthropic client
- [ ] Returns `QuickResearchResult` with all 6 fields populated
- [ ] `result.build_this_first` is a single actionable sentence, not a research summary
- [ ] `result.validate_with` contains 3 concrete questions a founder could ask a real user
- [ ] `result.personas` contains 2-3 `QuickPersona` objects with plain-English `archetype`, `top_concern`, and `would_pay_if` fields
- [ ] `quick_research_sync()` works as a synchronous wrapper
- [ ] `from voice_of_agents.research import quick_research` works
- [ ] `pytest tests/unit/research/test_quick.py` passes

---

### Phase 001-C — `voa research demo` — 60-Second Wow Moment

**What:**
Add a `voa research demo` CLI command that runs a preset research scenario with no configuration required. The demo:

- Uses a preset question about developer tool adoption (about a tool like this library)
- Runs with 3 subjects (not 12) — fast and cheap (~$0.30)
- Shows a live progress indicator during the run
- Produces a legible, opinionated 5-bullet output to the terminal (no YAML, no files unless `--save` is passed)
- Tells the user exactly what just happened and what to do next

The demo is the *first experience*. It must be surprising and delightful. The output should make the user say "I didn't know a tool could tell me this in 60 seconds."

The preset question: *"Why do developers adopt AI developer tools enthusiastically at first but abandon them within the first month?"*

**Files to modify:**
- `src/voice_of_agents/cli/research_cli.py` — add `demo` command
- `src/voice_of_agents/research/quick.py` — add `run_demo()` function with preset config and Rich progress display

**Acceptance Criteria:**
- [ ] `voa research demo` runs with only `ANTHROPIC_API_KEY` set — no other config required
- [ ] Command completes in under 90 seconds on a standard connection
- [ ] Terminal output is human-readable, uses Rich formatting, shows at least 5 behavioral findings
- [ ] Output includes "What to do next" section with 3 concrete next steps
- [ ] Command shows a progress indicator while Claude calls are in-flight (not a hanging terminal)
- [ ] Running `voa research demo --save` writes the session YAML and `RESEARCH-SUMMARY.md` to `./demo-output/`
- [ ] No configuration files or interactive prompts required

---

### Phase 001-D — `voa research quickstart` — Plain-English Entry

**What:**
Replace the current `voa research init` flow (which asks for methodology-vocabulary inputs) with a `voa research quickstart` command that asks three plain-English questions, then internally translates them into a valid `ResearchConfig` YAML.

```
voa research quickstart

What are you building? (one sentence)
> A Slack bot that helps teams track action items from meetings

Who are your users? (one sentence)  
> Engineering managers at startups

What's the #1 thing you want to understand about them?
> Why teams stop using action item trackers after the first few sprints

✓ Translated to research question: "Do teams abandon action-item trackers..."
✓ Generated research-config.yaml
→ Run: voa research run
```

The translation step uses a Claude call to reframe the plain-English input as a falsifiable hypothesis and appropriate scope. It shows the translated version and asks for confirmation before saving. Invalid translations (e.g., target-market strings that can't be reframed as falsifiable questions) surface a helpful error with an example of the right framing.

Also add `from_plain_english()` classmethod to `ResearchConfig` for programmatic use.

**Files to modify:**
- `src/voice_of_agents/cli/research_cli.py` — add `quickstart` command
- `src/voice_of_agents/research/config.py` — add `from_plain_english(what, who, understand)` classmethod + `_translate_to_config()` async helper
- `src/voice_of_agents/research/prompts/quick/translate_to_config.j2` — prompt that takes plain-English trio and outputs ResearchConfig fields
- `tests/unit/research/test_config.py` — add tests for `from_plain_english()` with mocked translation

**Acceptance Criteria:**
- [ ] `voa research quickstart` asks exactly 3 questions, no more
- [ ] Translation step runs a single Claude call and shows the translated question before saving
- [ ] User can confirm (Enter) or reject (Ctrl+C) the translation
- [ ] `research-config.yaml` is written and immediately runnable with `voa research run`
- [ ] `ResearchConfig.from_plain_english(what=..., who=..., understand=...)` is callable in Python
- [ ] Invalid inputs that cannot be translated into falsifiable questions surface a clear error with an example
- [ ] `pytest tests/unit/research/test_config.py` passes with new tests

---

### Phase 001-E — Cost + Time Transparency

**What:**
Every `voa research run` invocation must show a cost estimate and time estimate *before* making any API calls, with a confirmation prompt. The user must opt in to spending money.

Estimates are based on:
- Model selected (`claude-opus-4-7` vs `claude-haiku-4-5`)
- Subject count (10-16)
- Stages selected (all 4 vs subset)
- Typical token usage per stage (documented constants)

Also add a `--dry-run` flag to `voa research run` that shows the estimate without executing.

Add a `--model haiku` shortcut that switches to `claude-haiku-4-5-20251001` for low-cost exploration runs (1/20th the cost, still produces useful output for hypothesis exploration).

Display a live cost accumulator in the terminal footer during runs (using Rich Live) showing `$X.XX spent | ~$X.XX remaining`.

**Files to create:**
- `src/voice_of_agents/research/cost.py` — `CostEstimate` model, `estimate_run_cost()`, `COST_PER_STAGE` constants, `track_cost()` context manager

**Files to modify:**
- `src/voice_of_agents/cli/research_cli.py` — add `--dry-run`, `--model haiku` flags; show estimate + confirmation before run; show live cost during run
- `src/voice_of_agents/research/pipeline.py` — integrate `track_cost()` context manager
- `src/voice_of_agents/research/client.py` — add token counting wrapper on `client.messages.create()`
- `tests/unit/research/test_cost.py` — new test file

**Acceptance Criteria:**
- [ ] `voa research run` shows cost estimate before executing: `Estimated cost: $X.XX–$X.XX | Estimated time: X–X minutes`
- [ ] User must press Enter to confirm or Ctrl+C to abort
- [ ] `voa research run --dry-run` shows estimate and exits without API calls
- [ ] `voa research run --model haiku` uses `claude-haiku-4-5-20251001` for all calls
- [ ] Live cost display updates in terminal footer during run (not on every line — Rich Live footer)
- [ ] `estimate_run_cost(config)` returns `CostEstimate` with `low`, `high`, `time_minutes_low`, `time_minutes_high`
- [ ] `pytest tests/unit/research/test_cost.py` passes

---

### Phase 001-F — Decision-Oriented Output Layer

**What:**
Add a `DecisionReport` model and `generate_decision_report()` function that transforms a completed `ResearchSession` into the outputs founders and product engineers actually need:

- **`build_this_first`**: Single highest-signal feature or capability, backed by evidence
- **`kill_these_assumptions`**: List of founder assumptions the research refuted
- **`top_churn_triggers`**: Ranked list of things that would cause each user type to leave
- **`pricing_signals`**: What the research says about willingness to pay and at what threshold
- **`segment_map`**: Plain-English description of 2-3 user archetypes (no "behavioral segment" jargon)
- **`validated_hypotheses`** / **`refuted_hypotheses`**: Split by verdict
- **`open_questions`**: What the synthetic research couldn't answer — requires real user validation

This is generated as a separate artifact from `RESEARCH-SUMMARY.md`. It lives at `DECISION-REPORT.md` in the session output directory and is printed to the terminal at the end of `voa research run`.

Also update `voa research export` to emit both `RESEARCH-SUMMARY.md` and `DECISION-REPORT.md` by default.

**Files to create:**
- `src/voice_of_agents/research/decisions.py` — `DecisionReport`, `generate_decision_report()`, `generate_decision_report_sync()`
- `src/voice_of_agents/research/prompts/decisions/synthesize_decision_report.j2` — prompt that synthesizes session → DecisionReport fields
- `tests/unit/research/test_decisions.py` — new test file

**Files to modify:**
- `src/voice_of_agents/research/session.py` — add `generate_decision_report()` method delegating to `decisions.py`
- `src/voice_of_agents/research/pipeline.py` — emit `DECISION-REPORT.md` at pipeline end
- `src/voice_of_agents/cli/research_cli.py` — print `DECISION-REPORT.md` to terminal at end of `voa research run`; update `export` command
- `src/voice_of_agents/research/__init__.py` — export `DecisionReport`, `generate_decision_report`

**Acceptance Criteria:**
- [ ] `session.generate_decision_report()` returns `DecisionReport` with all 7 fields populated
- [ ] `build_this_first` is a single sentence, not a paragraph
- [ ] `kill_these_assumptions` is a list of strings, each phrased as "Your assumption that X is wrong because Y"
- [ ] `DECISION-REPORT.md` is written to the session output directory at pipeline completion
- [ ] `voa research run` prints `DECISION-REPORT.md` content to terminal as the final output (not the YAML path)
- [ ] `voa research export` emits both `RESEARCH-SUMMARY.md` and `DECISION-REPORT.md`
- [ ] `pytest tests/unit/research/test_decisions.py` passes

---

### Phase 001-G — Research → Eval Bridge

**What:**
Wire the most unique workflow nobody currently knows about: **synthetic research → typed canonical personas → real browser-based product exploration**.

This is the "demo that goes viral." A developer runs `voa research quickstart`, gets synthetic personas, then runs `voa eval run` and watches those personas navigate their actual product in a browser, producing friction reports and backlog items. The full loop from "I don't know my users" to "I have typed personas navigating my product with evidence-backed failure modes."

This requires:
1. A `to_canonical_persona()` method on `UXWPersonaSidecar` that converts research output to the `Persona` model used by `eval/`
2. A `voa research seed-eval` CLI command that takes a session YAML and populates `data/personas/` with canonical persona YAML files ready for `voa eval phase2`
3. A `ResearchSession.to_eval_personas()` method
4. Updated `voa research export` to include a `--seed-eval` flag
5. A `BRIDGE-WORKFLOW.md` document explaining the full loop with exact commands

The bridge must preserve all behavioral evidence: `voice_profile` calibrated from `constraint_profile` and `failure_or_abandonment_mode`, `pain_points` derived from `verbatim_quote_bank`, `trust_requirements` from `decision_topology`.

**Files to create:**
- `src/voice_of_agents/research/bridge.py` — `to_canonical_persona()`, `ResearchSession.to_eval_personas()`, `seed_eval_personas()`
- `docs/BRIDGE-WORKFLOW.md` — the documented killer workflow (full command sequence with expected output)
- `tests/unit/research/test_bridge.py` — conversion correctness tests

**Files to modify:**
- `src/voice_of_agents/research/models.py` — add `to_canonical_persona()` to `UXWPersonaSidecar`
- `src/voice_of_agents/research/session.py` — add `to_eval_personas()` method
- `src/voice_of_agents/cli/research_cli.py` — add `seed-eval` command; add `--seed-eval` flag to `export`
- `src/voice_of_agents/research/__init__.py` — export `seed_eval_personas`

**Acceptance Criteria:**
- [ ] `UXWPersonaSidecar.to_canonical_persona()` returns a valid `Persona` object that passes `validate_personas()` from `eval/phase1_generate.py`
- [ ] `ResearchSession.to_eval_personas()` returns `list[Persona]` — one per sidecar
- [ ] `voa research seed-eval <session.yaml>` writes `data/personas/P-{id:02d}-{slug}.yaml` files for each persona in the session
- [ ] Seeded personas can be immediately used by `voa eval phase2` without modification
- [ ] `VoiceProfile` on each seeded persona reflects the sidecar's behavioral evidence (skepticism, vocabulary, motivation)
- [ ] `BRIDGE-WORKFLOW.md` documents the full loop with exact commands: `voa research quickstart → voa research run → voa research seed-eval → voa eval run`
- [ ] `pytest tests/unit/research/test_bridge.py` passes

---

### Phase 001-H — Real Signal Ingestion

**What:**
Add `from_transcripts()`, `from_csv()`, and `from_json()` constructors to `ResearchConfig` that allow developers to bring real signals (interview notes, NPS responses, support tickets, survey data) and use the library to synthesize *on top of real data* rather than purely from Claude's priors.

In hybrid mode:
- Real signals are embedded into the researcher briefing prompts as grounding context
- The synthetic subjects must be consistent with the real signals (cannot contradict them)
- Subjects derived from real transcripts are marked `source: "real"` in metadata; purely synthetic ones are `source: "synthetic"`
- The `SYNTHETIC-DATA-NOTICE.md` adjusts its language based on what percentage of subjects are real-grounded

This is the transition from "synthetic research theater" to "synthetic research with real guardrails" — the genuinely defensible mode.

**Files to create:**
- `src/voice_of_agents/research/signals.py` — `RealSignal`, `SignalIngester`, `from_transcripts()`, `from_csv()`, `from_json()`
- `src/voice_of_agents/research/prompts/_partials/real_signal_context.j2` — partial included in researcher_brief when real signals are present
- `tests/unit/research/test_signals.py` — ingestion and grounding tests

**Files to modify:**
- `src/voice_of_agents/research/config.py` — add `real_signals: list[RealSignal]` field; add `from_transcripts()`, `from_csv()`, `from_json()` classmethods
- `src/voice_of_agents/research/product_research.py` — inject real signal context into `researcher_brief.j2` when signals are present
- `src/voice_of_agents/research/notice.py` — adjust notice language based on hybrid vs. pure-synthetic mode
- `src/voice_of_agents/research/__init__.py` — export `from_transcripts`, `from_csv`, `from_json`

**Acceptance Criteria:**
- [ ] `ResearchConfig.from_transcripts(["interview1.txt", "interview2.txt"])` loads and chunks text files as `RealSignal` objects
- [ ] `ResearchConfig.from_csv("nps_responses.csv", text_column="comment")` loads CSV text column as signals
- [ ] `ResearchConfig.from_json("support_tickets.json", text_field="body")` loads JSON array as signals
- [ ] When real signals are present, the researcher prompt includes the signal context as grounding
- [ ] Synthetic subjects do not contradict real signal content (tested by assertion in the prompt)
- [ ] `SYNTHETIC-DATA-NOTICE.md` says "partially grounded in real signals" when hybrid mode is active
- [ ] `pytest tests/unit/research/test_signals.py` passes

---

### Phase 001-I — Manifesto, README, and Examples

**What:**
Replace the current README with the strategic positioning, ship the manifesto, and add an `examples/` directory with three complete, runnable examples — one for each target persona.

**The manifesto** (`docs/MANIFESTO.md`): A 3-page document titled *"Why most startup research is useless and what to do instead."* It argues that:
- Founders interview happy users → learn nothing about why they'll churn
- Real user research is too slow and expensive for pre-PMF decisions
- Synthetic research is not a replacement for real research — it's a *forcing function* for better questions
- The sampling frame (including abandoners, critics, refusers) is the insight engine
- Ship fast hypotheses before you ship slow features

The manifesto ends with: "This library is the implementation of this worldview. Fork it, adapt it, argue with it."

**The README** rewrite:
- Opens with the 60-second `voa research demo` output (copy-pasted terminal recording)
- Shows `quick_research()` one-liner in the second paragraph
- Positions as: *"Research-grade rigor for developers who can't afford a research team"*
- Explains the synthetic-then-validate loop explicitly (not buried in a disclaimer)
- Shows the full `research → eval` bridge workflow
- Links to manifesto, examples, and `BRIDGE-WORKFLOW.md`

**The examples** (`examples/`):
- `examples/solo-founder/` — pre-PMF solo founder use case: `quickstart → run → decision-report`
- `examples/product-engineer/` — product engineer use case: `quick_research()` one-liner with mocked client, output parsing
- `examples/dx-practitioner/` — DX practitioner use case: `quickstart → run → seed-eval → eval run` (the full bridge)

Each example includes: a `README.md`, a `research-config.yaml`, and a `run.py` or shell script.

**Files to create:**
- `docs/MANIFESTO.md`
- `docs/BRIDGE-WORKFLOW.md` (if not created in Phase G)
- `examples/solo-founder/README.md`
- `examples/solo-founder/research-config.yaml`
- `examples/solo-founder/run.sh`
- `examples/product-engineer/README.md`
- `examples/product-engineer/research-config.yaml`
- `examples/product-engineer/run.py`
- `examples/dx-practitioner/README.md`
- `examples/dx-practitioner/research-config.yaml`
- `examples/dx-practitioner/run.sh`

**Files to modify:**
- `README.md` — full rewrite per positioning above

**Acceptance Criteria:**
- [ ] `README.md` opens with a terminal recording or ASCII demo output — no architecture diagram on line 1
- [ ] `README.md` shows `quick_research()` one-liner within the first 20 lines
- [ ] `README.md` positions the tool as "research-grade rigor for developers who can't afford a research team"
- [ ] `docs/MANIFESTO.md` is 800-1500 words, uses plain language, ends with the fork invitation
- [ ] `examples/solo-founder/run.sh` executes end-to-end with `ANTHROPIC_API_KEY` set and `--model haiku`
- [ ] `examples/product-engineer/run.py` runs with a mocked client (no API key required for the demo)
- [ ] `examples/dx-practitioner/run.sh` includes `voa research seed-eval` and `voa eval` commands in sequence
- [ ] All example READMEs explain what the user should see as output and what to do with it

---

## Execution Sequence

```
001-A (Epistemic Honesty)
  ↓
001-B (quick_research one-liner)
  ↓              ↓              ↓
001-C (demo)  001-D (quickstart) 001-E (cost transparency)
  ↓
001-F (Decision-Oriented Output)
  ↓              ↓
001-G (Eval Bridge)  001-H (Real Signals)
  ↓
001-I (Manifesto + README + Examples)
```

---

## Files Modified Across All Phases (Summary)

**New files:**
- `src/voice_of_agents/research/notice.py`
- `src/voice_of_agents/research/quick.py`
- `src/voice_of_agents/research/cost.py`
- `src/voice_of_agents/research/decisions.py`
- `src/voice_of_agents/research/bridge.py`
- `src/voice_of_agents/research/signals.py`
- `src/voice_of_agents/research/prompts/quick/translate_to_question.j2`
- `src/voice_of_agents/research/prompts/quick/translate_to_config.j2`
- `src/voice_of_agents/research/prompts/quick/synthesize_result.j2`
- `src/voice_of_agents/research/prompts/decisions/synthesize_decision_report.j2`
- `src/voice_of_agents/research/prompts/_partials/real_signal_context.j2`
- `tests/unit/research/test_quick.py`
- `tests/unit/research/test_cost.py`
- `tests/unit/research/test_decisions.py`
- `tests/unit/research/test_bridge.py`
- `tests/unit/research/test_signals.py`
- `docs/MANIFESTO.md`
- `docs/BRIDGE-WORKFLOW.md`
- `examples/solo-founder/` (3 files)
- `examples/product-engineer/` (3 files)
- `examples/dx-practitioner/` (3 files)

**Modified files:**
- `src/voice_of_agents/research/__init__.py`
- `src/voice_of_agents/research/session.py`
- `src/voice_of_agents/research/pipeline.py`
- `src/voice_of_agents/research/config.py`
- `src/voice_of_agents/research/models.py`
- `src/voice_of_agents/research/product_research.py`
- `src/voice_of_agents/research/client.py`
- `src/voice_of_agents/cli/research_cli.py`
- `README.md`

---

## Verification: End-to-End Test After All Phases

```bash
# The 60-second wow moment — no config, just an API key
export ANTHROPIC_API_KEY=sk-...
voa research demo

# The quickstart path — 3 plain-English questions → runnable config
voa research quickstart
voa research validate-config research-config.yaml
voa research run research-config.yaml --dry-run  # shows cost, no API calls
voa research run research-config.yaml --model haiku  # cheap exploration run

# The Python one-liner
python -c "
from voice_of_agents.research import quick_research
r = quick_research(what='a coding assistant', who='senior devs at startups', understand='why they abandon AI tools')
print(r.build_this_first)
print(r.validate_with)
"

# The killer workflow — research to real browser exploration
voa research run research-config.yaml
voa research seed-eval research-sessions/my-slug.yaml
voa eval run --all

# The hybrid mode — real signals
python -c "
from voice_of_agents.research.config import ResearchConfig
config = ResearchConfig.from_transcripts(['interviews/user1.txt', 'interviews/user2.txt'])
"

# Test suite
pytest tests/unit/research/ -v  # all new tests pass
pytest tests/ -q               # full suite: 292+ passing
```

## Success Criteria

The plan is complete when a developer with no prior knowledge of this library can:

1. Run `voa research demo` in under 90 seconds and produce legible, surprising output
2. Go from "I don't know my users" to `DECISION-REPORT.md` in under 10 minutes using `voa research quickstart` + `voa research run --model haiku`
3. Read `README.md` and understand what the tool does, why it exists, and what to do with the output — without reading any other documentation
4. Run the full `research → eval` bridge workflow using exactly the commands in `docs/BRIDGE-WORKFLOW.md`
5. Pass all 292+ tests with `pytest tests/ -q`
