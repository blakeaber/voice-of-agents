"""voa bridge — cross-layer integration commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table


@click.group("bridge")
def bridge_cli():
    """Cross-layer integration between design and eval."""
    pass


@bridge_cli.command("status")
def bridge_status_cmd():
    """Show per-persona design vs eval coverage."""
    from voice_of_agents.eval.bridge import bridge_status
    from voice_of_agents.eval.config import VoAConfig

    config = VoAConfig.load()
    result = bridge_status(config)
    console = Console()
    table = Table(title="Bridge Status — Design vs Eval Coverage")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Name")
    table.add_column("Design Mapping", justify="center")
    table.add_column("Eval Results", justify="center")
    table.add_column("Goals", justify="right")
    for p in result["personas"]:
        table.add_row(
            str(p["id"]),
            p["name"],
            "[green]✓[/green]" if p["has_design_mapping"] else "[dim]—[/dim]",
            "[green]✓[/green]" if p["has_eval_results"] else "[dim]—[/dim]",
            str(p["goals"]),
        )
    console.print(table)


@bridge_cli.command("sync-gaps")
@click.option("--dir", "project_dir", default=".", show_default=True,
              help="Directory containing capabilities.yaml and workflows/")
def sync_gaps_cmd(project_dir: str):
    """Sync design-layer gap analysis findings into backlog.jsonl."""
    from pathlib import Path

    from voice_of_agents.core.io import load_capability_registry
    from voice_of_agents.design.gap_analysis import GapAnalyzer
    from voice_of_agents.design.io import load_workflow_mappings_dir
    from voice_of_agents.eval.bridge import sync_gap_analysis_to_backlog
    from voice_of_agents.eval.config import VoAConfig

    p = Path(project_dir)
    cap_path = p / "capabilities.yaml"
    wf_dir = p / "workflows"

    if not cap_path.exists():
        click.echo(f"capabilities.yaml not found at {cap_path}", err=True)
        raise SystemExit(1)

    registry = load_capability_registry(cap_path)
    mappings = load_workflow_mappings_dir(wf_dir) if wf_dir.exists() else []
    if not mappings:
        click.echo("No workflow mappings found — nothing to sync.", err=True)
        raise SystemExit(0)

    analyzer = GapAnalyzer(registry)
    report = analyzer.analyze(mappings)
    config = VoAConfig.load()
    n = sync_gap_analysis_to_backlog(report, config)
    click.echo(f"Synced {n} new backlog item(s) from gap analysis ({len(report.feature_recommendations)} total gaps found).")
