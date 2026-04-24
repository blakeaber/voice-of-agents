"""Offline demo replay — loads a frozen QuickResearchResult fixture and renders it.

This is the zero-API-key path for `voa research demo --offline`. Rather than
mocking every stage of the pipeline, the offline mode loads a pre-baked result
fixture bundled with the package and renders the same terminal output shape
that a live `voa research demo` run produces.

Regeneration: see `src/voice_of_agents/fixtures/demo_result.yaml`.
"""

from __future__ import annotations

import importlib.resources
from typing import Any

import yaml
from rich.console import Console


def load_demo_fixture() -> dict[str, Any]:
    """Load the bundled offline-demo fixture from the package's fixtures/ dir.

    Raises:
        FileNotFoundError: if the fixture file is missing from the installed
            package (indicates a packaging bug; file should always ship).
        yaml.YAMLError: if the fixture is malformed.
    """
    fixtures = importlib.resources.files("voice_of_agents.fixtures")
    fixture_path = fixtures / "demo_result.yaml"
    if not fixture_path.is_file():
        raise FileNotFoundError(
            "Offline demo fixture not found at "
            "voice_of_agents/fixtures/demo_result.yaml. "
            "This indicates a packaging problem — please file an issue."
        )
    return yaml.safe_load(fixture_path.read_text())


def render_offline_demo(console: Console, data: dict[str, Any]) -> None:
    """Render the offline demo fixture to the console using the same section
    headings and order as the live `voa research demo` output.

    Args:
        console: Rich Console to render into.
        data: Fixture dict (from load_demo_fixture()).
    """
    console.print("\n[bold]Voice of Agents — Research Demo (offline)[/bold]")
    console.print(f"Research question: {data.get('preset_question', '').strip()}")
    console.print("[dim]Using bundled cassette fixture — no API key required.[/dim]\n")

    console.print("[bold green]Research complete.[/bold green]\n")

    console.print("[bold]Top Findings:[/bold]")
    for i, finding in enumerate(data.get("top_findings", []), 1):
        console.print(f"  {i}. {finding}")

    build_first = data.get("build_this_first", "")
    console.print(f"\n[bold]Build This First:[/bold]\n  {build_first}")

    console.print("\n[bold]User Archetypes:[/bold]")
    for persona in data.get("personas", []):
        archetype = persona.get("archetype", "?")
        top_concern = persona.get("top_concern", "")
        console.print(f"  • [cyan]{archetype}[/cyan]: {top_concern}")

    console.print("\n[bold]What Would Make Them Leave:[/bold]")
    for trigger in data.get("churn_triggers", []):
        console.print(f"  • {trigger}")

    console.print("\n[bold]Validate With Real Users — Ask These:[/bold]")
    for i, q in enumerate(data.get("validate_with", []), 1):
        console.print(f"  {i}. {q}")

    console.print("\n[bold]What to do next:[/bold]")
    for step in data.get("next_steps", []):
        console.print(f"  • {step}")
