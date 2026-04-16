"""Voice of Agents CLI — persona-driven UX evaluation pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from voice_of_agents.config import VoAConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _load_config() -> VoAConfig:
    """Load config, or fail with helpful message."""
    try:
        return VoAConfig.load()
    except Exception:
        raise click.ClickException(
            "No voa-config.json found. Run 'voa init' first."
        )


@click.group()
@click.version_option(package_name="voice-of-agents")
def cli():
    """Voice of Agents — persona-driven UX evaluation pipeline."""
    pass


# ── Init ───────────────────────────────────────────────────────────────

@cli.command()
@click.option("--target", default="http://localhost:3000", help="Target app URL")
@click.option("--api", default="http://localhost:8420", help="Target API URL")
@click.option("--data", default="./data", help="Data directory")
def init(target: str, api: str, data: str):
    """Initialize a new evaluation project."""
    config = VoAConfig(target_url=target, api_url=api, data_dir=data)
    config.save()

    # Create data directories
    config.data_path.mkdir(parents=True, exist_ok=True)
    config.personas_path.mkdir(parents=True, exist_ok=True)
    config.results_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Initialized Voice of Agents project:")
    click.echo(f"  Target: {target}")
    click.echo(f"  API:    {api}")
    click.echo(f"  Data:   {data}")
    click.echo(f"\nConfig saved to voa-config.json")


# ── Import ─────────────────────────────────────────────────────────────

@cli.group(name="import")
def import_group():
    """Import data from external sources."""
    pass


@import_group.command(name="personas")
@click.argument("source_dir", type=click.Path(exists=True))
def import_personas(source_dir: str):
    """Import personas from markdown workflow files (rooben-pro format)."""
    config = _load_config()
    from voice_of_agents.contracts.personas import import_from_markdown

    source = Path(source_dir)
    personas = import_from_markdown(source, config.personas_path)
    click.echo(f"Imported {len(personas)} personas to {config.personas_path}")
    for p in personas:
        click.echo(f"  {p.id}: {p.name} — {p.role} ({p.tier})")


@import_group.command(name="inventory")
@click.argument("source_file", type=click.Path(exists=True))
def import_inventory(source_file: str):
    """Import feature inventory from YAML."""
    import shutil
    config = _load_config()
    shutil.copy2(source_file, config.inventory_path)
    click.echo(f"Imported inventory to {config.inventory_path}")


# ── Phase Commands ─────────────────────────────────────────────────────

@cli.command()
@click.option("--generate-personas", is_flag=True, help="Auto-generate personas from app analysis")
def phase1(generate_personas: bool):
    """Phase 1: Generate or validate personas."""
    config = _load_config()
    from voice_of_agents.contracts.personas import load_personas, validate_persona

    if generate_personas:
        from voice_of_agents.phases.phase1_generate import generate_personas as gen
        personas = gen(config)
        click.echo(f"Generated {len(personas)} personas")
    else:
        personas = load_personas(config.personas_path)
        if not personas:
            raise click.ClickException(
                f"No personas found in {config.personas_path}. "
                "Use --generate-personas or 'voa import personas <dir>'"
            )
        click.echo(f"Validating {len(personas)} personas...")
        for p in personas:
            issues = validate_persona(p)
            if issues:
                click.echo(f"  {p.id} {p.name}: {', '.join(issues)}", err=True)
            else:
                click.echo(f"  {p.id} {p.name}: OK ({len(p.objectives)} objectives)")


@cli.command()
@click.option("--personas", default=None, help="Comma-separated persona IDs (e.g. UXW-01,UXW-02)")
@click.option("--batch", default=None, type=int, help="Batch number (1-7, 5 personas each)")
@click.option("--all", "run_all", is_flag=True, help="Run all personas")
def phase2(personas: str | None, batch: int | None, run_all: bool):
    """Phase 2: Adaptive persona exploration via browser."""
    config = _load_config()
    from voice_of_agents.contracts.personas import load_personas
    from voice_of_agents.phases.phase2_explore import explore_personas

    all_personas = load_personas(config.personas_path)
    if not all_personas:
        raise click.ClickException("No personas loaded. Run 'voa import personas' first.")

    selected = _select_personas(all_personas, personas, batch, run_all)
    click.echo(f"Exploring as {len(selected)} personas against {config.target_url}")

    explore_personas(selected, config)


@cli.command()
@click.option("--personas", default=None, help="Comma-separated persona IDs")
@click.option("--batch", default=None, type=int, help="Batch number (1-7)")
@click.option("--all", "run_all", is_flag=True, help="Run all personas")
def phase3(personas: str | None, batch: int | None, run_all: bool):
    """Phase 3: Generate synthetic focus group evaluations."""
    config = _load_config()
    from voice_of_agents.contracts.personas import load_personas
    from voice_of_agents.phases.phase3_evaluate import evaluate_personas

    all_personas = load_personas(config.personas_path)
    selected = _select_personas(all_personas, personas, batch, run_all)
    click.echo(f"Generating evaluations for {len(selected)} personas")

    evaluate_personas(selected, config)


@cli.command()
def phase4():
    """Phase 4: Synthesize findings from all evaluations."""
    config = _load_config()
    from voice_of_agents.phases.phase4_synthesize import synthesize_findings

    synthesize_findings(config)
    click.echo(f"Findings written to {config.findings_path}")


@cli.command()
def phase5():
    """Phase 5: Score and prioritize backlog."""
    config = _load_config()
    from voice_of_agents.phases.phase5_prioritize import prioritize_backlog
    from voice_of_agents.contracts.backlog import save_backlog_markdown

    prioritize_backlog(config)
    save_backlog_markdown(config.backlog_jsonl_path, config.backlog_md_path)
    click.echo(f"Backlog updated: {config.backlog_md_path}")


# ── Full Pipeline ──────────────────────────────────────────────────────

@cli.command()
@click.option("--personas", default=None, help="Comma-separated persona IDs")
@click.option("--batch", default=None, type=int, help="Batch number (1-7)")
@click.option("--all", "run_all", is_flag=True, help="Run all personas")
def run(personas: str | None, batch: int | None, run_all: bool):
    """Run full pipeline (Phases 2-5) for selected personas."""
    config = _load_config()
    from voice_of_agents.contracts.personas import load_personas
    from voice_of_agents.phases.phase2_explore import explore_personas
    from voice_of_agents.phases.phase3_evaluate import evaluate_personas
    from voice_of_agents.phases.phase4_synthesize import synthesize_findings
    from voice_of_agents.phases.phase5_prioritize import prioritize_backlog
    from voice_of_agents.contracts.backlog import save_backlog_markdown

    all_personas = load_personas(config.personas_path)
    selected = _select_personas(all_personas, personas, batch, run_all)
    click.echo(f"Running full pipeline for {len(selected)} personas\n")

    click.echo("Phase 2: Exploring...")
    explore_personas(selected, config)

    click.echo("\nPhase 3: Evaluating...")
    evaluate_personas(selected, config)

    click.echo("\nPhase 4: Synthesizing findings...")
    synthesize_findings(config)

    click.echo("\nPhase 5: Prioritizing backlog...")
    prioritize_backlog(config)
    save_backlog_markdown(config.backlog_jsonl_path, config.backlog_md_path)

    click.echo(f"\nDone. Backlog at {config.backlog_md_path}")


# ── Utilities ──────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show evaluation status — what's been run, what's pending."""
    config = _load_config()
    from voice_of_agents.contracts.personas import load_personas

    all_personas = load_personas(config.personas_path)
    click.echo(f"Personas: {len(all_personas)} loaded")

    completed = 0
    for p in all_personas:
        persona_dir = config.results_path / p.slug
        runs = sorted(persona_dir.glob("*")) if persona_dir.exists() else []
        if runs:
            latest = runs[-1].name
            click.echo(f"  {p.id} {p.name}: {len(runs)} run(s), latest {latest}")
            completed += 1
        else:
            click.echo(f"  {p.id} {p.name}: no runs")

    click.echo(f"\n{completed}/{len(all_personas)} personas evaluated")

    # Backlog status
    if config.backlog_jsonl_path.exists():
        from voice_of_agents.contracts.backlog import materialize_backlog
        items = materialize_backlog(config.backlog_jsonl_path)
        open_items = [i for i in items if i.status == "open"]
        resolved = [i for i in items if i.status == "resolved"]
        click.echo(f"Backlog: {len(items)} items ({len(open_items)} open, {len(resolved)} resolved)")
    else:
        click.echo("Backlog: not yet generated")


@cli.command()
def backlog():
    """Pretty-print the current backlog."""
    config = _load_config()
    from voice_of_agents.contracts.backlog import render_backlog_markdown
    click.echo(render_backlog_markdown(config.backlog_jsonl_path))


@cli.command()
def inventory():
    """Pretty-print the feature inventory."""
    config = _load_config()
    from voice_of_agents.contracts.inventory import load_inventory
    inv = load_inventory(config.inventory_path)
    summary = inv.summary()
    click.echo(f"Feature Inventory: {len(inv.features)} features")
    for status, count in sorted(summary.items()):
        click.echo(f"  {status}: {count}")
    click.echo()
    for area, features in inv.features_by_area().items():
        click.echo(f"[{area}]")
        for f in features:
            latest = f.latest_test
            test_info = f" (tested {latest.run}: {latest.status})" if latest else ""
            click.echo(f"  {f.id} {f.name} [{f.status}]{test_info}")


@cli.command()
def diff():
    """Generate diff report comparing latest run to prior."""
    config = _load_config()
    from voice_of_agents.reporting.diff import generate_diff
    generate_diff(config)
    click.echo(f"Diff report at {config.diff_report_path}")


# ── Helpers ────────────────────────────────────────────────────────────

def _select_personas(all_personas, persona_ids: str | None, batch: int | None, run_all: bool):
    """Filter personas based on CLI options."""
    if run_all:
        return all_personas

    if persona_ids:
        ids = {p.strip() for p in persona_ids.split(",")}
        return [p for p in all_personas if p.id in ids]

    if batch:
        batch_size = 5
        start = (batch - 1) * batch_size
        end = start + batch_size
        return all_personas[start:end]

    raise click.ClickException(
        "Specify --personas, --batch, or --all"
    )
