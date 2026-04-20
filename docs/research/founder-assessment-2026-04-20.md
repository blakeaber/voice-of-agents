# Founder Assessment: `voice_of_agents.research`

**Date:** 2026-04-20  
**Perspective:** Multi-exit founder with deep product and DevX experience  
**Subject:** The `voice_of_agents.research` module — DX, workflows, value, gaps, and strategic positioning

---

## What This Library Actually Is

Before assessing anything else, I need to name the thing clearly, because **the library itself doesn't know what it is** — and that's the root of most of the problems.

This is a **synthetic research simulation engine** backed by Claude. Every "research subject," every "focus group participant," every "abandoner with a failure mode" — they are all Claude roleplaying. The 8-field SubjectRecord schema looks rigorous. The sampling frame enforcement is methodologically sound. But the entire pipeline produces **synthetic artifacts generated from a language model's priors**, not from real human behavior.

This is not a criticism. It's the most important thing to understand about where the tool fits, what problems it solves, and why it will succeed or fail.

---

## Where It Provides Genuine, Unique Value

### 1. Forced methodological discipline

The best thing this library does is encode *what good research methodology looks like* as **executable guardrails**. Most founders skip straight to building. This library catches:

- "You asked about a target market, not a falsifiable question" → rejected
- "You have only 1 abandoner in your sampling frame" → rejected
- "All your hypotheses returned `supports`" → confirmation bias warning

These aren't just validations. They're a research curriculum embedded in a Python package. That's genuinely rare and valuable. A developer who runs this library even once and reads the error messages learns something real about how to think about customers.

### 2. The sampling frame is the real insight engine

The 2D matrix — adoption-status × context-segment — with hard minimums on abandoners, critics, and refusers is the methodologically honest part of this library. Most founders interview their happy users. This library structurally *forces* you to include the people who left, evaluated-and-rejected, and actively advise others against you.

That's not a feature. That's a worldview. Encode it, enforce it, lead with it.

### 3. Parallel synthetic speed

10-16 simultaneous Claude calls synthesizing independent perspectives in 60 seconds is genuinely novel. Not because the data is real — it isn't — but because it's fast enough to be *iterative*. You can run this before a Monday planning meeting, generate five hypotheses, and kill three of them before they become roadmap items. That's a real workflow unlock.

### 4. The `ResearchSession` persistence pattern

Git-friendly, stage-by-stage YAML with resumability is solid engineering. This is what research *should* look like for a developer — not a Notion doc, not a Miro board, but a typed artifact you can diff, version, and feed into downstream systems.

---

## Where It Falls Short — Honest Critique

### 1. The epistemic danger is not disclosed

This is the most serious problem, and it's existential.

The library produces outputs that *look* like research. `UXWPersonaSidecar` with 8 fields and embedded citations. `SubjectRecord` with `failure_or_abandonment_mode` and `verbatim_quote_bank`. These artifacts carry the visual grammar of rigorous user research. They will be treated as real by developers who are under pressure, optimistic, and not methodologically trained.

A founder who uses this library to *avoid* talking to real customers — because they feel like they've already done the research — will build the wrong thing with high confidence. That's worse than no research at all.

**The library needs a prominent, opinionated disclaimer built into every output artifact.** Not legal boilerplate — a real statement like: *"These are synthetic personas based on language model priors, not observed human behavior. Treat them as hypotheses to test, not conclusions to act on."*

### 2. Time-to-value is catastrophically long

The current first-run flow:
1. `voa research init` → answer 4 methodological questions
2. `voa research validate-config`
3. `voa research run` → wait 3-10 minutes, spend $5-25 in API calls
4. Get a YAML file and a markdown summary
5. Now what?

A developer encountering this for the first time will hit step 3, watch the terminal hang, pay real money, get a YAML file, open it, not know what to do with the Pydantic objects, and never return.

There is no `voa research demo`. There is no demo mode with 3 subjects and a preset question. There is no cost or time estimate before the run starts. This will kill organic adoption.

### 3. The entry question is expert-gated

"Research question (falsifiable question about a customer population, NOT a target-market name)"

This is the first thing a new user sees. Most developers don't know what "falsifiable question" means in a research context. Most founders, when asked to describe their research question, will say something like "do people want this" or "who is my customer." The library rejects both of those and gives them a methodology lecture.

The methodology is *correct*. But making it the entry gate ensures that only people who already know product research will successfully start. That's not a library — that's a tool for researchers who already know what they're doing.

### 4. The four-stage chain is overengineered for the primary use case

Most developers who discover this tool want one thing: *"Tell me what to build next."*

The library requires them to run four stages, each producing intermediate artifacts they don't know what to do with. `ProductResearchOutput` → `PersonaResearchInput` → `PersonaResearchOutput` → `WorkflowResearchInput`... by stage 3, you've lost 90% of the people who started.

The four-stage chain is the right *internal* architecture. It should not be the *user-facing* experience.

### 5. The outputs don't connect to decisions

What do you do after `run_full_pipeline_sync` returns? You have a `ResearchSession` with typed Pydantic objects. You have a `RESEARCH-SUMMARY.md`. But there's no "here are the 3 things to build next, ranked by evidence strength." The library stops at analysis and never reaches the thing founders actually need: **a ranked, actionable decision.**

The gap between "synthesized segments" and "ship this feature first" is the entire job of a product leader. The library leaves that gap completely open.

### 6. Zero integration with real signals

The library is 100% synthetic. There's no path for:
- Importing real NPS comments
- Ingesting real support tickets
- Combining Mixpanel funnel data with synthetic research
- Grounding synthetic personas with real segment behavior

This means the library competes with real research (and loses, because it's synthetic) rather than *augmenting* real research (which it could win at — by being the cheap, fast first pass before you do the expensive, slow real thing).

### 7. The "synthetically run focus groups" claim is misleading

These aren't focus groups. They're Claude pretending to be users. For a bootstrapped founder, this is "synthetic research theater" — it feels like real research but produces synthetic data. The danger is founders using this to *avoid* talking to real customers.

### 8. The DevX is rough for the first-time user

- `voa research init` then `voa research validate-config` then `voa research run` — three commands before you see any value
- No `voa research quickstart` or demo mode
- The interactive prompts ask for complex methodological concepts ("falsifiable question", "population scope") that most developers can't answer off the top of their head
- No examples shipped with the package

### 9. The submodule use case is backwards

The RESEARCH-SUMMARY.md is supposed to be "the artifact that Claude Code reads." But the actual workflow is undefined. Claude Code reads it and then... does what exactly? There's no documented workflow for "Claude Code reads this and then does X."

### 10. Pricing/cost model is invisible

Running `run_full_pipeline_sync` with 12 subjects + top-up + focus group could easily cost $5-20 in API calls with Claude Opus. Developers need to know this upfront.

---

## What Entrepreneurial Developers Would Actually Use This For

There are three personas who might genuinely adopt this:

### The pre-PMF solo founder

They're building something and need to think through "who actually has this problem." They can't afford real UX research. They don't have a design partner yet. They need a cheap, fast way to pressure-test their assumptions before spending 3 months building.

This persona would use the library if the time-to-value was under 5 minutes and the first output was a human-readable list of "here's what your three most likely user types care about, and here's what would make them quit."

They would *not* use it as currently designed because it requires too much methodological sophistication to configure and produces outputs too far from actionable decisions.

### The product engineer who owns roadmap decisions

They're on a team of 5-15 people. They own both code and product decisions. They want to run a quick "what would our users think about this feature idea" check before writing a spec. They understand Python. They would appreciate a type-safe, git-friendly research workflow.

This persona would use `run_product_research_sync` if it could be invoked with a single well-described question and produced a markdown summary with ranked findings in under 2 minutes.

### The developer-experience practitioner building tools for developers

They're building developer tools, SDKs, or platforms. They need to generate realistic developer personas for testing their onboarding flows. This library's eval pipeline integration — connecting synthetic personas to Playwright-based browser exploration — is genuinely useful for this.

This is the highest-value, least-addressed persona. The connection between synthetic research → typed personas → automated browser evaluation is the genuinely novel pipeline nobody else has. It's buried in the eval/ module and not marketed at all.

---

## What Needs to Change for Organic Adoption

These are in priority order. The first three are existential.

**1. Ship a 60-second demo that produces legible value**

```bash
voa research demo
```

Preset question (about the library itself), 3 subjects, no configuration, runs in 60 seconds, costs $0.30, produces 5 bullet points. The first experience must be *surprising and delightful*, not a methodology tutorial.

**2. Make the input human-friendly, not research-methodology-friendly**

```bash
voa research quickstart
→ What are you building? (one sentence)
→ Who is your user? (one sentence)  
→ What's the main thing you're trying to understand?
```

The library translates this into a falsifiable hypothesis and sampling frame *internally*. The developer never sees the methodology machinery — they just get the output.

**3. Add an explicit "this is synthetic, use it as a starting point" contract**

Every run should emit a `SYNTHETIC-DATA-NOTICE.md` alongside `RESEARCH-SUMMARY.md`. Not as a disclaimer — as a **workflow guide**: "Here's what to do next with this output. Here are the 3 questions to ask a real user to validate or invalidate what you just synthesized."

**4. Flatten the primary user path to one command**

```python
from voice_of_agents.research import quick_research

result = quick_research(
    "Why do developers abandon AI coding tools?",
    product="a coding assistant",
)
# → result.top_findings (list of ranked strings)
# → result.personas (3 behaviorally distinct types)
# → result.build_this_first (the one highest-signal recommendation)
```

The 4-stage pipeline should be an implementation detail, not the API surface.

**5. Build the bridge to real signals**

Add `from_transcripts(files)`, `from_csv(path)`, `from_json(path)` to `ResearchConfig`. Let developers bring real interview notes, support tickets, or NPS responses and have the library synthesize *on top of* real data. That's when this becomes genuinely defensible — synthetic research grounded in real signals, not synthetic research in isolation.

**6. Wire up the most valuable workflow that nobody talks about**

`research/ output → eval/ Playwright exploration` is the unique thing. A typed, evidence-backed persona that actually *uses your product* via a real browser — that's the demo that goes viral on Hacker News. It needs to be a first-class, documented, one-command workflow.

---

## Strategic Positioning for Open Source

### The thesis

Most software is built for an imagined user. The developer imagines the user in the shower, writes the spec in a Google Doc, ships the feature, and wonders why nobody uses it. The gap between "I think users want X" and "I know users need X" is expensive — in the form of wasted engineering time, failed products, and burnt capital.

This library's job is to **make that gap smaller, earlier, and cheaper** than any alternative.

### The positioning

Not "AI-powered user research." That's a commodity claim and epistemically dubious.

Not "synthetic focus groups." That's accurate but sounds like a toy.

**"Research-grade rigor for developers who can't afford a research team."**

The competitor is not Dovetail, not UserTesting, not Maze. The competitor is *nothing* — the founder who skips research entirely because it's too expensive and too slow. The tool wins by being faster and cheaper than doing nothing wrong, not by being more rigorous than a real research firm.

### The community play

Open source this as the *methodology*, not the *tool*.

The 8-field subject schema, the sampling frame enforcement, the hypothesis falsification requirement — these are research design decisions that represent a specific worldview about how to understand customers. Make that worldview the brand. The library is an expression of the worldview, not the thing itself.

Write the 3-page manifesto: *"Why most startup research is useless and what to do instead."* The library is the implementation of that manifesto. Developers who read the manifesto and agree become evangelists before they write a single line of code.

### The strategic moat

Every competitor in "AI user research" is building a SaaS product with a chat interface. Their moat is distribution and UX polish. This library's moat, if it captures it, is **developer trust through transparency**. Open source, typed artifacts, git-friendly outputs, no vendor lock-in, Claude-agnostic (the prompts are in `.j2` files anyone can fork). That's a defensible position against every SaaS player in this space.

### The strategic risk

The risk is becoming a "neat prototype" that gets forked, starred, and never maintained. Open source tools die from abandonment, not competition. The path to escape that is: **one marquee integration that creates a flywheel.**

That integration is `voa research → voa eval → RESEARCH-SUMMARY.md → Claude Code context`. The complete loop from "I don't know my users" to "I have typed personas running through my product via a real browser, and the results are in my git repo" — **that's the demo that changes how developers think about product research.**

Ship that loop, document it obsessively, and the library becomes the reference implementation for something that didn't exist before.

---

## The One Thing

If I had to distill this to a single directive:

**The library is currently organized around research methodology. It needs to be reorganized around developer decisions.**

Every API surface, every CLI command, every output artifact should answer a developer's question, not a researcher's question. "What should I build first?" not "What are my behavioral segments?" "Why did my last three users churn?" not "What is the dominant failure mode for the ABANDONER row?"

The methodology is the engine. The developer's decision is the exhaust. Right now the library is showing you the engine and hiding the exhaust. Flip it.
