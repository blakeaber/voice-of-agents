"""Pydantic models for persona workflow mappings."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from voice_of_agents.models.persona import Tier


class GoalCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    DELEGATION = "delegation"
    GOVERNANCE = "governance"
    MARKETPLACE = "marketplace"
    AUTOMATION = "automation"
    COLLABORATION = "collaboration"


class GoalPriority(str, Enum):
    PRIMARY = "primary"          # Day-1 value
    SECONDARY = "secondary"      # Month-1 expansion
    ASPIRATIONAL = "aspirational"  # Quarter-1 advanced usage


class Complexity(str, Enum):
    TRIVIAL = "trivial"
    SMALL = "small"
    MEDIUM = "medium"


class WorkflowStep(BaseModel):
    seq: int = Field(ge=1)
    action: str
    capability_id: str
    api_endpoint: Optional[str] = None
    ui_page: Optional[str] = None
    success_criteria: Optional[str] = None
    friction_risk: Optional[str] = None


class Workflow(BaseModel):
    id: str = Field(pattern=r"^W-\d+-\d+-[a-z]$")
    title: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[WorkflowStep] = Field(default_factory=list)
    capabilities_used: list[str] = Field(default_factory=list)
    capabilities_missing: list[str] = Field(default_factory=list)

    def uses_capability(self, cap_id: str) -> bool:
        return cap_id in self.capabilities_used

    def has_gaps(self) -> bool:
        return len(self.capabilities_missing) > 0


class ValueMetrics(BaseModel):
    time_saved: Optional[str] = None
    error_reduction: Optional[str] = None
    cost_impact: Optional[str] = None


class Goal(BaseModel):
    id: str = Field(pattern=r"^G-\d+-\d+$")
    title: str
    category: GoalCategory
    priority: GoalPriority
    trigger: Optional[str] = None
    success_statement: Optional[str] = None
    value_metrics: Optional[ValueMetrics] = None
    workflows: list[Workflow] = Field(default_factory=list)

    def all_capabilities_used(self) -> set[str]:
        caps: set[str] = set()
        for wf in self.workflows:
            caps.update(wf.capabilities_used)
        return caps

    def all_capabilities_missing(self) -> set[str]:
        gaps: set[str] = set()
        for wf in self.workflows:
            gaps.update(wf.capabilities_missing)
        return gaps


class FeatureRecommendation(BaseModel):
    id: str = Field(pattern=r"^FR-\d+-\d+$")
    title: str
    description: Optional[str] = None
    complexity: Complexity
    extends_capability: Optional[str] = None
    personas_benefited: list[int] = Field(default_factory=list)
    value_statement: Optional[str] = None


class PersonaWorkflowMapping(BaseModel):
    """Complete workflow mapping for a single persona."""

    persona_id: int
    persona_name: str
    persona_tier: Tier
    goals: list[Goal] = Field(default_factory=list)
    feature_recommendations: list[FeatureRecommendation] = Field(default_factory=list)

    def all_capabilities_used(self) -> set[str]:
        caps: set[str] = set()
        for goal in self.goals:
            caps.update(goal.all_capabilities_used())
        return caps

    def all_gaps(self) -> set[str]:
        gaps: set[str] = set()
        for goal in self.goals:
            gaps.update(goal.all_capabilities_missing())
        return gaps

    def goals_by_priority(self, priority: GoalPriority) -> list[Goal]:
        return [g for g in self.goals if g.priority == priority]
