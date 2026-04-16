"""Tests for FeatureInventory."""

from voice_of_agents.contracts.inventory import Feature, FeatureInventory, TestResult


class TestFeatureLatestTest:
    """Feature.latest_test returns last test result or None."""

    def test_no_tests_returns_none(self):
        f = Feature(id="F-01", name="Search", area="knowledge")
        assert f.latest_test is None

    def test_single_test_returned(self):
        tr = TestResult(run="2026-04-01", status="working", notes="OK")
        f = Feature(id="F-01", name="Search", area="knowledge", test_results=[tr])
        assert f.latest_test is tr

    def test_multiple_tests_returns_last(self):
        tr1 = TestResult(run="2026-03-01", status="broken")
        tr2 = TestResult(run="2026-04-01", status="working")
        f = Feature(id="F-01", name="Search", area="knowledge", test_results=[tr1, tr2])
        assert f.latest_test is tr2
        assert f.latest_test.status == "working"


class TestAddFeature:
    """add_feature() for new feature appends; for duplicate, merges."""

    def test_add_new_feature_appends(self):
        inv = FeatureInventory()
        f = Feature(id="F-01", name="Search", area="knowledge")
        inv.add_feature(f)
        assert len(inv.features) == 1
        assert inv.features[0].id == "F-01"

    def test_add_new_feature_sets_first_reported(self):
        inv = FeatureInventory()
        f = Feature(id="F-01", name="Search", area="knowledge")
        assert f.first_reported == ""
        inv.add_feature(f)
        # first_reported is filled in by add_feature
        assert inv.features[0].first_reported != ""

    def test_add_duplicate_merges_status(self):
        inv = FeatureInventory()
        f1 = Feature(id="F-01", name="Search", area="knowledge", status="implemented")
        inv.add_feature(f1)
        assert inv.features[0].status == "implemented"

        f2 = Feature(id="F-01", name="Search", area="knowledge", status="partial")
        inv.add_feature(f2)
        # Should NOT create a second feature
        assert len(inv.features) == 1
        # Status updated to the new value
        assert inv.features[0].status == "partial"

    def test_add_duplicate_merges_test_results(self):
        inv = FeatureInventory()
        tr1 = TestResult(run="2026-03-01", status="working")
        f1 = Feature(id="F-01", name="Search", area="knowledge", test_results=[tr1])
        inv.add_feature(f1)

        tr2 = TestResult(run="2026-04-01", status="broken")
        f2 = Feature(id="F-01", name="Search", area="knowledge", test_results=[tr2])
        inv.add_feature(f2)

        assert len(inv.features) == 1
        assert len(inv.features[0].test_results) == 2
        assert inv.features[0].test_results[0].status == "working"
        assert inv.features[0].test_results[1].status == "broken"

    def test_add_duplicate_merges_requested_by(self):
        inv = FeatureInventory()
        f1 = Feature(id="F-01", name="Search", area="knowledge", requested_by=["UXW-01"])
        inv.add_feature(f1)

        f2 = Feature(id="F-01", name="Search", area="knowledge", requested_by=["UXW-01", "UXW-20"])
        inv.add_feature(f2)

        assert len(inv.features) == 1
        assert set(inv.features[0].requested_by) == {"UXW-01", "UXW-20"}

    def test_add_duplicate_merges_pages(self):
        inv = FeatureInventory()
        f1 = Feature(id="F-01", name="Search", area="knowledge", pages=["/search"])
        inv.add_feature(f1)

        f2 = Feature(id="F-01", name="Search", area="knowledge", pages=["/search", "/pro/search"])
        inv.add_feature(f2)

        assert len(inv.features) == 1
        assert set(inv.features[0].pages) == {"/search", "/pro/search"}


class TestFeaturesByArea:
    """features_by_area() groups correctly."""

    def test_groups_by_area(self):
        inv = FeatureInventory(features=[
            Feature(id="F-01", name="Search", area="knowledge"),
            Feature(id="F-02", name="Import", area="knowledge"),
            Feature(id="F-03", name="Delegation", area="delegation"),
        ])
        grouped = inv.features_by_area()
        assert set(grouped.keys()) == {"knowledge", "delegation"}
        assert len(grouped["knowledge"]) == 2
        assert len(grouped["delegation"]) == 1

    def test_empty_inventory_groups_to_empty_dict(self):
        inv = FeatureInventory()
        assert inv.features_by_area() == {}


class TestSummary:
    """summary() counts by status."""

    def test_counts_by_status(self):
        inv = FeatureInventory(features=[
            Feature(id="F-01", name="A", area="x", status="implemented"),
            Feature(id="F-02", name="B", area="x", status="implemented"),
            Feature(id="F-03", name="C", area="x", status="missing"),
            Feature(id="F-04", name="D", area="x", status="partial"),
        ])
        s = inv.summary()
        assert s["implemented"] == 2
        assert s["missing"] == 1
        assert s["partial"] == 1

    def test_empty_inventory_summary(self):
        inv = FeatureInventory()
        assert inv.summary() == {}


class TestEmptyInventoryOperations:
    """Empty inventory edge cases."""

    def test_get_nonexistent(self):
        inv = FeatureInventory()
        assert inv.get("F-999") is None

    def test_summary_empty(self):
        inv = FeatureInventory()
        assert inv.summary() == {}

    def test_features_by_area_empty(self):
        inv = FeatureInventory()
        assert inv.features_by_area() == {}
