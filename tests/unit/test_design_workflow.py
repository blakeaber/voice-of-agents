"""Unit tests for design/workflow.py — Goal, Workflow, PersonaWorkflowMapping."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from voice_of_agents.core.enums import GoalCategory, GoalPriority, Tier
from voice_of_agents.design.workflow import (
    Goal,
    PersonaWorkflowMapping,
    Workflow,
)


class TestWorkflow:
    def test_uses_capability(self):
        wf = Workflow(
            id="W-01-1-a",
            title="Test",
            capabilities_used=["CAP-LEARN-SEARCH", "CAP-LEARN-CREATE"],
        )
        assert wf.uses_capability("CAP-LEARN-SEARCH") is True
        assert wf.uses_capability("CAP-ROUTE-FIND") is False

    def test_has_gaps(self):
        wf = Workflow(id="W-01-1-a", title="Test", capabilities_missing=["CAP-IMPORT-BULK"])
        assert wf.has_gaps() is True

    def test_no_gaps(self):
        wf = Workflow(id="W-01-1-a", title="Test")
        assert wf.has_gaps() is False

    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError):
            Workflow(id="bad-id", title="Test")


class TestGoal:
    def _goal(self, **kwargs):
        defaults = dict(
            id="G-01-1",
            title="Test",
            category=GoalCategory.KNOWLEDGE,
            priority=GoalPriority.PRIMARY,
        )
        defaults.update(kwargs)
        return Goal(**defaults)

    def test_basic_creation(self):
        g = self._goal()
        assert g.id == "G-01-1"
        assert g.priority == GoalPriority.PRIMARY

    def test_all_capabilities(self):
        goal = self._goal(
            workflows=[
                Workflow(
                    id="W-01-1-a",
                    title="A",
                    capabilities_used=["CAP-LEARN-SEARCH"],
                    capabilities_missing=["CAP-IMPORT-BULK"],
                ),
                Workflow(
                    id="W-01-1-b",
                    title="B",
                    capabilities_used=["CAP-LEARN-CREATE"],
                ),
            ]
        )
        assert goal.all_capabilities_used() == {"CAP-LEARN-SEARCH", "CAP-LEARN-CREATE"}
        assert goal.all_capabilities_missing() == {"CAP-IMPORT-BULK"}

    def test_invalid_id_pattern(self):
        with pytest.raises(ValidationError):
            self._goal(id="G01-1")


class TestPersonaWorkflowMapping:
    def _mapping(self, **kwargs):
        defaults = dict(
            persona_id=1,
            persona_name="Test",
            persona_tier=Tier.DEVELOPER,
            goals=[
                Goal(
                    id="G-01-1",
                    title="Goal 1",
                    category=GoalCategory.KNOWLEDGE,
                    priority=GoalPriority.PRIMARY,
                    workflows=[
                        Workflow(id="W-01-1-a", title="WF", capabilities_used=["CAP-LEARN-SEARCH"])
                    ],
                ),
                Goal(
                    id="G-01-2",
                    title="Goal 2",
                    category=GoalCategory.DELEGATION,
                    priority=GoalPriority.SECONDARY,
                    workflows=[
                        Workflow(
                            id="W-01-2-a",
                            title="WF2",
                            capabilities_used=["CAP-ROUTE-FIND"],
                            capabilities_missing=["CAP-IMPORT-BULK"],
                        )
                    ],
                ),
            ],
        )
        defaults.update(kwargs)
        return PersonaWorkflowMapping(**defaults)

    def test_all_capabilities_used(self):
        m = self._mapping()
        assert m.all_capabilities_used() == {"CAP-LEARN-SEARCH", "CAP-ROUTE-FIND"}

    def test_all_gaps(self):
        m = self._mapping()
        assert m.all_gaps() == {"CAP-IMPORT-BULK"}

    def test_goals_by_priority(self):
        m = self._mapping()
        assert len(m.goals_by_priority(GoalPriority.PRIMARY)) == 1
        assert len(m.goals_by_priority(GoalPriority.SECONDARY)) == 1
        assert len(m.goals_by_priority(GoalPriority.ASPIRATIONAL)) == 0

    def test_no_feature_recommendations_required(self):
        m = self._mapping()
        assert m.feature_recommendations == []

    def test_feature_recommendations_are_backlog_items(self):
        from voice_of_agents.core.backlog import BacklogItem

        item = BacklogItem(
            id="B-001",
            title="Test feat",
            description="Desc",
            source="design",
            extends_capability="CAP-LEARN-SEARCH",
        )
        m = self._mapping(feature_recommendations=[item])
        assert m.feature_recommendations[0].source == "design"
        assert m.feature_recommendations[0].extends_capability == "CAP-LEARN-SEARCH"
