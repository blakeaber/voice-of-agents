"""Unit tests for core/capability.py — Capability, CapabilityRegistry, TestResult."""

from __future__ import annotations


from voice_of_agents.core.capability import Capability, CapabilityRegistry, TestResult


def _cap(**kwargs):
    defaults = dict(
        id="CAP-LEARN-SEARCH",
        name="Learning Search",
        description="Search learnings",
        status="complete",
        feature_area="Learning System",
    )
    defaults.update(kwargs)
    return Capability(**defaults)


class TestCapability:
    def test_basic_creation(self):
        c = _cap()
        assert c.id == "CAP-LEARN-SEARCH"
        assert c.feature_area == "Learning System"

    def test_is_available_complete(self):
        assert _cap(status="complete").is_available() is True

    def test_is_available_partial(self):
        assert _cap(status="partial").is_available() is True

    def test_is_available_planned(self):
        assert _cap(status="planned").is_available() is False

    def test_is_available_future(self):
        assert _cap(status="future").is_available() is False

    def test_latest_test_empty(self):
        assert _cap().latest_test() is None

    def test_latest_test_returns_last(self):
        c = _cap(
            test_results=[
                TestResult(run_date="2026-01-01", status="pass"),
                TestResult(run_date="2026-02-01", status="fail"),
            ]
        )
        assert c.latest_test().status == "fail"
        assert c.latest_test().run_date == "2026-02-01"

    def test_requested_by_defaults_empty(self):
        assert _cap().requested_by == []

    def test_personas_in_test_result(self):
        c = _cap(
            test_results=[
                TestResult(run_date="2026-01-01", status="pass", personas_tested=[1, 2, 3])
            ]
        )
        assert c.latest_test().personas_tested == [1, 2, 3]


class TestCapabilityRegistry:
    def _registry(self):
        return CapabilityRegistry(
            product="TestApp",
            version="1.0.0",
            capabilities=[
                _cap(id="CAP-LEARN-SEARCH", status="complete", feature_area="Learning"),
                _cap(id="CAP-LEARN-CREATE", status="partial", feature_area="Learning"),
                _cap(id="CAP-DELEG-ROUTE", status="planned", feature_area="Delegation"),
                _cap(id="CAP-GOV-AUDIT", status="future", feature_area="Governance"),
            ],
        )

    def test_get_found(self):
        r = self._registry()
        c = r.get("CAP-LEARN-SEARCH")
        assert c is not None
        assert c.name == "Learning Search"

    def test_get_not_found(self):
        assert self._registry().get("CAP-NONEXISTENT") is None

    def test_available(self):
        avail = self._registry().available()
        assert len(avail) == 2
        assert all(c.is_available() for c in avail)

    def test_by_feature_area(self):
        learning = self._registry().by_feature_area("Learning")
        assert len(learning) == 2

    def test_by_feature_area_none(self):
        assert self._registry().by_feature_area("Nonexistent") == []

    def test_by_status(self):
        planned = self._registry().by_status("planned")
        assert len(planned) == 1
        assert planned[0].id == "CAP-DELEG-ROUTE"

    def test_feature_areas_sorted(self):
        areas = self._registry().feature_areas()
        assert areas == sorted(areas)
        assert "Learning" in areas
        assert "Delegation" in areas
