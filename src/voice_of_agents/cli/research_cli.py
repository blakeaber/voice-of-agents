"""voa research — CLI commands for the primary research pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from voice_of_agents.research.session import ResearchSession

console = Console()


@click.group("research")
def research_cli() -> None:
    """Primary research pipeline: product-research → personas → workflows → journey."""
    pass


@research_cli.command("init")
@click.argument("slug", required=False)
@click.option("--question", default=None, help="Research question")
@click.option("--scope", default=None, help="Population scope")
@click.option("--product", default=None, help="Product context")
@click.option("--output", "-o", default="research-config.yaml", show_default=True)
def research_init(
    slug: str | None,
    question: str | None,
    scope: str | None,
    product: str | None,
    output: str,
) -> None:
    """Create a new research-config.yaml interactively."""
    from voice_of_agents.research.config import ResearchConfig

    if slug and question and scope and product:
        config = ResearchConfig(
            research_question=question,
            scope=scope,
            slug=slug,
            product_context=product,
        )
    else:
        config = ResearchConfig.from_interactive()

    out_path = Path(output)
    config.save(out_path)
    console.print(f"[green]Research config saved to {out_path}[/green]")
    console.print("\nNext step:")
    console.print(f"  [bold]voa research validate-config {out_path}[/bold]")
    console.print(f"  [bold]voa research run {out_path}[/bold]")


@research_cli.command("validate-config")
@click.argument("config_file", default="research-config.yaml")
def research_validate_config(config_file: str) -> None:
    """Validate a research config before running (no API calls)."""
    from voice_of_agents.research.config import ResearchConfig

    path = Path(config_file)
    if not path.exists():
        console.print(f"[red]Config file not found: {path}[/red]")
        sys.exit(1)

    try:
        config = ResearchConfig.from_file(path)
    except Exception as exc:
        console.print(f"[red]Config parse error: {exc}[/red]")
        sys.exit(1)

    problems = config.validate_before_run()
    if problems:
        console.print("[red]Validation failed:[/red]")
        for p in problems:
            console.print(f"  [yellow]•[/yellow] {p}")
        sys.exit(1)
    else:
        console.print("[green]Config is valid — ready to run.[/green]")
        console.print(f"\n  Research question: {config.research_question[:80]}")
        console.print(f"  Scope:             {config.scope[:80]}")
        console.print(f"  Slug:              {config.slug}")
        console.print(f"  Subject count:     {config.subject_count}")
        console.print(f"  Model:             {config.anthropic_model}")


@research_cli.command("run")
@click.argument("config_file", default="research-config.yaml")
@click.option(
    "--stage",
    type=click.Choice(
        ["all", "product-research", "personas", "workflows", "journey"],
        case_sensitive=False,
    ),
    default="all",
    show_default=True,
    help="Which stage(s) to run.",
)
@click.option("--session", default=None, help="Path to an existing session YAML to resume.")
@click.option("--model", default=None, help="Override the Anthropic model.")
@click.option(
    "--model-haiku",
    "use_haiku",
    is_flag=True,
    default=False,
    help="Use claude-haiku-4-5-20251001 for low-cost exploration (~1/20th the cost).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show cost/time estimate and exit without making API calls.",
)
@click.option("--anchor-segment", default=None, help="Journey anchor segment (Stage 4 only).")
def research_run(
    config_file: str,
    stage: str,
    session: str | None,
    model: str | None,
    use_haiku: bool,
    dry_run: bool,
    anchor_segment: str | None,
) -> None:
    """Run the research pipeline (all stages or a single stage)."""
    import asyncio
    from voice_of_agents.research.config import ResearchConfig
    from voice_of_agents.research.session import ResearchSession
    from voice_of_agents.research.pipeline import run_full_pipeline
    from voice_of_agents.research.cost import estimate_run_cost

    path = Path(config_file)
    if not path.exists():
        console.print(f"[red]Config file not found: {path}[/red]")
        sys.exit(1)

    config = ResearchConfig.from_file(path)

    effective_model = (
        "claude-haiku-4-5-20251001" if use_haiku else (model or config.anthropic_model)
    )
    config = config.model_copy(update={"anthropic_model": effective_model})

    problems = config.validate_before_run()
    if problems:
        console.print("[red]Config validation failed:[/red]")
        for p in problems:
            console.print(f"  [yellow]•[/yellow] {p}")
        sys.exit(1)

    # Cost/time estimate before any API calls
    estimate = estimate_run_cost(
        model=effective_model,
        subject_count=config.subject_count,
    )
    console.print("\n[bold]Run estimate:[/bold]")
    console.print(estimate.display())

    if dry_run:
        console.print("\n[dim]--dry-run: no API calls made.[/dim]")
        return

    console.print("\nPress [bold]Enter[/bold] to continue or Ctrl+C to abort.")
    try:
        input()
    except KeyboardInterrupt:
        console.print("[yellow]Aborted.[/yellow]")
        return

    existing_session: ResearchSession | None = None
    if session:
        session_path = Path(session)
        if session_path.exists():
            existing_session = ResearchSession.load(session_path)
            console.print(f"Resuming session: {existing_session.session_id}")
            console.print(
                f"Completed stages: {', '.join(existing_session.stages_completed) or 'none'}"
            )

    jrd_config: dict = {}
    if anchor_segment:
        jrd_config["anchor_segment"] = anchor_segment

    try:
        result = asyncio.run(
            run_full_pipeline(
                config,
                journey_redesign_config=jrd_config or None,
                existing_session=existing_session,
            )
        )
        _print_session_summary(result)
    except Exception as exc:
        console.print(f"[red]Pipeline error: {exc}[/red]")
        raise


@research_cli.command("status")
@click.argument("session_file")
def research_status(session_file: str) -> None:
    """Show completion status of a research session."""
    from voice_of_agents.research.session import ResearchSession

    path = Path(session_file)
    if not path.exists():
        console.print(f"[red]Session file not found: {path}[/red]")
        sys.exit(1)

    session = ResearchSession.load(path)

    table = Table(title=f"Session: {session.slug} ({session.session_id})")
    table.add_column("Stage", style="cyan")
    table.add_column("Status")
    table.add_column("Detail")

    stages = [
        ("product_research", "Stage 1", session.product_research_output),
        ("personas_from_research", "Stage 2", session.persona_research_output),
        ("workflows_from_interviews", "Stage 3", session.workflow_research_output),
        ("journey_redesign", "Stage 4", session.journey_redesign_output),
    ]

    for stage_key, label, output in stages:
        if session.is_stage_complete(stage_key):
            status = "[green]complete[/green]"
            if stage_key == "product_research" and output:
                detail = f"{len(output.subjects)} subjects, {len(output.segments)} segments"
            elif stage_key == "personas_from_research" and output:
                detail = f"{len(output.persona_sidecars)} personas"
            elif stage_key == "workflows_from_interviews" and output:
                detail = f"{len(output.episodes)} episodes, {len(output.workflow_maps)} maps"
            elif stage_key == "journey_redesign" and output:
                detail = f"avg score {output.average_score:.1f}/10"
            else:
                detail = ""
        else:
            status = "[dim]pending[/dim]"
            detail = ""
        table.add_row(label, status, detail)

    console.print(table)

    if session.error_log:
        console.print("\n[red]Errors:[/red]")
        for err in session.error_log:
            console.print(f"  {err}")


@research_cli.command("export")
@click.argument("session_file")
@click.option(
    "--output",
    "-o",
    default="RESEARCH-SUMMARY.md",
    show_default=True,
    help="Output path for the summary artifact.",
)
def research_export(session_file: str, output: str) -> None:
    """Export a RESEARCH-SUMMARY.md artifact from a completed session."""
    from voice_of_agents.research.session import ResearchSession

    path = Path(session_file)
    if not path.exists():
        console.print(f"[red]Session file not found: {path}[/red]")
        sys.exit(1)

    session = ResearchSession.load(path)
    out_path = Path(output)
    content = session.export_summary(out_path)
    console.print(f"[green]Summary exported to {out_path}[/green]")
    console.print(f"\n{content[:500]}...")


@research_cli.command("list-sessions")
@click.option("--dir", "sessions_dir", default="research-sessions", show_default=True)
def research_list_sessions(sessions_dir: str) -> None:
    """List all research sessions in the sessions directory."""
    from voice_of_agents.research.session import ResearchSession

    dir_path = Path(sessions_dir)
    if not dir_path.exists():
        console.print(f"[dim]No sessions directory found at {dir_path}[/dim]")
        return

    yaml_files = sorted(dir_path.glob("*.yaml"))
    if not yaml_files:
        console.print(f"[dim]No sessions found in {dir_path}[/dim]")
        return

    table = Table(title=f"Research Sessions ({dir_path})")
    table.add_column("Slug", style="cyan")
    table.add_column("Date")
    table.add_column("Stages")
    table.add_column("File")

    for f in yaml_files:
        try:
            session = ResearchSession.load(f)
            completed = ", ".join(session.stages_completed) or "none"
            table.add_row(session.slug, session.created_at, completed, f.name)
        except Exception:
            table.add_row("[dim]?[/dim]", "[dim]?[/dim]", "[dim]parse error[/dim]", f.name)

    console.print(table)


@research_cli.command("demo")
@click.option("--save", is_flag=True, default=False, help="Save session output to ./demo-output/")
@click.option(
    "--model", default="claude-opus-4-7", show_default=True, help="Anthropic model to use."
)
def research_demo(save: bool, model: str) -> None:
    """Run the 60-second preset demo — no config required.

    Runs a preset research question about developer tool adoption.
    Uses a small subject count (~$0.30 with claude-opus-4-7).
    """
    import asyncio
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from voice_of_agents.research.quick import run_demo

    console.print("\n[bold]Voice of Agents — Research Demo[/bold]")
    console.print("Research question: Why do developers adopt AI dev tools then abandon them?")
    console.print(f"Model: {model} | Subjects: 10 (demo preset)\n")

    save_dir = "demo-output" if save else None

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Running synthetic research interviews...", total=None)
            result = asyncio.run(run_demo(model=model, save_dir=save_dir))
            progress.remove_task(task)

        console.print("[bold green]Research complete.[/bold green]\n")

        console.print("[bold]Top Findings:[/bold]")
        for i, finding in enumerate(result.top_findings, 1):
            console.print(f"  {i}. {finding}")

        console.print(f"\n[bold]Build This First:[/bold]\n  {result.build_this_first}")

        console.print("\n[bold]User Archetypes:[/bold]")
        for persona in result.personas:
            console.print(f"  • [cyan]{persona.archetype}[/cyan]: {persona.top_concern}")

        console.print("\n[bold]What Would Make Them Leave:[/bold]")
        for trigger in result.churn_triggers:
            console.print(f"  • {trigger}")

        console.print("\n[bold]Validate With Real Users — Ask These:[/bold]")
        for i, q in enumerate(result.validate_with, 1):
            console.print(f"  {i}. {q}")

        if save_dir:
            console.print(f"\n[green]Session saved to ./{save_dir}/[/green]")

        console.print("\n[bold]What to do next:[/bold]")
        console.print("  1. Schedule 3 user calls and ask the validation questions above")
        console.print("  2. Run 'voa research quickstart' to configure your own research")
        console.print("  3. Run 'voa research run' to execute the full 4-stage pipeline")

    except Exception as exc:
        console.print(f"[red]Demo failed: {exc}[/red]")
        raise


@research_cli.command("quickstart")
@click.option(
    "--output",
    "-o",
    default="research-config.yaml",
    show_default=True,
    help="Output path for the generated config.",
)
def research_quickstart(output: str) -> None:
    """Configure research with 3 plain-English questions — no methodology vocabulary.

    Translates your answers into a valid ResearchConfig using Claude.
    """
    import asyncio

    console.print("\n[bold]Voice of Agents — Research Quickstart[/bold]")
    console.print("Answer 3 questions. We'll handle the research design.\n")

    what = click.prompt("What are you building? (one sentence)")
    who = click.prompt("Who are your users? (one sentence)")
    understand = click.prompt("What's the #1 thing you want to understand about them?")

    console.print("\n[dim]Translating to a research question...[/dim]")

    try:
        config = asyncio.run(_async_from_plain_english(what=what, who=who, understand=understand))
    except Exception as exc:
        console.print(f"[red]Translation failed: {exc}[/red]")
        console.print("Try being more specific about the behavior you want to understand.")
        raise SystemExit(1)

    console.print("\n[bold]Translated research question:[/bold]")
    console.print(f"  {config.research_question}")
    console.print(f"\n[bold]Scope:[/bold] {config.scope}")
    console.print(f"[bold]Slug:[/bold] {config.slug}")

    confirmed = click.confirm("\nDoes this look right?", default=True)
    if not confirmed:
        console.print("[yellow]Aborted. Try running again with more specific answers.[/yellow]")
        return

    out_path = Path(output)
    config.save(out_path)
    console.print(f"\n[green]Config saved to {out_path}[/green]")
    console.print(f"\nNext: [bold]voa research run {out_path}[/bold]")


async def _async_from_plain_english(what: str, who: str, understand: str):
    from voice_of_agents.research.config import ResearchConfig

    return await ResearchConfig.from_plain_english(what=what, who=who, understand=understand)


@research_cli.command("seed-eval")
@click.argument("session_file")
@click.option(
    "--output",
    "-o",
    default="data/personas",
    show_default=True,
    help="Directory to write canonical Persona YAML files.",
)
@click.option(
    "--starting-id",
    default=100,
    show_default=True,
    help="Starting integer ID for generated personas (avoids collisions with existing).",
)
def research_seed_eval(session_file: str, output: str, starting_id: int) -> None:
    """Convert research personas to eval-ready Persona objects.

    Reads a completed research session and writes canonical Persona YAML files
    to the output directory. Each persona has metadata.source='generated' and
    validation_status='draft' — promote to 'validated' after real user confirmation.
    """
    from voice_of_agents.research.session import ResearchSession
    from voice_of_agents.research.bridge import session_to_personas, write_bridge_workflow

    path = Path(session_file)
    if not path.exists():
        console.print(f"[red]Session file not found: {path}[/red]")
        sys.exit(1)

    session = ResearchSession.load(path)

    if not session.persona_research_output:
        console.print("[red]Session has no persona output. Run at least Stage 2 first.[/red]")
        sys.exit(1)

    personas = session_to_personas(session, starting_id=starting_id)
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    import yaml

    for persona in personas:
        slug = persona.slug
        out_path = out_dir / f"{slug}.yaml"
        out_path.write_text(
            yaml.dump(
                persona.model_dump(mode="json", exclude_none=True),
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        )
        console.print(f"  [green]✓[/green] {out_path}")

    write_bridge_workflow(out_dir)
    console.print(f"\n[green]{len(personas)} personas written to {out_dir}/[/green]")
    console.print("[dim]All personas have validation_status=draft.[/dim]")
    console.print("Promote to 'validated' after a real user confirms the archetype.")
    console.print(f"\nSee {out_dir}/BRIDGE-WORKFLOW.md for usage guide.")


def _print_session_summary(session: "ResearchSession") -> None:  # type: ignore[name-defined]
    console.print(f"\n[green]Pipeline complete[/green] — session: {session.session_id}")
    console.print(f"Stages completed: {', '.join(session.stages_completed)}")
    if session.product_research_output:
        pr = session.product_research_output
        console.print(f"\nStage 1: {len(pr.subjects)} subjects, {len(pr.segments)} segments")
        if pr.all_hypotheses_supported_flag:
            console.print(
                "[yellow]  WARNING: All hypotheses supported — review for confirmation bias[/yellow]"
            )
    if session.persona_research_output:
        per = session.persona_research_output
        console.print(f"Stage 2: {len(per.persona_sidecars)} personas synthesized")
    if session.workflow_research_output:
        wf = session.workflow_research_output
        console.print(
            f"Stage 3: {len(wf.episodes)} episodes, {len(wf.workflow_maps)} workflow maps"
        )
    if session.journey_redesign_output:
        jrd = session.journey_redesign_output
        console.print(
            f"Stage 4: avg score {jrd.average_score:.1f}/10, {len(jrd.cross_cutting_must_fixes)} cross-cutting must-fixes"
        )

    console.print(f"\nNext: [bold]voa research export research-sessions/{session.slug}.yaml[/bold]")
