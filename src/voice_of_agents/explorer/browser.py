"""Playwright-based adaptive persona explorer.

Navigates the target app as a specific persona, pursuing their objectives
and recording the journey. This is NOT a fixed test script — the explorer
adapts to what the app offers.

Tier 1: Structured nav parsing, href navigation, proper latency
Tier 2: Multi-step journeys, form interaction, page-aware exploration
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from voice_of_agents.contracts.personas import Persona, Objective

logger = logging.getLogger(__name__)

MAX_STEPS_PER_OBJECTIVE = 8


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
                {"action": s.action, "observation": s.observation,
                 "reaction": s.reaction, "page_url": s.page_url,
                 "latency_ms": s.latency_ms, "screenshot": s.screenshot}
                for s in self.journey
            ],
            "friction_points": [
                {"type": f.type, "description": f.description,
                 "severity": f.severity, "persona_quote": f.persona_quote}
                for f in self.friction_points
            ],
            "surprises": [
                {"type": s.type, "description": s.description}
                for s in self.surprises
            ],
            "missing_capabilities": self.missing_capabilities,
        }


async def explore_as_persona(
    persona: Persona,
    target_url: str,
    session_token: str | None = None,
    screenshot_dir: Path | None = None,
) -> list[ExplorationResult]:
    """Explore the target app as a specific persona, pursuing their objectives.

    Multi-step adaptive exploration: navigates to relevant pages, fills forms
    with objective-derived content, observes results, and follows links.
    """
    from playwright.async_api import async_playwright

    results: list[ExplorationResult] = []
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})

        # Set session
        if session_token:
            await context.add_cookies([{
                "name": "rooben_session",
                "value": session_token,
                "domain": "localhost",
                "path": "/",
            }])
            page = await context.new_page()
            await page.goto(target_url, wait_until="networkidle", timeout=15000)
            await page.evaluate(f"localStorage.setItem('rooben_session', '{session_token}')")
        else:
            page = await context.new_page()

        for obj in persona.objectives:
            result = ExplorationResult(
                persona_id=persona.id,
                persona_name=persona.name,
                run_timestamp=ts,
                objective=obj.goal,
                objective_trigger=obj.trigger,
                objective_success=obj.success_definition,
            )

            try:
                await _explore_objective(page, persona, obj, result, target_url, screenshot_dir)
            except Exception as e:
                result.outcome = "blocked"
                result.friction_points.append(FrictionPoint(
                    type="broken",
                    description=f"Exploration failed: {e}",
                    severity="critical",
                ))
                logger.error("Exploration failed for %s obj '%s': %s", persona.id, obj.goal, e)

            results.append(result)

        await browser.close()

    return results


async def _explore_objective(
    page, persona: Persona, objective: Objective,
    result: ExplorationResult, target_url: str,
    screenshot_dir: Path | None,
) -> None:
    """Multi-step exploration of a single objective."""
    step_num = 0

    # Step 1: Navigate to app root
    t0 = time.monotonic()
    await page.goto(target_url, wait_until="networkidle", timeout=15000)
    latency = int((time.monotonic() - t0) * 1000)
    current_url = page.url
    result.pages_visited.append(current_url)

    result.journey.append(JourneyStep(
        action=f"Open {target_url}",
        observation=f"Redirected to {current_url}" if current_url != target_url else f"Loaded {current_url}",
        reaction=_react_to_landing(persona, current_url),
        page_url=current_url,
        latency_ms=latency,
    ))
    step_num += 1

    if screenshot_dir:
        await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-landing")

    # Step 2: Parse navigation
    nav_links = await _parse_nav_links(page)

    result.journey.append(JourneyStep(
        action="Scan sidebar navigation",
        observation=f"Found {len(nav_links)} nav links: {[l.text for l in nav_links]}",
        reaction=_react_to_nav(persona, nav_links),
        page_url=current_url,
    ))
    step_num += 1

    # Step 3: Navigate to the most relevant page for this objective
    best_link = _find_best_link(objective, nav_links)

    if not best_link:
        result.outcome = "blocked"
        result.friction_points.append(FrictionPoint(
            type="gap",
            description=f"No sidebar link matches objective: {objective.goal}",
            severity="high",
            persona_quote=_quote_cant_find(persona, objective),
        ))
        result.missing_capabilities.append(f"Direct navigation for: {objective.goal}")
        return

    t0 = time.monotonic()
    await page.goto(f"{target_url}{best_link.href}", wait_until="networkidle", timeout=10000)
    latency = int((time.monotonic() - t0) * 1000)
    current_url = page.url
    result.pages_visited.append(current_url)

    page_content = await _read_page_content(page)

    result.journey.append(JourneyStep(
        action=f"Navigate to '{best_link.text}' ({best_link.href})",
        observation=f"Page: {page_content['title']}. {page_content['summary']}",
        reaction=_react_to_page(persona, objective, page_content),
        page_url=current_url,
        latency_ms=latency,
    ))
    step_num += 1

    if screenshot_dir:
        await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-{best_link.text.lower().replace(' ', '-')}")

    # Check for empty state
    if page_content["is_empty"]:
        result.friction_points.append(FrictionPoint(
            type="empty_state",
            description=f"'{best_link.text}' page is empty — {page_content['empty_message']}",
            severity="medium",
            persona_quote=_quote_empty_state(persona, objective, best_link.text),
        ))

    # Step 4: Interact with the page if possible
    if page_content["has_inputs"] and step_num < MAX_STEPS_PER_OBJECTIVE:
        input_text = _derive_input_text(persona, objective)
        if input_text:
            interaction = await _interact_with_page(page, input_text, persona, objective)
            result.journey.append(interaction)
            step_num += 1

            if screenshot_dir:
                await _screenshot(page, screenshot_dir, f"step-{step_num:02d}-after-input")

    # Step 5: Look for and follow relevant action links on the page
    if step_num < MAX_STEPS_PER_OBJECTIVE:
        action_link = await _find_action_link(page, objective)
        if action_link:
            t0 = time.monotonic()
            try:
                await page.click(f"text={action_link}", timeout=3000)
                await page.wait_for_load_state("networkidle", timeout=5000)
                latency = int((time.monotonic() - t0) * 1000)
                new_url = page.url
                result.pages_visited.append(new_url)
                new_content = await _read_page_content(page)

                result.journey.append(JourneyStep(
                    action=f"Click '{action_link}'",
                    observation=f"Navigated to {new_url}. {new_content['summary']}",
                    reaction=_react_to_page(persona, objective, new_content),
                    page_url=new_url,
                    latency_ms=latency,
                ))
                step_num += 1
            except Exception:
                pass  # Link click failed — not critical

    # Determine outcome
    if any(s.observation and "error" in s.observation.lower() for s in result.journey):
        result.outcome = "blocked"
    elif len(result.pages_visited) >= 2 and not page_content["is_empty"]:
        result.outcome = "partial"
    elif len(result.pages_visited) >= 2:
        result.outcome = "partial"
    else:
        result.outcome = "not_attempted"

    # Check if success criteria could be met
    if objective.success_definition:
        all_content = " ".join(s.observation for s in result.journey).lower()
        success_keywords = objective.success_definition.lower().split()[:5]
        if any(kw in all_content for kw in success_keywords if len(kw) > 3):
            result.outcome = "achieved"
            result.surprises.append(Surprise(
                type="delight",
                description=f"Found content related to success criteria: {objective.success_definition}",
            ))


# ── Navigation Parsing ────────────────────────────────────────────────

async def _parse_nav_links(page) -> list[NavLink]:
    """Extract structured nav links from the sidebar."""
    links: list[NavLink] = []
    try:
        nav = page.locator("[aria-label='Main navigation']")
        if await nav.count() == 0:
            # Fallback: try any nav element
            nav = page.locator("nav").first

        link_elements = nav.get_by_role("link")
        count = await link_elements.count()

        for i in range(count):
            el = link_elements.nth(i)
            text = (await el.text_content() or "").strip()
            href = await el.get_attribute("href") or ""
            # Clean text: remove emoji and excessive whitespace
            clean_text = " ".join(text.split()).strip()
            if clean_text and href and len(clean_text) < 50:
                links.append(NavLink(text=clean_text, href=href))
    except Exception as e:
        logger.warning("Failed to parse nav links: %s", e)

    return links


def _find_best_link(objective: Objective, links: list[NavLink]) -> NavLink | None:
    """Find the most relevant nav link for a persona's objective."""
    goal = objective.goal.lower()
    trigger = (objective.trigger or "").lower()
    combined = goal + " " + trigger

    # Score each link by keyword relevance
    scored: list[tuple[int, NavLink]] = []
    for link in links:
        link_text = link.text.lower()
        score = 0

        # Direct keyword matches
        if any(k in combined for k in ["knowledge", "learn", "capture", "decision", "remember", "retriev", "search"]):
            if "workspace" in link_text:
                score += 10
            if "knowledge" in link_text or "library" in link_text or "learning" in link_text:
                score += 8

        if any(k in combined for k in ["delegate", "route", "expert", "find", "assign"]):
            if "expert" in link_text or "find" in link_text:
                score += 10
            if "delegate" in link_text or "delegation" in link_text or "inbox" in link_text:
                score += 8

        if any(k in combined for k in ["agent", "profile", "publish", "create agent"]):
            if "profile" in link_text:
                score += 10
            if "agent" in link_text and "directory" in link_text:
                score += 6

        if any(k in combined for k in ["cost", "roi", "budget", "spending", "dashboard", "analytics"]):
            if "dashboard" in link_text:
                score += 10

        if any(k in combined for k in ["contradict", "conflict", "inconsist", "flag"]):
            if "knowledge" in link_text or "library" in link_text:
                score += 10

        if any(k in combined for k in ["workflow", "create", "build", "produce"]):
            if "create" in link_text or "new" in link_text:
                score += 8

        if score > 0:
            scored.append((score, link))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    return None


# ── Page Content Reading ──────────────────────────────────────────────

async def _read_page_content(page) -> dict:
    """Read and summarize the current page's content and structure."""
    title = await page.title()

    # Get main content
    main_text = ""
    try:
        main_el = page.locator("main")
        if await main_el.count() > 0:
            main_text = (await main_el.first.text_content() or "")[:1000]
    except Exception:
        pass

    # Check for headings
    headings = []
    try:
        h_elements = page.locator("main h1, main h2")
        for i in range(min(await h_elements.count(), 5)):
            h_text = (await h_elements.nth(i).text_content() or "").strip()
            if h_text:
                headings.append(h_text)
    except Exception:
        pass

    # Check for inputs
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

    # Check for buttons
    buttons = []
    try:
        btn_elements = page.locator("main button")
        for i in range(min(await btn_elements.count(), 5)):
            btn_text = (await btn_elements.nth(i).text_content() or "").strip()
            if btn_text and len(btn_text) < 40:
                buttons.append(btn_text)
    except Exception:
        pass

    # Detect empty state
    main_lower = main_text.lower()
    is_empty = any(phrase in main_lower for phrase in [
        "no learnings yet", "no delegations yet", "no agents",
        "no data", "empty", "get started", "no results",
    ])
    empty_message = ""
    if is_empty:
        for phrase in ["no learnings yet", "no delegations yet", "no agents yet"]:
            if phrase in main_lower:
                empty_message = phrase
                break
        if not empty_message:
            empty_message = "Page appears to have no data"

    # Build summary
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


# ── Page Interaction ──────────────────────────────────────────────────

def _derive_input_text(persona: Persona, objective: Objective) -> str:
    """Generate realistic input text from the persona's objective context."""
    # Use trigger as the most specific scenario description
    if objective.trigger:
        return objective.trigger

    # Fall back to goal-derived text
    goal = objective.goal.lower()
    role = persona.role.lower()

    if "retriev" in goal or "search" in goal or "find" in goal:
        return f"{persona.role} looking for prior {persona.industry} case strategy"
    if "capture" in goal or "learn" in goal:
        return f"New {persona.industry} requirement discovered — need to record for future reference"
    if "route" in goal or "delegate" in goal:
        return f"Need {persona.industry} expertise for a {role} question"
    if "contradict" in goal or "conflict" in goal:
        return f"Check for conflicting guidance in {persona.industry} decisions"

    return objective.goal


async def _interact_with_page(page, input_text: str, persona: Persona, objective: Objective) -> JourneyStep:
    """Fill the first available input on the page and observe the result."""
    t0 = time.monotonic()

    try:
        inputs = page.get_by_role("textbox")
        if await inputs.count() > 0:
            first_input = inputs.first
            await first_input.fill(input_text)
            # Wait for any dynamic updates (e.g., sidebar populating)
            await page.wait_for_timeout(2000)
            latency = int((time.monotonic() - t0) * 1000)

            # Read what changed
            content = await _read_page_content(page)

            return JourneyStep(
                action=f"Type '{input_text[:60]}...' into input field",
                observation=f"After typing: {content['summary']}",
                reaction=_react_to_input_result(persona, objective, content),
                page_url=page.url,
                latency_ms=latency,
            )
    except Exception as e:
        return JourneyStep(
            action=f"Attempted to type into input field",
            observation=f"Failed: {e}",
            reaction="The input didn't respond as expected.",
            page_url=page.url,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )

    return JourneyStep(
        action="Looked for input fields",
        observation="No interactive inputs found on this page",
        reaction="I expected to be able to enter something here but there's no input.",
        page_url=page.url,
    )


async def _find_action_link(page, objective: Objective) -> str | None:
    """Find a relevant action link or button on the current page."""
    goal_lower = objective.goal.lower()

    try:
        links = page.locator("main a, main button")
        count = await links.count()
        for i in range(min(count, 10)):
            text = (await links.nth(i).text_content() or "").strip()
            if not text or len(text) > 50:
                continue
            text_lower = text.lower()

            # Look for action-oriented links
            if any(kw in text_lower for kw in ["view", "open", "start", "create", "add", "search"]):
                if any(kw in goal_lower for kw in text_lower.split() if len(kw) > 3):
                    return text
    except Exception:
        pass

    return None


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


def _react_to_nav(persona: Persona, links: list[NavLink]) -> str:
    count = len(links)
    relevant = [l for l in links if _is_relevant_to_persona(l, persona)]
    if count > 10:
        if persona.voice.skepticism == "high":
            return f"{count} navigation items. That's a lot. I see {len(relevant)} that look relevant to my work."
        return f"{count} options in the sidebar. {len(relevant)} look relevant to me."
    return f"Clean sidebar with {count} items. I can see {len(relevant)} that match what I need."


def _react_to_page(persona: Persona, objective: Objective, content: dict) -> str:
    if content["is_empty"]:
        if persona.voice.skepticism == "high":
            return f"It's empty. How do I get my existing {persona.industry.lower()} data in here? I have years of work that needs to be here before this is useful."
        return "Empty for now. I need to add some data to see if this works for me."

    if content["has_inputs"]:
        placeholders = content.get("input_placeholders", [])
        if placeholders:
            return f"I see an input field ({placeholders[0]}). Let me try entering something related to my work."
        return "There are input fields. Let me try using them."

    headings = content.get("headings", [])
    if headings:
        return f"I see '{headings[0]}'. Let me read through this and see what's useful."

    return "Page loaded. Let me explore what's here."


def _react_to_input_result(persona: Persona, objective: Objective, content: dict) -> str:
    if content["is_empty"]:
        baseline = objective.efficiency_baseline or "my current method"
        return f"I typed my query but nothing came back. Without data here, this isn't faster than {baseline}."
    buttons = content.get("buttons", [])
    if buttons:
        return f"Results appeared. I can see options: {', '.join(buttons[:3])}. Let me see if any match what I need."
    return "Something appeared after I typed. Let me review."


def _react_to_empty_state(persona: Persona, objective: Objective, page_name: str) -> str:
    baseline = objective.efficiency_baseline or "my current approach"
    if persona.voice.skepticism == "high":
        return f"The {page_name} is empty. Before this can replace {baseline}, I need a way to populate it with my existing knowledge."
    return f"Empty {page_name}. I'll need to add some data first."


def _quote_cant_find(persona: Persona, objective: Objective) -> str:
    """Generate an in-character quote about not finding what they need."""
    goal_short = objective.goal.lower()[:60]
    if persona.voice.motivation == "fear":
        return f"I can't find where to {goal_short}. In my field, not being able to access this quickly is a liability."
    if persona.voice.motivation == "compliance":
        return f"I need to be able to {goal_short} for audit purposes. Where is this capability?"
    return f"I expected to be able to {goal_short} from the sidebar, but I don't see an obvious path."


def _quote_empty_state(persona: Persona, objective: Objective, page_name: str) -> str:
    baseline = objective.efficiency_baseline or "my current process"
    return f"The {page_name} is empty. I need to import or enter my existing data — I can't start from scratch when I have years of {persona.industry.lower()} work in {baseline}."


def _is_relevant_to_persona(link: NavLink, persona: Persona) -> bool:
    """Check if a nav link is relevant to this persona's work."""
    text = link.text.lower()
    if persona.team_size <= 1:
        # Solo users — knowledge features are relevant, team features less so
        return any(k in text for k in ["workspace", "knowledge", "library", "profile", "setting"])
    else:
        # Team users — delegation features also relevant
        return any(k in text for k in ["workspace", "knowledge", "library", "profile", "agent",
                                        "expert", "delegation", "dashboard", "setting"])


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
