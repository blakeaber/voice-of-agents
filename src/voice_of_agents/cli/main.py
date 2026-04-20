"""Root voa CLI — dispatches to design and eval subgroups."""

from __future__ import annotations

import click

from voice_of_agents.cli.bridge_cli import bridge_cli
from voice_of_agents.cli.design_cli import design_cli
from voice_of_agents.cli.eval_cli import eval_cli
from voice_of_agents.cli.research_cli import research_cli


@click.group()
@click.version_option(package_name="voice-of-agents")
def cli():
    """Voice of Agents — unified persona research pipeline."""
    pass


cli.add_command(design_cli, name="design")
cli.add_command(eval_cli, name="eval")
cli.add_command(bridge_cli, name="bridge")
cli.add_command(research_cli, name="research")
