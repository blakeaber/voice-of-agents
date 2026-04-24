"""Stage 4: Journey Redesign — focus group evaluation and must-fix synthesis."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

import yaml
from anthropic import AsyncAnthropic

from voice_of_agents.research.client import get_async_client, get_template_env
from voice_of_agents.research.models import (
    FocusGroupResponse,
    JourneyDesignStep,
    JourneyRedesignInput,
    JourneyRedesignOutput,
    MustFix,
    UXWPersonaSidecar,
)
from voice_of_agents.research.validation import guard_stage4_input

_DEFAULT_MODEL = "claude-opus-4-7"
_CROSS_CUTTING_THRESHOLD = 3  # must-fix raised by this many personas = cross-cutting


async def _draft_v0_journey(
    input: JourneyRedesignInput,
    client: AsyncAnthropic,
    model: str,
) -> list[JourneyDesignStep]:
    """Generate the initial v0 journey design from the anchor segment and scope."""
    personas_summary = "\n".join(
        f"- {s.uxw_id}: {s.jtbd[:80]}"
        for s in input.persona_research.persona_sidecars
        if s.uxw_id in input.focus_panel_uxw_ids
    )
    workflow_summary = "\n".join(
        f"- {wf.title}: {wf.intent_goal[:80]}" for wf in input.workflow_research.workflow_maps
    )

    prompt = (
        f"You are designing a product journey for the anchor segment: {input.anchor_segment}.\n\n"
        f"Journeys in scope: {', '.join(input.journeys_in_scope)}\n"
        f"Build form: {input.build_form}\n\n"
        f"Focus panel personas:\n{personas_summary}\n\n"
        f"Known workflow pain points:\n{workflow_summary}\n\n"
        "Draft a v0 journey design (8-15 steps). For each step specify:\n"
        "- screen_or_route: URL or screen name\n"
        "- affordance: what the user can do here\n"
        "- copy_sample: a sample of UI copy\n"
        "- principle_reference: which design principle this step embodies\n\n"
        "Respond ONLY with YAML:\n\n"
        "```yaml\n"
        "journey_steps:\n"
        "  - step_number: 1\n"
        '    screen_or_route: "[route]"\n'
        '    affordance: "[what they can do]"\n'
        '    copy_sample: "[UI copy]"\n'
        '    principle_reference: "[principle]"\n'
        "    must_fix_numbers: []\n"
        "```\n"
    )
    response = await client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_journey_steps(response.content[0].text)


def _parse_journey_steps(raw: str) -> list[JourneyDesignStep]:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return []

    steps = []
    for item in data.get("journey_steps", []):
        if not isinstance(item, dict):
            continue
        steps.append(
            JourneyDesignStep(
                step_number=item.get("step_number", len(steps) + 1),
                screen_or_route=item.get("screen_or_route", ""),
                affordance=item.get("affordance", ""),
                copy_sample=item.get("copy_sample", ""),
                principle_reference=item.get("principle_reference", ""),
                must_fix_numbers=item.get("must_fix_numbers", []),
            )
        )
    return steps


async def _run_focus_group(
    input: JourneyRedesignInput,
    v0_steps: list[JourneyDesignStep],
    client: AsyncAnthropic,
    model: str,
) -> list[FocusGroupResponse]:
    """Spawn parallel focus group calls (3-6, one per persona)."""
    env = get_template_env()
    template = env.get_template("journey_redesign/focus_group_participant.j2")

    panel_sidecars = [
        s for s in input.persona_research.persona_sidecars if s.uxw_id in input.focus_panel_uxw_ids
    ]

    async def call_one(sidecar: UXWPersonaSidecar) -> FocusGroupResponse:
        prompt = template.render(
            persona_name=sidecar.name,
            uxw_id=sidecar.uxw_id,
            jtbd=sidecar.jtbd,
            constraint_profile=sidecar.constraint_profile,
            failure_or_abandonment_mode=sidecar.failure_or_abandonment_mode,
            anti_model_of_success=sidecar.anti_model_of_success,
            verbatim_quote_bank=sidecar.verbatim_quote_bank,
            journey_title=", ".join(input.journeys_in_scope),
            anchor_segment=input.anchor_segment,
            journey_steps=v0_steps,
            score=5,
            would_pay="conditional",
        )
        response = await client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_focus_group_response(response.content[0].text, sidecar)

    tasks = [call_one(sidecar) for sidecar in panel_sidecars]
    return list(await asyncio.gather(*tasks))


def _parse_focus_group_response(raw: str, sidecar: UXWPersonaSidecar) -> FocusGroupResponse:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    loved = data.get("what_i_loved", ["[not captured]", "[not captured]"])
    if len(loved) < 2:
        loved = loved + ["[not captured]"] * (2 - len(loved))

    quit_items = data.get("what_made_me_quit", ["[not captured]", "[not captured]"])
    if len(quit_items) < 2:
        quit_items = quit_items + ["[not captured]"] * (2 - len(quit_items))

    must_fixes = data.get(
        "top_3_must_fixes", ["[not captured]", "[not captured]", "[not captured]"]
    )
    while len(must_fixes) < 3:
        must_fixes.append("[not captured]")

    try:
        score = int(data.get("score", 5))
        score = max(1, min(10, score))
    except (TypeError, ValueError):
        score = 5

    would_pay_raw = str(data.get("would_pay", "conditional")).lower()
    if would_pay_raw not in ("yes", "no", "conditional"):
        would_pay_raw = "conditional"

    return FocusGroupResponse(
        persona_name=sidecar.name,
        uxw_id=sidecar.uxw_id,
        score=score,
        what_i_loved=loved[:4],
        what_made_me_quit=quit_items[:4],
        top_3_must_fixes=must_fixes[:3],
        segment_specific_concern=data.get("segment_specific_concern", ""),
        would_pay=would_pay_raw,
        would_pay_reason=data.get("would_pay_reason", ""),
    )


async def _synthesize_must_fixes_and_revise(
    input: JourneyRedesignInput,
    v0_steps: list[JourneyDesignStep],
    focus_group_responses: list[FocusGroupResponse],
    client: AsyncAnthropic,
    model: str,
) -> tuple[list[MustFix], list[MustFix], list[JourneyDesignStep]]:
    env = get_template_env()
    template = env.get_template("journey_redesign/journey_synthesis.j2")

    scores = [r.score for r in focus_group_responses]
    prompt = template.render(
        journey_title=", ".join(input.journeys_in_scope),
        anchor_segment=input.anchor_segment,
        v0_steps=v0_steps,
        focus_group_responses=focus_group_responses,
        scores=scores,
    )
    response = await client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_synthesis(response.content[0].text, v0_steps)


def _parse_synthesis(
    raw: str, v0_steps: list[JourneyDesignStep]
) -> tuple[list[MustFix], list[MustFix], list[JourneyDesignStep]]:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    must_fixes = [
        MustFix(
            number=item.get("number", i + 1),
            description=item.get("description", ""),
            raised_by_persona_ids=item.get("raised_by_persona_ids", []),
            is_cross_cutting=item.get("is_cross_cutting", False),
        )
        for i, item in enumerate(data.get("must_fixes", []))
        if isinstance(item, dict)
    ]

    secondary_asks = [
        MustFix(
            number=item.get("number", i + 100),
            description=item.get("description", ""),
            raised_by_persona_ids=item.get("raised_by_persona_ids", []),
            is_cross_cutting=False,
        )
        for i, item in enumerate(data.get("secondary_asks", []))
        if isinstance(item, dict)
    ]

    revised = _parse_journey_steps(raw)
    if not revised:
        revised = v0_steps

    return must_fixes, secondary_asks, revised


def _extract_yaml_block(text: str) -> str:
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ── Public API ─────────────────────────────────────────────────────────


async def run_journey_redesign(
    input: JourneyRedesignInput,
    client: Optional[AsyncAnthropic] = None,
    model: str = _DEFAULT_MODEL,
    output_dir: Path = Path("docs/research"),
) -> JourneyRedesignOutput:
    """Execute the journey redesign pipeline.

    Stages:
    1. Draft v0 journey design from anchor segment + workflow evidence
    2. Spawn parallel focus group (3-6 personas via asyncio.gather)
    3. Synthesize must-fixes (cross-cutting = raised by ≥3 personas)
    4. Revise journey to address all cross-cutting must-fixes
    5. Emit plan structure
    """
    if client is None:
        client = get_async_client()

    guard_stage4_input(input.persona_research, input.focus_panel_uxw_ids)

    v0_steps = await _draft_v0_journey(input, client, model)

    focus_group_responses = await _run_focus_group(input, v0_steps, client, model)

    must_fixes, secondary_asks, revised_steps = await _synthesize_must_fixes_and_revise(
        input, v0_steps, focus_group_responses, client, model
    )

    scores = [r.score for r in focus_group_responses]
    average_score = sum(scores) / len(scores) if scores else 0.0

    cross_cutting = [mf for mf in must_fixes if mf.is_cross_cutting]

    plan_slug = f"{input.anchor_segment.lower().replace('→', '-to-').replace(' ', '-')}-journey"
    plan_dir = f"docs/plans/{plan_slug}/"

    return JourneyRedesignOutput(
        v0_journey_steps=v0_steps,
        focus_group_responses=focus_group_responses,
        average_score=average_score,
        cross_cutting_must_fixes=cross_cutting,
        secondary_asks=secondary_asks,
        revised_journey_steps=revised_steps,
        plan_dir=plan_dir,
        plan_slug=plan_slug,
    )


def run_journey_redesign_sync(
    input: JourneyRedesignInput,
    **kwargs,
) -> JourneyRedesignOutput:
    """Synchronous wrapper for use in non-async contexts."""
    return asyncio.run(run_journey_redesign(input, **kwargs))
