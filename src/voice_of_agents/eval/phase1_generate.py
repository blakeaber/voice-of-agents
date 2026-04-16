"""Phase 1: Generate starter personas from target app analysis."""

from __future__ import annotations

import logging

from voice_of_agents.core.io import save_persona
from voice_of_agents.core.pain import PainPoint, PainTheme
from voice_of_agents.core.persona import Persona, VoiceProfile
from voice_of_agents.eval.config import VoAConfig

logger = logging.getLogger(__name__)


def generate_personas(config: VoAConfig) -> list[Persona]:
    """Generate a minimal starter set of canonical Personas.

    This is a bootstrap function — real persona development should be done
    manually with domain expertise. A full implementation would crawl the
    target app to understand features.
    """
    starters = [
        Persona(
            id=1,
            name="Solo Professional",
            role="Domain Expert",
            industry="Consulting",
            segment="b2c",
            tier="DEVELOPER",
            org_size=1,
            income=80000,
            experience_years=10,
            pain_points=[
                PainPoint(
                    description="Can't find prior decisions when needed",
                    impact="severity 8/10, daily",
                ),
            ],
            pain_themes=[PainTheme(theme="A", intensity="HIGH")],
            trust_requirements=["Must surface my own work, not generic AI"],
            voice=VoiceProfile(skepticism="moderate", motivation="efficiency"),
        ),
        Persona(
            id=2,
            name="Team Leader",
            role="Department Manager",
            industry="Technology",
            segment="b2b",
            tier="TEAM",
            org_size=8,
            income=120000,
            experience_years=12,
            pain_points=[
                PainPoint(
                    description="I'm the bottleneck for all team questions",
                    impact="severity 9/10, daily",
                ),
            ],
            pain_themes=[PainTheme(theme="B", intensity="CRITICAL")],
            trust_requirements=["Must route to verified experts, not guess"],
            voice=VoiceProfile(skepticism="high", motivation="efficiency"),
        ),
    ]

    for persona in starters:
        save_persona(persona, config.personas_path)
        logger.info("Generated persona: %s — %s", persona.id, persona.name)

    return starters
