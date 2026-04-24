"""Tests for research/validation.py — cross-stage guard functions."""

import pytest

from voice_of_agents.research.models import (
    AdoptionStatus,
    BehavioralSegment,
    ContextSegment,
    Hypothesis,
    HypothesisScore,
    HypothesisVerdict,
    PersonaResearchOutput,
    ProductResearchOutput,
    SamplingCell,
    UXWPersonaSidecar,
    UXWTaskCard,
    VerbatimQuote,
)
from voice_of_agents.research.validation import (
    ResearchValidationError,
    check_all_hypotheses_supported,
    guard_stage2_input,
    guard_stage3_input,
    guard_stage4_input,
    validate_hypothesis_set,
    validate_sampling_frame_row_counts,
)


def _make_quotes(n: int = 5) -> list[VerbatimQuote]:
    return [VerbatimQuote(key=f"Q{i + 1}", text=f"q{i + 1}") for i in range(n)]


def _minimal_product_output() -> ProductResearchOutput:
    return ProductResearchOutput(
        slug="test",
        run_date="2026-01-01",
        run_dir="docs/research/test",
        hypotheses=[
            Hypothesis(id=f"H{i + 1}", statement="s", falsification_condition="f") for i in range(4)
        ],
        hypotheses_ratified=True,
        sampling_frame=[],
        subjects=[],
        hypothesis_scores=[
            HypothesisScore(hypothesis_id=f"H{i + 1}", verdict=HypothesisVerdict.REFUTES)
            for i in range(4)
        ],
        segments=[
            BehavioralSegment(
                name="seg",
                description="d",
                subject_ids=["subject-01", "subject-02"],
                primary_jtbd="j",
                adoption_trajectory_shape="t",
                dominant_constraint_profile="c",
                dominant_failure_mode="f",
                gaps_vs_product_positioning="g",
            )
        ],
    )


def _minimal_sidecar(uxw_id: str = "UXW-01") -> UXWPersonaSidecar:
    return UXWPersonaSidecar(
        uxw_id=uxw_id,
        name="Alice",
        segment_source="seg",
        subject_ids=["subject-01", "subject-02"],
        jtbd="x",
        adoption_trajectory="x",
        last_concrete_episode="x",
        constraint_profile="x",
        failure_or_abandonment_mode="x",
        decision_topology="x",
        anti_model_of_success="x",
        verbatim_quote_bank=_make_quotes(5),
    )


def _minimal_persona_output() -> PersonaResearchOutput:
    sidecar = _minimal_sidecar()
    task_card = UXWTaskCard(
        uxw_id="UXW-01",
        name="Alice",
        role="tester",
        intent="x",
        trigger="x",
        success_definition="x",
        today_workaround="x",
        preconditions=[],
        steps=[],
        success_criteria=[],
        persona_evaluation_rubric="x",
    )
    return PersonaResearchOutput(
        topup_subjects=[],
        persona_sidecars=[sidecar],
        task_cards=[task_card],
        coverage_map={"seg": 3},
    )


class TestSamplingFrameValidation:
    def _frame_with_counts(self, **counts: int) -> list[SamplingCell]:
        cells = []
        for status_val, count in counts.items():
            status = AdoptionStatus(status_val)
            for _ in range(count):
                cells.append(
                    SamplingCell(
                        adoption_status=status,
                        context_segment=ContextSegment.B2B_SMALL,
                        subject_profile="test",
                    )
                )
        return cells

    def test_valid_frame_passes(self):
        frame = self._frame_with_counts(
            adopter=1,
            **{"partial-adopter": 1},
            abandoner=2,
            **{"evaluated-and-rejected": 2},
            **{"never-tried-aware": 1},
            **{"actively-anti": 2},
        )
        validate_sampling_frame_row_counts(frame)

    def test_insufficient_abandoners_raises(self):
        frame = self._frame_with_counts(
            adopter=2,
            **{"partial-adopter": 2},
            abandoner=1,  # needs 2
            **{"evaluated-and-rejected": 2},
            **{"never-tried-aware": 1},
            **{"actively-anti": 2},
        )
        with pytest.raises(ResearchValidationError, match="abandoner"):
            validate_sampling_frame_row_counts(frame)

    def test_missing_actively_anti_raises(self):
        frame = self._frame_with_counts(
            adopter=2,
            **{"partial-adopter": 2},
            abandoner=2,
            **{"evaluated-and-rejected": 2},
            **{"never-tried-aware": 1},
        )
        with pytest.raises(ResearchValidationError, match="actively-anti"):
            validate_sampling_frame_row_counts(frame)


class TestHypothesisSetValidation:
    def _make_hypotheses(n: int) -> list[Hypothesis]:
        return [
            Hypothesis(id=f"H{i + 1}", statement="s", falsification_condition="f") for i in range(n)
        ]

    def test_fewer_than_4_raises(self):
        with pytest.raises(ResearchValidationError, match="Minimum 4"):
            validate_hypothesis_set(TestHypothesisSetValidation._make_hypotheses(3))

    def test_more_than_7_raises(self):
        with pytest.raises(ResearchValidationError, match="Maximum 7"):
            validate_hypothesis_set(TestHypothesisSetValidation._make_hypotheses(8))

    def test_4_to_7_passes(self):
        for n in range(4, 8):
            validate_hypothesis_set(TestHypothesisSetValidation._make_hypotheses(n))

    def test_missing_falsification_condition_raises(self):
        hypotheses = [
            Hypothesis(id="H1", statement="s", falsification_condition="f"),
            Hypothesis(id="H2", statement="s", falsification_condition="f"),
            Hypothesis(id="H3", statement="s", falsification_condition="f"),
            Hypothesis(id="H4", statement="s", falsification_condition=""),  # blank
        ]
        with pytest.raises(ResearchValidationError, match="falsification condition"):
            validate_hypothesis_set(hypotheses)


class TestAllHypothesesSupported:
    def test_all_supports_returns_true(self):
        scores = [
            HypothesisScore(hypothesis_id=f"H{i}", verdict=HypothesisVerdict.SUPPORTS)
            for i in range(4)
        ]
        assert check_all_hypotheses_supported(scores) is True

    def test_mixed_verdicts_returns_false(self):
        scores = [
            HypothesisScore(hypothesis_id="H1", verdict=HypothesisVerdict.SUPPORTS),
            HypothesisScore(hypothesis_id="H2", verdict=HypothesisVerdict.REFUTES),
        ]
        assert check_all_hypotheses_supported(scores) is False

    def test_empty_scores_returns_false(self):
        assert check_all_hypotheses_supported([]) is False


class TestGuardStage2:
    def test_valid_output_passes(self):
        guard_stage2_input(_minimal_product_output())

    def test_missing_scores_raises(self):
        out = _minimal_product_output()
        out = out.model_copy(update={"hypothesis_scores": []})
        with pytest.raises(ResearchValidationError, match="hypothesis scores"):
            guard_stage2_input(out)

    def test_missing_segments_raises(self):
        out = _minimal_product_output()
        out = out.model_copy(update={"segments": []})
        with pytest.raises(ResearchValidationError, match="segments"):
            guard_stage2_input(out)

    def test_all_supported_raises_without_override(self):
        out = _minimal_product_output()
        out = out.model_copy(update={"all_hypotheses_supported_flag": True})
        with pytest.raises(ResearchValidationError, match="confirmation-bias"):
            guard_stage2_input(out)

    def test_all_supported_passes_with_override(self):
        out = _minimal_product_output()
        out = out.model_copy(update={"all_hypotheses_supported_flag": True})
        guard_stage2_input(out, allow_all_supported=True)


class TestGuardStage3:
    def test_valid_persona_output_passes(self):
        guard_stage3_input(_minimal_persona_output())

    def test_empty_sidecars_raises(self):
        out = _minimal_persona_output()
        out = out.model_copy(update={"persona_sidecars": []})
        with pytest.raises(ResearchValidationError, match="No persona sidecars"):
            guard_stage3_input(out)


class TestGuardStage4:
    def test_valid_panel_passes(self):
        out = _minimal_persona_output()
        out.persona_sidecars.append(_minimal_sidecar("UXW-02"))
        out.persona_sidecars.append(_minimal_sidecar("UXW-03"))
        guard_stage4_input(out, ["UXW-01", "UXW-02", "UXW-03"])

    def test_fewer_than_3_panel_raises(self):
        out = _minimal_persona_output()
        with pytest.raises(ResearchValidationError, match="≥3"):
            guard_stage4_input(out, ["UXW-01", "UXW-02"])

    def test_missing_uxw_id_raises(self):
        out = _minimal_persona_output()
        with pytest.raises(ResearchValidationError, match="not found"):
            guard_stage4_input(out, ["UXW-01", "UXW-99", "UXW-100"])
