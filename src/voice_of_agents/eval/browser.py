"""Playwright-based adaptive persona explorer.

Navigates the target app as a specific persona, pursuing their objectives
and recording the journey. This is NOT a fixed test script — the explorer
adapts to what the app offers using an LLM-driven action loop.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from voice_of_agents.core.persona import Persona

logger = logging.getLogger(__name__)

MAX_STEPS_PER_OBJECTIVE = 12


@dataclass
class ExplorationGoal:
    """Lightweight goal descriptor used by the browser explorer."""

    goal: str
    trigger: str = ""
    success_definition: str = ""
    efficiency_baseline: str = ""


@dataclass
class NavLink:
    text: str
    href: str


@dataclass
class JourneyStep:
    action: str
    observation: str
    reaction: str
    page_url: str = ""
    latency_ms: int = 0
    screenshot: str = ""


@dataclass
class FrictionPoint:
    type: str  # gap, slow, confusing, broken, missing, empty_state
    description: str
    severity: str = "medium"  # low, medium, high, critical
    persona_quote: str = ""


@dataclass
class Surprise:
    type: str  # delight, confusion, unexpected
    description: str


@dataclass
class ExplorationResult:
    persona_id: str
    persona_name: str
    run_timestamp: str
    objective: str
    objective_trigger: str = ""
    objective_success: str = ""
    outcome: str = "not_attempted"  # achieved, partial, blocked, not_attempted
    journey: list[JourneyStep] = field(default_factory=list)
    friction_points: list[FrictionPoint] = field(default_factory=list)
    surprises: list[Surprise] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    pages_visited: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "persona_name": self.persona_name,
            "run_timestamp": self.run_timestamp,
            "objective": self.objective,
            "objective_trigger": self.objective_trigger,
            "objective_success": self.objective_success,
            "outcome": self.outcome,
            "pages_visited": self.pages_visited,
            "journey": [
                {
                    "action": s.action,
                    "observation": s.observation,
                    "reaction": s.reaction,
                    "page_url": s.page_url,
                    "latency_ms": s.latency_ms,
                    "screenshot": s.screenshot,
                }
                for s in self.journey
            ],
            "friction_points": [
                {
                    "type": f.type,
                    "description": f.description,
                    "severity": f.severity,
                    "persona_quote": f.persona_quote,
                }
                for f in self.friction_points
            ],
            "surprises": [{"type": s.type, "description": s.description} for s in self.surprises],
            "missing_capabilities": self.missing_capabilities,
        }


async def explore_as_persona(
    persona: Persona,
    target_url: str,
    session_token: str | None = None,
    screenshot_dir: Path | None = None,
    goals: list[ExplorationGoal] | None = None,
) -> list[ExplorationResult]:
    """Explore the target app as a specific persona, pursuing their objectives.

    LLM-driven adaptive exploration: takes screenshots, asks Claude what to do
    next, executes actions via Playwright, and records the full journey.
    """
    from playwright.async_api import async_playwright

    goals = goals or []
    results: list[ExplorationResult] = []
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})

        if session_token:
            await context.add_cookies(
                [
                    {
                        "name": "rooben_session",
                        "value": session_token,
                        "domain": "localhost",
                        "path": "/",
                    }
                ]
            )
            page = await context.new_page()
            await page.goto(target_url, wait_until="networkidle", timeout=15000)
            await page.evaluate(f"localStorage.setItem('rooben_session', '{session_token}')")
        else:
            page = await context.new_page()

        for goal in goals:
            result = ExplorationResult(
                persona_id=str(persona.id),
                persona_name=persona.name,
                run_timestamp=ts,
                objective=goal.goal,
                objective_trigger=goal.trigger,
                objective_success=goal.success_definition,
            )

            try:
                await _explore_objective(page, persona, goal, result, target_url, screenshot_dir)
            except Exception as e:
                result.outcome = "blocked"
                result.friction_points.append(
                    FrictionPoint(
                        type="broken",
                        description=f"Exploration failed: {e}",
                        severity="critical",
                    )
                )
                logger.error("Exploration failed for %s goal '%s': %s", persona.id, goal.goal, e)

            results.append(result)

        await browser.close()

    return results


async def _explore_objective(
    page,
    persona: Persona,
    objective: ExplorationGoal,
    result: ExplorationResult,
    target_url: str,
    screenshot_dir: Path | None,
) -> None:
    """LLM-driven multi-step exploration of a single objective.

    Takes a screenshot each step, sends it to Claude with persona context,
    executes the returned action, and loops until achieved/blocked/max steps.
    """
    import anthropic

    client = anthropic.Anthropic()

    # Step 1: Navigate to app root
    t0 = time.monotonic()
    await page.goto(target_url, wait_until="networkidle", timeout=15000)
    latency = int((time.monotonic() - t0) * 1000)
    current_url = page.url
    result.pages_visited.append(current_url)

    result.journey.append(
        JourneyStep(
            action=f"Open {target_url}",
            observation=f"Redirected to {current_url}"
            if current_url != target_url
            else f"Loaded {current_url}",
            reaction=_react_to_landing(persona, current_url),
            page_url=current_url,
            latency_ms=latency,
        )
    )

    if screenshot_dir:
        fname = await _screenshot(page, screenshot_dir, "step-01-landing")
        if result.journey:
            result.journey[-1].screenshot = fname

    # Track (action, target_text) pairs already attempted per URL to prevent loops
    tried_on_url: dict[str, set[tuple[str, str]]] = {}

    # Agentic action loop
    for step_num in range(2, MAX_STEPS_PER_OBJECTIVE + 2):
        screenshot_b64 = await _capture_screenshot_b64(page)
        page_state = await _get_page_state(page)
        url_before = page.url

        recent_steps = result.journey[-5:]
        action_history = "\n".join(f"- {s.action}: {s.observation[:120]}" for s in recent_steps)

        # Build list of already-tried actions on this URL for the prompt
        already_tried = sorted(tried_on_url.get(url_before, set()))
        tried_hint = (
            "Actions you have ALREADY tried on this URL (do NOT repeat them): "
            + ", ".join(f'"{a} {t}"' for a, t in already_tried)
            if already_tried
            else ""
        )

        action_json = await _ask_llm_for_action(
            client=client,
            persona=persona,
            objective=objective,
            page_state=page_state,
            screenshot_b64=screenshot_b64,
            action_history=action_history,
            tried_hint=tried_hint,
            step_num=step_num - 1,
        )

        action = action_json.get("action", "blocked")
        reason = action_json.get("reason", "")
        observation = action_json.get("observation", "")

        if action_json.get("friction"):
            f = action_json["friction"]
            if isinstance(f, dict):
                result.friction_points.append(
                    FrictionPoint(
                        type=f.get("type", "gap"),
                        description=f.get("description", ""),
                        severity=f.get("severity", "medium"),
                        persona_quote=f.get("persona_quote", ""),
                    )
                )

        if action_json.get("missing_capability"):
            cap = action_json["missing_capability"]
            if isinstance(cap, str) and cap:
                result.missing_capabilities.append(cap)

        if action == "achieved":
            result.journey.append(
                JourneyStep(
                    action="Objective achieved",
                    observation=observation or "Successfully completed the objective",
                    reaction=reason,
                    page_url=page.url,
                )
            )
            result.outcome = "achieved"
            if screenshot_dir:
                await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-achieved")
            return

        if action == "blocked":
            result.journey.append(
                JourneyStep(
                    action="Blocked — cannot proceed",
                    observation=observation or "No path forward found",
                    reaction=reason,
                    page_url=page.url,
                )
            )
            result.outcome = "blocked"
            if not any(
                fp.severity == "high" or fp.severity == "critical" for fp in result.friction_points
            ):
                result.friction_points.append(
                    FrictionPoint(
                        type="gap",
                        description=reason or f"Cannot complete: {objective.goal}",
                        severity="high",
                        persona_quote=_quote_cant_find(persona, objective),
                    )
                )
            if screenshot_dir:
                await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-blocked")
            return

        # Record this action as tried on the current URL before executing
        target_key = (action, (action_json.get("target_text") or "").strip()[:60])
        tried_on_url.setdefault(url_before, set()).add(target_key)

        t0 = time.monotonic()
        success, exec_observation = await _execute_action(page, action_json, target_url)
        latency = int((time.monotonic() - t0) * 1000)

        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        new_url = page.url
        if new_url not in result.pages_visited:
            result.pages_visited.append(new_url)

        # Detect same-page loop: action succeeded but URL didn't change
        url_changed = new_url != url_before
        if not url_changed and action == "click":
            exec_observation = (
                (exec_observation or observation or "")
                + " [URL unchanged — this was a selection toggle, not a navigation. Look for Continue/Submit/Next.]"
            )

        target_desc = (
            action_json.get("target_text")
            or action_json.get("url")
            or action_json.get("value", "")
            or action_json.get("key", "")
        )
        step = JourneyStep(
            action=f"{action.capitalize()}: {str(target_desc)[:80]}",
            observation=exec_observation or observation,
            reaction=reason,
            page_url=new_url,
            latency_ms=latency,
        )
        if screenshot_dir:
            fname = await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-{action}")
            step.screenshot = fname

        result.journey.append(step)

        if not success:
            logger.debug(
                "Action failed at step %d for %s: %s", step_num, persona.id, exec_observation
            )

    # Exhausted steps without terminal state
    result.outcome = "partial"


# ── LLM Action Engine ─────────────────────────────────────────────────


async def _capture_screenshot_b64(page) -> str:
    """Capture a JPEG screenshot and return as base64 string."""
    try:
        screenshot_bytes = await page.screenshot(type="jpeg", quality=55)
        return base64.b64encode(screenshot_bytes).decode()
    except Exception as e:
        logger.warning("Screenshot capture failed: %s", e)
        return ""


async def _get_page_state(page) -> str:
    """Extract a concise text representation of the current page's interactive state."""
    parts = [f"URL: {page.url}"]

    try:
        title = await page.title()
        if title:
            parts.append(f"Title: {title}")
    except Exception:
        pass

    try:
        headings = []
        h_els = page.locator("h1, h2, h3")
        for i in range(min(await h_els.count(), 6)):
            text = (await h_els.nth(i).text_content() or "").strip()
            if text and len(text) < 100:
                headings.append(text)
        if headings:
            parts.append(f"Headings: {headings}")
    except Exception:
        pass

    try:
        buttons = []
        btn_els = page.locator("button:visible, [role='button']:visible")
        for i in range(min(await btn_els.count(), 20)):
            text = (await btn_els.nth(i).text_content() or "").strip()
            if text and len(text) < 60:
                buttons.append(text)
        if buttons:
            parts.append(f"Buttons: {buttons}")
    except Exception:
        pass

    try:
        links = []
        link_els = page.locator("a[href]:visible")
        for i in range(min(await link_els.count(), 25)):
            text = (await link_els.nth(i).text_content() or "").strip()
            href = await link_els.nth(i).get_attribute("href") or ""
            if text and len(text) < 60 and href:
                links.append(f"{text} ({href})")
        if links:
            parts.append(f"Links: {links[:20]}")
    except Exception:
        pass

    try:
        inputs = []
        input_els = page.locator("input:visible, textarea:visible, select:visible")
        for i in range(min(await input_els.count(), 10)):
            el = input_els.nth(i)
            ph = await el.get_attribute("placeholder") or ""
            label = await el.get_attribute("aria-label") or ""
            name = await el.get_attribute("name") or ""
            type_ = await el.get_attribute("type") or "text"
            inputs.append(f"{type_}[{label or ph or name}]")
        if inputs:
            parts.append(f"Inputs: {inputs}")
    except Exception:
        pass

    try:
        main_el = page.locator("main, [role='main']")
        if await main_el.count() > 0:
            text = (await main_el.first.text_content() or "")[:400].strip()
            if text:
                parts.append(f"Main content (truncated): {text}")
    except Exception:
        pass

    return "\n".join(parts)


async def _ask_llm_for_action(
    client,
    persona: Persona,
    objective: ExplorationGoal,
    page_state: str,
    screenshot_b64: str,
    action_history: str,
    tried_hint: str,
    step_num: int,
) -> dict:
    """Ask Claude what the next best action is, given the current page and persona context."""
    pain_summary = ""
    if persona.pain_points:
        pain_summary = (persona.pain_points[0].description or "")[:200]

    system_prompt = f"""You are {persona.name}, a {persona.role} in {persona.industry}.
Mindset: {(persona.mindset or "")[:250]}
Primary pain: {pain_summary}

You are navigating a web application to achieve a specific objective. Your job is to decide the single best next action.

Objective: {objective.goal}
Why you care: {objective.trigger}
Success looks like: {objective.success_definition}
Step: {step_num} of {MAX_STEPS_PER_OBJECTIVE}

Recent actions (most recent last):
{action_history or "None yet — this is your first action."}

{tried_hint}

Current page state:
{page_state}

Respond ONLY with a single valid JSON object — no markdown fences, no explanation, no trailing text:
{{
  "action": "click|fill|goto|scroll|press_key|achieved|blocked",
  "target_text": "exact visible text of the element to interact with (for click/fill)",
  "element_role": "button|link|textbox|combobox|checkbox (for click/fill)",
  "value": "text to type into the field (for fill only)",
  "url": "relative or absolute URL to navigate to (for goto only)",
  "key": "Enter|Tab|Escape|Space (for press_key only)",
  "observation": "1-2 sentences describing what you currently see on this page",
  "reason": "why this action, in first person as {persona.name}",
  "friction": null,
  "missing_capability": null
}}

For friction, replace null with:
{{"type": "gap|slow|confusing|broken|missing|empty_state", "description": "...", "severity": "low|medium|high|critical", "persona_quote": "direct quote in {persona.name}'s voice"}}

Critical rules:
- NEVER repeat an action already listed in the tried-actions list above
- If a click did NOT change the URL, it was a SELECTION TOGGLE (like a card or checkbox), not a navigation. After selecting, look for and click the Continue, Next, or Submit button to advance.
- Multi-step forms: select options first, THEN click the advance button (Continue →, Next →, Submit, Create, etc.)
- If you see a "Continue →", "Next →", "Submit", or "Create a Plan" button and you've already made a selection, click it NOW
- Use "achieved" only when the objective is fully complete
- Use "blocked" only after genuinely exhausting all options — not after one failure
- Prefer clicking visible buttons/links over goto navigation"""

    content: list[dict] = []
    if screenshot_b64:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": screenshot_b64,
                },
            }
        )
    content.append(
        {
            "type": "text",
            "text": "Based on the page state above and this screenshot, what is the best single next action to take?",
        }
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=system_prompt,
            messages=[{"role": "user", "content": content}],
        )
        return _parse_action_json(response.content[0].text.strip())
    except Exception as e:
        logger.warning("LLM action call failed at step %d: %s", step_num, e)
        return {"action": "blocked", "reason": f"LLM error: {e}", "observation": ""}


def _parse_action_json(text: str) -> dict:
    """Extract and parse the JSON action object from an LLM response.

    Handles: plain JSON, ```json fences, extra prose before/after the object.
    Uses brace-depth scanning instead of greedy regex to avoid capturing
    nested structures incorrectly.
    """
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    stripped = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    stripped = re.sub(r"\s*```\s*$", "", stripped, flags=re.MULTILINE).strip()

    # Direct parse first (covers the happy path)
    try:
        return json.loads(stripped)
    except Exception:
        pass

    # Brace-depth scan: find the first complete {...} object
    depth = 0
    start = None
    for i, ch in enumerate(stripped):
        if ch == "{":
            if start is None:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = stripped[start : i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    # Keep scanning — maybe a later object is valid
                    start = None

    logger.warning("Could not parse LLM action JSON: %s", text[:300])
    return {
        "action": "blocked",
        "reason": "Could not parse LLM response",
        "observation": text[:200],
    }


async def _execute_action(page, action_json: dict, target_url: str) -> tuple[bool, str]:
    """Execute a parsed LLM action via Playwright. Returns (success, observation)."""
    action = action_json.get("action", "")
    target_text = (action_json.get("target_text") or "").strip()
    element_role = (action_json.get("element_role") or "").strip()
    value = action_json.get("value") or ""
    url = (action_json.get("url") or "").strip()
    key = (action_json.get("key") or "Enter").strip()

    try:
        if action == "click":
            clicked = False

            # Strategy 1: role + name
            if element_role and target_text:
                try:
                    loc = page.get_by_role(element_role, name=target_text)
                    if await loc.count() > 0:
                        await loc.first.click(timeout=5000)
                        clicked = True
                except Exception:
                    pass

            # Strategy 2: text match on common interactive elements
            if not clicked and target_text:
                for selector in [
                    f"button:has-text('{target_text}')",
                    f"a:has-text('{target_text}')",
                    f"[role='button']:has-text('{target_text}')",
                    f"[role='link']:has-text('{target_text}')",
                    f"label:has-text('{target_text}')",
                ]:
                    try:
                        loc = page.locator(selector)
                        if await loc.count() > 0:
                            await loc.first.click(timeout=5000)
                            clicked = True
                            break
                    except Exception:
                        continue

            # Strategy 3: partial text via get_by_text
            if not clicked and target_text:
                try:
                    loc = page.get_by_text(target_text, exact=False)
                    if await loc.count() > 0:
                        await loc.first.click(timeout=5000)
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                return False, f"Could not find clickable element: '{target_text}'"

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            return True, f"Clicked '{target_text}' → now at {page.url}"

        elif action == "fill":
            filled = False
            if target_text:
                for locator in [
                    page.get_by_label(target_text),
                    page.get_by_placeholder(target_text),
                    page.locator(f"input[name='{target_text}']"),
                    page.locator(f"input[aria-label='{target_text}']"),
                ]:
                    try:
                        if await locator.count() > 0:
                            await locator.first.fill(value, timeout=3000)
                            filled = True
                            break
                    except Exception:
                        continue

            if not filled:
                try:
                    textbox = page.get_by_role("textbox")
                    if await textbox.count() > 0:
                        await textbox.first.fill(value, timeout=3000)
                        filled = True
                except Exception:
                    pass

            if not filled:
                return False, f"Could not find input field: '{target_text}'"

            await page.wait_for_timeout(400)
            return True, f"Filled '{target_text or 'input'}' with '{str(value)[:60]}'"

        elif action == "goto":
            if not url:
                return False, "goto action missing url"
            if not url.startswith("http"):
                base = target_url.rstrip("/")
                url = f"{base}/{url.lstrip('/')}"
            await page.goto(url, wait_until="networkidle", timeout=12000)
            return True, f"Navigated to {page.url}"

        elif action == "scroll":
            await page.evaluate("window.scrollBy(0, 500)")
            await page.wait_for_timeout(400)
            return True, "Scrolled down 500px"

        elif action == "press_key":
            await page.keyboard.press(key)
            await page.wait_for_timeout(800)
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            return True, f"Pressed {key}"

    except Exception as e:
        return False, f"Action execution error: {e}"

    return False, f"Unknown action: {action}"


# ── Page Content Reading ──────────────────────────────────────────────


async def _read_page_content(page) -> dict:
    """Read and summarize the current page's content and structure."""
    title = await page.title()

    main_text = ""
    try:
        main_el = page.locator("main")
        if await main_el.count() > 0:
            main_text = (await main_el.first.text_content() or "")[:1000]
    except Exception:
        pass

    headings = []
    try:
        h_elements = page.locator("main h1, main h2")
        for i in range(min(await h_elements.count(), 5)):
            h_text = (await h_elements.nth(i).text_content() or "").strip()
            if h_text:
                headings.append(h_text)
    except Exception:
        pass

    has_inputs = False
    input_placeholders = []
    try:
        inputs = page.get_by_role("textbox")
        input_count = await inputs.count()
        has_inputs = input_count > 0
        for i in range(min(input_count, 3)):
            ph = await inputs.nth(i).get_attribute("placeholder") or ""
            if ph:
                input_placeholders.append(ph)
    except Exception:
        pass

    buttons = []
    try:
        btn_elements = page.locator("main button")
        for i in range(min(await btn_elements.count(), 5)):
            btn_text = (await btn_elements.nth(i).text_content() or "").strip()
            if btn_text and len(btn_text) < 40:
                buttons.append(btn_text)
    except Exception:
        pass

    main_lower = main_text.lower()
    is_empty = any(
        phrase in main_lower
        for phrase in [
            "no learnings yet",
            "no delegations yet",
            "no agents",
            "no data",
            "empty",
            "get started",
            "no results",
        ]
    )
    empty_message = ""
    if is_empty:
        for phrase in ["no learnings yet", "no delegations yet", "no agents yet"]:
            if phrase in main_lower:
                empty_message = phrase
                break
        if not empty_message:
            empty_message = "Page appears to have no data"

    summary_parts = []
    if headings:
        summary_parts.append(f"Headings: {headings}")
    if input_placeholders:
        summary_parts.append(f"Input fields: {input_placeholders}")
    if buttons:
        summary_parts.append(f"Buttons: {buttons}")
    if is_empty:
        summary_parts.append(f"Empty state: '{empty_message}'")
    summary = ". ".join(summary_parts) if summary_parts else f"Content: {main_text[:200]}"

    return {
        "title": title,
        "headings": headings,
        "summary": summary,
        "has_inputs": has_inputs,
        "input_placeholders": input_placeholders,
        "buttons": buttons,
        "is_empty": is_empty,
        "empty_message": empty_message,
        "raw_text": main_text,
    }


# ── Persona-Voice Reactions ───────────────────────────────────────────


def _react_to_landing(persona: Persona, url: str) -> str:
    if "/login" in url:
        return "I need to log in first."
    if "/onboarding" in url:
        return "Setting up my account."
    if "/workspace" in url:
        if persona.voice.skepticism == "high":
            return f"Good, it dropped me right into the workspace. Let's see if it understands {persona.industry.lower()} work."
        return "I'm in the workspace. Let me see what I can do here."
    if "/agents/profile" in url:
        return "It wants me to set up my expert profile first. Makes sense for team delegation."
    return "I'm on the main page. Let me figure out where to go."


def _quote_cant_find(persona: Persona, objective: ExplorationGoal) -> str:
    """Generate an in-character quote about not finding what they need."""
    goal_short = objective.goal.lower()[:60]
    if persona.voice.motivation == "fear":
        return f"I can't find where to {goal_short}. In my field, not being able to access this quickly is a liability."
    if persona.voice.motivation == "compliance":
        return f"I need to be able to {goal_short} for audit purposes. Where is this capability?"
    return f"I expected to be able to {goal_short} from the navigation, but I don't see an obvious path forward."


def _is_relevant_to_persona(link: NavLink, persona: Persona) -> bool:
    text = link.text.lower()
    if persona.org_size <= 1:
        return any(k in text for k in ["workspace", "knowledge", "library", "profile", "setting"])
    else:
        return any(
            k in text
            for k in [
                "workspace",
                "knowledge",
                "library",
                "profile",
                "agent",
                "expert",
                "delegation",
                "dashboard",
                "setting",
            ]
        )


async def _screenshot(page, screenshot_dir: Path, name: str) -> str:
    """Take a screenshot and return the filename."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{name}.png"
    path = screenshot_dir / filename
    try:
        await page.screenshot(path=str(path))
        return filename
    except Exception as e:
        logger.warning("Screenshot failed: %s", e)
        return ""
