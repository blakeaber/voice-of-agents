"""Test data seeding for persona preconditions."""

from __future__ import annotations

import logging
import time

from voice_of_agents.core.persona import Persona
from voice_of_agents.eval.api import TargetAPI

logger = logging.getLogger(__name__)


def seed_persona(persona: Persona, api: TargetAPI) -> dict:
    """Set up a persona's account and preconditions.

    Returns a dict with session info and any created resources.
    """
    email = f"{persona.id:02d}@voa-test.dev"
    result: dict = {"email": email, "persona_id": persona.id}

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
        logger.info("Signup failed for %s (%s), attempting alternate...", persona.id, e)
        try:
            alt_email = f"{persona.id:02d}-{int(time.time()) % 10000}@voa-test.dev"
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

    goals = _derive_goals(persona)
    if goals:
        try:
            api.save_onboarding_step("goals", {"goals": goals})
            result["goals"] = goals
        except Exception as e:
            logger.warning("Failed to set goals for %s: %s", persona.id, e)

    try:
        api.save_onboarding_step("complete", {})
    except Exception:
        pass

    return result


def _derive_goals(persona: Persona) -> list[str]:
    """Map persona attributes to onboarding goals."""
    goals = ["knowledge"]

    if persona.org_size > 1:
        goals.append("delegation")

    income = persona.income or 0
    if persona.voice.price_sensitivity == "high" or income < 60000:
        goals.append("cost")

    for pt in persona.pain_themes:
        if pt.theme.value == "E" and "delegation" not in goals:
            goals.append("delegation")
        elif pt.theme.value == "F" and "workflows" not in goals:
            goals.append("workflows")

    return goals
