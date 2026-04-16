"""Test data seeding for persona preconditions."""

from __future__ import annotations

import logging
import time

from voice_of_agents.contracts.personas import Persona
from voice_of_agents.explorer.api import TargetAPI

logger = logging.getLogger(__name__)


def seed_persona(persona: Persona, api: TargetAPI) -> dict:
    """Set up a persona's account and preconditions.

    Returns a dict with session info and any created resources.
    """
    email = f"{persona.id.lower()}@voa-test.dev"
    result: dict = {"email": email, "persona_id": persona.id}

    # Signup
    try:
        signup_data = api.signup(
            email=email,
            org_name=f"{persona.name}'s Org",
            display_name=persona.name,
        )
        result["user_id"] = signup_data.get("user_id")
        result["api_key"] = signup_data.get("api_key")
        result["session_token"] = signup_data.get("session_token")
        logger.info("Signed up %s (%s)", persona.name, persona.id)
    except Exception as e:
        # May already exist — try login with stored API key
        logger.info("Signup failed for %s (%s), attempting login...", persona.id, e)
        try:
            # Try to get session via a fresh signup with a different email suffix
            alt_email = f"{persona.id.lower()}-{int(time.time()) % 10000}@voa-test.dev"
            signup_data = api.signup(
                email=alt_email,
                org_name=f"{persona.name}'s Org",
                display_name=persona.name,
            )
            result["user_id"] = signup_data.get("user_id")
            result["api_key"] = signup_data.get("api_key")
            result["session_token"] = signup_data.get("session_token")
            result["email"] = alt_email
            logger.info("Created alternate account for %s: %s", persona.name, alt_email)
        except Exception as e2:
            logger.warning("Could not create account for %s: %s", persona.id, e2)
            return result

    # Set onboarding goals based on persona pain themes
    goals = _derive_goals(persona)
    if goals:
        try:
            api.save_onboarding_step("goals", {"goals": goals})
            result["goals"] = goals
        except Exception as e:
            logger.warning("Failed to set goals for %s: %s", persona.id, e)

    # Complete onboarding
    try:
        api.save_onboarding_step("complete", {})
    except Exception:
        pass

    return result


def _derive_goals(persona: Persona) -> list[str]:
    """Map persona attributes to onboarding goals."""
    goals = []

    # All personas benefit from knowledge management
    goals.append("knowledge")

    # Team users need delegation
    if persona.team_size > 1:
        goals.append("delegation")

    # Cost-sensitive personas want cost control
    if persona.voice.price_sensitivity == "high" or persona.income < 60000:
        goals.append("cost")

    # Check pain themes for workflow needs
    for pp in persona.pain_points:
        if pp.theme == "E":  # Governance
            if "delegation" not in goals:
                goals.append("delegation")
        elif pp.theme == "F":  # Integration
            if "workflows" not in goals:
                goals.append("workflows")

    return goals
