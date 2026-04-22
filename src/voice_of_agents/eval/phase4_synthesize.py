"""Phase 4: Finding synthesis — aggregate persona evaluations into structured findings."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

from voice_of_agents.eval.config import VoAConfig

logger = logging.getLogger(__name__)


def synthesize_findings(config: VoAConfig) -> None:
    """Aggregate all persona evaluations into deduplicated findings.

    Scans all evaluation files, groups unmet needs by similarity,
    counts affected personas, and appends findings to 004-findings.md.
    """
    # Collect all evaluations
    evaluations = _load_all_evaluations(config.results_path)
    if not evaluations:
        logger.warning("No evaluations found. Run phase3 first.")
        return

    logger.info("Synthesizing findings from %d evaluations", len(evaluations))

    # Extract all unmet needs
    all_needs: list[dict] = []
    for ev in evaluations:
        persona_id = ev.get("persona", {}).get("id", "?")
        for need in ev.get("unmet_needs", []):
            need["_persona_id"] = persona_id
            all_needs.append(need)

    if not all_needs:
        logger.info("No unmet needs found across evaluations.")
        return

    # Group by theme
    by_theme: dict[str, list[dict]] = defaultdict(list)
    for need in all_needs:
        by_theme[need.get("pain_theme", "A")].append(need)

    # Deduplicate within themes (group similar descriptions)
    findings = []
    finding_id = 1

    for theme, needs in sorted(by_theme.items()):
        # Simple grouping: cluster by first significant word
        clusters: dict[str, list[dict]] = defaultdict(list)
        for need in needs:
            key = _cluster_key(need.get("need", ""))
            clusters[key].append(need)

        for cluster_key, cluster_needs in clusters.items():
            personas_affected = list({n["_persona_id"] for n in cluster_needs})
            avg_severity = sum(n.get("severity", 5) for n in cluster_needs) / len(cluster_needs)
            quotes = [
                {"persona": n["_persona_id"], "quote": n.get("persona_quote", "")}
                for n in cluster_needs if n.get("persona_quote")
            ][:3]

            findings.append({
                "id": f"F-{finding_id:03d}",
                "type": "gap" if avg_severity >= 7 else "request",
                "title": cluster_needs[0].get("need", "Unknown need"),
                "description": f"Reported by {len(personas_affected)} persona(s). Theme: {theme}.",
                "evidence": {
                    "personas_affected": personas_affected,
                    "persona_count": len(personas_affected),
                    "coverage": round(len(personas_affected) / max(len(evaluations), 1), 2),
                    "representative_quotes": quotes,
                },
                "classification": {
                    "pain_theme": theme,
                    "segment": _classify_segment(len(personas_affected), len(evaluations)),
                },
                "impact": {
                    "severity": round(avg_severity, 1),
                    "breadth": round(len(personas_affected) / max(len(evaluations), 1), 2),
                },
                "status": "open",
                "first_reported": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            finding_id += 1

    # Sort by persona count descending
    findings.sort(key=lambda f: f["evidence"]["persona_count"], reverse=True)

    # Append to findings file
    _append_findings(findings, config.findings_path, len(evaluations))
    logger.info("Synthesized %d findings from %d evaluations", len(findings), len(evaluations))


def _load_all_evaluations(results_path: Path) -> list[dict]:
    """Load the latest evaluation for each persona."""
    evaluations = []
    if not results_path.exists():
        return evaluations

    for persona_dir in sorted(results_path.iterdir()):
        if not persona_dir.is_dir():
            continue
        runs = sorted(persona_dir.glob("*"))
        if not runs:
            continue
        eval_path = runs[-1] / "003-evaluation.yaml"
        if eval_path.exists():
            try:
                evaluations.append(yaml.safe_load(eval_path.read_text()))
            except Exception as e:
                logger.warning("Failed to load %s: %s", eval_path, e)

    return evaluations


def _cluster_key(description: str) -> str:
    """Generate a simple clustering key from a need description."""
    words = description.lower().split()
    # Use first 3 significant words
    stop_words = {"the", "a", "an", "to", "for", "of", "in", "on", "is", "it", "no", "not", "i"}
    significant = [w for w in words if w not in stop_words][:3]
    return " ".join(significant) if significant else description[:30]


def _classify_segment(persona_count: int, total: int) -> str:
    if total == 0:
        return "unknown"
    ratio = persona_count / total
    if ratio >= 0.7:
        return "universal"
    if ratio >= 0.3:
        return "segment"
    return "niche"


def _append_findings(findings: list[dict], path: Path, eval_count: int) -> None:
    """Append findings section to the findings markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"\n---\n\n## Findings — {run_date} ({eval_count} personas evaluated)\n",
    ]

    for f in findings:
        lines.append(f"### {f['id']}: {f['title']}")
        lines.append(f"**Type:** {f['type']} | **Theme:** {f['classification']['pain_theme']} "
                      f"| **Severity:** {f['impact']['severity']} | **Breadth:** {f['impact']['breadth']}")
        personas_list = [str(p) for p in f['evidence']['personas_affected']]
        lines.append(f"**Personas:** {', '.join(personas_list)} "
                      f"({f['evidence']['persona_count']}/{eval_count})")
        lines.append(f"**Status:** {f['status']}")

        for q in f["evidence"].get("representative_quotes", []):
            lines.append(f'> "{q["quote"]}" — {q["persona"]}')
        lines.append("")

    with open(path, "a") as fh:
        fh.write("\n".join(lines) + "\n")
