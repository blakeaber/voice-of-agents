"""Root voa CLI — dispatches to design and eval subgroups."""

from __future__ import annotations

import click
from dotenv import load_dotenv

# Load .env from CWD (and parents), then fall back to ~/.env.
# override=False means an already-exported shell var wins over the file.
from pathlib import Path as _Path

load_dotenv(override=False)
_home_env = _Path.home() / ".env"
if _home_env.exists():
    load_dotenv(_home_env, override=False)

# Subcommand imports must follow load_dotenv() above, because submodules
# may read env vars at import time.
from voice_of_agents.cli.bridge_cli import bridge_cli  # noqa: E402
from voice_of_agents.cli.design_cli import design_cli  # noqa: E402
from voice_of_agents.cli.eval_cli import eval_cli  # noqa: E402
from voice_of_agents.cli.research_cli import research_cli  # noqa: E402


@click.group()
@click.version_option(package_name="voice-of-agents")
def cli():
    """Voice of Agents — unified persona research pipeline."""
    pass


cli.add_command(design_cli, name="design")
cli.add_command(eval_cli, name="eval")
cli.add_command(bridge_cli, name="bridge")
cli.add_command(research_cli, name="research")
