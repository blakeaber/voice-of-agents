"""Shared async client factory and Jinja2 template environment."""

from __future__ import annotations

import os
from pathlib import Path

from anthropic import AsyncAnthropic
from jinja2 import Environment, FileSystemLoader


def get_async_client(api_key: str | None = None) -> AsyncAnthropic:
    """Return an AsyncAnthropic client.

    Uses ANTHROPIC_API_KEY env var by default.
    All research functions call this factory — never instantiate the client directly.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Export it via `export ANTHROPIC_API_KEY=sk-...` "
            "or pass api_key= to ResearchConfig."
        )
    return AsyncAnthropic(api_key=key)


def get_template_env() -> Environment:
    """Return a Jinja2 Environment pointing at research/prompts/.

    Templates use {% include '_partials/...' %} for shared protocol sections.
    """
    prompts_dir = Path(__file__).parent / "prompts"
    return Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
