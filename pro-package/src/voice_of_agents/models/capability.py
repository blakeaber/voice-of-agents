"""Pydantic models for the capability registry."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    PLANNED = "planned"
    FUTURE = "future"


class CapabilityMetadata(BaseModel):
    implemented_in: Optional[str] = None
    test_coverage: Optional[bool] = None
    notes: Optional[str] = None


class Capability(BaseModel):
    """A single platform capability that workflows reference."""

    id: str = Field(pattern=r"^CAP-[A-Z]+-[A-Z]+$")
    name: str
    description: Optional[str] = None
    status: CapabilityStatus
    api_endpoint: Optional[str] = None
    ui_page: Optional[str] = None
    feature_area: str
    dependencies: list[str] = Field(default_factory=list)
    metadata: CapabilityMetadata = Field(default_factory=CapabilityMetadata)

    def is_available(self) -> bool:
        return self.status in (CapabilityStatus.COMPLETE, CapabilityStatus.PARTIAL)


class CapabilityRegistry(BaseModel):
    """Collection of all platform capabilities."""

    product: str = Field(description="Product name this registry belongs to")
    version: str = Field(default="0.1.0")
    capabilities: list[Capability] = Field(default_factory=list)

    def get(self, capability_id: str) -> Optional[Capability]:
        for cap in self.capabilities:
            if cap.id == capability_id:
                return cap
        return None

    def available(self) -> list[Capability]:
        return [c for c in self.capabilities if c.is_available()]

    def by_feature_area(self, area: str) -> list[Capability]:
        return [c for c in self.capabilities if c.feature_area == area]

    def by_status(self, status: CapabilityStatus) -> list[Capability]:
        return [c for c in self.capabilities if c.status == status]

    def feature_areas(self) -> list[str]:
        return sorted({c.feature_area for c in self.capabilities})
