"""Tests for YAML I/O and validation."""

from pathlib import Path

import pytest

from voice_of_agents.validators.io import (
    LoadError,
    load_capability_registry,
    load_persona,
    load_workflow_mapping,
    save_persona,
    save_workflow_mapping,
)
from voice_of_agents.models.persona import Persona, Segment, Tier
from voice_of_agents.models.workflow import (
    Goal,
    GoalCategory,
    GoalPriority,
    PersonaWorkflowMapping,
    Workflow,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestLoadPersona:
    def test_load_valid(self):
        persona = load_persona(FIXTURES / "sample_persona.yaml")
        assert persona.id == 1
        assert persona.name == "Maria Gutierrez"
        assert persona.tier == Tier.DEVELOPER
        assert len(persona.pain_points) == 2
        assert len(persona.pain_themes) == 3

    def test_load_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            load_persona(FIXTURES / "nonexistent.yaml")


class TestLoadCapabilityRegistry:
    def test_load_valid(self):
        registry = load_capability_registry(FIXTURES / "sample_registry.yaml")
        assert registry.product == "Rooben Pro"
        assert len(registry.capabilities) == 10
        assert len(registry.available()) == 9
        assert registry.get("CAP-IMPORT-BULK") is not None
        assert registry.get("CAP-IMPORT-BULK").is_available() is False


class TestLoadWorkflowMapping:
    def test_load_valid(self):
        mapping = load_workflow_mapping(FIXTURES / "sample_workflow.yaml")
        assert mapping.persona_id == 1
        assert len(mapping.goals) == 3
        assert mapping.goals[0].priority == GoalPriority.PRIMARY
        assert len(mapping.goals[0].workflows[0].steps) == 3
        assert len(mapping.feature_recommendations) == 1


class TestSavePersona:
    def test_round_trip(self, tmp_path):
        persona = Persona(
            id=99,
            name="Test User",
            role="Tester",
            segment=Segment.B2C,
            industry="Testing",
            tier=Tier.FREE,
        )
        path = save_persona(persona, tmp_path)
        assert path.exists()

        loaded = load_persona(path)
        assert loaded.id == 99
        assert loaded.name == "Test User"


class TestSaveWorkflowMapping:
    def test_round_trip(self, tmp_path):
        mapping = PersonaWorkflowMapping(
            persona_id=99,
            persona_name="Test User",
            persona_tier=Tier.FREE,
            goals=[
                Goal(
                    id="G-99-1",
                    title="Test Goal",
                    category=GoalCategory.KNOWLEDGE,
                    priority=GoalPriority.PRIMARY,
                    workflows=[
                        Workflow(
                            id="W-99-1-a",
                            title="Test WF",
                            capabilities_used=["CAP-LEARN-SEARCH"],
                        )
                    ],
                )
            ],
        )
        path = save_workflow_mapping(mapping, tmp_path)
        assert path.exists()

        loaded = load_workflow_mapping(path)
        assert loaded.persona_id == 99
        assert len(loaded.goals) == 1
