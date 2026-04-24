"""Stage 3: Workflows from Interviews — extract PWM workflow maps from episode episodes."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

import yaml
from anthropic import AsyncAnthropic

from voice_of_agents.research.client import get_async_client, get_template_env
from voice_of_agents.research.models import (
    EpisodeRecord,
    EpisodeStep,
    PWMWorkflow,
    PWMWorkflowStep,
    UXWPersonaSidecar,
    WorkflowResearchInput,
    WorkflowResearchOutput,
)
from voice_of_agents.research.validation import guard_stage3_input

_DEFAULT_MODEL = "claude-opus-4-7"

_EPISODE_SCENARIOS = [
    (
        "primary-task",
        "3 weeks ago",
        "The most recent time you completed your primary task from start to finish",
    ),
    (
        "under-pressure",
        "last month",
        "A time you had to complete this task under unusual time pressure",
    ),
    (
        "failure-recovery",
        "2 months ago",
        "A time something went wrong mid-task and you had to recover",
    ),
    (
        "delegation",
        "last quarter",
        "A time you had to hand off this task to someone else or receive a handoff",
    ),
    (
        "new-constraint",
        "recently",
        "A time you encountered a new constraint that changed how you worked",
    ),
]


def _get_sidecar(input: WorkflowResearchInput) -> UXWPersonaSidecar:
    """Find the target persona sidecar by UXW ID."""
    sidecar = next(
        (s for s in input.persona_research.persona_sidecars if s.uxw_id == input.target_uxw_id),
        None,
    )
    if sidecar is None:
        raise ValueError(
            f"UXW ID '{input.target_uxw_id}' not found in persona research output. "
            f"Available: {[s.uxw_id for s in input.persona_research.persona_sidecars]}"
        )
    return sidecar


async def _run_episode_interviews(
    sidecar: UXWPersonaSidecar,
    episode_count: int,
    client: AsyncAnthropic,
    model: str,
) -> list[EpisodeRecord]:
    """Spawn parallel episode explorer calls (3-5) for a single persona."""
    env = get_template_env()
    template = env.get_template("workflows_from_interviews/episode_explorer.j2")
    scenarios = _EPISODE_SCENARIOS[:episode_count]

    async def call_one(
        episode_name: str,
        time_anchor: str,
        scenario_description: str,
    ) -> EpisodeRecord:
        prompt = template.render(
            persona_name=sidecar.name,
            uxw_id=sidecar.uxw_id,
            jtbd=sidecar.jtbd,
            adoption_trajectory=sidecar.adoption_trajectory,
            constraint_profile=sidecar.constraint_profile,
            failure_or_abandonment_mode=sidecar.failure_or_abandonment_mode,
            anti_model_of_success=sidecar.anti_model_of_success,
            verbatim_quote_bank=sidecar.verbatim_quote_bank,
            episode_name=episode_name,
            time_anchor=time_anchor,
            scenario_description=scenario_description,
        )
        response = await client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_episode(response.content[0].text, episode_name, time_anchor)

    tasks = [
        call_one(ep_name, time_anchor, scenario) for ep_name, time_anchor, scenario in scenarios
    ]
    return list(await asyncio.gather(*tasks))


def _parse_episode(raw: str, episode_name: str, date: str) -> EpisodeRecord:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        data = {}

    steps = []
    for s in data.get("steps", []):
        if isinstance(s, dict):
            steps.append(
                EpisodeStep(
                    step=s.get("step", ""),
                    tool=s.get("tool", "none"),
                    input=s.get("input", ""),
                    output=s.get("output", ""),
                    time=s.get("time", ""),
                    blocker=s.get("blocker", "none"),
                )
            )
    if not steps:
        steps = [
            EpisodeStep(
                step="[no steps captured]",
                tool="none",
                input="",
                output="",
                time="",
                blocker="none",
            )
        ]

    return EpisodeRecord(
        episode=data.get("episode", episode_name),
        date=data.get("date", date),
        pre_state=data.get("pre_state", "[not captured]"),
        steps=steps,
        post_state=data.get("post_state", "[not captured]"),
        what_i_wished_existed=data.get("what_i_wished_existed", ""),
    )


async def _synthesize_workflow_maps(
    sidecar: UXWPersonaSidecar,
    episodes: list[EpisodeRecord],
    client: AsyncAnthropic,
    model: str,
) -> list[PWMWorkflow]:
    env = get_template_env()
    template = env.get_template("workflows_from_interviews/workflow_synthesis.j2")

    uxw_number_str = sidecar.uxw_id.replace("UXW-", "")
    try:
        persona_id = int(uxw_number_str)
    except ValueError:
        persona_id = 1

    prompt = template.render(
        uxw_id=sidecar.uxw_id,
        persona_name=sidecar.name,
        jtbd=sidecar.jtbd,
        persona_id=persona_id,
        episodes=episodes,
    )
    response = await client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_workflow_maps(response.content[0].text, sidecar.uxw_id, persona_id)


def _parse_workflow_maps(raw: str, uxw_id: str, persona_id: int) -> list[PWMWorkflow]:
    block = _extract_yaml_block(raw)
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return []

    workflows = []
    for item in data.get("workflows", []):
        if not isinstance(item, dict):
            continue
        steps = [
            PWMWorkflowStep(
                number=s.get("number", i + 1),
                action=s.get("action", ""),
                tool=s.get("tool", "none"),
                input=s.get("input", ""),
                output=s.get("output", ""),
                time=s.get("time", ""),
                blocker=s.get("blocker", "none"),
                friction_risk=s.get("friction_risk", ""),
            )
            for i, s in enumerate(item.get("steps", []))
            if isinstance(s, dict)
        ]
        if not steps:
            continue
        workflows.append(
            PWMWorkflow(
                id=item.get("id", f"{uxw_id}-01"),
                persona=persona_id,
                title=item.get("title", ""),
                intent_goal=item.get("intent_goal", ""),
                intent_trigger=item.get("intent_trigger", ""),
                success_definition=item.get("success_definition", ""),
                preconditions=item.get("preconditions", []),
                steps=steps,
                success_criteria=item.get("success_criteria", []),
                satisfaction_drivers=item.get("satisfaction_drivers", []),
                dealbreakers=item.get("dealbreakers", []),
                efficiency_baseline_method=item.get("efficiency_baseline_method", ""),
                efficiency_baseline_time=item.get("efficiency_baseline_time", ""),
                value_time_saved=item.get("value_time_saved", ""),
                value_errors_prevented=item.get("value_errors_prevented", ""),
                value_knowledge_preserved=item.get("value_knowledge_preserved", ""),
            )
        )
    return workflows


def _extract_yaml_block(text: str) -> str:
    match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ── Public API ─────────────────────────────────────────────────────────


async def run_workflows_from_interviews(
    input: WorkflowResearchInput,
    client: Optional[AsyncAnthropic] = None,
    model: str = _DEFAULT_MODEL,
    output_dir: Path = Path("docs/research"),
) -> WorkflowResearchOutput:
    """Execute the workflows-from-interviews pipeline for a single persona.

    Group mode is explicitly refused — one persona per invocation.

    Stages:
    1. Load and validate the target persona sidecar
    2. Spawn 3-5 parallel episode explorer calls (asyncio.gather)
    3. Extract time-ordered narratives from episode responses
    4. Synthesize 2-3 workflow maps from episodes
    """
    if client is None:
        client = get_async_client()

    guard_stage3_input(input.persona_research)
    sidecar = _get_sidecar(input)

    # Spawn parallel episode interviews
    episodes = await _run_episode_interviews(sidecar, input.episode_count, client, model)

    # Synthesize workflow maps from episodes
    workflow_maps = await _synthesize_workflow_maps(sidecar, episodes, client, model)

    return WorkflowResearchOutput(
        uxw_id=input.target_uxw_id,
        episodes=episodes,
        workflow_maps=workflow_maps,
        archived_prior_pwm=[],
    )


def run_workflows_from_interviews_sync(
    input: WorkflowResearchInput,
    **kwargs,
) -> WorkflowResearchOutput:
    """Synchronous wrapper for use in non-async contexts."""
    return asyncio.run(run_workflows_from_interviews(input, **kwargs))
