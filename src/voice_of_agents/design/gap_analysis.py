"""Gap analysis engine — identifies missing capabilities across all persona workflows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from jinja2 import Template

from voice_of_agents.core.backlog import BacklogItem
from voice_of_agents.core.capability import CapabilityRegistry
from voice_of_agents.core.persona import Persona
from voice_of_agents.design.workflow import GoalPriority, PersonaWorkflowMapping
from voice_of_agents.design.prompts import GAP_ANALYSIS_PROMPT


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
        return len(set(self.persona_ids))


@dataclass
class GapAnalysisReport:
    """Complete gap analysis output."""

    coverage: dict[str, CapabilityCoverage] = field(default_factory=dict)
    gaps: dict[str, GapEntry] = field(default_factory=dict)
    unused_capabilities: list[str] = field(default_factory=list)
    feature_recommendations: list[BacklogItem] = field(default_factory=list)

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


_EFFORT_MAP = {"trivial": "trivial", "small": "small", "medium": "medium"}


class GapAnalyzer:
    """Analyzes gaps between persona workflows and platform capabilities."""

    def __init__(self, registry: CapabilityRegistry):
        self.registry = registry

    def analyze(
        self,
        mappings: list[PersonaWorkflowMapping],
        personas: list[Persona] | None = None,
    ) -> GapAnalysisReport:
        report = GapAnalysisReport()

        used_caps: defaultdict[str, CapabilityCoverage] = defaultdict(
            lambda: CapabilityCoverage(capability_id="")
        )
        gap_caps: defaultdict[str, GapEntry] = defaultdict(
            lambda: GapEntry(capability_id="")
        )

        for mapping in mappings:
            for goal in mapping.goals:
                for wf in goal.workflows:
                    for cap_id in wf.capabilities_used:
                        if cap_id not in used_caps:
                            used_caps[cap_id] = CapabilityCoverage(capability_id=cap_id)
                        used_caps[cap_id].persona_ids.append(mapping.persona_id)
                        used_caps[cap_id].workflow_count += 1

                    for cap_id in wf.capabilities_missing:
                        if cap_id not in gap_caps:
                            gap_caps[cap_id] = GapEntry(capability_id=cap_id)
                        gap_caps[cap_id].persona_ids.append(mapping.persona_id)
                        gap_caps[cap_id].goal_ids.append(goal.id)

        report.coverage = dict(used_caps)
        report.gaps = dict(gap_caps)

        all_cap_ids = {c.id for c in self.registry.capabilities if c.is_available()}
        used_cap_ids = set(used_caps.keys())
        report.unused_capabilities = sorted(all_cap_ids - used_cap_ids)

        return report

    def build_recommendation_prompt(
        self,
        report: GapAnalysisReport,
        product_name: str,
    ) -> str:
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

    def parse_recommendations(
        self,
        raw_yaml: str,
        report: GapAnalysisReport,
    ) -> list[BacklogItem]:
        """Parse LLM-generated feature recommendations into BacklogItem objects."""
        import yaml as _yaml

        items: list[BacklogItem] = []
        try:
            data = _yaml.safe_load(raw_yaml)
        except Exception:
            return items

        entries = data if isinstance(data, list) else [data]
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            complexity = entry.get("complexity", "medium")
            effort = _EFFORT_MAP.get(complexity, "medium")
            persona_ids = entry.get("personas_benefited", [])
            item = BacklogItem(
                id=entry.get("id", f"FR-{i+1:02d}"),
                title=entry.get("title", "Untitled"),
                description=entry.get("description", ""),
                source="design",
                effort=effort,
                extends_capability=entry.get("extends_capability"),
                value_statement=entry.get("value_statement"),
                personas=persona_ids,
            )
            items.append(item)

        report.feature_recommendations = items
        return items

    def coverage_by_feature_area(
        self,
        mappings: list[PersonaWorkflowMapping],
    ) -> dict[str, dict]:
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
