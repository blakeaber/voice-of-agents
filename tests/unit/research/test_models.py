"""Tests for research/models.py — validators and schema enforcement."""

import pytest
from pydantic import ValidationError

from voice_of_agents.research.models import (
    AdoptionStatus,
    ContextSegment,
    EpisodeRecord,
    EpisodeStep,
    ProductResearchInput,
    SubjectRecord,
    UXWPersonaSidecar,
    VerbatimQuote,
)


def _make_quotes(n: int = 5) -> list[VerbatimQuote]:
    return [VerbatimQuote(key=f"Q{i + 1}", text=f"quote {i + 1}") for i in range(n)]


def _make_subject(
    adoption_status: AdoptionStatus = AdoptionStatus.ADOPTER,
    failure_mode: str = "",
) -> SubjectRecord:
    return SubjectRecord(
        subject_id="subject-01",
        adoption_status=adoption_status,
        context_segment=ContextSegment.B2B_SMALL,
        jtbd="get my work done",
        adoption_trajectory="tried it, liked it",
        last_concrete_episode="last week",
        constraint_profile="time, budget",
        failure_or_abandonment_mode=failure_mode,
        decision_topology="solo",
        anti_model_of_success="losing data",
        verbatim_quote_bank=_make_quotes(5),
    )


class TestSubjectRecord:
    def test_adopter_failure_mode_can_be_blank(self):
        s = _make_subject(AdoptionStatus.ADOPTER, "")
        assert s.failure_or_abandonment_mode == ""

    def test_abandoner_requires_failure_mode(self):
        with pytest.raises(ValidationError, match="failure_or_abandonment_mode"):
            _make_subject(AdoptionStatus.ABANDONER, "")

    def test_evaluated_requires_failure_mode(self):
        with pytest.raises(ValidationError, match="failure_or_abandonment_mode"):
            _make_subject(AdoptionStatus.EVALUATED_AND_REJECTED, "")

    def test_actively_anti_requires_failure_mode(self):
        with pytest.raises(ValidationError, match="failure_or_abandonment_mode"):
            _make_subject(AdoptionStatus.ACTIVELY_ANTI, "")

    def test_partial_adopter_requires_failure_mode(self):
        with pytest.raises(ValidationError, match="failure_or_abandonment_mode"):
            _make_subject(AdoptionStatus.PARTIAL_ADOPTER, "")

    def test_abandoner_with_failure_mode_passes(self):
        s = _make_subject(AdoptionStatus.ABANDONER, "it was too slow")
        assert s.failure_or_abandonment_mode == "it was too slow"

    def test_verbatim_quotes_min_5(self):
        with pytest.raises(ValidationError):
            SubjectRecord(
                subject_id="subject-01",
                adoption_status=AdoptionStatus.ADOPTER,
                context_segment=ContextSegment.B2B_SMALL,
                jtbd="x",
                adoption_trajectory="x",
                last_concrete_episode="x",
                constraint_profile="x",
                failure_or_abandonment_mode="",
                decision_topology="x",
                anti_model_of_success="x",
                verbatim_quote_bank=_make_quotes(3),
            )

    def test_verbatim_quotes_max_8(self):
        with pytest.raises(ValidationError):
            SubjectRecord(
                subject_id="subject-01",
                adoption_status=AdoptionStatus.ADOPTER,
                context_segment=ContextSegment.B2B_SMALL,
                jtbd="x",
                adoption_trajectory="x",
                last_concrete_episode="x",
                constraint_profile="x",
                failure_or_abandonment_mode="",
                decision_topology="x",
                anti_model_of_success="x",
                verbatim_quote_bank=_make_quotes(9),
            )


class TestProductResearchInput:
    def test_slug_max_six_words(self):
        with pytest.raises(ValidationError, match="slug"):
            ProductResearchInput(
                question="Do abandoners quit because X?",
                scope="US, 2024",
                slug="one-two-three-four-five-six-seven",
                product_context="A tool",
            )

    def test_valid_six_word_slug(self):
        inp = ProductResearchInput(
            question="Do abandoners quit because X?",
            scope="US, 2024",
            slug="one-two-three-four-five-six",
            product_context="A tool",
        )
        assert inp.slug == "one-two-three-four-five-six"

    def test_subject_count_range(self):
        with pytest.raises(ValidationError):
            ProductResearchInput(
                question="Q?",
                scope="US",
                slug="test",
                product_context="tool",
                subject_count=9,
            )
        with pytest.raises(ValidationError):
            ProductResearchInput(
                question="Q?",
                scope="US",
                slug="test",
                product_context="tool",
                subject_count=17,
            )


class TestUXWPersonaSidecar:
    def test_min_two_subjects_enforced(self):
        with pytest.raises(ValidationError, match="2 contributing subjects"):
            UXWPersonaSidecar(
                uxw_id="UXW-01",
                name="Alice",
                segment_source="segment",
                subject_ids=["subject-01"],  # only one
                jtbd="x",
                adoption_trajectory="x",
                last_concrete_episode="x",
                constraint_profile="x",
                failure_or_abandonment_mode="x",
                decision_topology="x",
                anti_model_of_success="x",
                verbatim_quote_bank=_make_quotes(5),
            )

    def test_two_subjects_passes(self):
        sidecar = UXWPersonaSidecar(
            uxw_id="UXW-01",
            name="Alice",
            segment_source="segment",
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
        assert sidecar.uxw_id == "UXW-01"


class TestEpisodeRecord:
    def test_empty_pre_state_rejected(self):
        with pytest.raises(ValidationError, match="pre_state"):
            EpisodeRecord(
                episode="test",
                date="yesterday",
                pre_state="",
                steps=[
                    EpisodeStep(
                        step="s", tool="none", input="i", output="o", time="1", blocker="none"
                    )
                ],
                post_state="done",
                what_i_wished_existed="x",
            )

    def test_empty_steps_rejected(self):
        with pytest.raises(ValidationError, match="steps"):
            EpisodeRecord(
                episode="test",
                date="yesterday",
                pre_state="started",
                steps=[],
                post_state="done",
                what_i_wished_existed="x",
            )

    def test_valid_episode(self):
        ep = EpisodeRecord(
            episode="test",
            date="yesterday",
            pre_state="started",
            steps=[
                EpisodeStep(step="s", tool="none", input="i", output="o", time="1", blocker="none")
            ],
            post_state="done",
            what_i_wished_existed="better tool",
        )
        assert len(ep.steps) == 1
