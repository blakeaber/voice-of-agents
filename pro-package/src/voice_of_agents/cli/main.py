"""Voice of Agents CLI — persona management and workflow generation."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from voice_of_agents import __version__

console = Console()

# Default project layout
DEFAULT_PERSONAS_DIR = "personas"
DEFAULT_WORKFLOWS_DIR = "workflows"
DEFAULT_REGISTRY_FILE = "capabilities.yaml"


def _resolve_paths(
    project_dir: str,
) -> tuple[Path, Path, Path]:
    """Resolve standard project paths."""
    root = Path(project_dir)
    return (
        root / DEFAULT_PERSONAS_DIR,
        root / DEFAULT_WORKFLOWS_DIR,
        root / DEFAULT_REGISTRY_FILE,
    )


@click.group()
@click.version_option(version=__version__)
def cli():
    """Voice of Agents — Persona management and workflow generation."""
    pass


# ─── Init ───────────────────────────────────────────────────────────────


@cli.command()
@click.argument("project_dir", default=".")
@click.option("--product", prompt="Product name", help="Name of the product")
def init(project_dir: str, product: str):
    """Initialize a new VoA project directory."""
    root = Path(project_dir)
    personas_dir = root / DEFAULT_PERSONAS_DIR
    workflows_dir = root / DEFAULT_WORKFLOWS_DIR
    registry_path = root / DEFAULT_REGISTRY_FILE

    personas_dir.mkdir(parents=True, exist_ok=True)
    workflows_dir.mkdir(parents=True, exist_ok=True)

    if not registry_path.exists():
        import yaml

        from voice_of_agents.models.capability import CapabilityRegistry

        registry = CapabilityRegistry(product=product, capabilities=[])
        with open(registry_path, "w") as f:
            yaml.dump(
                registry.model_dump(mode="json", exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
        console.print(f"[green]Created[/] {registry_path}")

    console.print(f"[green]Initialized VoA project[/] at {root.absolute()}")
    console.print(f"  personas/       — persona YAML files")
    console.print(f"  workflows/      — workflow mapping files")
    console.print(f"  capabilities.yaml — capability registry")


# ─── Persona commands ───────────────────────────────────────────────────


@cli.group()
def persona():
    """Manage personas."""
    pass


@persona.command("list")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def persona_list(project_dir: str):
    """List all personas."""
    personas_dir, _, _ = _resolve_paths(project_dir)

    from voice_of_agents.validators.io import load_personas_dir

    if not personas_dir.exists():
        console.print("[yellow]No personas directory found.[/]")
        return

    personas = load_personas_dir(personas_dir)
    if not personas:
        console.print("[yellow]No personas found.[/]")
        return

    table = Table(title=f"Personas ({len(personas)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Role")
    table.add_column("Segment")
    table.add_column("Tier")
    table.add_column("Industry")
    table.add_column("Status")

    for p in personas:
        table.add_row(
            str(p.id),
            p.name,
            p.role,
            p.segment.value.upper(),
            p.tier.value,
            p.industry,
            p.metadata.validation_status.value,
        )

    console.print(table)


@persona.command("validate")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def persona_validate(project_dir: str):
    """Validate all persona files."""
    personas_dir, _, _ = _resolve_paths(project_dir)

    from voice_of_agents.validators.io import LoadError, load_persona

    errors = 0
    valid = 0
    for path in sorted(personas_dir.glob("*.yaml")):
        try:
            load_persona(path)
            valid += 1
        except LoadError as e:
            console.print(f"[red]FAIL[/] {path.name}: {e}")
            errors += 1

    console.print(f"\n{valid} valid, {errors} error(s)")
    if errors:
        raise SystemExit(1)


@persona.command("generate-prompt")
@click.option("--dir", "project_dir", default=".", help="Project directory")
@click.option("--product", required=True, help="Product name")
@click.option("--description", required=True, help="Product description")
@click.option("--industry", required=True, help="Target industry")
@click.option("--roles", required=True, help="Comma-separated roles to explore")
@click.option("--segment", default="b2c", help="b2c or b2b")
@click.option("--count", default=3, help="Number of personas to generate")
@click.option("--output", "-o", default=None, help="Write prompt to file")
def persona_generate_prompt(
    project_dir: str,
    product: str,
    description: str,
    industry: str,
    roles: str,
    segment: str,
    count: int,
    output: str | None,
):
    """Generate an LLM prompt for creating new personas."""
    personas_dir, _, _ = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.persona_pipeline import (
        PersonaGenerationRequest,
        PersonaPipeline,
    )

    pipeline = PersonaPipeline(personas_dir)
    request = PersonaGenerationRequest(
        product_name=product,
        product_description=description,
        industry=industry,
        roles=[r.strip() for r in roles.split(",")],
        segment=segment,
        count=count,
    )

    prompt = pipeline.build_prompt(request)

    if output:
        Path(output).write_text(prompt)
        console.print(f"[green]Prompt written to[/] {output}")
    else:
        console.print(prompt)


@persona.command("import")
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--dir", "project_dir", default=".", help="Project directory")
def persona_import(yaml_file: str, project_dir: str):
    """Import personas from an LLM response YAML file."""
    personas_dir, _, _ = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.persona_pipeline import PersonaPipeline

    pipeline = PersonaPipeline(personas_dir)
    raw = Path(yaml_file).read_text()
    result = pipeline.parse_response(raw)

    if result.errors:
        for err in result.errors:
            console.print(f"[red]ERROR[/] {err}")

    if result.personas:
        paths = pipeline.save_personas(result.personas)
        for path in paths:
            console.print(f"[green]Saved[/] {path}")
        console.print(f"\n{len(result.personas)} persona(s) imported")
    else:
        console.print("[yellow]No valid personas found in input.[/]")


# ─── Workflow commands ──────────────────────────────────────────────────


@cli.group()
def workflow():
    """Manage workflow mappings."""
    pass


@workflow.command("list")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def workflow_list(project_dir: str):
    """List all workflow mappings."""
    _, workflows_dir, _ = _resolve_paths(project_dir)

    from voice_of_agents.validators.io import load_workflow_mappings_dir

    if not workflows_dir.exists():
        console.print("[yellow]No workflows directory found.[/]")
        return

    mappings = load_workflow_mappings_dir(workflows_dir)
    if not mappings:
        console.print("[yellow]No workflow mappings found.[/]")
        return

    table = Table(title=f"Workflow Mappings ({len(mappings)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Persona", style="bold")
    table.add_column("Tier")
    table.add_column("Goals", justify="center")
    table.add_column("Primary", justify="center")
    table.add_column("Caps Used", justify="center")
    table.add_column("Gaps", justify="center")

    for m in mappings:
        primary = len([g for g in m.goals if g.priority.value == "primary"])
        caps = len(m.all_capabilities_used())
        gaps = len(m.all_gaps())
        gap_style = "red" if gaps > 0 else "green"

        table.add_row(
            str(m.persona_id),
            m.persona_name,
            m.persona_tier.value,
            str(len(m.goals)),
            str(primary),
            str(caps),
            f"[{gap_style}]{gaps}[/{gap_style}]",
        )

    console.print(table)


@workflow.command("generate-prompt")
@click.argument("persona_id", type=int)
@click.option("--dir", "project_dir", default=".", help="Project directory")
@click.option("--goals", default=2, help="Number of new goals to generate")
@click.option("--output", "-o", default=None, help="Write prompt to file")
def workflow_generate_prompt(persona_id: int, project_dir: str, goals: int, output: str | None):
    """Generate an LLM prompt for creating workflows for a persona."""
    personas_dir, workflows_dir, registry_path = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.workflow_pipeline import WorkflowPipeline
    from voice_of_agents.validators.io import load_personas_dir

    personas = load_personas_dir(personas_dir)
    persona = next((p for p in personas if p.id == persona_id), None)
    if not persona:
        console.print(f"[red]Persona #{persona_id} not found[/]")
        raise SystemExit(1)

    pipeline = WorkflowPipeline(registry_path, workflows_dir)
    existing = pipeline.load_existing_mapping(persona)
    prompt = pipeline.build_prompt(persona, existing, goal_count=goals)

    if output:
        Path(output).write_text(prompt)
        console.print(f"[green]Prompt written to[/] {output}")
    else:
        console.print(prompt)


@workflow.command("import")
@click.argument("yaml_file", type=click.Path(exists=True))
@click.argument("persona_id", type=int)
@click.option("--dir", "project_dir", default=".", help="Project directory")
def workflow_import(yaml_file: str, persona_id: int, project_dir: str):
    """Import workflow goals from an LLM response YAML file."""
    personas_dir, workflows_dir, registry_path = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.workflow_pipeline import WorkflowPipeline
    from voice_of_agents.validators.io import load_personas_dir

    personas = load_personas_dir(personas_dir)
    persona = next((p for p in personas if p.id == persona_id), None)
    if not persona:
        console.print(f"[red]Persona #{persona_id} not found[/]")
        raise SystemExit(1)

    pipeline = WorkflowPipeline(registry_path, workflows_dir)
    existing = pipeline.load_existing_mapping(persona)

    raw = Path(yaml_file).read_text()
    result = pipeline.parse_response(raw, persona, existing)

    if result.errors:
        for err in result.errors:
            console.print(f"[red]ERROR[/] {err}")

    if result.mapping:
        path = pipeline.save_mapping(result.mapping)
        console.print(f"[green]Saved[/] {path}")
        console.print(f"  {len(result.new_goals)} new goal(s) added")
        console.print(f"  {len(result.mapping.goals)} total goal(s)")


# ─── Analysis commands ──────────────────────────────────────────────────


@cli.group()
def analyze():
    """Run analysis across personas and workflows."""
    pass


@analyze.command("gaps")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def analyze_gaps(project_dir: str):
    """Analyze capability gaps across all workflow mappings."""
    _, workflows_dir, registry_path = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.gap_analysis import GapAnalyzer
    from voice_of_agents.validators.io import (
        load_capability_registry,
        load_workflow_mappings_dir,
    )

    registry = load_capability_registry(registry_path)
    mappings = load_workflow_mappings_dir(workflows_dir)

    if not mappings:
        console.print("[yellow]No workflow mappings found.[/]")
        return

    analyzer = GapAnalyzer(registry)
    report = analyzer.analyze(mappings)

    console.print(f"\n[bold]Gap Analysis Report[/bold]\n")
    console.print(report.summary())

    # Coverage by feature area
    coverage = analyzer.coverage_by_feature_area(mappings)
    if coverage:
        console.print(f"\n[bold]Coverage by Feature Area[/bold]")
        table = Table()
        table.add_column("Feature Area")
        table.add_column("Used", justify="center")
        table.add_column("Total", justify="center")
        table.add_column("Rate", justify="center")

        for area, data in sorted(coverage.items()):
            rate = data["used"] / data["total"] if data["total"] else 0
            style = "green" if rate >= 0.7 else ("yellow" if rate >= 0.3 else "red")
            table.add_row(
                area,
                str(data["used"]),
                str(data["total"]),
                f"[{style}]{rate:.0%}[/{style}]",
            )

        console.print(table)


@analyze.command("coverage")
@click.option("--dir", "project_dir", default=".", help="Project directory")
def analyze_coverage(project_dir: str):
    """Show which capabilities are used by which personas."""
    _, workflows_dir, registry_path = _resolve_paths(project_dir)

    from voice_of_agents.pipelines.gap_analysis import GapAnalyzer
    from voice_of_agents.validators.io import (
        load_capability_registry,
        load_workflow_mappings_dir,
    )

    registry = load_capability_registry(registry_path)
    mappings = load_workflow_mappings_dir(workflows_dir)

    if not mappings:
        console.print("[yellow]No workflow mappings found.[/]")
        return

    analyzer = GapAnalyzer(registry)
    report = analyzer.analyze(mappings)

    table = Table(title="Capability Coverage")
    table.add_column("Capability", style="bold")
    table.add_column("Status")
    table.add_column("Personas", justify="center")
    table.add_column("Workflows", justify="center")

    for cap in registry.capabilities:
        cov = report.coverage.get(cap.id)
        if cov:
            table.add_row(
                f"{cap.id}\n  {cap.name}",
                cap.status.value,
                str(cov.persona_count),
                str(cov.workflow_count),
            )
        else:
            table.add_row(
                f"{cap.id}\n  {cap.name}",
                cap.status.value,
                "[dim]0[/dim]",
                "[dim]0[/dim]",
            )

    console.print(table)


# ─── Validate command ───────────────────────────────────────────────────


@cli.command()
@click.option("--dir", "project_dir", default=".", help="Project directory")
def validate(project_dir: str):
    """Validate all personas, workflows, and cross-references."""
    personas_dir, workflows_dir, registry_path = _resolve_paths(project_dir)

    from voice_of_agents.validators.io import (
        load_capability_registry,
        load_personas_dir,
        load_workflow_mappings_dir,
    )
    from voice_of_agents.validators.validate import validate_all

    personas = load_personas_dir(personas_dir) if personas_dir.exists() else []
    mappings = load_workflow_mappings_dir(workflows_dir) if workflows_dir.exists() else []
    registry = load_capability_registry(registry_path) if registry_path.exists() else None

    if registry is None:
        console.print("[red]No capability registry found.[/]")
        raise SystemExit(1)

    console.print(f"Validating {len(personas)} persona(s), {len(mappings)} mapping(s)...")
    result = validate_all(personas, mappings, registry)
    console.print(result.summary())

    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
