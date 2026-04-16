"""Shared YAML I/O for canonical core models."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from voice_of_agents.core.capability import CapabilityRegistry
from voice_of_agents.core.persona import Persona


class LoadError(Exception):
    def __init__(self, path: Path, errors: list[str]):
        self.path = path
        self.errors = errors
        super().__init__(f"Failed to load {path}: {'; '.join(errors)}")


def load_persona(path: Path) -> Persona:
    with open(path) as f:
        data = yaml.safe_load(f)
    try:
        return Persona(**data)
    except Exception as e:
        raise LoadError(path, [str(e)]) from e


def load_personas_dir(directory: Path) -> list[Persona]:
    """Load all P-*.yaml files, sorted by persona ID."""
    personas = []
    for p in sorted(directory.glob("P-*.yaml")):
        personas.append(load_persona(p))
    return sorted(personas, key=lambda x: x.id)


def save_persona(persona: Persona, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    name_slug = re.sub(r"[^a-z0-9]+", "-", persona.name.lower()).strip("-")
    path = directory / f"P-{persona.id:02d}-{name_slug}.yaml"
    with open(path, "w") as f:
        yaml.dump(persona.model_dump(mode="json"), f, default_flow_style=False, allow_unicode=True)
    return path


def load_capability_registry(path: Path) -> CapabilityRegistry:
    with open(path) as f:
        data = yaml.safe_load(f)
    try:
        return CapabilityRegistry(**data)
    except Exception as e:
        raise LoadError(path, [str(e)]) from e


def save_capability_registry(registry: CapabilityRegistry, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(registry.model_dump(mode="json"), f, default_flow_style=False, allow_unicode=True)
