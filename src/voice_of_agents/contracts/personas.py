"""Persona contract — load, validate, generate, and manage persona definitions."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Objective:
    id: str
    goal: str
    trigger: str = ""
    success_definition: str = ""
    efficiency_baseline: str = ""
    target_efficiency: str = ""


@dataclass
class PainPoint:
    description: str
    severity: int = 5
    frequency: str = "weekly"
    theme: str = "A"


@dataclass
class Voice:
    skepticism: str = "moderate"  # low, moderate, high
    vocabulary: str = "general"  # legal, medical, technical, financial, general
    motivation: str = "efficiency"  # fear, ambition, efficiency, legacy, compliance
    price_sensitivity: str = "moderate"  # low, moderate, high


@dataclass
class Persona:
    id: str
    name: str
    role: str
    industry: str = ""
    experience_years: int = 5
    income: int = 60000
    team_size: int = 1
    tier: str = "DEVELOPER"
    objectives: list[Objective] = field(default_factory=list)
    pain_points: list[PainPoint] = field(default_factory=list)
    trust_requirements: list[str] = field(default_factory=list)
    voice: Voice = field(default_factory=Voice)

    @property
    def slug(self) -> str:
        """URL-safe slug: UXW-01-maria-gutierrez"""
        name_slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"{self.id}-{name_slug}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "industry": self.industry,
            "experience_years": self.experience_years,
            "income": self.income,
            "team_size": self.team_size,
            "tier": self.tier,
            "objectives": [
                {"id": o.id, "goal": o.goal, "trigger": o.trigger,
                 "success_definition": o.success_definition,
                 "efficiency_baseline": o.efficiency_baseline,
                 "target_efficiency": o.target_efficiency}
                for o in self.objectives
            ],
            "pain_points": [
                {"description": p.description, "severity": p.severity,
                 "frequency": p.frequency, "theme": p.theme}
                for p in self.pain_points
            ],
            "trust_requirements": self.trust_requirements,
            "voice": {
                "skepticism": self.voice.skepticism,
                "vocabulary": self.voice.vocabulary,
                "motivation": self.voice.motivation,
                "price_sensitivity": self.voice.price_sensitivity,
            },
        }


def load_personas(personas_dir: Path) -> list[Persona]:
    """Load all persona YAML files from a directory."""
    personas = []
    for f in sorted(personas_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text())
            personas.append(_parse_persona(data))
        except Exception as e:
            logger.warning("Failed to load persona %s: %s", f.name, e)
    return personas


def load_persona(path: Path) -> Persona:
    """Load a single persona from a YAML file."""
    data = yaml.safe_load(path.read_text())
    return _parse_persona(data)


def save_persona(persona: Persona, personas_dir: Path) -> Path:
    """Save a persona to YAML file. Returns the file path."""
    personas_dir.mkdir(parents=True, exist_ok=True)
    path = personas_dir / f"{persona.slug}.yaml"
    path.write_text(yaml.dump(persona.to_dict(), default_flow_style=False, sort_keys=False))
    return path


def validate_persona(persona: Persona) -> list[str]:
    """Validate a persona definition. Returns list of issues (empty = valid)."""
    issues = []
    if not persona.id:
        issues.append("Missing id")
    if not persona.name:
        issues.append("Missing name")
    if not persona.role:
        issues.append("Missing role")
    if not persona.objectives:
        issues.append("No objectives defined")
    if not persona.pain_points:
        issues.append("No pain points defined")
    if persona.tier not in ("FREE", "DEVELOPER", "TEAM", "ENTERPRISE"):
        issues.append(f"Invalid tier: {persona.tier}")
    for obj in persona.objectives:
        if not obj.goal:
            issues.append(f"Objective {obj.id} has no goal")
    return issues


def import_from_markdown(md_dir: Path, out_dir: Path) -> list[Persona]:
    """Import personas from markdown workflow files (rooben-pro format) to YAML.

    Parses the markdown header to extract persona attributes and converts
    workflow step tables into objectives.
    """
    personas = []
    for f in sorted(md_dir.glob("UXW-*.md")):
        try:
            persona = _parse_markdown_persona(f)
            if persona:
                save_persona(persona, out_dir)
                personas.append(persona)
        except Exception as e:
            logger.warning("Failed to import %s: %s", f.name, e)
    return personas


def _parse_persona(data: dict) -> Persona:
    """Parse a persona dict (from YAML) into a Persona dataclass."""
    objectives = [
        Objective(**obj) for obj in data.get("objectives", [])
    ]
    pain_points = [
        PainPoint(**pp) for pp in data.get("pain_points", [])
    ]
    voice_data = data.get("voice", {})
    voice = Voice(**voice_data) if voice_data else Voice()

    return Persona(
        id=data["id"],
        name=data["name"],
        role=data.get("role", ""),
        industry=data.get("industry", ""),
        experience_years=data.get("experience_years", 5),
        income=data.get("income", 60000),
        team_size=data.get("team_size", 1),
        tier=data.get("tier", "DEVELOPER"),
        objectives=objectives,
        pain_points=pain_points,
        trust_requirements=data.get("trust_requirements", []),
        voice=voice,
    )


def _parse_markdown_persona(path: Path) -> Persona | None:
    """Parse a rooben-pro UXW markdown file into a Persona.

    Expected format:
    # UXW-XX: Name — Role
    **Persona**: Name (#XX) — Role, context
    **Tier**: TIER ($XX/mo)
    **Core pain**: ...
    **Motivation**: ...
    **Trust**: ...
    """
    text = path.read_text()
    lines = text.split("\n")

    # Extract header
    header_match = re.match(r"# (UXW-\d+): (.+?) — (.+)", lines[0])
    if not header_match:
        return None

    persona_id = header_match.group(1)
    name = header_match.group(2)
    role = header_match.group(3)

    # Extract attributes from bold lines
    tier = "DEVELOPER"
    core_pain = ""
    motivation = ""
    trust = ""
    industry = ""
    income = 60000
    team_size = 1
    experience_years = 5

    for line in lines[1:20]:
        if line.startswith("**Tier**:"):
            tier_match = re.search(r"(FREE|DEVELOPER|TEAM|ENTERPRISE)", line)
            if tier_match:
                tier = tier_match.group(1)
            price_match = re.search(r"\$(\d+)", line)
            if price_match:
                monthly = int(price_match.group(1))
                # Rough income estimate from willingness to pay
                income = max(40000, monthly * 1500)
        elif line.startswith("**Persona**:"):
            # Extract team size if mentioned
            team_match = re.search(r"(\d+)-person", line)
            if team_match:
                team_size = int(team_match.group(1))
            # Extract industry hints
            for ind in ["Legal", "Medical", "Finance", "Tech", "Manufacturing", "Education",
                        "Real Estate", "Consulting", "HR", "Compliance", "Marketing"]:
                if ind.lower() in line.lower():
                    industry = ind
                    break
        elif line.startswith("**Core pain**:"):
            core_pain = line.split(":", 1)[1].strip()
        elif line.startswith("**Motivation**:"):
            motivation = line.split(":", 1)[1].strip()
        elif line.startswith("**Trust**:"):
            trust = line.split(":", 1)[1].strip()

    # Derive voice attributes
    skepticism = "high" if "skeptic" in trust.lower() or "don't trust" in trust.lower() else "moderate"
    vocab = "general"
    if industry in ("Legal",):
        vocab = "legal"
    elif industry in ("Medical",):
        vocab = "medical"
    elif industry in ("Finance", "Compliance"):
        vocab = "financial"
    elif industry in ("Tech",):
        vocab = "technical"

    motiv = "efficiency"
    if "fear" in motivation.lower() or "liability" in motivation.lower():
        motiv = "fear"
    elif "compliance" in motivation.lower() or "regulator" in motivation.lower():
        motiv = "compliance"
    elif "legacy" in motivation.lower() or "survive" in motivation.lower():
        motiv = "legacy"

    price_sens = "moderate"
    if income < 50000:
        price_sens = "high"
    elif income > 120000:
        price_sens = "low"

    # Extract objectives from workflow sections
    objectives = []
    workflow_sections = re.findall(
        r"## (UXW-\d+-\d+): (.+?)(?:\n\n|\n---)",
        text, re.DOTALL,
    )
    for i, (wf_id, title) in enumerate(workflow_sections):
        # Find the Intent and Success lines after this section
        section_start = text.find(f"## {wf_id}")
        section_text = text[section_start:section_start + 1000]

        intent_match = re.search(r"\*\*Intent\*\*: (.+?)(?:\n)", section_text)
        success_match = re.search(r"\*\*Success \(her words\)\*\*: (.+?)(?:\n)", section_text)
        if not success_match:
            success_match = re.search(r"\*\*Success \(his words\)\*\*: (.+?)(?:\n)", section_text)
        today_match = re.search(r"\*\*Today.*?\*\*: (.+?)(?:\n)", section_text)

        objectives.append(Objective(
            id=f"OBJ-{i + 1:02d}",
            goal=title.strip(),
            trigger=intent_match.group(1).strip() if intent_match else "",
            success_definition=success_match.group(1).strip().strip('"') if success_match else "",
            efficiency_baseline=today_match.group(1).strip() if today_match else "",
        ))

    # Extract pain points
    pain_points = []
    if core_pain:
        pain_points.append(PainPoint(
            description=core_pain,
            severity=8,
            frequency="daily",
            theme="A",
        ))

    trust_reqs = [trust] if trust else []

    return Persona(
        id=persona_id,
        name=name,
        role=role,
        industry=industry,
        experience_years=experience_years,
        income=income,
        team_size=team_size,
        tier=tier,
        objectives=objectives,
        pain_points=pain_points,
        trust_requirements=trust_reqs,
        voice=Voice(
            skepticism=skepticism,
            vocabulary=vocab,
            motivation=motiv,
            price_sensitivity=price_sens,
        ),
    )
