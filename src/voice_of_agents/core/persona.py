"""Canonical Persona model — single source of truth for both design and eval layers."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from voice_of_agents.core.enums import Tier, Segment, ValidationStatus
from voice_of_agents.core.pain import PainPoint, PainTheme


class VoiceProfile(BaseModel):
    """Behavioral calibration for persona-authentic evaluation narratives.

    All fields have defaults representing a neutral "average person" —
    eval code can always access these unconditionally without None guards.
    """

    skepticism: Literal["low", "moderate", "high"] = "moderate"
    vocabulary: Literal["legal", "medical", "financial", "technical", "general"] = "general"
    motivation: Literal["fear", "ambition", "efficiency", "legacy", "compliance"] = "efficiency"
    price_sensitivity: Literal["low", "moderate", "high"] = "moderate"


class PersonaMetadata(BaseModel):
    source: Literal["manual", "generated", "hybrid"] = "manual"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    research_basis: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.DRAFT
    legacy_id: Optional[str] = None  # e.g. "UXW-01" — migration tracing only


class Persona(BaseModel):
    """A market-grounded user persona used by both design planning and runtime evaluation."""

    id: int = Field(ge=1)
    name: str
    role: str
    industry: str
    segment: Segment
    tier: Tier

    age: Optional[int] = Field(default=None, ge=18, le=80)
    income: Optional[int] = Field(default=None, ge=0)
    org_size: int = Field(default=1, ge=1)
    experience_years: Optional[int] = Field(default=None, ge=0)

    ai_history: Optional[str] = None
    mindset: Optional[str] = None
    pain_points: list[PainPoint] = Field(default_factory=list)
    pain_themes: list[PainTheme] = Field(default_factory=list)
    unmet_need: Optional[str] = None
    proof_point: Optional[str] = None
    trust_requirements: list[str] = Field(default_factory=list)

    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    metadata: PersonaMetadata = Field(default_factory=PersonaMetadata)

    @property
    def slug(self) -> str:
        """URL-safe identifier: '01-maria-gutierrez'."""
        name_slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"{self.id:02d}-{name_slug}"

    def theme_intensity(self, theme_code: str) -> Optional[str]:
        """Return intensity for a pain theme code, or None if not present."""
        from voice_of_agents.core.enums import ThemeCode
        for pt in self.pain_themes:
            if pt.theme.value == theme_code:
                return pt.intensity.value
        return None

    def is_regulated(self) -> bool:
        """Heuristic: HIGH or CRITICAL trust theme implies regulated industry."""
        intensity = self.theme_intensity("D")
        return intensity in ("HIGH", "CRITICAL")
