"""Stage 1: Product Research — question decomposition through behavioral segmentation."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import yaml
from anthropic import AsyncAnthropic

from voice_of_agents.research.client import get_async_client, get_template_env
from voice_of_agents.research.models import (
    AdoptionStatus,
    BehavioralSegment,
    ContextSegment,
    Hypothesis,
    HypothesisScore,
    HypothesisVerdict,
    ProductResearchInput,
    ProductResearchOutput,
    SamplingCell,
    SubjectRecord,
    VerbatimQuote,
)
from voice_of_agents.research.validation import (
    check_all_hypotheses_supported,
    validate_hypothesis_set,
    validate_sampling_frame_row_counts,
)

_DEFAULT_MODEL = "claude-opus-4-7"

_SAMPLING_FRAME_TEMPLATE: list[tuple[AdoptionStatus, ContextSegment, str]] = [
    (AdoptionStatus.ADOPTER, ContextSegment.B2B_MID, "Mid-market B2B power user"),
    (AdoptionStatus.ADOPTER, ContextSegment.B2C_HIGH_AUTONOMY, "Solo practitioner"),
    (AdoptionStatus.PARTIAL_ADOPTER, ContextSegment.B2B_SMALL, "Small team inconsistent user"),
    (AdoptionStatus.PARTIAL_ADOPTER, ContextSegment.B2C_LOW_AUTONOMY, "Individual needing buy-in"),
    (AdoptionStatus.ABANDONER, ContextSegment.B2B_MID, "Mid-market team that churned"),
    (AdoptionStatus.ABANDONER, ContextSegment.B2C_HIGH_AUTONOMY, "Solo practitioner who left"),
    (
        AdoptionStatus.EVALUATED_AND_REJECTED,
        ContextSegment.B2B_LARGE_REGULATED,
        "Regulated enterprise that passed",
    ),
    (
        AdoptionStatus.EVALUATED_AND_REJECTED,
        ContextSegment.B2B_SMALL,
        "Small team that chose a competitor",
    ),
    (AdoptionStatus.NEVER_TRIED_AWARE, ContextSegment.B2B_MID, "Aware but never started"),
    (AdoptionStatus.ACTIVELY_ANTI, ContextSegment.B2B_MID, "Active critic"),
    (
        AdoptionStatus.ACTIVELY_ANTI,
        ContextSegment.B2C_HIGH_AUTONOMY,
        "Solo practitioner who advises against",
    ),
    (
        AdoptionStatus.PARTIAL_ADOPTER,
        ContextSegment.B2B_LARGE_REGULATED,
        "Regulated enterprise partial user",
    ),
]


def _build_default_sampling_frame(subject_count: int) -> list[SamplingCell]:
    """Build the canonical 2D sampling frame, limited to subject_count cells."""
    cells = []
    for status, segment, profile in _SAMPLING_FRAME_TEMPLATE[:subject_count]:
        cells.append(
            SamplingCell(
                adoption_status=status,
                context_segment=segment,
                subject_profile=profile,
            )
        )
    return cells


async def _stage1_decompose_question(
    input: ProductResearchInput,
    client: AsyncAnthropic,
    model: str,
) -> list[Hypothesis]:
    """Generate 4-7 falsifiable hypotheses from the research question."""
    prompt = (
        f"You are a research strategist decomposing a research question into falsifiable hypotheses.\n\n"
        f"Research question: {input.question}\n"
        f"Population scope: {input.scope}\n"
        f"Product context: {input.product_context}\n\n"
        "Generate 4-7 falsifiable hypotheses. Each must:\n"
        "- Make a specific causal or behavioral claim\n"
        "- State explicit evidence that would REFUTE it\n"
        "- NOT be demographic-only ('enterprise users prefer X')\n\n"
        "Respond ONLY with YAML:\n\n"
        "```yaml\n"
        "hypotheses:\n"
        "  - id: H1\n"
        '    statement: "[the hypothesis]"\n'
        '    falsification_condition: "[what evidence would force a refutes verdict]"\n'
        "```\n"
    )
    response = await client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_hypotheses(response.content[0].text)


def _parse_hypotheses(raw: str) -> list[Hypothesis]:
    block = _extract_yaml_block(raw)
    data = yaml.safe_load(block)
    return [Hypothesis(**h) for h in data.get("hypotheses", [])]


async def _stage3_parallel_interviews(
    frame: list[SamplingCell],
    input: ProductResearchInput,
    hypotheses: list[Hypothesis],
    client: AsyncAnthropic,
    model: str,
) -> list[SubjectRecord]:
    """Dispatch all researcher prompts simultaneously using asyncio.gather.

    This is the core parallel-subagent pattern from the SKILL.md files,
    translated to Python. Each coroutine is one independent "researcher".
    """
    env = get_template_env()
    template = env.get_template("product_research/researcher_brief.j2")

    async def call_one(cell: SamplingCell, subject_id: str) -> SubjectRecord:
        prompt = template.render(
            subject_id=subject_id,
            adoption_status=cell.adoption_status.value,
            context_segment=cell.context_segment.value,
            subject_profile=cell.subject_profile,
            question=input.question,
            scope=input.scope,
            product_context=input.product_context,
            hypotheses=hypotheses,
        )
        response = await client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_subject_record(response.content[0].text, subject_id, cell)

    tasks = [call_one(cell, f"subject-{i + 1:02d}") for i, cell in enumerate(frame)]
    return list(await asyncio.gather(*tasks))


def _parse_subject_record(raw: str, subject_id: str, cell: SamplingCell) -> SubjectRecord:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    quotes_raw = data.get("verbatim_quote_bank", [])
    quotes = [
        VerbatimQuote(key=q["key"], text=q["text"]) for q in quotes_raw if isinstance(q, dict)
    ]
    if len(quotes) < 5:
        for i in range(5 - len(quotes)):
            quotes.append(VerbatimQuote(key=f"Q{len(quotes) + 1}", text="[placeholder]"))

    return SubjectRecord(
        subject_id=subject_id,
        adoption_status=cell.adoption_status,
        context_segment=cell.context_segment,
        jtbd=data.get("jtbd", ""),
        adoption_trajectory=data.get("adoption_trajectory", ""),
        last_concrete_episode=data.get("last_concrete_episode", ""),
        constraint_profile=data.get("constraint_profile", ""),
        failure_or_abandonment_mode=data.get("failure_or_abandonment_mode", ""),
        decision_topology=data.get("decision_topology", ""),
        anti_model_of_success=data.get("anti_model_of_success", ""),
        verbatim_quote_bank=quotes[:8],
    )


async def _stage4_score_hypotheses(
    hypotheses: list[Hypothesis],
    subjects: list[SubjectRecord],
    client: AsyncAnthropic,
    model: str,
) -> list[HypothesisScore]:
    env = get_template_env()
    template = env.get_template("product_research/hypothesis_scoring.j2")
    prompt = template.render(
        question="(research question)",
        hypotheses=hypotheses,
        subjects=subjects,
    )
    response = await client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_hypothesis_scores(response.content[0].text)


def _parse_hypothesis_scores(raw: str) -> list[HypothesisScore]:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return []

    scores = []
    for item in data.get("scores", []):
        try:
            verdict = HypothesisVerdict(item.get("verdict", "insufficient-evidence"))
        except ValueError:
            verdict = HypothesisVerdict.INSUFFICIENT_EVIDENCE
        scores.append(
            HypothesisScore(
                hypothesis_id=item.get("hypothesis_id", ""),
                verdict=verdict,
                supporting_subject_ids=item.get("supporting_subject_ids", []),
                refuting_subject_ids=item.get("refuting_subject_ids", []),
                key_quotes=item.get("key_quotes", []),
            )
        )
    return scores


async def _stage5_segment(
    subjects: list[SubjectRecord],
    scores: list[HypothesisScore],
    input: ProductResearchInput,
    client: AsyncAnthropic,
    model: str,
) -> list[BehavioralSegment]:
    env = get_template_env()
    template = env.get_template("product_research/segmentation.j2")
    prompt = template.render(
        question=input.question,
        product_context=input.product_context,
        scores=scores,
        subjects=subjects,
    )
    response = await client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_segments(response.content[0].text)


def _parse_segments(raw: str) -> list[BehavioralSegment]:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return []

    segments = []
    for item in data.get("segments", []):
        segments.append(
            BehavioralSegment(
                name=item.get("name", ""),
                description=item.get("description", ""),
                subject_ids=item.get("subject_ids", []),
                primary_jtbd=item.get("primary_jtbd", ""),
                adoption_trajectory_shape=item.get("adoption_trajectory_shape", ""),
                dominant_constraint_profile=item.get("dominant_constraint_profile", ""),
                dominant_failure_mode=item.get("dominant_failure_mode", ""),
                gaps_vs_product_positioning=item.get("gaps_vs_product_positioning", ""),
            )
        )
    return segments


def _extract_yaml_block(text: str) -> str:
    """Extract content between ```yaml ... ``` fences, or return raw text."""
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ── Public API ─────────────────────────────────────────────────────────


async def run_product_research(
    input: ProductResearchInput,
    client: Optional[AsyncAnthropic] = None,
    model: str = _DEFAULT_MODEL,
    output_dir: Path = Path("docs/research"),
    hypotheses_ratification_callback: Optional[Callable] = None,
) -> ProductResearchOutput:
    """Execute the 5-stage product research process.

    Stages:
    1. Decompose question into 4-7 falsifiable hypotheses
    2. Build sampling frame (2D: adoption-status × context-segment)
    3. Parallel interviews via asyncio.gather (10-16 simultaneous)
    4. Score hypotheses against subject evidence
    5. Bottom-up behavioral segmentation

    The hypotheses_ratification_callback is called after Stage 1 with the generated
    hypotheses. Use it to implement human review (CLI pause, UI confirmation, etc.).
    If None, hypotheses are used without ratification — suitable for automated pipelines.
    """
    if client is None:
        client = get_async_client()

    # Stage 1 — Hypothesis generation or use pre-ratified
    if input.ratified_hypotheses:
        hypotheses = input.ratified_hypotheses
        ratified = True
    else:
        hypotheses = await _stage1_decompose_question(input, client, model)
        ratified = False
        if hypotheses_ratification_callback:
            hypotheses = await hypotheses_ratification_callback(hypotheses)
            ratified = True

    validate_hypothesis_set(hypotheses)

    # Stage 2 — Sampling frame
    sampling_frame = _build_default_sampling_frame(input.subject_count)
    validate_sampling_frame_row_counts(sampling_frame)

    # Stage 3 — Parallel interviews (THE core async pattern)
    subjects = await _stage3_parallel_interviews(sampling_frame, input, hypotheses, client, model)

    # Stage 4 — Hypothesis scoring
    scores = await _stage4_score_hypotheses(hypotheses, subjects, client, model)
    all_supported = check_all_hypotheses_supported(scores)

    # Stage 5 — Bottom-up segmentation
    segments = await _stage5_segment(subjects, scores, input, client, model)

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = f"docs/research/product-research/{run_date}-{input.slug}"

    return ProductResearchOutput(
        slug=input.slug,
        run_date=run_date,
        run_dir=run_dir,
        hypotheses=hypotheses,
        hypotheses_ratified=ratified,
        sampling_frame=sampling_frame,
        subjects=subjects,
        hypothesis_scores=scores,
        segments=segments,
        all_hypotheses_supported_flag=all_supported,
    )


def run_product_research_sync(
    input: ProductResearchInput,
    **kwargs,
) -> ProductResearchOutput:
    """Synchronous wrapper for use in non-async contexts."""
    return asyncio.run(run_product_research(input, **kwargs))
