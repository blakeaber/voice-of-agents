"""Cross-stage guard functions that mirror the SKILL.md halting conditions."""

from __future__ import annotations

from voice_of_agents.research.models import (
    AdoptionStatus,
    BehavioralSegment,
    Hypothesis,
    HypothesisScore,
    HypothesisVerdict,
    PersonaResearchOutput,
    ProductResearchOutput,
    SamplingCell,
)


class ResearchValidationError(ValueError):
    """Raised when a stage-entry gate condition is not met."""
    pass


# ── Sampling frame row-count gate ──────────────────────────────────────

MINIMUM_COUNTS: dict[AdoptionStatus, int] = {
    AdoptionStatus.ABANDONER: 2,
    AdoptionStatus.EVALUATED_AND_REJECTED: 2,
    AdoptionStatus.ACTIVELY_ANTI: 2,
    AdoptionStatus.ADOPTER: 1,
    AdoptionStatus.PARTIAL_ADOPTER: 1,
    AdoptionStatus.NEVER_TRIED_AWARE: 1,
}


def validate_sampling_frame_row_counts(frame: list[SamplingCell]) -> None:
    """Halt if any row falls below the minimum required subject count.

    Mirrors the SKILL.md row-count refusal gate exactly.
    Abandoners and refusers are structurally required for adoption-friction analysis.
    """
    counts: dict[AdoptionStatus, int] = {}
    for cell in frame:
        counts[cell.adoption_status] = counts.get(cell.adoption_status, 0) + 1

    for status, minimum in MINIMUM_COUNTS.items():
        actual = counts.get(status, 0)
        if actual < minimum:
            raise ResearchValidationError(
                f"Expand recruitment in row '{status.value}': "
                f"minimum {minimum} subject(s) required, {actual} assigned. "
                f"Refusers and abandoners are structurally required — "
                f"they answer adoption-friction questions that adopters cannot."
            )


def validate_hypothesis_set(hypotheses: list[Hypothesis]) -> None:
    """Enforce 4-7 hypotheses, each with a falsification condition."""
    if len(hypotheses) < 4:
        raise ResearchValidationError(
            f"Minimum 4 hypotheses required; {len(hypotheses)} provided."
        )
    if len(hypotheses) > 7:
        raise ResearchValidationError(
            f"Maximum 7 hypotheses per run; {len(hypotheses)} provided."
        )
    for h in hypotheses:
        if not h.falsification_condition.strip():
            raise ResearchValidationError(
                f"Hypothesis {h.id} is missing a falsification condition. "
                f"Every hypothesis must state what evidence would force a 'refutes' verdict."
            )


def check_all_hypotheses_supported(scores: list[HypothesisScore]) -> bool:
    """Return True if all hypotheses returned 'supports' — high confirmation-bias risk."""
    if not scores:
        return False
    return all(s.verdict == HypothesisVerdict.SUPPORTS for s in scores)


# ── Stage entry guards ─────────────────────────────────────────────────


def guard_stage2_input(
    product_output: ProductResearchOutput,
    allow_all_supported: bool = False,
) -> None:
    """Gate: personas-from-research requires verdicts and segments (Stage 4+5 complete)."""
    if not product_output.hypothesis_scores:
        raise ResearchValidationError(
            "Cannot synthesize personas from a run without hypothesis scores. "
            "Stage 4 scoring must complete before persona synthesis."
        )
    if not product_output.segments:
        raise ResearchValidationError(
            "Cannot synthesize personas: segments are absent. "
            "Stage 5 segmentation must complete before persona synthesis."
        )
    if product_output.all_hypotheses_supported_flag and not allow_all_supported:
        raise ResearchValidationError(
            "All hypotheses supported in the upstream run — high confirmation-bias risk. "
            "Pass allow_all_supported=True to override, or review the sampling frame "
            "for solution-affine overrepresentation."
        )


def guard_stage3_input(persona_output: PersonaResearchOutput) -> None:
    """Gate: workflows-from-interviews requires at least one validated persona sidecar."""
    if not persona_output.persona_sidecars:
        raise ResearchValidationError(
            "No persona sidecars found. Run personas_from_research first."
        )
    for sidecar in persona_output.persona_sidecars:
        if len(sidecar.subject_ids) < 2:
            raise ResearchValidationError(
                f"Persona {sidecar.uxw_id} is based on fewer than 2 subjects "
                f"({len(sidecar.subject_ids)}). "
                f"Single-subject personas are rejected — minimum cluster size is 2."
            )


def guard_stage4_input(
    persona_output: PersonaResearchOutput,
    focus_panel_uxw_ids: list[str],
) -> None:
    """Gate: journey-redesign requires ≥3 focus panel personas, all present in output."""
    if len(focus_panel_uxw_ids) < 3:
        raise ResearchValidationError(
            f"Journey redesign requires ≥3 focus panel personas; "
            f"{len(focus_panel_uxw_ids)} specified."
        )
    available = {s.uxw_id for s in persona_output.persona_sidecars}
    missing = set(focus_panel_uxw_ids) - available
    if missing:
        raise ResearchValidationError(
            f"Focus panel UXW IDs not found in persona output: {sorted(missing)}. "
            f"Available: {sorted(available)}"
        )
