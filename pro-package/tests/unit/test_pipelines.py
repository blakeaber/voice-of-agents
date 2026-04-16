"""Tests for pipeline logic (prompt building, response parsing)."""

from pathlib import Path

import pytest

from voice_of_agents.models.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityStatus,
)
from voice_of_agents.models.persona import Persona, Segment, Tier
from voice_of_agents.pipelines.persona_pipeline import (
    PersonaGenerationRequest,
    PersonaPipeline,
    _extract_yaml_blocks,
)
from voice_of_agents.pipelines.workflow_pipeline import WorkflowPipeline
from voice_of_agents.pipelines.gap_analysis import GapAnalyzer
from voice_of_agents.models.workflow import (
    Goal,
    GoalCategory,
    GoalPriority,
    PersonaWorkflowMapping,
    Workflow,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestExtractYamlBlocks:
    def test_single_block(self):
        text = "Some text\n```yaml\nid: 1\nname: test\n```\nMore text"
        blocks = _extract_yaml_blocks(text)
        assert len(blocks) == 1
        assert "id: 1" in blocks[0]

    def test_multiple_blocks(self):
        text = "```yaml\nfirst: 1\n```\n\n```yaml\nsecond: 2\n```"
        blocks = _extract_yaml_blocks(text)
        assert len(blocks) == 2

    def test_no_blocks(self):
        text = "Just plain text without any YAML"
        blocks = _extract_yaml_blocks(text)
        assert len(blocks) == 0


class TestPersonaPipeline:
    def test_build_prompt(self, tmp_path):
        pipeline = PersonaPipeline(tmp_path / "personas")
        request = PersonaGenerationRequest(
            product_name="Test Product",
            product_description="A test product",
            industry="Technology",
            roles=["Developer", "Designer"],
            count=2,
        )
        prompt = pipeline.build_prompt(request)
        assert "Test Product" in prompt
        assert "Technology" in prompt
        assert "Developer" in prompt
        assert "Designer" in prompt

    def test_parse_valid_response(self, tmp_path):
        pipeline = PersonaPipeline(tmp_path / "personas")
        raw = """```yaml
- id: 1
  name: "Test User"
  role: "Developer"
  segment: "b2c"
  industry: "Technology"
  tier: "DEVELOPER"
```"""
        result = pipeline.parse_response(raw)
        assert result.ok
        assert len(result.personas) == 1
        assert result.personas[0].name == "Test User"

    def test_parse_invalid_response(self, tmp_path):
        pipeline = PersonaPipeline(tmp_path / "personas")
        raw = """```yaml
- id: 0
  name: ""
```"""
        result = pipeline.parse_response(raw)
        assert len(result.errors) > 0

    def test_next_id_empty(self, tmp_path):
        pipeline = PersonaPipeline(tmp_path / "personas")
        assert pipeline.next_id == 1

    def test_save_and_reload(self, tmp_path):
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        pipeline = PersonaPipeline(personas_dir)

        persona = Persona(
            id=1,
            name="Saved User",
            role="Tester",
            segment=Segment.B2C,
            industry="Testing",
            tier=Tier.FREE,
        )
        paths = pipeline.save_personas([persona])
        assert len(paths) == 1
        assert paths[0].exists()

        # Cache should be invalidated
        assert pipeline.next_id == 2


class TestWorkflowPipeline:
    def test_build_prompt(self, tmp_path):
        # Write a minimal registry
        import yaml

        reg = CapabilityRegistry(
            product="Test",
            capabilities=[
                Capability(
                    id="CAP-LEARN-SEARCH",
                    name="Search",
                    status=CapabilityStatus.COMPLETE,
                    feature_area="Learning",
                )
            ],
        )
        reg_path = tmp_path / "capabilities.yaml"
        with open(reg_path, "w") as f:
            yaml.dump(reg.model_dump(mode="json", exclude_none=True), f)

        pipeline = WorkflowPipeline(reg_path, tmp_path / "workflows")
        persona = Persona(
            id=1,
            name="Test",
            role="Tester",
            segment=Segment.B2C,
            industry="Testing",
            tier=Tier.DEVELOPER,
        )
        prompt = pipeline.build_prompt(persona)
        assert "Test" in prompt
        assert "CAP-LEARN-SEARCH" in prompt


class TestGapAnalyzer:
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
                    id="CAP-DELEG-CREATE",
                    name="Delegation",
                    status=CapabilityStatus.COMPLETE,
                    feature_area="Delegation",
                ),
            ],
        )

    def _make_mappings(self):
        return [
            PersonaWorkflowMapping(
                persona_id=1,
                persona_name="A",
                persona_tier=Tier.DEVELOPER,
                goals=[
                    Goal(
                        id="G-01-1",
                        title="G1",
                        category=GoalCategory.KNOWLEDGE,
                        priority=GoalPriority.PRIMARY,
                        workflows=[
                            Workflow(
                                id="W-01-1-a",
                                title="WF",
                                capabilities_used=["CAP-LEARN-SEARCH"],
                                capabilities_missing=["CAP-IMPORT-BULK"],
                            )
                        ],
                    )
                ],
            ),
            PersonaWorkflowMapping(
                persona_id=2,
                persona_name="B",
                persona_tier=Tier.TEAM,
                goals=[
                    Goal(
                        id="G-02-1",
                        title="G2",
                        category=GoalCategory.DELEGATION,
                        priority=GoalPriority.PRIMARY,
                        workflows=[
                            Workflow(
                                id="W-02-1-a",
                                title="WF2",
                                capabilities_used=["CAP-LEARN-SEARCH", "CAP-ROUTE-FIND"],
                                capabilities_missing=["CAP-IMPORT-BULK"],
                            )
                        ],
                    )
                ],
            ),
        ]

    def test_analyze(self):
        analyzer = GapAnalyzer(self._make_registry())
        report = analyzer.analyze(self._make_mappings())

        # CAP-LEARN-SEARCH used by both personas
        assert report.coverage["CAP-LEARN-SEARCH"].persona_count == 2
        # CAP-ROUTE-FIND used by 1
        assert report.coverage["CAP-ROUTE-FIND"].persona_count == 1
        # CAP-DELEG-CREATE unused
        assert "CAP-DELEG-CREATE" in report.unused_capabilities
        # Gap: CAP-IMPORT-BULK
        assert "CAP-IMPORT-BULK" in report.gaps
        assert report.gaps["CAP-IMPORT-BULK"].severity == 2

    def test_utilization_rate(self):
        analyzer = GapAnalyzer(self._make_registry())
        report = analyzer.analyze(self._make_mappings())
        # 2 of 3 capabilities used
        assert report.utilization_rate == pytest.approx(2 / 3, abs=0.01)

    def test_coverage_by_feature_area(self):
        analyzer = GapAnalyzer(self._make_registry())
        areas = analyzer.coverage_by_feature_area(self._make_mappings())
        assert "Learning" in areas
        assert areas["Learning"]["used"] == 1
        assert areas["Learning"]["total"] == 1

    def test_priority_coverage(self):
        analyzer = GapAnalyzer(self._make_registry())
        pc = analyzer.priority_coverage(self._make_mappings())
        assert "CAP-LEARN-SEARCH" in pc["primary"]
        assert len(pc["secondary"]) == 0
