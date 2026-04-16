"""Feature inventory contract — append-only feature tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    run: str  # ISO date
    status: str  # working, partial, broken, untested
    notes: str = ""
    personas_tested: list[str] = field(default_factory=list)


@dataclass
class Feature:
    id: str
    name: str
    area: str  # knowledge, delegation, billing, admin, etc.
    status: str = "implemented"  # implemented, partial, missing, planned
    pages: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    first_reported: str = ""
    requested_by: list[str] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)

    @property
    def latest_test(self) -> TestResult | None:
        return self.test_results[-1] if self.test_results else None

    def add_test_result(self, status: str, notes: str = "", personas: list[str] | None = None):
        self.test_results.append(TestResult(
            run=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            status=status,
            notes=notes,
            personas_tested=personas or [],
        ))


@dataclass
class FeatureInventory:
    source: str = ""
    features: list[Feature] = field(default_factory=list)

    def get(self, feature_id: str) -> Feature | None:
        return next((f for f in self.features if f.id == feature_id), None)

    def add_feature(self, feature: Feature) -> None:
        """Add a feature. Never overwrites — appends or updates existing."""
        existing = self.get(feature.id)
        if existing:
            # Merge: update status, append test results, extend requested_by
            existing.status = feature.status
            existing.test_results.extend(feature.test_results)
            existing.requested_by = list(set(existing.requested_by + feature.requested_by))
            if feature.pages:
                existing.pages = list(set(existing.pages + feature.pages))
            if feature.endpoints:
                existing.endpoints = list(set(existing.endpoints + feature.endpoints))
        else:
            if not feature.first_reported:
                feature.first_reported = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.features.append(feature)

    def features_by_area(self) -> dict[str, list[Feature]]:
        result: dict[str, list[Feature]] = {}
        for f in self.features:
            result.setdefault(f.area, []).append(f)
        return result

    def summary(self) -> dict[str, int]:
        """Count features by status."""
        counts: dict[str, int] = {}
        for f in self.features:
            counts[f.status] = counts.get(f.status, 0) + 1
        return counts


def load_inventory(path: Path) -> FeatureInventory:
    """Load feature inventory from YAML."""
    if not path.exists():
        return FeatureInventory()

    data = yaml.safe_load(path.read_text())
    if not data:
        return FeatureInventory()

    features = []
    for fd in data.get("features", []):
        test_results = [
            TestResult(**tr) if isinstance(tr, dict) else tr
            for tr in fd.get("test_results", [])
        ]
        features.append(Feature(
            id=fd["id"],
            name=fd["name"],
            area=fd.get("area", ""),
            status=fd.get("status", "implemented"),
            pages=fd.get("pages", []),
            endpoints=fd.get("endpoints", []),
            first_reported=fd.get("first_reported", ""),
            requested_by=fd.get("requested_by", []),
            test_results=test_results,
        ))

    return FeatureInventory(source=data.get("source", ""), features=features)


def save_inventory(inventory: FeatureInventory, path: Path) -> None:
    """Save feature inventory to YAML. Preserves all existing data."""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": inventory.source,
        "features": [
            {
                "id": f.id,
                "name": f.name,
                "area": f.area,
                "status": f.status,
                "pages": f.pages,
                "endpoints": f.endpoints,
                "first_reported": f.first_reported,
                "requested_by": f.requested_by,
                "test_results": [
                    {"run": tr.run, "status": tr.status, "notes": tr.notes,
                     "personas_tested": tr.personas_tested}
                    for tr in f.test_results
                ],
            }
            for f in inventory.features
        ],
    }

    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
