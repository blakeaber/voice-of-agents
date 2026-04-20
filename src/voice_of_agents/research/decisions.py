"""Decision-oriented output layer — transforms a ResearchSession into actionable findings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from voice_of_agents.research.models import HypothesisVerdict


class DecisionReport(BaseModel):
    """Actionable output for founders and product engineers.

    Translates the full research session into decisions, not summaries.
    """

    build_this_first: str
    kill_these_assumptions: list[str]
    top_churn_triggers: list[str]
    pricing_signals: list[str]
    segment_map: list[dict]
    validated_hypotheses: list[str]
    refuted_hypotheses: list[str]
    open_questions: list[str]

    def render_markdown(self) -> str:
        segments = "\n".join(
            f"- **{s.get('name', '')}**: {s.get('description', '')}"
            for s in self.segment_map
        )
        validated = "\n".join(f"- {h}" for h in self.validated_hypotheses) or "- none"
        refuted = "\n".join(f"- {h}" for h in self.refuted_hypotheses) or "- none"
        churn = "\n".join(f"- {t}" for t in self.top_churn_triggers) or "- none identified"
        pricing = "\n".join(f"- {p}" for p in self.pricing_signals) or "- insufficient signal"
        kill = "\n".join(f"- {a}" for a in self.kill_these_assumptions) or "- none refuted"
        open_q = "\n".join(f"- {q}" for q in self.open_questions) or "- none"

        return f"""# Decision Report

> This is the output you act on. Every finding is backed by the synthetic research.
> Validate the highest-risk items with 3 real user calls before committing resources.

## Build This First

{self.build_this_first}

## Kill These Assumptions

{kill}

## User Segments (Plain English)

{segments}

## What Would Make Users Leave

{churn}

## Pricing Signals

{pricing}

## Hypotheses: What the Research Supports

{validated}

## Hypotheses: What the Research Refuted

{refuted}

## Open Questions (Requires Real User Validation)

{open_q}
"""


async def generate_decision_report(
    session,
    client,
    model: str,
) -> DecisionReport:
    """Transform a completed ResearchSession into a DecisionReport via a Claude call.

    Requires at least Stage 1 (product_research) to be complete. Stage 2 persona
    data is used when available to enrich segment descriptions and churn triggers.

    Args:
        session: A ResearchSession with product_research_output populated.
        client: An AsyncAnthropic client (from get_async_client()).
        model: Anthropic model ID for the synthesis call.

    Returns:
        DecisionReport with build_this_first, kill_these_assumptions, top_churn_triggers,
        pricing_signals, segment_map, validated_hypotheses, refuted_hypotheses,
        and open_questions fields populated.
    """
    """Transform a completed ResearchSession into a DecisionReport via a Claude call."""
    from voice_of_agents.research.client import get_template_env

    product_out = session.product_research_output
    persona_out = session.persona_research_output

    if not product_out:
        return DecisionReport(
            build_this_first="Insufficient data — complete at least Stage 1 first.",
            kill_these_assumptions=[],
            top_churn_triggers=[],
            pricing_signals=[],
            segment_map=[],
            validated_hypotheses=[],
            refuted_hypotheses=[],
            open_questions=["Run Stage 1 (product research) before generating a decision report."],
        )

    validated = [
        f"{s.hypothesis_id}: {s.verdict}"
        for s in product_out.hypothesis_scores
        if s.verdict == HypothesisVerdict.SUPPORTS
    ]
    refuted = [
        f"{s.hypothesis_id}: {s.verdict}"
        for s in product_out.hypothesis_scores
        if s.verdict in (HypothesisVerdict.REFUTES, HypothesisVerdict.ORTHOGONAL)
    ]
    segments_data = [
        {
            "name": seg.name,
            "description": seg.description,
            "failure_mode": seg.dominant_failure_mode,
            "gaps": seg.gaps_vs_product_positioning,
            "jtbd": seg.primary_jtbd,
        }
        for seg in product_out.segments
    ]

    personas_data = []
    if persona_out:
        for sc in persona_out.persona_sidecars:
            personas_data.append(
                {
                    "id": sc.uxw_id,
                    "name": sc.name,
                    "constraint": sc.constraint_profile,
                    "failure": sc.failure_or_abandonment_mode,
                    "anti_model": sc.anti_model_of_success,
                }
            )

    synthesis_prompt = f"""You are synthesizing a synthetic research session into a decision report for a founder.

Research question: {session.product_research_input.question}
Product context: {session.product_research_input.product_context}

Segments: {json.dumps(segments_data, indent=2)}
Personas: {json.dumps(personas_data, indent=2)}
Validated hypotheses: {validated}
Refuted hypotheses: {refuted}

Return a JSON object with exactly these fields:
{{
  "build_this_first": "<single highest-signal feature/capability, one actionable sentence>",
  "kill_these_assumptions": ["<assumptions the research refutes — things the founder probably believed but is wrong>"],
  "top_churn_triggers": ["<one trigger per segment — what would make them leave>"],
  "pricing_signals": ["<what the research says about willingness to pay and at what threshold>"],
  "segment_map": [
    {{"name": "<plain-English segment name>", "description": "<what makes this type of user distinct, one sentence>"}}
  ],
  "validated_hypotheses": ["<hypotheses the research supports, in plain English — not just IDs>"],
  "refuted_hypotheses": ["<hypotheses the research refutes, in plain English>"],
  "open_questions": ["<3-5 things synthetic research can't answer — require real user validation>"]
}}

Be specific. Use evidence from the segments and personas. Avoid generic research language.
Return ONLY the JSON object."""

    response = await client.messages.create(
        model=model,
        max_tokens=2500,
        messages=[{"role": "user", "content": synthesis_prompt}],
    )
    text = response.content[0].text.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    raw = match.group(0) if match else text
    data = json.loads(raw)

    return DecisionReport(
        build_this_first=data.get("build_this_first", ""),
        kill_these_assumptions=data.get("kill_these_assumptions", []),
        top_churn_triggers=data.get("top_churn_triggers", []),
        pricing_signals=data.get("pricing_signals", []),
        segment_map=data.get("segment_map", []),
        validated_hypotheses=data.get("validated_hypotheses", []),
        refuted_hypotheses=data.get("refuted_hypotheses", []),
        open_questions=data.get("open_questions", []),
    )


def write_decision_report(report: DecisionReport, directory: Path) -> Path:
    """Write DECISION-REPORT.md to the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "DECISION-REPORT.md"
    path.write_text(report.render_markdown())
    return path
