"""Pipeline for generating workflow mappings from personas + capability registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from jinja2 import Template
from pydantic import ValidationError

from voice_of_agents.core.capability import CapabilityRegistry
from voice_of_agents.core.io import load_capability_registry
from voice_of_agents.core.persona import Persona
from voice_of_agents.design.workflow import Goal, PersonaWorkflowMapping
from voice_of_agents.design.io import load_workflow_mapping, save_workflow_mapping
from voice_of_agents.design.prompts import WORKFLOW_GENERATION_PROMPT


@dataclass
class WorkflowGenerationResult:
    mapping: Optional[PersonaWorkflowMapping] = None
    new_goals: list[Goal] = field(default_factory=list)
    prompt_used: str = ""
    raw_response: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


class WorkflowPipeline:
    """Generates workflow mappings for personas against a capability registry."""

    def __init__(self, registry_path: Path, workflows_dir: Path):
        self.registry_path = registry_path
        self.workflows_dir = workflows_dir
        self._registry: Optional[CapabilityRegistry] = None

    @property
    def registry(self) -> CapabilityRegistry:
        if self._registry is None:
            self._registry = load_capability_registry(self.registry_path)
        return self._registry

    def build_prompt(
        self,
        persona: Persona,
        existing_mapping: Optional[PersonaWorkflowMapping] = None,
        goal_count: int = 2,
    ) -> str:
        persona_yaml = yaml.dump(
            persona.model_dump(mode="json", exclude_none=True),
            default_flow_style=False,
        )

        existing_goals = existing_mapping.goals if existing_mapping else []
        next_seq = max((int(g.id.split("-")[-1]) for g in existing_goals), default=0) + 1

        template = Template(WORKFLOW_GENERATION_PROMPT)
        return template.render(
            persona_name=persona.name,
            persona_id=persona.id,
            persona_role=persona.role,
            persona_industry=persona.industry,
            persona_yaml=persona_yaml,
            capabilities=[c for c in self.registry.capabilities],
            existing_goals=existing_goals,
            goal_count=goal_count,
            next_goal_seq=next_seq,
        )

    def parse_response(
        self,
        raw_yaml: str,
        persona: Persona,
        existing_mapping: Optional[PersonaWorkflowMapping] = None,
    ) -> WorkflowGenerationResult:
        result = WorkflowGenerationResult(raw_response=raw_yaml)

        yaml_blocks = _extract_yaml_blocks(raw_yaml)
        if not yaml_blocks:
            yaml_blocks = [raw_yaml]

        new_goals: list[Goal] = []
        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError as e:
                result.errors.append(f"YAML parse error: {e}")
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    result.errors.append(f"Expected dict, got {type(item).__name__}")
                    continue
                try:
                    goal = Goal(**item)
                    new_goals.append(goal)
                except ValidationError as e:
                    result.errors.append(f"Goal validation error: {e}")

        result.new_goals = new_goals

        if existing_mapping:
            all_goals = list(existing_mapping.goals) + new_goals
            result.mapping = PersonaWorkflowMapping(
                persona_id=persona.id,
                persona_name=persona.name,
                persona_tier=persona.tier,
                goals=all_goals,
                feature_recommendations=list(existing_mapping.feature_recommendations),
            )
        else:
            result.mapping = PersonaWorkflowMapping(
                persona_id=persona.id,
                persona_name=persona.name,
                persona_tier=persona.tier,
                goals=new_goals,
            )

        return result

    def load_existing_mapping(self, persona: Persona) -> Optional[PersonaWorkflowMapping]:
        slug = persona.name.lower().replace(" ", "-").replace(".", "")
        path = self.workflows_dir / f"PWM-{persona.id:02d}-{slug}.yaml"
        if path.exists():
            return load_workflow_mapping(path)
        return None

    def save_mapping(self, mapping: PersonaWorkflowMapping) -> Path:
        return save_workflow_mapping(mapping, self.workflows_dir)


def _extract_yaml_blocks(text: str) -> list[str]:
    blocks = []
    in_block = False
    current: list[str] = []

    for line in text.split("\n"):
        if line.strip().startswith("```yaml") or line.strip().startswith("```yml"):
            in_block = True
            current = []
        elif line.strip() == "```" and in_block:
            in_block = False
            if current:
                blocks.append("\n".join(current))
        elif in_block:
            current.append(line)

    return blocks
