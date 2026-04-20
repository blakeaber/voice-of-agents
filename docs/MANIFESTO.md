# Why Most Startup Research Is Useless (And What to Do Instead)

Most founders interview the wrong people, ask the wrong questions, and draw the wrong conclusions. Not because they're bad at research — because the incentive structure of early-stage startups guarantees it.

Here's the problem.

---

## You Interview Happy Users

When you decide it's time to do user research, you go to your most engaged users. They're the easiest to reach. They love your product. They'll talk to you for an hour.

And everything they tell you is correct — for them.

But they're not the people who will determine whether your startup succeeds. The people who matter most are the ones who tried your product and left, the ones who evaluated it and said no, and the ones who've heard of you but never gotten past the homepage.

Those people won't respond to your cold outreach. And when they do, they won't be honest — because they don't want to hurt your feelings, and because they've already moved on.

So you end up with research that confirms what you already believed, optimizes for the users you already have, and completely misses the churn patterns that will kill you.

## Real Research Is Too Slow

The alternative — proper qualitative research with 20+ interviews, rigorous coding, and a professional analyst — takes 6-8 weeks and costs $15,000-$50,000.

For a pre-PMF startup with 4 months of runway, that's not research. That's a pivot you didn't take.

So most founders skip the research entirely and build based on intuition, a few anecdotes, and whatever the loudest user said at the last conference.

## The Synthetic Shortcut (And Why It Matters)

This library takes a different position.

Synthetic research — using a language model to simulate a sampling frame of users, including adopters, abandoners, skeptics, and refusers — is not a replacement for real research. It is a *forcing function* for better questions.

Here's what it does:

**It forces you to be specific about your hypotheses before you build.** You can't run a synthetic research session without declaring a falsifiable question. Not "who are my users?" but "Do abandoners quit because the first-week experience fails to produce a concrete outcome, or because they never trusted the output enough to act on it?"

**It includes the users you'd never think to recruit.** The sampling frame this library uses has a mandatory minimum of people who abandoned your product, people who evaluated it and rejected it, and people who actively advocate against it. These are the people who know exactly what's broken about your product. Real research skips them because they're hard to find. Synthetic research treats them as required.

**It produces testable hypotheses, not summaries.** The output of a research session is a set of hypothesis verdicts — supported, refuted, orthogonal, or insufficient evidence. If you get a result, you know what to do next: validate the refuted hypotheses with real users before committing resources to the wrong direction.

**It costs less than a customer dinner.** The full 4-stage pipeline — 12 synthetic subjects, 3 personas, workflow maps, and journey redesign — costs less than $2.00 with the flagship model. With Haiku it's under $0.10.

## What Synthetic Research Is NOT

Let's be honest about the limits.

Language models simulate what users *might* say based on patterns in training data. They don't know your specific market. They don't have access to your NPS scores, your support tickets, or your activation data. They will hallucinate confidence where there is none.

The output of this library is not evidence. It is a map of the hypothesis space — a structured way to ask "what would have to be true for this to work, and what would have to be false?"

Every finding should be treated as a hypothesis to validate, not a conclusion to act on. The `SYNTHETIC-DATA-NOTICE.md` that appears in every session directory is not a legal disclaimer. It's a workflow guide: here's what to do next, here are the questions to ask a real user, here's what the synthetic research can't tell you.

## The Sampling Frame Is the Insight Engine

The most powerful idea in this library is not the LLM calls. It's the sampling frame.

Traditional user research recruits users who opted in to your product. This library mandates that every research session includes a 2D matrix of users across two dimensions:

1. **Adoption status** — adopter, partial adopter, abandoner, evaluated and rejected, never tried, actively anti
2. **Context segment** — the firm size and buyer type that shapes how they relate to the category

The mandatory minimum: at least 2 subjects from the abandoner, evaluated-and-rejected, and actively-anti rows.

This is the insight engine because the people who left, rejected, and oppose your product know things about your product's failure modes that your best customers will never tell you.

## Ship Fast Hypotheses Before You Ship Slow Features

The workflow this library enables:

1. Declare a falsifiable hypothesis before you build the feature ("we believe abandoners quit in week 1 because they never got a concrete outcome from the first session")
2. Run a synthetic session to stress-test the hypothesis against a sampling frame that includes abandoners
3. Get a verdict: supported, refuted, orthogonal, or insufficient evidence
4. If refuted: revise the hypothesis and run again, or recruit 3 real users to validate
5. If supported: build with confidence that you're solving a real problem, not a perceived one

The average time from question to hypothesis verdict: 15-30 minutes.

The average time from "we should do some user research" to actually interviewing users: 3-6 weeks.

The difference between those two timelines is the difference between a team that builds based on evidence and a team that builds based on intuition dressed up as user-centricity.

## The Research → Eval Bridge

One workflow that isn't obvious until you see it: synthetic research personas can directly seed your evaluation pipeline.

If you're building an AI product and using LLM-as-judge evaluation, your eval personas should represent the actual users you're building for — not generic "expert user" and "novice user" abstractions.

This library includes a bridge (`voice_of_agents.research.bridge`) that converts the UXWPersonaSidecar objects produced by the personas stage into canonical Persona objects for eval seeding. The personas include constraint profiles, failure modes, anti-models of success, and behavioral archetypes — exactly the signal you need to write eval rubrics that catch the things your real users will complain about.

The full loop: research → personas → eval seeding → eval run → catch failure modes before they reach users.

## Fork It, Argue With It

This library is an implementation of a worldview, not a neutral tool. The worldview is:

- Research that only talks to happy users is not research — it's validation theater
- Synthetic research is only valuable when it's epistemically honest about its limits
- The best use of $2 and 30 minutes is not building another CRUD endpoint — it's checking whether your core assumption is false before you spend 3 months on it
- Developers who can't afford a research team deserve the same rigor as those who can

If you disagree with any of this, fork it and implement your own sampling frame. If you find a way to make it more honest or more useful, open a PR. If you use it and it helps you avoid building the wrong thing, tell someone.

The alternative is building based on vibes and hoping you guessed right.

---

*This library is part of [Voice of Agents](https://github.com/blakeaber/voice-of-agents) — a toolkit for building AI products that are grounded in user behavior, not user opinions.*
