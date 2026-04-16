"""Tests for cross-reference validation."""

import pytest

from voice_of_agents.models.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
)
from voice_of_agents.models.persona import Persona, Segment, Tier
from voice_of_agents.models.workflow import (
    Goal,
    GoalCategory,
    GoalPriority,
    PersonaWorkflowMapping,
    Workflow,
    WorkflowStep,
)
from voice_of_agents.validators.validate import (
    validate_all,
    validate_workflow_against_persona,
    validate_workflow_against_registry,
)


def _make_registry():
    return CapabilityRegistry(
        product="Test",
        capabilities=[
            Capability(
                id="CAP-LEARN-SEARCH",
                name="Search",
                status=CapabilityStatus.COMPLETE,
                feature_area="Learning",
            ),
            Capability(
                id="CAP-LEARN-CREATE",
                name="Create",
                status=CapabilityStatus.COMPLETE,
                feature_area="Learning",
            ),
        ],
    )


def _make_persona(persona_id=1, segment=Segment.B2C, tier=Tier.DEVELOPER):
    return Persona(
        id=persona_id,
        name="Test",
        role="Tester",
        segment=segment,
        industry="Testing",
        tier=tier,
    )


def _make_mapping(persona_id=1, tier=Tier.DEVELOPER, goals=None):
    if goals is None:
        goals = [
            Goal(
                id=f"G-{persona_id:02d}-1",
                title="Test Goal",
                category=GoalCategory.KNOWLEDGE,
                priority=GoalPriority.PRIMARY,
                workflows=[
                    Workflow(
                        id=f"W-{persona_id:02d}-1-a",
                        title="Test WF",
                        steps=[
                            WorkflowStep(
                                seq=1,
                                action="Do something",
                                capability_id="CAP-LEARN-SEARCH",
                            )
                        ],
                        capabilities_used=["CAP-LEARN-SEARCH"],
                    )
                ],
            )
        ]
    return PersonaWorkflowMapping(
        persona_id=persona_id,
        persona_name="Test",
        persona_tier=tier,
        goals=goals,
    )


class TestValidateWorkflowAgainstRegistry:
    def test_valid(self):
        result = validate_workflow_against_registry(_make_mapping(), _make_registry())
        assert result.ok

    def test_unknown_capability_in_step(self):
        mapping = _make_mapping(goals=[
            Goal(
                id="G-01-1",
                title="Test",
                category=GoalCategory.KNOWLEDGE,
                priority=GoalPriority.PRIMARY,
                workflows=[
                    Workflow(
                        id="W-01-1-a",
                        title="Test",
                        steps=[
                            WorkflowStep(
                                seq=1,
                                action="Do",
                                capability_id="CAP-NONEXIST",
                            )
                        ],
                        capabilities_used=["CAP-NONEXIST"],
                    )
                ],
            )
        ])
        result = validate_workflow_against_registry(mapping, _make_registry())
        assert not result.ok
        assert len(result.errors) == 2  # step + capabilities_used

    def test_missing_but_available_warns(self):
        mapping = _make_mapping(goals=[
            Goal(
                id="G-01-1",
                title="Test",
                category=GoalCategory.KNOWLEDGE,
                priority=GoalPriority.PRIMARY,
                workflows=[
                    Workflow(
                        id="W-01-1-a",
                        title="Test",
                        capabilities_used=["CAP-LEARN-SEARCH"],
                        capabilities_missing=["CAP-LEARN-CREATE"],
                    )
                ],
            )
        ])
        result = validate_workflow_against_registry(mapping, _make_registry())
        assert result.ok  # warnings, not errors
        assert len(result.warnings) == 1


class TestValidateWorkflowAgainstPersona:
    def test_valid(self):
        result = validate_workflow_against_persona(_make_mapping(), _make_persona())
        assert result.ok

    def test_id_mismatch(self):
        result = validate_workflow_against_persona(
            _make_mapping(persona_id=2),
            _make_persona(persona_id=1),
        )
        assert not result.ok

    def test_no_primary_goals(self):
        mapping = _make_mapping(goals=[
            Goal(
                id="G-01-1",
                title="Test",
                category=GoalCategory.KNOWLEDGE,
                priority=GoalPriority.ASPIRATIONAL,
                workflows=[],
            )
        ])
        result = validate_workflow_against_persona(mapping, _make_persona())
        assert not result.ok

    def test_b2b_missing_governance_warns(self):
        mapping = _make_mapping()
        persona = _make_persona(segment=Segment.B2B)
        result = validate_workflow_against_persona(mapping, persona)
        assert len(result.warnings) >= 1


class TestValidateAll:
    def test_valid(self):
        result = validate_all(
            [_make_persona()],
            [_make_mapping()],
            _make_registry(),
        )
        assert result.ok

    def test_missing_persona(self):
        result = validate_all(
            [],
            [_make_mapping()],
            _make_registry(),
        )
        assert not result.ok

    def test_unmapped_persona_warns(self):
        result = validate_all(
            [_make_persona(persona_id=1), _make_persona(persona_id=2)],
            [_make_mapping(persona_id=1)],
            _make_registry(),
        )
        assert result.ok
        assert len(result.warnings) >= 1
