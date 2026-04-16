"""Pydantic models for persona definitions."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Segment(str, Enum):
    B2C = "b2c"
    B2B = "b2b"


class Tier(str, Enum):
    FREE = "FREE"
    DEVELOPER = "DEVELOPER"
    TEAM = "TEAM"
    ENTERPRISE = "ENTERPRISE"


class ThemeCode(str, Enum):
    A = "A"  # Knowledge retrieval failure
    B = "B"  # Bus factor / SPOF
    C = "C"  # Contextual failure of generic AI
    D = "D"  # Trust deficit
    E = "E"  # Governance vacuum
    F = "F"  # Integration failure


class Intensity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    STALE = "stale"


class PainPoint(BaseModel):
    description: str
    impact: str = Field(description="Quantified impact: hours, dollars, error rate")
    current_workaround: Optional[str] = None


class PainTheme(BaseModel):
    theme: ThemeCode
    intensity: Intensity


class PersonaMetadata(BaseModel):
    source: str = Field(default="manual", description="manual | generated | hybrid")
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    research_basis: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.DRAFT


class Persona(BaseModel):
    """A market-grounded user persona."""

    id: int = Field(ge=1)
    name: str
    role: str
    segment: Segment
    industry: str
    tier: Tier

    age: Optional[int] = Field(default=None, ge=18, le=80)
    income: Optional[int] = Field(default=None, ge=0)
    org_size: int = Field(default=1, ge=1)
    experience_years: Optional[int] = Field(default=None, ge=0)

    ai_history: Optional[str] = None
    mindset: Optional[str] = None
    pain_points: list[PainPoint] = Field(default_factory=list)
    unmet_need: Optional[str] = None
    proof_point: Optional[str] = None

    pain_themes: list[PainTheme] = Field(default_factory=list)
    metadata: PersonaMetadata = Field(default_factory=PersonaMetadata)

    def theme_intensity(self, theme: ThemeCode) -> Optional[Intensity]:
        """Get intensity for a specific pain theme, or None if not present."""
        for pt in self.pain_themes:
            if pt.theme == theme:
                return pt.intensity
        return None

    def is_regulated(self) -> bool:
        """Heuristic: persona is in a regulated industry if trust theme is HIGH+."""
        intensity = self.theme_intensity(ThemeCode.D)
        return intensity in (Intensity.HIGH, Intensity.CRITICAL) if intensity else False
