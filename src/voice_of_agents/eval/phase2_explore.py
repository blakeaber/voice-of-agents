"""Phase 2: Adaptive persona exploration against the live product."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from voice_of_agents.core.persona import Persona
from voice_of_agents.eval.api import TargetAPI
from voice_of_agents.eval.browser import ExplorationGoal, explore_as_persona
from voice_of_agents.eval.config import VoAConfig
from voice_of_agents.eval.seed import seed_persona

logger = logging.getLogger(__name__)


def _load_goals_for_persona(persona: Persona, config: VoAConfig) -> list[ExplorationGoal]:
    """Load exploration goals from PersonaWorkflowMapping, or return empty list."""
    workflows_dir = config.workflows_path
    if not workflows_dir.exists():
        return []

    for wf_path in workflows_dir.glob(f"PWM-{persona.id:02d}-*.yaml"):
        try:
            data = yaml.safe_load(wf_path.read_text())
            goals = []
            for g in data.get("goals", []):
                vm = g.get("value_metrics") or {}
                goals.append(ExplorationGoal(
                    goal=g.get("title", ""),
                    trigger=g.get("trigger", ""),
                    success_definition=g.get("success_statement", ""),
                    efficiency_baseline=vm.get("time_saved", "") if isinstance(vm, dict) else "",
                ))
            return goals
        except Exception as e:
            logger.warning("Failed to load workflow mapping %s: %s", wf_path, e)

    return []


def explore_personas(personas: list[Persona], config: VoAConfig) -> None:
    """Run adaptive exploration for each persona against the target app."""
    api = TargetAPI(config.api_url)

    if not api.health_check():
        logger.error("Target API at %s is not healthy. Is it running?", config.api_url)
        return

    for persona in personas:
        logger.info("Exploring as %s (%s)...", persona.name, persona.id)

        seed_result = seed_persona(persona, api)
        session_token = seed_result.get("session_token")

        goals = _load_goals_for_persona(persona, config)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        result_dir = config.results_path / persona.slug / ts
        screenshot_dir = result_dir / "screenshots"

        results = asyncio.get_event_loop().run_until_complete(
            explore_as_persona(persona, config.target_url, session_token, screenshot_dir, goals)
        )
        result_dir.mkdir(parents=True, exist_ok=True)

        exploration_data = {
            "persona_id": persona.id,
            "persona_name": persona.name,
            "run_timestamp": ts,
            "target_url": config.target_url,
            "objectives_attempted": len(results),
            "objectives": [r.to_dict() for r in results],
        }

        log_path = result_dir / "002-exploration.yaml"
        log_path.write_text(yaml.dump(exploration_data, default_flow_style=False, sort_keys=False))
        logger.info("  Results written to %s", log_path)

        outcomes = {r.outcome for r in results}
        friction_count = sum(len(r.friction_points) for r in results)
        missing_count = sum(len(r.missing_capabilities) for r in results)
        logger.info(
            "  %s: %d objectives, outcomes=%s, %d friction points, %d missing capabilities",
            persona.id, len(results), outcomes, friction_count, missing_count,
        )
