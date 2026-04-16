"""Phase 1: Generate personas from target app analysis."""

from __future__ import annotations

import logging

from voice_of_agents.eval.config import VoAConfig
from voice_of_agents.contracts.personas import Persona, Objective, PainPoint, Voice, save_persona

logger = logging.getLogger(__name__)


def generate_personas(config: VoAConfig) -> list[Persona]:
    """Analyze the target app and generate starter personas.

    This is a bootstrap function — generates a minimal set of personas
    spanning different user types, tiers, and pain themes. Real persona
    development should be done manually with domain expertise.
    """
    # For now, generate a minimal starter set
    # A full implementation would crawl the target app to understand features
    starters = [
        Persona(
            id="UXW-01",
            name="Solo Professional",
            role="Domain Expert",
            industry="Consulting",
            experience_years=10,
            income=80000,
            team_size=1,
            tier="DEVELOPER",
            objectives=[
                Objective(
                    id="OBJ-01",
                    goal="Capture and retrieve professional knowledge",
                    trigger="Working on a task similar to one handled before",
                    success_definition="Past decisions surface automatically within 60 seconds",
                    efficiency_baseline="Manual search through files (30+ minutes)",
                    target_efficiency="Automatic retrieval (<60 seconds)",
                ),
            ],
            pain_points=[
                PainPoint(description="Can't find prior decisions when needed", severity=8, theme="A"),
            ],
            trust_requirements=["Must surface my own work, not generic AI"],
            voice=Voice(skepticism="moderate", motivation="efficiency"),
        ),
        Persona(
            id="UXW-02",
            name="Team Leader",
            role="Department Manager",
            industry="Technology",
            experience_years=12,
            income=120000,
            team_size=8,
            tier="TEAM",
            objectives=[
                Objective(
                    id="OBJ-01",
                    goal="Route questions to the right expert on my team",
                    trigger="Team member asks a question I can't answer",
                    success_definition="Question reaches the right person without my involvement",
                    efficiency_baseline="Manual forwarding via email/Slack (20+ messages/day)",
                    target_efficiency="Automatic routing (<5 manual interventions/day)",
                ),
            ],
            pain_points=[
                PainPoint(description="I'm the bottleneck for all team questions", severity=9, theme="B"),
            ],
            trust_requirements=["Must route to verified experts, not guess"],
            voice=Voice(skepticism="high", motivation="efficiency"),
        ),
    ]

    for persona in starters:
        save_persona(persona, config.personas_path)
        logger.info("Generated persona: %s — %s", persona.id, persona.name)

    return starters
