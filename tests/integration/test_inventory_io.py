"""Integration tests: Feature inventory YAML save/load roundtrip."""

import pytest

from voice_of_agents.contracts.inventory import (
    Feature, FeatureInventory, TestResult,
    load_inventory, save_inventory,
)


class TestInventoryRoundtrip:
    def test_save_load_preserves_features(self, tmp_data_dir):
        inv = FeatureInventory(source="test")
        inv.add_feature(Feature(
            id="F-001", name="Knowledge Library", area="knowledge",
            status="implemented", pages=["/pro/learnings"],
        ))
        inv.features[0].add_test_result("working", "All good", ["UXW-01"])

        path = tmp_data_dir / "feature-inventory.yaml"
        save_inventory(inv, path)
        loaded = load_inventory(path)

        assert loaded.source == "test"
        assert len(loaded.features) == 1
        f = loaded.features[0]
        assert f.id == "F-001"
        assert f.name == "Knowledge Library"
        assert f.status == "implemented"
        assert f.pages == ["/pro/learnings"]
        assert len(f.test_results) == 1
        assert f.test_results[0].status == "working"
        assert f.test_results[0].personas_tested == ["UXW-01"]

    def test_missing_file_returns_empty(self, tmp_data_dir):
        inv = load_inventory(tmp_data_dir / "nonexistent.yaml")
        assert len(inv.features) == 0

    def test_add_test_result_persists(self, tmp_data_dir):
        path = tmp_data_dir / "inv.yaml"
        inv = FeatureInventory(source="test")
        inv.add_feature(Feature(id="F-001", name="Test", area="test"))
        inv.features[0].add_test_result("working")
        inv.features[0].add_test_result("broken", "Regression")
        save_inventory(inv, path)
        loaded = load_inventory(path)
        assert len(loaded.features[0].test_results) == 2
        assert loaded.features[0].test_results[1].status == "broken"
