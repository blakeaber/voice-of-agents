"""Primary public API for voice_of_agents.research — one-liner quick research."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Optional

import yaml
from pydantic import BaseModel

from voice_of_agents.research.client import get_async_client, get_template_env
from voice_of_agents.research.config import ResearchConfig
from voice_of_agents.research.session import ResearchSession

_DEFAULT_MODEL = "claude-opus-4-7"
_QUICK_SUBJECT_COUNT = 10  # minimum valid subject_count for speed; full runs use 12-16


class QuickPersona(BaseModel):
    """Plain-English user archetype for quick research results."""

    uxw_id: str
    archetype: str
    top_concern: str
    would_pay_if: str


class QuickResearchResult(BaseModel):
    """Decision-oriented output from quick_research().

    All fields are plain English — no research methodology vocabulary.
    """

    top_findings: list[str]
    build_this_first: str
    churn_triggers: list[str]
    validate_with: list[str]
    personas: list[QuickPersona]
    session: ResearchSession

    model_config = {"arbitrary_types_allowed": True}


async def _translate_to_config(
    what: str,
    who: str,
    understand: str,
    client,
    model: str,
) -> ResearchConfig:
    """Use Claude to translate plain-English inputs into a valid ResearchConfig."""
    env = get_template_env()
    template = env.get_template("quick/translate_to_question.j2")
    prompt = template.render(what=what, who=who, understand=understand)

    response = await client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    # Extract YAML from code block if present
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    raw = match.group(1) if match else text

    data = yaml.safe_load(raw)
    return ResearchConfig.from_dict(
        {
            "research_question": data.get("research_question", understand),
            "scope": data.get("scope", who),
            "slug": data.get("slug", "quick-research"),
            "product_context": data.get("product_context", what),
        }
    )


async def _synthesize_result(
    session: ResearchSession,
    client,
    model: str,
) -> QuickResearchResult:
    """Synthesize a completed session into a QuickResearchResult."""
    product_out = session.product_research_output
    persona_out = session.persona_research_output

    env = get_template_env()
    template = env.get_template("quick/synthesize_result.j2")
    prompt = template.render(
        research_question=session.product_research_input.question,
        product_context=session.product_research_input.product_context,
        subject_count=len(product_out.subjects) if product_out else 0,
        segments=product_out.segments if product_out else [],
        hypothesis_scores=product_out.hypothesis_scores if product_out else [],
        persona_sidecars=persona_out.persona_sidecars if persona_out else [],
    )

    response = await client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    # Extract JSON
    match = re.search(r"\{.*\}", text, re.DOTALL)
    raw = match.group(0) if match else text
    data = json.loads(raw)

    personas = [QuickPersona(**p) for p in data.get("personas", [])]

    return QuickResearchResult(
        top_findings=data.get("top_findings", []),
        build_this_first=data.get("build_this_first", ""),
        churn_triggers=data.get("churn_triggers", []),
        validate_with=data.get("validate_with", []),
        personas=personas,
        session=session,
    )


async def quick_research(
    what: str,
    who: str,
    understand: str,
    model: str = _DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> QuickResearchResult:
    """Run an abbreviated research pipeline and return decision-oriented findings.

    The primary public API for this library. Accepts plain-English inputs,
    hides the 4-stage pipeline, and returns a QuickResearchResult with
    actionable fields — no research methodology vocabulary required.

    Args:
        what: One sentence describing what you are building.
        who: One sentence describing your target users.
        understand: The #1 thing you want to understand about them.
        model: Anthropic model to use (default: claude-opus-4-7).
        api_key: Optional API key (falls back to ANTHROPIC_API_KEY env var).

    Returns:
        QuickResearchResult with top_findings, build_this_first, churn_triggers,
        validate_with, personas, and the full ResearchSession for power users.

    Example:
        result = await quick_research(
            what="a coding assistant that helps developers write tests",
            who="senior developers at startups",
            understand="why developers abandon AI coding tools after the first week",
        )
        print(result.build_this_first)
    """
    from voice_of_agents.research.pipeline import run_full_pipeline

    client = get_async_client(api_key=api_key)

    config = await _translate_to_config(what, who, understand, client, model)
    config = config.model_copy(
        update={"anthropic_model": model, "subject_count": _QUICK_SUBJECT_COUNT}
    )

    session = await run_full_pipeline(config, journey_redesign_config=None)
    result = await _synthesize_result(session, client, model)
    return result


def quick_research_sync(
    what: str,
    who: str,
    understand: str,
    **kwargs,
) -> QuickResearchResult:
    """Synchronous wrapper for quick_research(). See quick_research() for docs."""
    return asyncio.run(quick_research(what, who, understand, **kwargs))


DEMO_PRESET = {
    "what": "a synthetic research library that lets developers run user research via Claude API calls",
    "who": "solo founders and product engineers at early-stage startups",
    "understand": "why developers adopt AI developer tools enthusiastically at first but abandon them within the first month",
}


async def run_demo(
    model: str = _DEFAULT_MODEL,
    api_key: Optional[str] = None,
    save_dir: Optional[str] = None,
) -> QuickResearchResult:
    """Run the preset demo scenario — no configuration required.

    Uses a preset research question about developer tool adoption.
    Runs with 3 subjects for speed and low cost (~$0.30).
    """
    from voice_of_agents.research.pipeline import run_full_pipeline

    client = get_async_client(api_key=api_key)
    config = ResearchConfig.from_dict(
        {
            "research_question": (
                "Do developers abandon AI developer tools within the first month "
                "because the tool breaks their flow more than it helps?"
            ),
            "scope": "solo founders and product engineers at early-stage startups, 2024-2026",
            "slug": "dev-tool-abandonment-demo",
            "product_context": DEMO_PRESET["what"],
            "subject_count": 12,  # 9 required minimums + 3 free slots for LLM flexibility
            "anthropic_model": model,
        }
    )

    session = await run_full_pipeline(config)
    result = await _synthesize_result(session, client, model)

    if save_dir:
        from pathlib import Path

        out_dir = Path(save_dir)
        session_path = out_dir / f"{config.slug}.yaml"
        session.save(session_path)
        session.export_summary(out_dir / "RESEARCH-SUMMARY.md")

    return result
