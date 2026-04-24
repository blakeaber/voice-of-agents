"""Diff reporting — compare current run to prior runs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from voice_of_agents.eval.config import VoAConfig

logger = logging.getLogger(__name__)


def generate_diff(config: VoAConfig) -> None:
    """Generate a diff report comparing the latest evaluation run to the prior one.

    Appends a section to 006-diff-report.md showing:
    - New findings added
    - Findings resolved since last run
    - Score changes on existing backlog items
    - Sentiment shifts per persona
    """
    results_path = config.results_path
    if not results_path.exists():
        logger.warning("No results directory found.")
        return

    # Collect per-persona run history
    persona_runs: dict[str, list[Path]] = {}
    for persona_dir in sorted(results_path.iterdir()):
        if not persona_dir.is_dir():
            continue
        runs = sorted(persona_dir.glob("*"))
        if len(runs) >= 1:
            persona_runs[persona_dir.name] = runs

    if not persona_runs:
        logger.warning("No persona runs found.")
        return

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"\n---\n\n## Diff Report — {run_date}\n",
    ]

    # Sentiment shifts (compare latest vs prior evaluation)
    sentiment_shifts = []
    for persona_slug, runs in persona_runs.items():
        if len(runs) < 2:
            continue

        current_eval = _load_eval(runs[-1])
        prior_eval = _load_eval(runs[-2])

        if current_eval and prior_eval:
            curr_overall = current_eval.get("scores", {}).get("overall", 0)
            prev_overall = prior_eval.get("scores", {}).get("overall", 0)
            if curr_overall != prev_overall:
                persona_id = current_eval.get("persona", {}).get("id", persona_slug)
                sentiment_shifts.append(
                    {
                        "persona": persona_id,
                        "previous_overall": prev_overall,
                        "current_overall": curr_overall,
                        "delta": curr_overall - prev_overall,
                    }
                )

    if sentiment_shifts:
        lines.append("### Sentiment Shifts\n")
        lines.append("| Persona | Previous | Current | Delta |")
        lines.append("|---------|----------|---------|-------|")
        for s in sorted(sentiment_shifts, key=lambda x: abs(x["delta"]), reverse=True):
            direction = "+" if s["delta"] > 0 else ""
            lines.append(
                f"| {s['persona']} | {s['previous_overall']} | {s['current_overall']} | {direction}{s['delta']} |"
            )
        lines.append("")
    else:
        lines.append("No sentiment shifts detected (first run or no prior evaluations).\n")

    # Summary
    total_personas = len(persona_runs)
    multi_run = sum(1 for runs in persona_runs.values() if len(runs) >= 2)
    lines.append(
        f"**Summary:** {total_personas} personas evaluated, {multi_run} with prior runs for comparison.\n"
    )

    # Append to diff report
    config.diff_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config.diff_report_path, "a") as f:
        f.write("\n".join(lines) + "\n")

    logger.info("Diff report appended to %s", config.diff_report_path)


def _load_eval(run_dir: Path) -> dict | None:
    """Load evaluation YAML from a run directory."""
    eval_path = run_dir / "003-evaluation.yaml"
    if eval_path.exists():
        try:
            return yaml.safe_load(eval_path.read_text())
        except Exception:
            return None
    return None
