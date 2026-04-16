"""Phase 5: Backlog prioritization — score findings and update the append-only backlog."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from voice_of_agents.eval.config import VoAConfig
from voice_of_agents.core.backlog import (
    BacklogItem,
    add_item,
    materialize_backlog,
    update_score,
)

logger = logging.getLogger(__name__)

# Effort estimates mapped to inverse scores
EFFORT_SCORES = {
    "trivial": 1.0,
    "small": 0.8,
    "medium": 0.5,
    "large": 0.3,
    "epic": 0.1,
}

# Tier weights for revenue impact
TIER_WEIGHTS = {
    "FREE": 0.10,
    "DEVELOPER": 0.30,
    "TEAM": 0.60,
    "ENTERPRISE": 1.00,
}


def prioritize_backlog(config: VoAConfig) -> None:
    """Score findings and update the append-only backlog.

    Reads findings and evaluations, calculates priority scores,
    and appends new items or updates existing scores in the JSONL log.
    """
    # Load findings
    findings = _load_findings(config.findings_path)
    if not findings:
        logger.warning("No findings to score. Run phase4 first.")
        return

    # Load persona evaluations for tier mapping
    persona_tiers = _load_persona_tiers(config.results_path)
    total_personas = max(len(persona_tiers), 1)

    # Load current backlog state
    existing_items = {item.id: item for item in materialize_backlog(config.backlog_jsonl_path)}

    for finding in findings:
        # Skip already-resolved findings
        if finding.get("status") == "resolved":
            continue

        finding_id = finding["id"]
        personas = finding.get("evidence", {}).get("personas_affected", [])
        severity = finding.get("impact", {}).get("severity", 5)
        theme = finding.get("classification", {}).get("pain_theme", "A")

        # Calculate scores
        coverage = len(personas) / total_personas
        pain = severity / 10
        revenue = _revenue_score(personas, persona_tiers)
        effort = _estimate_effort(finding)
        effort_inv = EFFORT_SCORES.get(effort, 0.5)

        # Weighted score
        score = (
            coverage * config.weight_coverage +
            pain * config.weight_pain +
            revenue * config.weight_revenue +
            effort_inv * config.weight_effort
        ) * 100

        # Check if this finding already has a backlog item
        backlog_id = f"B-{finding_id.replace('F-', '')}"

        if backlog_id in existing_items:
            # Update score if changed
            old_score = existing_items[backlog_id].score
            if abs(old_score - score) > 1:
                update_score(
                    config.backlog_jsonl_path,
                    backlog_id,
                    old_score,
                    round(score, 1),
                    reason=f"Re-scored from {len(personas)} personas",
                )
                logger.info("Updated %s score: %.1f → %.1f", backlog_id, old_score, score)
        else:
            # Add new item
            quotes = [
                {"persona": q.get("persona", ""), "quote": q.get("quote", "")}
                for q in finding.get("evidence", {}).get("representative_quotes", [])
            ]

            item = BacklogItem(
                id=backlog_id,
                title=finding.get("title", "Untitled"),
                description=finding.get("description", ""),
                source="eval",
                score=round(score, 1),
                finding_id=finding_id,
                personas=_to_int_ids(personas),
                pain_themes=[theme],
                effort=effort,
                status="open",
                persona_quotes=quotes,
                coverage_score=round(coverage, 3),
                pain_score=round(pain, 3),
                revenue_score=round(revenue, 3),
                effort_score=round(effort_inv, 3),
            )

            add_item(config.backlog_jsonl_path, item)
            logger.info("Added %s: %s (score: %.1f)", backlog_id, item.title, score)

    # Summary
    all_items = materialize_backlog(config.backlog_jsonl_path)
    open_items = [i for i in all_items if i.status == "open"]
    logger.info(
        "Backlog: %d total items (%d open), top score: %.1f",
        len(all_items),
        len(open_items),
        open_items[0].score if open_items else 0,
    )


def _load_findings(path: Path) -> list[dict]:
    """Parse findings from the markdown findings file.

    This is a simple parser that extracts finding blocks from the
    structured markdown format. Each finding starts with ### F-xxx.
    """
    if not path.exists():
        return []

    text = path.read_text()
    findings = []

    # Split by finding headers
    sections = re.split(r"### (F-\d+):", text)
    for i in range(1, len(sections), 2):
        finding_id = sections[i]
        content = sections[i + 1] if i + 1 < len(sections) else ""

        # Parse structured fields
        finding: dict = {"id": finding_id, "status": "open"}

        title_match = re.match(r"\s*(.+?)(?:\n|$)", content)
        if title_match:
            finding["title"] = title_match.group(1).strip()

        # Extract type and theme
        type_match = re.search(r"\*\*Type:\*\*\s*(\w+)", content)
        if type_match:
            finding["type"] = type_match.group(1)

        theme_match = re.search(r"\*\*Theme:\*\*\s*(\w)", content)
        if theme_match:
            finding.setdefault("classification", {})["pain_theme"] = theme_match.group(1)

        severity_match = re.search(r"\*\*Severity:\*\*\s*([\d.]+)", content)
        if severity_match:
            finding.setdefault("impact", {})["severity"] = float(severity_match.group(1))

        personas_match = re.search(r"\*\*Personas:\*\*\s*(.+?)(?:\n|$)", content)
        if personas_match:
            persona_text = personas_match.group(1)
            persona_ids = re.findall(r"UXW-\d+", persona_text)
            finding.setdefault("evidence", {})["personas_affected"] = persona_ids

        status_match = re.search(r"\*\*Status:\*\*\s*(\w+)", content)
        if status_match:
            finding["status"] = status_match.group(1)

        # Extract quotes
        quotes = re.findall(r'>\s*"(.+?)"\s*—\s*(UXW-\d+)', content)
        if quotes:
            finding.setdefault("evidence", {})["representative_quotes"] = [
                {"quote": q, "persona": p} for q, p in quotes
            ]

        findings.append(finding)

    return findings


def _load_persona_tiers(results_path: Path) -> dict[str, str]:
    """Load persona ID → tier mapping from evaluation files."""
    tiers: dict[str, str] = {}
    if not results_path.exists():
        return tiers

    for persona_dir in results_path.iterdir():
        if not persona_dir.is_dir():
            continue
        runs = sorted(persona_dir.glob("*"))
        if not runs:
            continue
        eval_path = runs[-1] / "003-evaluation.yaml"
        if eval_path.exists():
            try:
                ev = yaml.safe_load(eval_path.read_text())
                pid = ev.get("persona", {}).get("id", "")
                tier = ev.get("persona", {}).get("tier", "DEVELOPER")
                if pid:
                    tiers[pid] = tier
            except Exception:
                pass

    return tiers


def _revenue_score(personas: list[str], tiers: dict[str, str]) -> float:
    """Calculate revenue impact from affected personas' tiers."""
    if not personas:
        return 0.0
    weights = [TIER_WEIGHTS.get(tiers.get(p, "DEVELOPER"), 0.3) for p in personas]
    return max(weights) if weights else 0.3


def _to_int_ids(persona_ids: list) -> list[int]:
    """Convert persona IDs (str or int) to int, parsing UXW-style IDs."""
    result = []
    for p in persona_ids:
        if isinstance(p, int):
            result.append(p)
        elif isinstance(p, str):
            m = re.search(r"\d+", p)
            if m:
                result.append(int(m.group()))
    return result


def _estimate_effort(finding: dict) -> str:
    """Estimate implementation effort from finding type and description.

    Simple heuristic — production systems would use human estimates.
    """
    title = (finding.get("title", "") + " " + finding.get("description", "")).lower()

    if any(k in title for k in ["empty state", "placeholder", "text", "label", "copy"]):
        return "trivial"
    if any(k in title for k in ["button", "link", "cta", "badge", "banner"]):
        return "small"
    if any(k in title for k in ["import", "export", "integration", "api"]):
        return "large"
    if any(k in title for k in ["bulk", "migration", "infrastructure", "architecture"]):
        return "epic"

    return "medium"
