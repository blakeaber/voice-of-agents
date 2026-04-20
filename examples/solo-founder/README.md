# Solo Founder Example

**Who this is for:** Pre-PMF solo founders who need to test a hypothesis before building.

**What you'll do:** Run a full research session about developer tool abandonment and get a decision report that tells you what to build first and what to validate with real users.

**Cost:** ~$0.08 with Haiku | **Time:** 5-10 minutes

## Setup

```bash
export ANTHROPIC_API_KEY=sk-...
cd examples/solo-founder
```

## Run

```bash
chmod +x run.sh
./run.sh
```

## What you'll see

1. Config validation — checks your research question is falsifiable
2. Cost estimate — shows what this run will cost before spending anything
3. Progress output — live updates as synthetic interviews run in parallel
4. Session summary — stages completed, subjects interviewed, segments identified

## What you get

After the run completes, check `research-sessions/ai-tool-abandonment.yaml` and the directory it created:

- `DECISION-REPORT.md` — **This is what you act on.** Build this first. Kill these assumptions. What would make users leave.
- `SYNTHETIC-DATA-NOTICE.md` — 3 questions to ask real users to validate the highest-risk findings.
- `RESEARCH-SUMMARY.md` — Full structured summary for sharing with co-founders or Claude Code.

## Customize

Edit `research-config.yaml` to change the research question to match your product.

Or skip the config entirely and use the plain-English quickstart:

```bash
voa research quickstart
```

## Next steps after the run

1. Read `DECISION-REPORT.md`
2. Find the 3 questions in `SYNTHETIC-DATA-NOTICE.md`
3. Schedule 3 user calls this week (Calendly link to your signup list)
4. Ask those 3 questions verbatim
5. Compare answers to the synthetic findings

If 2 out of 3 real users contradict a finding, the finding is wrong. Adjust and re-run.

## See also

- [Product engineer example](../product-engineer/) — `quick_research()` one-liner, no config files
- [DX practitioner example](../dx-practitioner/) — Full research → eval bridge workflow
- [MANIFESTO.md](../../docs/MANIFESTO.md) — Why this approach exists
