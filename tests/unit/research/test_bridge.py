"""Tests for research/bridge.py — research → eval persona conversion."""

import tempfile
from pathlib import Path

import pytest

from voice_of_agents.research.bridge import (
    sidecar_to_canonical_persona,
    session_to_personas,
    write_bridge_workflow,
)
from voice_of_agents.research.models import (
    AdoptionStatus,
    ContextSegment,
    UXWPersonaSidecar,
    VerbatimQuote,
)
from voice_of_agents.core.enums import Segment, Tier, ValidationStatus


def _make_sidecar(uxw_id: str = "UXW-01") -> UXWPersonaSidecar:
    return UXWPersonaSidecar(
        uxw_id=uxw_id,
        name="Alice",
        segment_source="b2b-mid",
        subject_ids=["subject-01", "subject-02"],
        jtbd="get work done faster",
        adoption_trajectory="tried, liked, paying",
        last_concrete_episode="last week",
        constraint_profile="too little time to learn new tools",
        failure_or_abandonment_mode="lost trust after one bad output",
        decision_topology="solo",
        anti_model_of_success="never having to redo work",
        verbatim_quote_bank=[VerbatimQuote(key=f"Q{i}", text=f"quote {i}") for i in range(1, 6)],
    )


class TestSidecarToCanonicalPersona:
    def test_returns_persona(self):
        from voice_of_agents.core.persona import Persona
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert isinstance(persona, Persona)

    def test_name_preserved(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert persona.name == "Alice"

    def test_legacy_id_set_to_uxw_id(self):
        sidecar = _make_sidecar("UXW-03")
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert persona.metadata.legacy_id == "UXW-03"

    def test_validation_status_is_draft(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert persona.metadata.validation_status == ValidationStatus.DRAFT

    def test_source_is_generated(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert persona.metadata.source == "generated"

    def test_pain_points_populated(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert len(persona.pain_points) >= 1

    def test_b2b_context_maps_to_b2b_segment(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(
            sidecar, persona_id=1, context_segment=ContextSegment.B2B_SMALL
        )
        assert persona.segment == Segment.B2B

    def test_b2c_context_maps_to_b2c_segment(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(
            sidecar, persona_id=1, context_segment=ContextSegment.B2C_HIGH_AUTONOMY
        )
        assert persona.segment == Segment.B2C

    def test_session_slug_in_research_basis(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1, session_slug="my-research")
        assert any("my-research" in b for b in persona.metadata.research_basis)

    def test_jtbd_maps_to_mindset(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(sidecar, persona_id=1)
        assert persona.mindset == sidecar.jtbd

    def test_adopter_price_sensitivity_low(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(
            sidecar, persona_id=1, adoption_status=AdoptionStatus.ADOPTER
        )
        assert persona.voice.price_sensitivity == "low"

    def test_abandoner_price_sensitivity_high(self):
        sidecar = _make_sidecar()
        persona = sidecar_to_canonical_persona(
            sidecar, persona_id=1, adoption_status=AdoptionStatus.ABANDONER
        )
        assert persona.voice.price_sensitivity == "high"


class TestSessionToPersonas:
    def test_returns_empty_without_persona_output(self):
        from voice_of_agents.research.models import ProductResearchInput
        from voice_of_agents.research.session import ResearchSession

        session = ResearchSession.create(
            ProductResearchInput(
                question="test?",
                scope="US",
                slug="test",
                product_context="test",
            )
        )
        personas = session_to_personas(session)
        assert personas == []

    def test_returns_one_per_sidecar(self):
        from voice_of_agents.research.models import (
            ProductResearchInput,
            PersonaResearchOutput,
        )
        from voice_of_agents.research.session import ResearchSession

        session = ResearchSession.create(
            ProductResearchInput(
                question="test?",
                scope="US",
                slug="test",
                product_context="test",
            )
        )
        session.persona_research_output = PersonaResearchOutput(
            topup_subjects=[],
            persona_sidecars=[_make_sidecar("UXW-01"), _make_sidecar("UXW-02")],
            task_cards=[],
            coverage_map={},
        )
        personas = session_to_personas(session, starting_id=10)
        assert len(personas) == 2
        assert personas[0].id == 10
        assert personas[1].id == 11


class TestWriteBridgeWorkflow:
    def test_writes_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_bridge_workflow(Path(tmpdir))
            assert path.exists()
            assert path.name == "BRIDGE-WORKFLOW.md"

    def test_file_contains_usage_example(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_bridge_workflow(Path(tmpdir))
            content = path.read_text()
            assert "session_to_personas" in content
