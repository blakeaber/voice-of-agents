"""YAML I/O for workflow mappings (persona and capability I/O lives in core/io.py)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from voice_of_agents.design.workflow import PersonaWorkflowMapping


class LoadError(Exception):
    def __init__(self, path: Path, errors: list[str]):
        self.path = path
        self.errors = errors
        super().__init__(f"{path}: {'; '.join(errors)}")


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise LoadError(path, [f"Expected a YAML mapping, got {type(data).__name__}"])
    return data


def load_workflow_mapping(path: Path) -> PersonaWorkflowMapping:
    data = _load_yaml(path)
    try:
        return PersonaWorkflowMapping(**data)
    except ValidationError as e:
        raise LoadError(path, [str(err) for err in e.errors()]) from e


def load_workflow_mappings_dir(directory: Path) -> list[PersonaWorkflowMapping]:
    mappings = []
    for path in sorted(directory.glob("*.yaml")):
        mappings.append(load_workflow_mapping(path))
    return sorted(mappings, key=lambda m: m.persona_id)


def save_workflow_mapping(mapping: PersonaWorkflowMapping, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    slug = mapping.persona_name.lower().replace(" ", "-").replace(".", "")
    filename = f"PWM-{mapping.persona_id:02d}-{slug}.yaml"
    path = directory / filename
    data = mapping.model_dump(mode="json", exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return path
