"""Tests for typed handoffs between research pipeline stages."""

import pytest

from voice_of_agents.research.models import (
    AdoptionStatus,
    BehavioralSegment,
    ContextSegment,
    Hypothesis,
    HypothesisScore,
    HypothesisVerdict,
    PersonaResearchInput,
    PersonaResearchOutput,
    UXWPersonaSidecar,
    UXWTaskCard,
    VerbatimQuote,
    WorkflowResearchInput,
    WorkflowResearchOutput,
    EpisodeRecord,
    EpisodeStep,
    PWMWorkflow,
    PWMWorkflowStep,
    JourneyRedesignInput,
    ProductResearchOutput,
    SamplingCell,
)


def _make_quotes(n: int = 5) -> list[VerbatimQuote]:
    return [VerbatimQuote(key=f"Q{i+1}", text=f"quote {i+1}") for i in range(n)]


def _minimal_product_output() -> ProductResearchOutput:
    return ProductResearchOutput(
        slug="test",
        run_date="2026-01-01",
        run_dir="docs/research/test",
        hypotheses=[
            Hypothesis(id=f"H{i+1}", statement="s", falsification_condition="f")
            for i in range(4)
        ],
        hypotheses_ratified=True,
        sampling_frame=[
            SamplingCell(
                adoption_status=AdoptionStatus.ADOPTER,
                context_segment=ContextSegment.B2B_SMALL,
                subject_profile="test",
            )
        ],
        subjects=[],
        hypothesis_scores=[
            HypothesisScore(hypothesis_id=f"H{i+1}", verdict=HypothesisVerdict.REFUTES)
            for i in range(4)
        ],
        segments=[
            BehavioralSegment(
                name="seg-a",
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
        segment_source="seg-a",
        subject_ids=["subject-01", "subject-02"],
        jtbd="get work done",
        adoption_trajectory="tried, liked",
        last_concrete_episode="last week",
        constraint_profile="time",
        failure_or_abandonment_mode="too slow",
        decision_topology="solo",
        anti_model_of_success="data loss",
        verbatim_quote_bank=_make_quotes(5),
    )


def _minimal_persona_output() -> PersonaResearchOutput:
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
        persona_sidecars=[_minimal_sidecar("UXW-01"), _minimal_sidecar("UXW-02"), _minimal_sidecar("UXW-03")],
        task_cards=[task_card],
        coverage_map={"seg-a": 3},
    )


def _minimal_workflow() -> PWMWorkflow:
    return PWMWorkflow(
        id="UXW-01-01",
        persona=1,
        title="Primary workflow",
        intent_goal="get work done",
        intent_trigger="task arrives",
        success_definition="task complete",
        preconditions=[],
        steps=[
            PWMWorkflowStep(
                number=1,
                action="do thing",
                tool="none",
                input="data",
                output="result",
                time="5",
                blocker="none",
                friction_risk="low",
            )
        ],
        success_criteria=[],
        satisfaction_drivers=[],
        dealbreakers=[],
        efficiency_baseline_method="manual count",
        efficiency_baseline_time="30 min",
        value_time_saved="10 min",
        value_errors_prevented="format errors",
        value_knowledge_preserved="decision rationale",
    )


def _minimal_episode() -> EpisodeRecord:
    return EpisodeRecord(
        episode="test",
        date="yesterday",
        pre_state="started",
        steps=[
            EpisodeStep(step="s", tool="none", input="i", output="o", time="1", blocker="none")
        ],
        post_state="done",
        what_i_wished_existed="better tool",
    )


class TestStage1ToStage2Contract:
    def test_product_output_feeds_persona_input(self):
        product_out = _minimal_product_output()
        persona_in = PersonaResearchInput(product_research=product_out)
        assert persona_in.product_research.slug == "test"
        assert len(persona_in.product_research.segments) == 1

    def test_persona_input_preserves_segments(self):
        product_out = _minimal_product_output()
        persona_in = PersonaResearchInput(product_research=product_out)
        assert persona_in.product_research.segments[0].name == "seg-a"


class TestStage2ToStage3Contract:
    def test_persona_output_feeds_workflow_input(self):
        persona_out = _minimal_persona_output()
        workflow_in = WorkflowResearchInput(
            persona_research=persona_out,
            target_uxw_id="UXW-01",
        )
        assert workflow_in.target_uxw_id == "UXW-01"
        assert len(workflow_in.persona_research.persona_sidecars) == 3

    def test_invalid_uxw_id_detected_at_runtime(self):
        persona_out = _minimal_persona_output()
        workflow_in = WorkflowResearchInput(
            persona_research=persona_out,
            target_uxw_id="UXW-99",  # doesn't exist
        )
        from voice_of_agents.research.workflows_from_interviews import _get_sidecar
        with pytest.raises(ValueError, match="UXW-99"):
            _get_sidecar(workflow_in)


class TestStage3ToStage4Contract:
    def test_workflow_output_feeds_journey_input(self):
        workflow_out = WorkflowResearchOutput(
            uxw_id="UXW-01",
            episodes=[_minimal_episode()],
            workflow_maps=[_minimal_workflow()],
        )
        persona_out = _minimal_persona_output()
        journey_in = JourneyRedesignInput(
            workflow_research=workflow_out,
            persona_research=persona_out,
            anchor_segment="FREE→DEVELOPER",
            journeys_in_scope=["onboarding"],
            build_form="mockups_only",
            focus_panel_uxw_ids=["UXW-01", "UXW-02", "UXW-03"],
        )
        assert journey_in.workflow_research.uxw_id == "UXW-01"
        assert len(journey_in.focus_panel_uxw_ids) == 3

    def test_journey_input_rejects_fewer_than_3_panel(self):
        from pydantic import ValidationError
        workflow_out = WorkflowResearchOutput(
            uxw_id="UXW-01",
            episodes=[_minimal_episode()],
            workflow_maps=[_minimal_workflow()],
        )
        persona_out = _minimal_persona_output()
        with pytest.raises(ValidationError):
            JourneyRedesignInput(
                workflow_research=workflow_out,
                persona_research=persona_out,
                anchor_segment="FREE→DEVELOPER",
                journeys_in_scope=["onboarding"],
                build_form="mockups_only",
                focus_panel_uxw_ids=["UXW-01", "UXW-02"],  # only 2
            )
