"""ResearchConfig — structured input gathering that solves pain points 1 & 2."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from voice_of_agents.research.models import Hypothesis, ProductResearchInput


class ResearchConfig(BaseModel):
    """Top-level configuration for a research pipeline run.

    This is the single entrypoint for declaring what research to run.
    Required fields are required. Optional fields have documented defaults.

    Three construction methods:
    - from_interactive(): guided CLI prompts
    - from_file(path): YAML file for CI / programmatic use
    - from_dict(data): embed in Python code
    """

    # ── Required ──────────────────────────────────────────────────────
    research_question: str = Field(
        description=(
            "A falsifiable question about a customer population. "
            "Example: 'Do abandoners quit because cost-per-outcome is invisible, "
            "or because outcomes themselves are wrong?' "
            "NOT a target-market name ('US small business owners')."
        )
    )
    scope: str = Field(
        description=(
            "Population boundary. "
            "Example: 'US-based knowledge workers, 2+ years experience with AI tools, "
            "firm sizes 1-500 employees, 2024-2026'"
        )
    )
    slug: str = Field(
        description=(
            "≤6 kebab-case words identifying this run. "
            "Used in artifact directory names and session file names. "
            "Example: 'ai-adoption-friction-2026'"
        )
    )
    product_context: str = Field(
        description=(
            "Brief description of your product. Used to ground the 'Gaps vs. positioning' "
            "section in segmentation. Do NOT use as a target-market filter."
        )
    )

    # ── Optional pipeline configuration ──────────────────────────────
    subject_count: int = Field(
        default=12,
        ge=10,
        le=16,
        description="Number of parallel interview subjects (10-16). Default: 12.",
    )
    anthropic_model: str = Field(
        default="claude-opus-4-7",
        description="Anthropic model ID for all research API calls.",
    )
    output_dir: Path = Field(
        default=Path("docs/research"),
        description="Root directory for all artifact output.",
    )
    session_dir: Path = Field(
        default=Path("research-sessions"),
        description="Directory for ResearchSession YAML files.",
    )

    # ── Optional skip flags ────────────────────────────────────────────
    skip_topup: bool = Field(
        default=False,
        description="Skip top-up interviews in personas stage if ≥3 subjects/segment.",
    )

    # ── Optional pre-ratified hypotheses ─────────────────────────────
    hypotheses: Optional[list[Hypothesis]] = Field(
        default=None,
        description=(
            "Pre-ratified hypotheses. If None, the pipeline generates hypotheses "
            "and pauses for ratification before spawning subjects."
        ),
    )

    # ── Optional API key override ─────────────────────────────────────
    api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.",
    )

    def to_product_research_input(self) -> ProductResearchInput:
        return ProductResearchInput(
            question=self.research_question,
            scope=self.scope,
            slug=self.slug,
            product_context=self.product_context,
            subject_count=self.subject_count,
            ratified_hypotheses=self.hypotheses,
        )

    # ── Construction methods ──────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchConfig":
        """For embedding in Python code."""
        return cls(**data)

    @classmethod
    def from_file(cls, path: Path) -> "ResearchConfig":
        """For programmatic / CI use. Reads YAML or JSON."""
        raw = path.read_text()
        data = yaml.safe_load(raw)
        return cls(**data)

    @classmethod
    def from_interactive(cls) -> "ResearchConfig":
        """For CLI use. Prompts for each required field with guidance."""
        import click

        click.echo("\n=== Voice of Agents: Research Pipeline Setup ===\n")
        click.echo(
            "You will be prompted for 4 required fields. "
            "Press Enter to accept defaults for optional settings.\n"
        )

        research_question = click.prompt(
            "Research question\n"
            "  (falsifiable question about a customer population,\n"
            "   NOT a target-market name like 'US SMBs')\n"
            "  Question"
        )
        scope = click.prompt("\nPopulation scope\n  (region, firm-size, time window)\n  Scope")
        slug = click.prompt(
            "\nRun slug\n  (≤6 kebab-case words, used in file/directory names)\n  Slug"
        )
        product_context = click.prompt(
            "\nProduct context\n  (brief description — NOT a market filter)\n  Context"
        )

        click.echo("\n--- Optional settings (press Enter for defaults) ---\n")
        subject_count = click.prompt("Subject count (10-16)", default=12, type=int)
        anthropic_model = click.prompt("Anthropic model", default="claude-opus-4-7")

        return cls(
            research_question=research_question,
            scope=scope,
            slug=slug,
            product_context=product_context,
            subject_count=subject_count,
            anthropic_model=anthropic_model,
        )

    @classmethod
    async def from_plain_english(
        cls,
        what: str,
        who: str,
        understand: str,
        model: str = "claude-opus-4-7",
        api_key: Optional[str] = None,
    ) -> "ResearchConfig":
        """Translate plain-English inputs into a ResearchConfig using Claude.

        Three plain-English questions → valid ResearchConfig. No methodology
        vocabulary required. A single Claude call handles the translation.

        Args:
            what: One sentence describing what you are building.
            who: One sentence describing your target users.
            understand: The #1 thing you want to understand about them.
            model: Anthropic model for the translation call.
            api_key: Optional API key (falls back to ANTHROPIC_API_KEY).
        """
        import re

        from voice_of_agents.research.client import get_async_client, get_template_env

        client = get_async_client(api_key=api_key)
        env = get_template_env()
        template = env.get_template("quick/translate_to_config.j2")
        prompt = template.render(what=what, who=who, understand=understand)

        response = await client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        match = re.search(r"```(?:yaml)?\n(.*?)```", text, re.DOTALL)
        raw = match.group(1) if match else text

        data = yaml.safe_load(raw)
        return cls(
            research_question=data.get("research_question", understand),
            scope=data.get("scope", who),
            slug=data.get("slug", "quick-research"),
            product_context=data.get("product_context", what),
        )

    # ── Pre-run validation ─────────────────────────────────────────────

    def validate_before_run(self) -> list[str]:
        """Return a list of problems. Empty list means ready to run.

        Called before any API calls to surface config errors early.
        """
        problems: list[str] = []

        # Slug length
        if len(self.slug.split("-")) > 6:
            problems.append(
                f"slug has {len(self.slug.split('-'))} words; maximum is 6. "
                f"Shorten to: {'-'.join(self.slug.split('-')[:6])}"
            )

        # Question shape: warn if it looks like a market description
        market_signals = [
            "--market",
            "target market",
            "us small business",
            "smb ",
            "enterprise customers",
        ]
        lower_q = self.research_question.lower()
        for signal in market_signals:
            if signal in lower_q:
                problems.append(
                    f"research_question appears to be a target-market description "
                    f"(contains '{signal}'). This pre-biases sampling. "
                    f"Reframe as a falsifiable question starting with 'Do', 'Is', 'Are', or 'Why'."
                )

        # Subject count range
        if not (10 <= self.subject_count <= 16):
            problems.append(f"subject_count must be 10-16; got {self.subject_count}.")

        # Hypotheses: if pre-provided, validate them
        if self.hypotheses is not None:
            if len(self.hypotheses) < 4:
                problems.append(
                    f"hypotheses list has {len(self.hypotheses)} entries; minimum is 4."
                )
            if len(self.hypotheses) > 7:
                problems.append(
                    f"hypotheses list has {len(self.hypotheses)} entries; maximum is 7."
                )
            for h in self.hypotheses:
                if not h.falsification_condition.strip():
                    problems.append(f"Hypothesis {h.id} is missing a falsification_condition.")

        return problems

    def to_yaml(self) -> str:
        return yaml.dump(
            self.model_dump(mode="json", exclude_none=True),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml())
