"""Tests for Pydantic models."""

import pytest

from voice_of_agents.models.persona import (
    Intensity,
    PainPoint,
    PainTheme,
    Persona,
    Segment,
    ThemeCode,
    Tier,
)
from voice_of_agents.models.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
)
from voice_of_agents.models.workflow import (
    Complexity,
    FeatureRecommendation,
    Goal,
    GoalCategory,
    GoalPriority,
    PersonaWorkflowMapping,
    ValueMetrics,
    Workflow,
    WorkflowStep,
)


# ─── Persona tests ──────────────────────────────────────────────────────


class TestPersona:
    def test_create_minimal(self):
        p = Persona(
            id=1,
            name="Test User",
            role="Developer",
            segment=Segment.B2C,
            industry="Technology",
            tier=Tier.DEVELOPER,
        )
        assert p.id == 1
        assert p.segment == Segment.B2C
        assert p.org_size == 1

    def test_create_full(self):
        p = Persona(
            id=1,
            name="Maria Gutierrez",
            role="Immigration Paralegal",
            segment=Segment.B2C,
            industry="Legal Services",
            tier=Tier.DEVELOPER,
            age=27,
            income=52000,
            pain_points=[
                PainPoint(
                    description="15-20 visa apps per month",
                    impact="45 min searching per case",
                )
            ],
            pain_themes=[
                PainTheme(theme=ThemeCode.A, intensity=Intensity.HIGH),
                PainTheme(theme=ThemeCode.D, intensity=Intensity.CRITICAL),
            ],
        )
        assert p.theme_intensity(ThemeCode.A) == Intensity.HIGH
        assert p.theme_intensity(ThemeCode.D) == Intensity.CRITICAL
        assert p.theme_intensity(ThemeCode.E) is None
        assert p.is_regulated() is True

    def test_is_regulated_false(self):
        p = Persona(
            id=2,
            name="Sarah Kim",
            role="E-commerce Owner",
            segment=Segment.B2C,
            industry="Retail",
            tier=Tier.DEVELOPER,
            pain_themes=[
                PainTheme(theme=ThemeCode.D, intensity=Intensity.LOW),
            ],
        )
        assert p.is_regulated() is False

    def test_invalid_id(self):
        with pytest.raises(Exception):
            Persona(
                id=0,
                name="Bad",
                role="None",
                segment=Segment.B2C,
                industry="None",
                tier=Tier.FREE,
            )


# ─── Capability tests ───────────────────────────────────────────────────


class TestCapability:
    def test_is_available(self):
        cap = Capability(
            id="CAP-LEARN-SEARCH",
            name="Search",
            status=CapabilityStatus.COMPLETE,
            feature_area="Learning",
        )
        assert cap.is_available() is True

    def test_not_available(self):
        cap = Capability(
            id="CAP-IMPORT-BULK",
            name="Bulk Import",
            status=CapabilityStatus.FUTURE,
            feature_area="Learning",
        )
        assert cap.is_available() is False


class TestCapabilityRegistry:
    def _make_registry(self):
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
                    id="CAP-ROUTE-FIND",
                    name="Routing",
                    status=CapabilityStatus.COMPLETE,
                    feature_area="Routing",
                ),
                Capability(
                    id="CAP-IMPORT-BULK",
                    name="Bulk Import",
                    status=CapabilityStatus.FUTURE,
                    feature_area="Learning",
                ),
            ],
        )

    def test_get(self):
        reg = self._make_registry()
        assert reg.get("CAP-LEARN-SEARCH") is not None
        assert reg.get("CAP-NONEXIST") is None

    def test_available(self):
        reg = self._make_registry()
        assert len(reg.available()) == 2

    def test_by_feature_area(self):
        reg = self._make_registry()
        assert len(reg.by_feature_area("Learning")) == 2

    def test_feature_areas(self):
        reg = self._make_registry()
        assert reg.feature_areas() == ["Learning", "Routing"]


# ─── Workflow tests ──────────────────────────────────────────────────────


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


class TestGoal:
    def test_all_capabilities(self):
        goal = Goal(
            id="G-01-1",
            title="Test",
            category=GoalCategory.KNOWLEDGE,
            priority=GoalPriority.PRIMARY,
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
            ],
        )
        assert goal.all_capabilities_used() == {"CAP-LEARN-SEARCH", "CAP-LEARN-CREATE"}
        assert goal.all_capabilities_missing() == {"CAP-IMPORT-BULK"}


class TestPersonaWorkflowMapping:
    def test_all_capabilities_used(self):
        mapping = PersonaWorkflowMapping(
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
                        Workflow(
                            id="W-01-1-a",
                            title="WF",
                            capabilities_used=["CAP-LEARN-SEARCH"],
                        )
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
        assert mapping.all_capabilities_used() == {"CAP-LEARN-SEARCH", "CAP-ROUTE-FIND"}
        assert mapping.all_gaps() == {"CAP-IMPORT-BULK"}
        assert len(mapping.goals_by_priority(GoalPriority.PRIMARY)) == 1
