"""Canonical pain point and pain theme models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from voice_of_agents.core.enums import ThemeCode, Intensity


class PainPoint(BaseModel):
    description: str
    impact: str = Field(description="Quantified impact: hours, dollars, error rate")
    current_workaround: Optional[str] = None


class PainTheme(BaseModel):
    theme: ThemeCode
    intensity: Intensity
