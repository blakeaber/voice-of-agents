"""Pipeline for generating new personas from market/industry data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import yaml
from jinja2 import Template
from pydantic import ValidationError

from voice_of_agents.core.persona import Persona, PersonaMetadata
from voice_of_agents.core.io import load_personas_dir, save_persona
from voice_of_agents.design.prompts import PERSONA_GENERATION_PROMPT


@dataclass
class PersonaGenerationRequest:
    product_name: str
    product_description: str
    industry: str
    roles: list[str]
    segment: str = "b2c"
    org_size_range: str = "1-10"
    count: int = 3


@dataclass
class PersonaGenerationResult:
    personas: list[Persona] = field(default_factory=list)
    prompt_used: str = ""
    raw_response: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0 and len(self.personas) > 0


class PersonaPipeline:
    """Generates personas using LLM + validation."""

    def __init__(self, personas_dir: Path):
        self.personas_dir = personas_dir
        self._existing: Optional[list[Persona]] = None

    @property
    def existing_personas(self) -> list[Persona]:
        if self._existing is None:
            if self.personas_dir.exists():
                self._existing = load_personas_dir(self.personas_dir)
            else:
                self._existing = []
        return self._existing

    @property
    def next_id(self) -> int:
        if not self.existing_personas:
            return 1
        return max(p.id for p in self.existing_personas) + 1

    def build_prompt(self, request: PersonaGenerationRequest) -> str:
        template = Template(PERSONA_GENERATION_PROMPT)
        return template.render(
            product_name=request.product_name,
            product_description=request.product_description,
            industry=request.industry,
            org_size_range=request.org_size_range,
            roles=request.roles,
            segment=request.segment,
            count=request.count,
            existing_personas=self.existing_personas,
            next_id=self.next_id,
            today=date.today().isoformat(),
        )

    def parse_response(self, raw_yaml: str) -> PersonaGenerationResult:
        result = PersonaGenerationResult(raw_response=raw_yaml)

        yaml_blocks = _extract_yaml_blocks(raw_yaml)
        if not yaml_blocks:
            yaml_blocks = [raw_yaml]

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
                    persona = Persona(**item)
                    result.personas.append(persona)
                except ValidationError as e:
                    result.errors.append(f"Validation error: {e}")

        return result

    def save_personas(self, personas: list[Persona]) -> list[Path]:
        paths = []
        for persona in personas:
            if persona.metadata.source != "generated":
                persona.metadata = PersonaMetadata(
                    source="generated",
                    created_at=date.today().isoformat(),
                )
            path = save_persona(persona, self.personas_dir)
            paths.append(path)
        self._existing = None
        return paths

    def generate_prompt_only(self, request: PersonaGenerationRequest) -> str:
        return self.build_prompt(request)


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
