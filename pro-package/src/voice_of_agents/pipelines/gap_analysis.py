"""Gap analysis engine — identifies missing capabilities across all persona workflows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from jinja2 import Template

from voice_of_agents.models.capability import CapabilityRegistry, CapabilityStatus
from voice_of_agents.models.persona import Persona
from voice_of_agents.models.workflow import (
    FeatureRecommendation,
    GoalPriority,
    PersonaWorkflowMapping,
)
from voice_of_agents.pipelines.prompts import GAP_ANALYSIS_PROMPT


@dataclass
class CapabilityCoverage:
    """How well a capability is exercised across personas."""

    capability_id: str
    persona_ids: list[int] = field(default_factory=list)
    workflow_count: int = 0

    @property
    def persona_count(self) -> int:
        return len(set(self.persona_ids))


@dataclass
class GapEntry:
    """A capability needed but not available."""

    capability_id: str
    persona_ids: list[int] = field(default_factory=list)
    goal_ids: list[str] = field(default_factory=list)

    @property
    def severity(self) -> int:
        """Higher = more personas affected."""
        return len(set(self.persona_ids))


@dataclass
class GapAnalysisReport:
    """Complete gap analysis output."""

    coverage: dict[str, CapabilityCoverage] = field(default_factory=dict)
    gaps: dict[str, GapEntry] = field(default_factory=dict)
    unused_capabilities: list[str] = field(default_factory=list)
    feature_recommendations: list[FeatureRecommendation] = field(default_factory=list)

    @property
    def total_capabilities(self) -> int:
        return len(self.coverage) + len(self.unused_capabilities)

    @property
    def utilized_capabilities(self) -> int:
        return len(self.coverage)

    @property
    def utilization_rate(self) -> float:
        total = self.total_capabilities
        return self.utilized_capabilities / total if total else 0.0

    def gaps_by_severity(self) -> list[GapEntry]:
        return sorted(self.gaps.values(), key=lambda g: g.severity, reverse=True)

    def summary(self) -> str:
        lines = [
            f"Capability utilization: {self.utilized_capabilities}/{self.total_capabilities} "
            f"({self.utilization_rate:.0%})",
            f"Gaps identified: {len(self.gaps)}",
            f"Unused capabilities: {len(self.unused_capabilities)}",
        ]
        if self.gaps:
            lines.append("\nTop gaps by persona impact:")
            for gap in self.gaps_by_severity()[:10]:
                lines.append(
                    f"  {gap.capability_id}: {gap.severity} persona(s) — "
                    f"personas {sorted(set(gap.persona_ids))}"
                )
        if self.unused_capabilities:
            lines.append(f"\nUnused capabilities: {', '.join(self.unused_capabilities)}")
        return "\n".join(lines)


class GapAnalyzer:
    """Analyzes gaps between persona workflows and platform capabilities."""

    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def analyze(
        self,
        mappings: list[PersonaWorkflowMapping],
        personas: list[Persona] | None = None,
    ) -> GapAnalysisReport:
        """Run full gap analysis across all workflow mappings."""
        report = GapAnalysisReport()

        # Track capability usage
        used_caps: defaultdict[str, CapabilityCoverage] = defaultdict(
            lambda: CapabilityCoverage(capability_id="")
        )
        gap_caps: defaultdict[str, GapEntry] = defaultdict(
            lambda: GapEntry(capability_id="")
        )

        for mapping in mappings:
            for goal in mapping.goals:
                for wf in goal.workflows:
                    # Track used capabilities
                    for cap_id in wf.capabilities_used:
                        if cap_id not in used_caps:
                            used_caps[cap_id] = CapabilityCoverage(capability_id=cap_id)
                        used_caps[cap_id].persona_ids.append(mapping.persona_id)
                        used_caps[cap_id].workflow_count += 1

                    # Track missing capabilities
                    for cap_id in wf.capabilities_missing:
                        if cap_id not in gap_caps:
                            gap_caps[cap_id] = GapEntry(capability_id=cap_id)
                        gap_caps[cap_id].persona_ids.append(mapping.persona_id)
                        gap_caps[cap_id].goal_ids.append(goal.id)

        report.coverage = dict(used_caps)
        report.gaps = dict(gap_caps)

        # Find unused capabilities
        all_cap_ids = {c.id for c in self.registry.capabilities if c.is_available()}
        used_cap_ids = set(used_caps.keys())
        report.unused_capabilities = sorted(all_cap_ids - used_cap_ids)

        return report

    def build_recommendation_prompt(
        self,
        report: GapAnalysisReport,
        product_name: str,
    ) -> str:
        """Build prompt for LLM-assisted feature recommendation generation."""
        gaps_dict = {
            gap_id: sorted(set(entry.persona_ids))
            for gap_id, entry in report.gaps.items()
        }

        template = Template(GAP_ANALYSIS_PROMPT)
        return template.render(
            product_name=product_name,
            capabilities=[c for c in self.registry.capabilities],
            gaps=gaps_dict,
        )

    def coverage_by_feature_area(
        self,
        mappings: list[PersonaWorkflowMapping],
    ) -> dict[str, dict]:
        """Summarize capability coverage grouped by feature area."""
        report = self.analyze(mappings)
        areas: dict[str, dict] = {}

        for cap in self.registry.capabilities:
            area = cap.feature_area
            if area not in areas:
                areas[area] = {"total": 0, "used": 0, "capabilities": []}

            areas[area]["total"] += 1
            coverage = report.coverage.get(cap.id)
            if coverage:
                areas[area]["used"] += 1
                areas[area]["capabilities"].append({
                    "id": cap.id,
                    "name": cap.name,
                    "persona_count": coverage.persona_count,
                })
            else:
                areas[area]["capabilities"].append({
                    "id": cap.id,
                    "name": cap.name,
                    "persona_count": 0,
                })

        return areas

    def priority_coverage(
        self,
        mappings: list[PersonaWorkflowMapping],
    ) -> dict[str, set[str]]:
        """Which capabilities are used at each priority level."""
        result: dict[str, set[str]] = {
            "primary": set(),
            "secondary": set(),
            "aspirational": set(),
        }
        for mapping in mappings:
            for goal in mapping.goals:
                for wf in goal.workflows:
                    result[goal.priority.value].update(wf.capabilities_used)
        return result
