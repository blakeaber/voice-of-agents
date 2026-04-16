"""Target application configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "voa-config.json"


@dataclass
class VoAConfig:
    """Configuration for a Voice of Agents evaluation run."""

    target_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8420"
    data_dir: str = "./data"
    batch_size: int = 5

    # Scoring weights (must sum to 1.0)
    weight_coverage: float = 0.30
    weight_pain: float = 0.25
    weight_revenue: float = 0.25
    weight_effort: float = 0.20

    # Pain themes reference
    pain_themes: dict[str, str] = field(default_factory=lambda: {
        "A": "Knowledge Retrieval Failure",
        "B": "Single Point of Failure / Bus Factor",
        "C": "Contextual Failure",
        "D": "Trust Deficit",
        "E": "Governance Vacuum",
        "F": "Integration Failure",
    })

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def personas_path(self) -> Path:
        return self.data_path / "personas"

    @property
    def results_path(self) -> Path:
        return self.data_path / "results"

    @property
    def backlog_jsonl_path(self) -> Path:
        return self.data_path / "backlog.jsonl"

    @property
    def inventory_path(self) -> Path:
        return self.data_path / "feature-inventory.yaml"

    @property
    def findings_path(self) -> Path:
        return self.data_path / "004-findings.md"

    @property
    def focus_group_path(self) -> Path:
        return self.data_path / "003-focus-group-analysis.md"

    @property
    def backlog_md_path(self) -> Path:
        return self.data_path / "005-backlog.md"

    @property
    def diff_report_path(self) -> Path:
        return self.data_path / "006-diff-report.md"

    @property
    def capabilities_path(self) -> Path:
        return self.data_path / "capabilities.yaml"

    @property
    def workflows_path(self) -> Path:
        return self.data_path / "workflows"

    def resolve_result_slug(self, persona) -> str:
        """Return the best matching result directory slug for a persona.

        Checks new format (01-maria-gutierrez) first, then legacy UXW format.
        Returns the new-format slug regardless — callers use this to write new runs.
        """
        new_slug = persona.slug
        results = self.results_path
        if (results / new_slug).exists():
            return new_slug
        legacy_id = getattr(getattr(persona, "metadata", None), "legacy_id", None)
        if legacy_id:
            legacy_slug = f"{legacy_id.lower()}-{new_slug.split('-', 1)[1]}"
            if (results / legacy_slug).exists():
                return legacy_slug
        return new_slug

    def save(self, path: Path | None = None) -> None:
        """Save config to JSON file."""
        p = path or Path(CONFIG_FILE)
        p.write_text(json.dumps(self.__dict__, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path | None = None) -> VoAConfig:
        """Load config from JSON file, or return defaults."""
        p = path or Path(CONFIG_FILE)
        if p.exists():
            data = json.loads(p.read_text())
            # Filter to only known fields
            known = {f.name for f in cls.__dataclass_fields__.values()}
            return cls(**{k: v for k, v in data.items() if k in known})
        return cls()
