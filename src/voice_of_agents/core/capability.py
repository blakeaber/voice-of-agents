"""Unified Capability and CapabilityRegistry — absorbs both Pro's registry and Main's FeatureInventory."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Runtime test result recorded against a capability."""

    run_date: str
    status: Literal["pass", "fail", "skip", "not_tested"]
    personas_tested: list[int] = Field(default_factory=list)


class Capability(BaseModel):
    """A single platform capability referenced by workflows and tracked through testing."""

    id: str = Field(description="CAP-AREA-NAME format, e.g. CAP-LEARN-SEARCH")
    name: str
    description: str = ""
    status: Literal["complete", "partial", "planned", "future"]
    feature_area: str

    # Structural linkage (from Pro)
    api_endpoint: Optional[str] = None
    ui_page: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)

    # Runtime tracking (from Main's FeatureInventory)
    test_results: list[TestResult] = Field(default_factory=list)
    requested_by: list[int] = Field(default_factory=list)  # Persona IDs
    first_reported: Optional[str] = None

    def is_available(self) -> bool:
        return self.status in ("complete", "partial")

    def latest_test(self) -> Optional[TestResult]:
        return self.test_results[-1] if self.test_results else None


class CapabilityRegistry(BaseModel):
    """Collection of all platform capabilities."""

    product: str
    version: str = "1.0.0"
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

    def by_status(self, status: str) -> list[Capability]:
        return [c for c in self.capabilities if c.status == status]

    def feature_areas(self) -> list[str]:
        return sorted({c.feature_area for c in self.capabilities})
