"""Full pipeline orchestrator: runs all 4 research stages in sequence with resumability."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from voice_of_agents.research.config import ResearchConfig
from voice_of_agents.research.models import (
    JourneyRedesignInput,
    PersonaResearchInput,
    WorkflowResearchInput,
)
from voice_of_agents.research.session import ResearchSession
from voice_of_agents.research.journey_redesign import run_journey_redesign
from voice_of_agents.research.personas_from_research import run_personas_from_research
from voice_of_agents.research.product_research import run_product_research
from voice_of_agents.research.workflows_from_interviews import run_workflows_from_interviews


async def run_full_pipeline(
    config: ResearchConfig,
    journey_redesign_config: Optional[dict] = None,
    session_path: Optional[Path] = None,
    existing_session: Optional[ResearchSession] = None,
) -> ResearchSession:
    """Execute all 4 research stages in sequence.

    Persists the session YAML after every stage. If the process is killed,
    reload with ResearchSession.load() and pass as existing_session to resume.

    Args:
        config: ResearchConfig with all required inputs.
        journey_redesign_config: Optional overrides for Stage 4 (anchor_segment, etc.).
        session_path: Where to save the session YAML. Defaults to config.session_dir/<slug>.yaml.
        existing_session: An in-progress session to resume from.
    """
    from voice_of_agents.research.client import get_async_client

    problems = config.validate_before_run()
    if problems:
        raise ValueError("Config validation failed:\n" + "\n".join(f"  - {p}" for p in problems))

    client = get_async_client(api_key=config.api_key)
    _path = session_path or (config.session_dir / f"{config.slug}.yaml")

    if existing_session is not None:
        session = existing_session
    else:
        session = ResearchSession.create(config.to_product_research_input())

    # Stage 1: Product Research
    if not session.is_stage_complete("product_research"):
        try:
            session.product_research_output = await run_product_research(
                session.product_research_input,
                client=client,
                model=config.anthropic_model,
                output_dir=config.output_dir,
            )
            session.mark_stage_complete("product_research")
            session.save(_path)
        except Exception as exc:
            session.log_error("product_research", str(exc))
            session.save(_path)
            raise

    # Stage 2: Personas from Research
    if not session.is_stage_complete("personas_from_research") and session.product_research_output:
        try:
            persona_input = PersonaResearchInput(
                product_research=session.product_research_output,
                skip_topup=config.skip_topup,
            )
            session.persona_research_output = await run_personas_from_research(
                persona_input,
                client=client,
                model=config.anthropic_model,
                output_dir=config.output_dir,
            )
            session.mark_stage_complete("personas_from_research")
            session.save(_path)
        except Exception as exc:
            session.log_error("personas_from_research", str(exc))
            session.save(_path)
            raise

    # Stage 3: Workflows from Interviews (first persona by default)
    if (
        not session.is_stage_complete("workflows_from_interviews")
        and session.persona_research_output
    ):
        try:
            sidecars = session.persona_research_output.persona_sidecars
            if not sidecars:
                raise ValueError("No persona sidecars available for workflow interviews")
            first_uxw = sidecars[0].uxw_id
            workflow_input = WorkflowResearchInput(
                persona_research=session.persona_research_output,
                target_uxw_id=first_uxw,
            )
            session.workflow_research_output = await run_workflows_from_interviews(
                workflow_input,
                client=client,
                model=config.anthropic_model,
                output_dir=config.output_dir,
            )
            session.mark_stage_complete("workflows_from_interviews")
            session.save(_path)
        except Exception as exc:
            session.log_error("workflows_from_interviews", str(exc))
            session.save(_path)
            raise

    # Stage 4: Journey Redesign
    if not session.is_stage_complete("journey_redesign") and session.workflow_research_output:
        try:
            jrd_cfg = journey_redesign_config or {}
            sidecars = session.persona_research_output.persona_sidecars  # type: ignore[union-attr]
            focus_panel = [s.uxw_id for s in sidecars[:6]]

            journey_input = JourneyRedesignInput(
                workflow_research=session.workflow_research_output,
                persona_research=session.persona_research_output,  # type: ignore[arg-type]
                anchor_segment=jrd_cfg.get("anchor_segment", "onboarding"),
                journeys_in_scope=jrd_cfg.get("journeys_in_scope", ["onboarding"]),
                build_form=jrd_cfg.get("build_form", "mockups_only"),
                focus_panel_uxw_ids=jrd_cfg.get("focus_panel_uxw_ids", focus_panel[:3]),
            )
            session.journey_redesign_output = await run_journey_redesign(
                journey_input,
                client=client,
                model=config.anthropic_model,
                output_dir=config.output_dir,
            )
            session.mark_stage_complete("journey_redesign")
            session.save(_path)
        except Exception as exc:
            session.log_error("journey_redesign", str(exc))
            session.save(_path)
            raise

    return session


def run_full_pipeline_sync(
    config: ResearchConfig,
    **kwargs,
) -> ResearchSession:
    """Synchronous wrapper for use in non-async contexts."""
    return asyncio.run(run_full_pipeline(config, **kwargs))
