"""Stage 2: Personas from Research — synthesize evidence-backed persona cards."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

import yaml
from anthropic import AsyncAnthropic

from voice_of_agents.research.client import get_async_client, get_template_env
from voice_of_agents.research.models import (
    AdoptionStatus,
    BehavioralSegment,
    ContextSegment,
    PersonaResearchInput,
    PersonaResearchOutput,
    SubjectRecord,
    UXWPersonaSidecar,
    UXWTaskCard,
    VerbatimQuote,
)
from voice_of_agents.research.validation import guard_stage2_input

_DEFAULT_MODEL = "claude-opus-4-7"

_MINIMUM_SUBJECTS_PER_SEGMENT = 3


def _count_subjects_per_segment(
    subjects: list[SubjectRecord],
    segments: list[BehavioralSegment],
) -> dict[str, int]:
    """Map segment name → count of contributing subjects."""
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.name] = len(segment.subject_ids)
    return counts


def _segments_needing_topup(
    coverage_map: dict[str, int],
) -> list[str]:
    """Return segment names with fewer than MINIMUM_SUBJECTS_PER_SEGMENT subjects."""
    return [name for name, count in coverage_map.items() if count < _MINIMUM_SUBJECTS_PER_SEGMENT]


async def _run_topup_interviews(
    segments_needing_topup: list[str],
    all_subjects: list[SubjectRecord],
    input: PersonaResearchInput,
    client: AsyncAnthropic,
    model: str,
) -> list[SubjectRecord]:
    """Spawn parallel top-up researcher calls (6-12) for under-covered segments."""
    env = get_template_env()
    template = env.get_template("personas_from_research/topup_researcher.j2")
    product_output = input.product_research

    topup_cells: list[tuple[str, str, AdoptionStatus, ContextSegment]] = []
    for segment_name in segments_needing_topup:
        segment = next((s for s in product_output.segments if s.name == segment_name), None)
        if not segment:
            continue
        target_count = input.topup_subject_count_target - len(segment.subject_ids)
        for i in range(max(0, target_count)):
            topup_cells.append(
                (
                    segment_name,
                    segment.description,
                    AdoptionStatus.PARTIAL_ADOPTER,
                    ContextSegment.B2B_SMALL,
                )
            )

    existing_count = len(all_subjects)

    async def call_one(
        cell: tuple[str, str, AdoptionStatus, ContextSegment],
        idx: int,
    ) -> SubjectRecord:
        segment_name, segment_desc, status, context = cell
        subject_id = f"subject-{existing_count + idx + 1:02d}"
        prompt = template.render(
            subject_id=subject_id,
            segment_name=segment_name,
            current_count=len(all_subjects),
            adoption_status=status.value,
            context_segment=context.value,
            subject_profile=f"Top-up subject for {segment_name}",
            question=product_output.hypotheses[0].statement if product_output.hypotheses else "",
            hypotheses=product_output.hypotheses,
        )
        response = await client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_topup_subject(response.content[0].text, subject_id, status, context)

    tasks = [call_one(cell, i) for i, cell in enumerate(topup_cells)]
    return list(await asyncio.gather(*tasks))


def _parse_topup_subject(
    raw: str,
    subject_id: str,
    status: AdoptionStatus,
    context: ContextSegment,
) -> SubjectRecord:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    quotes_raw = data.get("verbatim_quote_bank", [])
    quotes = [
        VerbatimQuote(key=q["key"], text=q["text"]) for q in quotes_raw if isinstance(q, dict)
    ]
    while len(quotes) < 5:
        quotes.append(VerbatimQuote(key=f"Q{len(quotes) + 1}", text="[placeholder]"))

    return SubjectRecord(
        subject_id=subject_id,
        adoption_status=status,
        context_segment=context,
        jtbd=data.get("jtbd", ""),
        adoption_trajectory=data.get("adoption_trajectory", ""),
        last_concrete_episode=data.get("last_concrete_episode", ""),
        constraint_profile=data.get("constraint_profile", ""),
        failure_or_abandonment_mode=data.get("failure_or_abandonment_mode", ""),
        decision_topology=data.get("decision_topology", ""),
        anti_model_of_success=data.get("anti_model_of_success", ""),
        verbatim_quote_bank=quotes[:8],
    )


async def _synthesize_persona_sidecar(
    segment: BehavioralSegment,
    all_subjects: list[SubjectRecord],
    uxw_number: int,
    client: AsyncAnthropic,
    model: str,
) -> UXWPersonaSidecar:
    env = get_template_env()
    template = env.get_template("personas_from_research/persona_synthesis.j2")

    contributing_subjects = [s for s in all_subjects if s.subject_id in segment.subject_ids]
    if len(contributing_subjects) < 2:
        contributing_subjects = all_subjects[:2]

    prompt = template.render(
        segment_name=segment.name,
        segment_description=segment.description,
        subject_ids=segment.subject_ids,
        subjects=contributing_subjects,
        uxw_number=f"{uxw_number:02d}",
    )
    response = await client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_sidecar(response.content[0].text, segment, uxw_number)


def _parse_sidecar(raw: str, segment: BehavioralSegment, uxw_number: int) -> UXWPersonaSidecar:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    quotes_raw = data.get("verbatim_quote_bank", [])
    quotes = [
        VerbatimQuote(key=q["key"], text=q["text"]) for q in quotes_raw if isinstance(q, dict)
    ]
    while len(quotes) < 5:
        quotes.append(VerbatimQuote(key=f"Q{len(quotes) + 1}", text="[placeholder]"))

    subject_ids = data.get("subject_ids", segment.subject_ids[:2])
    if len(subject_ids) < 2:
        subject_ids = segment.subject_ids[:2] or ["subject-01", "subject-02"]

    return UXWPersonaSidecar(
        uxw_id=data.get("uxw_id", f"UXW-{uxw_number:02d}"),
        name=data.get("name", f"Persona{uxw_number:02d}"),
        segment_source=segment.name,
        subject_ids=subject_ids,
        jtbd=data.get("jtbd", segment.primary_jtbd),
        adoption_trajectory=data.get("adoption_trajectory", segment.adoption_trajectory_shape),
        last_concrete_episode=data.get("last_concrete_episode", ""),
        constraint_profile=data.get("constraint_profile", segment.dominant_constraint_profile),
        failure_or_abandonment_mode=data.get(
            "failure_or_abandonment_mode", segment.dominant_failure_mode
        ),
        decision_topology=data.get("decision_topology", ""),
        anti_model_of_success=data.get(
            "anti_model_of_success", segment.gaps_vs_product_positioning
        ),
        verbatim_quote_bank=quotes[:8],
    )


def _derive_task_card(sidecar: UXWPersonaSidecar) -> UXWTaskCard:
    """Derive a UXW task card from the persona sidecar."""
    return UXWTaskCard(
        uxw_id=sidecar.uxw_id,
        name=sidecar.name,
        role=sidecar.segment_source,
        intent=sidecar.jtbd[:100],
        trigger=sidecar.last_concrete_episode[:100] if sidecar.last_concrete_episode else "",
        success_definition=f"Accomplishes JTBD without the constraint: {sidecar.constraint_profile[:80]}",
        today_workaround=sidecar.failure_or_abandonment_mode[:120]
        if sidecar.failure_or_abandonment_mode
        else "No workaround documented",
        preconditions=[sidecar.constraint_profile[:80]] if sidecar.constraint_profile else [],
        steps=[
            "Navigate to relevant feature",
            "Complete primary task",
            "Verify outcome meets success definition",
        ],
        success_criteria=[
            f"Task completed without triggering failure mode: {sidecar.failure_or_abandonment_mode[:60]}"
        ],
        persona_evaluation_rubric=f"Rate on: speed to value, trust, absence of '{sidecar.anti_model_of_success[:60]}'",
    )


def _extract_yaml_block(text: str) -> str:
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ── Public API ─────────────────────────────────────────────────────────


async def run_personas_from_research(
    input: PersonaResearchInput,
    client: Optional[AsyncAnthropic] = None,
    model: str = _DEFAULT_MODEL,
    output_dir: Path = Path("docs/research"),
    allow_all_supported: bool = False,
) -> PersonaResearchOutput:
    """Execute the personas-from-research pipeline.

    Stages:
    1. Validate upstream product research output (requires verdicts + segments)
    2. Check coverage per segment (flag for top-up if <3 subjects per segment)
    3. Spawn parallel top-up researchers if needed (asyncio.gather)
    4. Synthesize persona sidecars (one per behavioral segment, parallel)
    5. Derive UXW task cards from sidecars
    """
    if client is None:
        client = get_async_client()

    guard_stage2_input(input.product_research, allow_all_supported=allow_all_supported)

    product_output = input.product_research
    all_subjects = list(product_output.subjects)
    coverage_map = _count_subjects_per_segment(all_subjects, product_output.segments)

    topup_subjects: list[SubjectRecord] = []
    if not input.skip_topup:
        segments_needing = _segments_needing_topup(coverage_map)
        if segments_needing:
            topup_subjects = await _run_topup_interviews(
                segments_needing, all_subjects, input, client, model
            )
            all_subjects.extend(topup_subjects)
            # Rebuild coverage map
            for segment in product_output.segments:
                new_topup_ids = [s.subject_id for s in topup_subjects]
                coverage_map[segment.name] = len(
                    [
                        sid
                        for sid in segment.subject_ids
                        if sid in [s.subject_id for s in all_subjects]
                    ]
                ) + len(new_topup_ids) // max(len(product_output.segments), 1)

    # Synthesize sidecars in parallel (one per behavioral segment)
    sidecar_tasks = [
        _synthesize_persona_sidecar(segment, all_subjects, i + 1, client, model)
        for i, segment in enumerate(product_output.segments)
    ]
    sidecars = list(await asyncio.gather(*sidecar_tasks))

    # Derive task cards from sidecars
    task_cards = [_derive_task_card(sidecar) for sidecar in sidecars]

    return PersonaResearchOutput(
        topup_subjects=topup_subjects,
        persona_sidecars=sidecars,
        task_cards=task_cards,
        archived_prior_personas=[],
        coverage_map=coverage_map,
    )


def run_personas_from_research_sync(
    input: PersonaResearchInput,
    **kwargs,
) -> PersonaResearchOutput:
    """Synchronous wrapper for use in non-async contexts."""
    return asyncio.run(run_personas_from_research(input, **kwargs))
