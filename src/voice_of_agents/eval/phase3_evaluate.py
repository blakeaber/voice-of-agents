"""Phase 3: Synthetic focus group evaluation.

Generates in-character persona evaluations from Phase 2 exploration results.
Uses LLM (Anthropic Claude) when available for authentic voice; falls back
to structured template generation. Validates score-narrative consistency.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import yaml

from voice_of_agents.core.persona import Persona
from voice_of_agents.eval.config import VoAConfig

logger = logging.getLogger(__name__)


def evaluate_personas(personas: list[Persona], config: VoAConfig) -> None:
    """Generate in-character evaluations for each persona."""
    for persona in personas:
        logger.info("Evaluating as %s (%s)...", persona.name, persona.id)

        exploration = _load_latest_exploration(config, persona)
        if not exploration:
            logger.warning("No exploration results for %s. Run phase2 first.", persona.id)
            continue

        # Generate evaluation — LLM if available, template fallback
        if os.environ.get("ANTHROPIC_API_KEY"):
            evaluation = _llm_generate_evaluation(persona, exploration)
        else:
            evaluation = _template_generate_evaluation(persona, exploration)

        # Validate score-narrative consistency
        issues = _validate_evaluation(evaluation)
        if issues:
            logger.warning("  Validation issues for %s: %s", persona.id, issues)
            evaluation = _fix_consistency(evaluation, issues)

        # Write to same timestamped directory
        persona_dir = config.results_path / persona.slug
        runs = sorted(persona_dir.glob("*"))
        if runs:
            eval_path = runs[-1] / "003-evaluation.yaml"
            eval_path.write_text(yaml.dump(evaluation, default_flow_style=False, sort_keys=False))
            logger.info("  Evaluation written to %s", eval_path)

    _append_cross_persona_analysis(personas, config)


# ── LLM-Backed Evaluation ─────────────────────────────────────────────

def _llm_generate_evaluation(persona: Persona, exploration: dict) -> dict:
    """Generate evaluation using Anthropic Claude with voice calibration."""
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed. Falling back to template.")
        return _template_generate_evaluation(persona, exploration)

    voice = _build_voice_profile(persona)
    journey_text = _format_journey_for_llm(exploration)
    tier_price = {"FREE": 0, "DEVELOPER": 29, "TEAM": 99, "ENTERPRISE": 299}.get(persona.tier.value, 29)
    exp_years = persona.experience_years or 0
    income = persona.income or 0

    if not journey_text.strip():
        journey_text = (
            "You visited the landing page but could not complete account creation "
            "(signup failed). You only saw the marketing copy and the signup form. "
            "You never made it inside the product."
        )
        experience_context = "Based on this first-contact experience (landing page + failed signup), provide your honest evaluation."
    else:
        experience_context = "Based on THIS SPECIFIC experience (not hypothetical), provide your honest evaluation."

    prompt = f"""You are {persona.name}, a {persona.role} with {exp_years} years of experience in {persona.industry}. Your annual income is ${income:,}. {voice['motivation_framing']}

You just tried Rooben Pro for the first time. Here's exactly what happened during your session:

{journey_text}

{experience_context}

SCORING (1-10 each):
- overall: Your overall impression
- goal_achievement: How close did you get to what you came here to do?
- efficiency: Was this faster than {voice['comparison_baseline']}?
- trust: Do you trust this tool enough to use it in your {persona.industry.lower()} work?
- learnability: Could you figure it out without help?
- value_for_price: Worth ${tier_price}/month given your ${income:,}/year income?

NARRATIVE (2-3 sentences each, in YOUR voice — {voice['vocabulary_style']} vocabulary, {voice['skepticism_level']} skepticism):
- first_impression: Your gut reaction on first seeing the app
- highlight_moment: The best part of the experience (reference a specific thing you saw)
- frustration_moment: The worst part (what blocked you or confused you)
- feature_request: The #1 thing you wish existed (in YOUR words, not technical jargon)
- objection: Why you might NOT pay for this
- would_recommend: Who you'd tell about it and what you'd say

VERDICT:
- would_pay: true/false at ${tier_price}/month
- would_recommend: true/false
- retention_risk: low/medium/high

UNMET NEEDS (list what you COULDN'T do that you came here to do):
Each with: need, pain_theme (A=retrieval failure, B=bus factor, C=context failure, D=trust deficit, E=governance vacuum, F=integration failure), severity (1-10), persona_quote (in your voice)

RULES:
- {voice['trust_bar']}
- Your scores must match your narrative. If you're frustrated, your scores should reflect it.
- If a feature was missing, you should express genuine disappointment, not polite acceptance.
- Reference your actual {persona.industry.lower()} work context, not generic examples.

Respond as valid YAML with keys: scores, narrative, verdict, unmet_needs"""

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        yaml_text = response.content[0].text
        # Clean up: remove ```yaml markers if present
        if yaml_text.startswith("```"):
            yaml_text = yaml_text.split("\n", 1)[1]
        if yaml_text.endswith("```"):
            yaml_text = yaml_text.rsplit("```", 1)[0]

        parsed = yaml.safe_load(yaml_text)

        # Build full evaluation structure
        return {
            "persona": _persona_header(persona),
            "run_date": exploration.get("run_timestamp", ""),
            "generation_method": "llm",
            "scores": parsed.get("scores", {}),
            "narrative": parsed.get("narrative", {}),
            "verdict": parsed.get("verdict", {}),
            "unmet_needs": parsed.get("unmet_needs", []),
        }

    except Exception as e:
        logger.warning("LLM evaluation failed for %s: %s. Falling back to template.", persona.id, e)
        return _template_generate_evaluation(persona, exploration)


# ── Template Fallback Evaluation ───────────────────────────────────────

def _template_generate_evaluation(persona: Persona, exploration: dict) -> dict:
    """Generate evaluation using structured templates (no LLM required)."""
    objectives = exploration.get("objectives", [])
    voice = _build_voice_profile(persona)

    # Extract outcomes and friction
    outcomes = [obj.get("outcome", "not_attempted") for obj in objectives]
    all_friction = []
    all_missing = []
    all_journey_steps = []
    pages_visited = set()
    for obj in objectives:
        all_friction.extend(obj.get("friction_points", []))
        all_missing.extend(obj.get("missing_capabilities", []))
        all_journey_steps.extend(obj.get("journey", []))
        pages_visited.update(obj.get("pages_visited", []))

    achieved = outcomes.count("achieved")
    partial = outcomes.count("partial")
    blocked = outcomes.count("blocked")
    total = max(len(outcomes), 1)

    # ── Score calculation with consistency enforcement ──
    goal_score = min(10, max(1, round((achieved * 10 + partial * 5 + blocked * 1) / total)))

    # Efficiency is capped relative to goal achievement
    raw_efficiency = max(1, 8 - len(all_friction) * 2)
    efficiency_score = min(raw_efficiency, goal_score + 2)

    # Trust score based on persona skepticism + friction severity
    trust_base = 5 if voice["skepticism_level"] == "high" else 7
    critical_friction = [f for f in all_friction if f.get("severity") in ("high", "critical")]
    trust_score = max(1, trust_base - len(critical_friction))

    # Learnability capped by goal achievement
    raw_learn = max(1, 8 - blocked * 3)
    learn_score = min(raw_learn, goal_score + 3)

    # Value depends on goal achievement and price sensitivity
    value_base = round((goal_score + efficiency_score) / 2)
    if persona.voice.price_sensitivity == "high":
        value_base -= 2
    elif persona.voice.price_sensitivity == "low":
        value_base += 1
    value_score = max(1, min(10, value_base))

    # Overall is average, but cannot exceed best individual + 1
    overall = round((goal_score + efficiency_score + trust_score + learn_score + value_score) / 5)
    overall = min(overall, max(goal_score, efficiency_score, trust_score, learn_score, value_score) + 1)

    # ── Voice-calibrated narrative ──
    tier_price = {"FREE": 0, "DEVELOPER": 29, "TEAM": 99, "ENTERPRISE": 299}.get(persona.tier.value, 29)
    exp_years = persona.experience_years or 0
    income = persona.income or 0

    # First impression
    if persona.voice.skepticism == "high":
        first_impression = (
            f"As someone with {exp_years} years in {persona.industry.lower()}, "
            f"I've seen many tools promise to solve my problems. The interface is clean, "
            f"but I need to see it work with my actual {persona.industry.lower()} data."
        )
    else:
        first_impression = (
            f"The signup was quick and it asked what I care about — {persona.industry.lower()} "
            f"knowledge management. That's a good start."
        )

    # Highlight — reference something specific from the journey
    highlight = "The onboarding asked about my goals and customized the interface accordingly."
    if len(pages_visited) > 1:
        highlight = (
            f"I was able to navigate to {len(pages_visited)} different pages. "
            f"The sidebar was focused on what's relevant to my work."
        )

    # Frustration — use actual friction points, not raw descriptions
    if all_friction:
        top = all_friction[0]
        desc = top.get("description", "")
        if "empty" in desc.lower():
            frustration = (
                f"Everything is empty. I have years of {persona.industry.lower()} knowledge "
                f"that needs to be here before this tool becomes useful. "
                f"There's no way to import what I already have."
            )
        elif "gap" in top.get("type", ""):
            obj_goal = objectives[0].get("objective", "") if objectives else ""
            frustration = (
                f"I came here to {obj_goal.lower()}, but I couldn't find a clear path to do that. "
                f"The navigation didn't match what I was looking for."
            )
        else:
            frustration = (
                f"I ran into an issue: {desc}. "
                f"In {persona.industry.lower()}, this kind of friction wastes time I don't have."
            )
    elif all_missing:
        frustration = (
            f"I need the ability to {all_missing[0].lower()}, "
            f"but it doesn't seem to exist yet."
        )
    else:
        frustration = (
            f"Without any of my existing data loaded, it's hard to tell "
            f"if this will actually be faster than {voice['comparison_baseline']}."
        )

    # Feature request in persona language
    if all_missing:
        request = (
            f"I need a way to {all_missing[0].lower()}. "
            f"That's the difference between a demo and something I'd actually use daily."
        )
    elif all_friction:
        request = f"Fix the {all_friction[0].get('type', 'issue')} I encountered — it blocked my primary workflow."
    else:
        request = (
            f"A way to import my existing {persona.industry.lower()} knowledge "
            f"so I'm not starting from zero."
        )

    # Objection calibrated to motivation
    if persona.voice.motivation == "fear":
        objection = (
            f"I need to be certain this won't give me wrong information. "
            f"In {persona.industry.lower()}, incorrect guidance creates liability. "
            f"I haven't seen enough to trust it with real cases yet."
        )
    elif persona.voice.motivation == "compliance":
        objection = (
            f"Can I prove to an auditor where every answer came from? "
            f"Without source attribution and an audit trail, I can't use this professionally."
        )
    else:
        objection = (
            f"At ${tier_price}/month against my ${income:,}/year income, "
            f"I need to see clear ROI in the first month. Right now it's too early to tell."
        )

    # Would recommend
    if overall >= 7:
        would_rec_text = (
            f"I'd tell colleagues in {persona.industry.lower()} to try it. "
            f"The concept is solid even if some features are still needed."
        )
    elif overall >= 5:
        would_rec_text = (
            f"I'd mention it to a colleague, but with caveats — "
            f"it's promising but not quite ready for my {persona.industry.lower()} workflow."
        )
    else:
        would_rec_text = (
            f"Not yet. I'd wait until it can handle my actual {persona.industry.lower()} "
            f"use case before recommending it."
        )

    # Verdict
    would_pay = overall >= 6 and value_score >= 5 and goal_score >= 4
    retention_risk = "low" if overall >= 7 else ("high" if overall <= 4 else "medium")

    upgrade_trigger = "When core features work reliably end-to-end without workarounds"
    churn_trigger = (
        f"If it gives incorrect {persona.industry.lower()} guidance, "
        f"or if I can't import my existing data within the trial period"
    )

    # Unmet needs
    unmet_needs = []
    for f in all_friction:
        unmet_needs.append({
            "need": f.get("description", ""),
            "pain_theme": _classify_theme(f.get("description", "")),
            "severity": {"low": 3, "medium": 5, "high": 7, "critical": 9}.get(f.get("severity", "medium"), 5),
            "persona_quote": f.get("persona_quote") or _generate_quote(persona, f),
        })
    for m in all_missing:
        unmet_needs.append({
            "need": m,
            "pain_theme": _classify_theme(m),
            "severity": 7,
            "persona_quote": _generate_missing_quote(persona, m),
        })

    return {
        "persona": _persona_header(persona),
        "run_date": exploration.get("run_timestamp", ""),
        "generation_method": "template",
        "scores": {
            "overall": overall,
            "goal_achievement": goal_score,
            "efficiency": efficiency_score,
            "trust": trust_score,
            "learnability": learn_score,
            "value_for_price": value_score,
        },
        "narrative": {
            "first_impression": first_impression,
            "highlight_moment": highlight,
            "frustration_moment": frustration,
            "feature_request": request,
            "objection": objection,
            "would_recommend": would_rec_text,
        },
        "verdict": {
            "would_pay": would_pay,
            "would_recommend": overall >= 7,
            "retention_risk": retention_risk,
            "upgrade_trigger": upgrade_trigger,
            "churn_trigger": churn_trigger,
        },
        "unmet_needs": unmet_needs,
    }


# ── Voice Calibration ─────────────────────────────────────────────────

def _build_voice_profile(persona: Persona) -> dict:
    """Build structured voice calibration parameters."""
    # Skepticism
    exp_years = persona.experience_years or 0
    if exp_years >= 10:
        skepticism = "high"
    elif exp_years >= 5:
        skepticism = "moderate"
    else:
        skepticism = "low"

    # Override with explicit voice setting
    if persona.voice.skepticism == "high":
        skepticism = "high"

    # Vocabulary
    vocab_map = {
        "legal": "legal and regulatory terminology",
        "medical": "clinical and medical terminology",
        "financial": "financial and accounting terminology",
        "technical": "technical and engineering terminology",
    }
    vocabulary = vocab_map.get(persona.voice.vocabulary, f"{persona.industry.lower()} professional language")

    # Motivation framing
    motiv_map = {
        "fear": f"You're driven by the fear of making a mistake in your {persona.industry.lower()} work. Errors have real consequences.",
        "compliance": f"You're driven by regulatory compliance. Everything must be auditable and defensible.",
        "efficiency": f"You're driven by efficiency. Time is money — you need tools that make you faster.",
        "legacy": f"You're protecting institutional knowledge. When people leave, knowledge shouldn't leave with them.",
        "ambition": f"You're building something. You want leverage — tools that multiply your output.",
    }
    motivation = motiv_map.get(persona.voice.motivation, "You want tools that help you do better work.")

    comparison = "my current manual process"

    # Trust bar
    trust_reqs = persona.trust_requirements
    trust_bar = (
        f"Your trust requirements: {'; '.join(trust_reqs)}"
        if trust_reqs
        else f"As a {persona.industry.lower()} professional, you need to trust the tool's outputs before acting on them."
    )

    return {
        "skepticism_level": skepticism,
        "vocabulary_style": vocabulary,
        "motivation_framing": motivation,
        "comparison_baseline": comparison,
        "trust_bar": trust_bar,
        "price_anchor": f"${_monthly_price(persona)}/mo against ${persona.income:,}/yr income" if persona.income else f"${_monthly_price(persona)}/mo",
    }


# ── Validation ─────────────────────────────────────────────────────────

def _validate_evaluation(evaluation: dict) -> list[str]:
    """Validate score-narrative consistency. Returns list of issues."""
    issues = []
    scores = evaluation.get("scores", {})
    narrative = evaluation.get("narrative", {})
    verdict = evaluation.get("verdict", {})

    overall = scores.get("overall") or 5
    goal = scores.get("goal_achievement") or 5
    trust = scores.get("trust") or 5
    value = scores.get("value_for_price") or 5
    efficiency = scores.get("efficiency") or 5

    # Goal achievement vs overall
    if goal <= 3 and overall >= 7:
        issues.append(f"overall={overall} but goal_achievement={goal} — inconsistent")

    # Efficiency can't wildly exceed goal achievement
    if efficiency > goal + 3:
        issues.append(f"efficiency={efficiency} but goal_achievement={goal} — gap too large")

    # Trust score vs trust narrative
    frustration = (narrative.get("frustration_moment", "") + narrative.get("objection", "")).lower()
    if trust >= 8 and any(k in frustration for k in ["trust", "worry", "concern", "certain", "liability", "audit"]):
        issues.append(f"trust={trust} but narrative expresses trust concerns")

    # Value vs would_pay
    if value <= 3 and verdict.get("would_pay"):
        issues.append(f"value_for_price={value} but would_pay=true")
    if value >= 7 and not verdict.get("would_pay"):
        issues.append(f"value_for_price={value} but would_pay=false")

    # Retention risk vs overall
    risk = verdict.get("retention_risk", "medium")
    if overall >= 8 and risk == "high":
        issues.append(f"overall={overall} but retention_risk=high")
    if overall <= 3 and risk == "low":
        issues.append(f"overall={overall} but retention_risk=low")

    return issues


def _fix_consistency(evaluation: dict, issues: list[str]) -> dict:
    """Adjust scores to fix consistency issues."""
    scores = evaluation["scores"]
    verdict = evaluation["verdict"]

    goal = scores["goal_achievement"]
    overall = scores["overall"]

    # Cap overall relative to goal
    if goal <= 3 and overall >= 7:
        scores["overall"] = min(overall, goal + 3)

    # Cap efficiency relative to goal
    if scores["efficiency"] > goal + 3:
        scores["efficiency"] = goal + 3

    # Fix value vs would_pay
    if scores["value_for_price"] <= 3:
        verdict["would_pay"] = False
    if scores["value_for_price"] >= 7 and scores["goal_achievement"] >= 5:
        verdict["would_pay"] = True

    # Fix retention risk vs overall
    recalc_overall = scores["overall"]
    if recalc_overall >= 7:
        verdict["retention_risk"] = "low"
    elif recalc_overall <= 4:
        verdict["retention_risk"] = "high"
    else:
        verdict["retention_risk"] = "medium"

    # Recalculate overall as average
    all_scores = [scores["goal_achievement"], scores["efficiency"], scores["trust"],
                  scores["learnability"], scores["value_for_price"]]
    scores["overall"] = round(sum(all_scores) / len(all_scores))

    return evaluation


# ── Helpers ────────────────────────────────────────────────────────────

def _persona_header(persona: Persona) -> dict:
    return {
        "id": persona.id,
        "name": persona.name,
        "role": persona.role,
        "industry": persona.industry,
        "experience_years": persona.experience_years,
        "tier": persona.tier.value,
        "income": persona.income,
    }


def _format_journey_for_llm(exploration: dict) -> str:
    """Format exploration journey for LLM prompt."""
    lines = []
    for obj in exploration.get("objectives", []):
        lines.append(f"\n**Objective: {obj.get('objective', '?')}**")
        lines.append(f"Outcome: {obj.get('outcome', '?')}")
        lines.append(f"Pages visited: {obj.get('pages_visited', [])}")

        for step in obj.get("journey", []):
            lines.append(f"  Action: {step.get('action', '')}")
            lines.append(f"  Observation: {step.get('observation', '')}")

        for fp in obj.get("friction_points", []):
            lines.append(f"  FRICTION [{fp.get('severity', 'medium')}]: {fp.get('description', '')}")

        for mc in obj.get("missing_capabilities", []):
            lines.append(f"  MISSING: {mc}")

    return "\n".join(lines)


def _load_latest_exploration(config: VoAConfig, persona: Persona) -> dict | None:
    persona_dir = config.results_path / persona.slug
    if not persona_dir.exists():
        return None
    runs = sorted(persona_dir.glob("*"))
    if not runs:
        return None
    path = runs[-1] / "002-exploration.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text())


def _monthly_price(persona: Persona) -> int:
    return {"FREE": 0, "DEVELOPER": 29, "TEAM": 99, "ENTERPRISE": 299}.get(persona.tier.value, 29)


def _classify_theme(description: str) -> str:
    d = description.lower()
    if any(k in d for k in ["find", "search", "retrieve", "locate", "navigation"]):
        return "A"
    if any(k in d for k in ["bottleneck", "single point", "bus factor", "delegate"]):
        return "B"
    if any(k in d for k in ["context", "irrelevant", "wrong", "empty"]):
        return "C"
    if any(k in d for k in ["trust", "verify", "accurate", "hallucinate"]):
        return "D"
    if any(k in d for k in ["governance", "audit", "compliance", "visibility"]):
        return "E"
    if any(k in d for k in ["integrate", "import", "connect", "external"]):
        return "F"
    return "A"


def _generate_quote(persona: Persona, friction: dict) -> str:
    desc = friction.get("description", "").lower()
    if "empty" in desc:
        return f"Everything is empty. I need my existing {persona.industry.lower()} data here before this is useful."
    if "navigation" in desc or "path" in desc:
        return f"I couldn't find a clear way to do what I came here for. That's frustrating."
    return f"I ran into an issue with {desc[:50]}. In {persona.industry.lower()}, this kind of thing slows me down."


def _generate_missing_quote(persona: Persona, capability: str) -> str:
    return (
        f"I expected to be able to {capability.lower()}, but it's not available. "
        f"For my {persona.industry.lower()} work, this is essential."
    )


def _append_cross_persona_analysis(personas: list[Persona], config: VoAConfig) -> None:
    """Append cross-persona analysis section."""
    evaluations = []
    for persona in personas:
        persona_dir = config.results_path / persona.slug
        if not persona_dir.exists():
            continue
        runs = sorted(persona_dir.glob("*"))
        if not runs:
            continue
        eval_path = runs[-1] / "003-evaluation.yaml"
        if eval_path.exists():
            evaluations.append(yaml.safe_load(eval_path.read_text()))

    if not evaluations:
        return

    from datetime import datetime, timezone
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"\n---\n\n## Cross-Persona Analysis — {run_date}\n",
        f"Personas evaluated: {len(evaluations)}\n",
        "\n### Score Summary\n",
        "| Persona | Role | Tier | Overall | Goal | Efficiency | Trust | Learn | Value |",
        "|---------|------|------|---------|------|------------|-------|-------|-------|",
    ]

    for ev in evaluations:
        p = ev.get("persona", {})
        s = ev.get("scores", {})
        lines.append(
            f"| {p.get('id', '?')} {p.get('name', '?')} | {p.get('role', '?')} | {p.get('tier', '?')} "
            f"| {s.get('overall', '?')} | {s.get('goal_achievement', '?')} "
            f"| {s.get('efficiency', '?')} | {s.get('trust', '?')} "
            f"| {s.get('learnability', '?')} | {s.get('value_for_price', '?')} |"
        )

    # Verdict summary
    would_pay = sum(1 for ev in evaluations if ev.get("verdict", {}).get("would_pay"))
    high_risk = sum(1 for ev in evaluations if ev.get("verdict", {}).get("retention_risk") == "high")
    lines.extend([
        "",
        f"**Would pay:** {would_pay}/{len(evaluations)}",
        f"**High retention risk:** {high_risk}/{len(evaluations)}",
    ])

    # Unmet needs summary
    all_needs = []
    for ev in evaluations:
        all_needs.extend(ev.get("unmet_needs", []))

    if all_needs:
        lines.extend(["\n### Top Unmet Needs\n"])
        from collections import Counter
        themes = Counter(n.get("pain_theme", "?") for n in all_needs)
        for theme, count in themes.most_common():
            theme_name = config.pain_themes.get(theme, theme)
            lines.append(f"- **Theme {theme} ({theme_name})**: {count} mentions")

    content = "\n".join(lines) + "\n"
    config.focus_group_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config.focus_group_path, "a") as f:
        f.write(content)
    logger.info("Cross-persona analysis appended to %s", config.focus_group_path)
