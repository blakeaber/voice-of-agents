"""YAML I/O utilities for loading and saving personas, capabilities, and workflows."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from voice_of_agents.models.capability import CapabilityRegistry
from voice_of_agents.models.persona import Persona
from voice_of_agents.models.workflow import PersonaWorkflowMapping

T = TypeVar("T", bound=BaseModel)


class LoadError(Exception):
    """Raised when a YAML file fails to load or validate."""

    def __init__(self, path: Path, errors: list[str]):
        self.path = path
        self.errors = errors
        super().__init__(f"{path}: {'; '.join(errors)}")


def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return the parsed dict."""
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise LoadError(path, [f"Expected a YAML mapping, got {type(data).__name__}"])
    return data


def load_persona(path: Path) -> Persona:
    """Load and validate a persona YAML file."""
    data = _load_yaml(path)
    try:
        return Persona(**data)
    except ValidationError as e:
        raise LoadError(path, [str(err) for err in e.errors()]) from e


def load_personas_dir(directory: Path) -> list[Persona]:
    """Load all persona YAML files from a directory, sorted by ID."""
    personas = []
    for path in sorted(directory.glob("*.yaml")):
        personas.append(load_persona(path))
    return sorted(personas, key=lambda p: p.id)


def load_capability_registry(path: Path) -> CapabilityRegistry:
    """Load and validate a capability registry YAML file."""
    data = _load_yaml(path)
    try:
        return CapabilityRegistry(**data)
    except ValidationError as e:
        raise LoadError(path, [str(err) for err in e.errors()]) from e


def load_workflow_mapping(path: Path) -> PersonaWorkflowMapping:
    """Load and validate a persona workflow mapping YAML file."""
    data = _load_yaml(path)
    try:
        return PersonaWorkflowMapping(**data)
    except ValidationError as e:
        raise LoadError(path, [str(err) for err in e.errors()]) from e


def load_workflow_mappings_dir(directory: Path) -> list[PersonaWorkflowMapping]:
    """Load all workflow mapping YAML files from a directory."""
    mappings = []
    for path in sorted(directory.glob("*.yaml")):
        mappings.append(load_workflow_mapping(path))
    return sorted(mappings, key=lambda m: m.persona_id)


def save_yaml(model: BaseModel, path: Path) -> None:
    """Save a Pydantic model as a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json", exclude_none=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def save_persona(persona: Persona, directory: Path) -> Path:
    """Save a persona to a YAML file, using naming convention."""
    slug = persona.name.lower().replace(" ", "-").replace(".", "")
    filename = f"P-{persona.id:02d}-{slug}.yaml"
    path = directory / filename
    save_yaml(persona, path)
    return path


def save_workflow_mapping(mapping: PersonaWorkflowMapping, directory: Path) -> Path:
    """Save a workflow mapping to a YAML file."""
    slug = mapping.persona_name.lower().replace(" ", "-").replace(".", "")
    filename = f"PWM-{mapping.persona_id:02d}-{slug}.yaml"
    path = directory / filename
    save_yaml(mapping, path)
    return path
