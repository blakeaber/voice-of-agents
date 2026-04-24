"""Cross-reference validation between personas, capabilities, and workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from voice_of_agents.core.capability import CapabilityRegistry
from voice_of_agents.core.persona import Persona
from voice_of_agents.design.workflow import PersonaWorkflowMapping


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def merge(self, other: ValidationResult) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"{len(self.errors)} error(s):")
            for e in self.errors:
                lines.append(f"  ERROR: {e}")
        if self.warnings:
            lines.append(f"{len(self.warnings)} warning(s):")
            for w in self.warnings:
                lines.append(f"  WARN: {w}")
        if self.ok and not self.warnings:
            lines.append("All validations passed.")
        return "\n".join(lines)


def validate_workflow_against_registry(
    mapping: PersonaWorkflowMapping,
    registry: CapabilityRegistry,
) -> ValidationResult:
    result = ValidationResult()
    known_ids = {c.id for c in registry.capabilities}

    for goal in mapping.goals:
        for wf in goal.workflows:
            for step in wf.steps:
                if step.capability_id not in known_ids:
                    result.error(
                        f"Persona {mapping.persona_id} / {wf.id} step {step.seq}: "
                        f"capability '{step.capability_id}' not in registry"
                    )

            for cap_id in wf.capabilities_used:
                if cap_id not in known_ids:
                    result.error(
                        f"Persona {mapping.persona_id} / {wf.id}: "
                        f"capabilities_used '{cap_id}' not in registry"
                    )

            for cap_id in wf.capabilities_missing:
                if cap_id in known_ids:
                    cap = registry.get(cap_id)
                    if cap and cap.is_available():
                        result.warn(
                            f"Persona {mapping.persona_id} / {wf.id}: "
                            f"'{cap_id}' listed as missing but is available in registry"
                        )

    return result


def validate_workflow_against_persona(
    mapping: PersonaWorkflowMapping,
    persona: Persona,
) -> ValidationResult:
    result = ValidationResult()

    if mapping.persona_id != persona.id:
        result.error(f"Persona ID mismatch: mapping={mapping.persona_id}, persona={persona.id}")

    if mapping.persona_tier.value != persona.tier.value:
        result.warn(
            f"Persona {persona.id}: tier mismatch "
            f"(mapping={mapping.persona_tier.value}, persona={persona.tier.value})"
        )

    if len(mapping.goals) < 2:
        result.warn(f"Persona {persona.id}: only {len(mapping.goals)} goal(s), expected >= 2")

    primary_goals = [g for g in mapping.goals if g.priority.value == "primary"]
    if not primary_goals:
        result.error(f"Persona {persona.id}: no primary goals defined")

    if persona.segment.value == "b2b":
        categories = {g.category.value for g in mapping.goals}
        if not categories & {"governance", "delegation", "collaboration"}:
            result.warn(f"Persona {persona.id} (B2B): no governance/delegation/collaboration goals")

    return result


def validate_all(
    personas: list[Persona],
    mappings: list[PersonaWorkflowMapping],
    registry: CapabilityRegistry,
) -> ValidationResult:
    result = ValidationResult()
    persona_map = {p.id: p for p in personas}

    for mapping in mappings:
        persona = persona_map.get(mapping.persona_id)
        if not persona:
            result.error(f"Workflow mapping for persona {mapping.persona_id}: persona not found")
            continue

        result.merge(validate_workflow_against_registry(mapping, registry))
        result.merge(validate_workflow_against_persona(mapping, persona))

    mapped_ids = {m.persona_id for m in mappings}
    for persona in personas:
        if persona.id not in mapped_ids:
            result.warn(f"Persona {persona.id} ({persona.name}): no workflow mapping found")

    return result
