"""Unit tests for eval/migrate.py — persona and feature inventory migration."""

from pathlib import Path

import pytest
import yaml

from voice_of_agents.eval.migrate import (
    migrate_feature_inventory,
    migrate_objectives_to_workflow,
    migrate_persona_yaml,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestMigratePersonaYaml:
    def test_basic_conversion(self):
        path = FIXTURES / "sample_persona_legacy.yaml"
        canonical, objectives = migrate_persona_yaml(path)

        assert canonical["id"] == 1
        assert canonical["name"] == "Maria Gutierrez"
        assert canonical["segment"] == "b2c"  # team_size=1
        assert canonical["org_size"] == 1
        assert canonical["tier"] == "DEVELOPER"
        assert canonical["metadata"]["legacy_id"] == "UXW-01"

    def test_pain_points_migrated(self):
        path = FIXTURES / "sample_persona_legacy.yaml"
        canonical, _ = migrate_persona_yaml(path)

        pps = canonical["pain_points"]
        assert len(pps) == 2
        assert pps[0]["description"] == "800 files in Google Drive, can't find anything"
        assert "severity 9/10" in pps[0]["impact"]
        assert "daily" in pps[0]["impact"]
        assert pps[0]["current_workaround"] is None

    def test_pain_themes_deduplicated(self):
        path = FIXTURES / "sample_persona_legacy.yaml"
        canonical, _ = migrate_persona_yaml(path)

        themes = {pt["theme"]: pt["intensity"] for pt in canonical["pain_themes"]}
        assert "A" in themes
        assert "D" in themes
        assert themes["A"] == "CRITICAL"  # severity 9 → CRITICAL
        assert themes["D"] == "HIGH"      # severity 8 → HIGH

    def test_voice_migrated(self):
        path = FIXTURES / "sample_persona_legacy.yaml"
        canonical, _ = migrate_persona_yaml(path)

        voice = canonical["voice"]
        assert voice["skepticism"] == "high"
        assert voice["vocabulary"] == "legal"
        assert voice["motivation"] == "fear"
        assert voice["price_sensitivity"] == "moderate"

    def test_objectives_returned(self):
        path = FIXTURES / "sample_persona_legacy.yaml"
        _, objectives = migrate_persona_yaml(path)

        assert len(objectives) == 2
        assert objectives[0]["goal"] == "Retrieve Past Visa Strategy for Similar Case"
        assert objectives[0]["trigger"] == "New client intake with a case type handled before"

    def test_b2b_segment_inferred(self, tmp_path):
        legacy = {
            "id": "UXW-05",
            "name": "Team Lead",
            "role": "Manager",
            "industry": "Tech",
            "team_size": 8,
            "tier": "TEAM",
            "pain_points": [],
        }
        path = tmp_path / "UXW-05.yaml"
        path.write_text(yaml.dump(legacy))
        canonical, _ = migrate_persona_yaml(path)

        assert canonical["segment"] == "b2b"
        assert canonical["org_size"] == 8

    def test_produces_valid_persona(self):
        from voice_of_agents.core.persona import Persona

        path = FIXTURES / "sample_persona_legacy.yaml"
        canonical, _ = migrate_persona_yaml(path)
        persona = Persona(**canonical)

        assert persona.id == 1
        assert persona.metadata.legacy_id == "UXW-01"
        assert persona.voice.skepticism == "high"
        assert persona.slug == "01-maria-gutierrez"


class TestMigrateObjectivesToWorkflow:
    def test_basic_wrapping(self):
        objectives = [
            {"goal": "Find prior case", "trigger": "New intake", "success_definition": "Found in 60s"},
        ]
        wf = migrate_objectives_to_workflow(1, "Maria Gutierrez", objectives)

        assert wf["persona_id"] == 1
        assert wf["persona_name"] == "Maria Gutierrez"
        assert len(wf["goals"]) == 1
        goal = wf["goals"][0]
        assert goal["id"] == "G-01-1"
        assert goal["title"] == "Find prior case"
        assert goal["trigger"] == "New intake"
        assert goal["success_statement"] == "Found in 60s"
        assert goal["category"] == "knowledge"
        assert goal["priority"] == "primary"

    def test_multiple_objectives(self):
        objectives = [
            {"goal": "Goal 1"},
            {"goal": "Goal 2"},
            {"goal": "Goal 3"},
        ]
        wf = migrate_objectives_to_workflow(7, "Test User", objectives)
        assert len(wf["goals"]) == 3
        assert wf["goals"][2]["id"] == "G-07-3"

    def test_empty_objectives(self):
        wf = migrate_objectives_to_workflow(1, "Empty", [])
        assert wf["goals"] == []


class TestMigrateFeatureInventory:
    def test_missing_file_returns_none(self, tmp_path):
        result = migrate_feature_inventory(tmp_path / "nonexistent.yaml")
        assert result is None

    def test_basic_conversion(self, tmp_path):
        inventory = {
            "product": "TestProduct",
            "features": [
                {
                    "id": "learning-search",
                    "name": "Learning Search",
                    "description": "Search through learnings",
                    "status": "implemented",
                    "area": "Knowledge",
                    "pages": ["/workspace"],
                    "test_results": [
                        {"run_date": "2026-01-01", "status": "pass", "personas_tested": [1, 2]}
                    ],
                }
            ],
        }
        path = tmp_path / "feature-inventory.yaml"
        path.write_text(yaml.dump(inventory))

        registry = migrate_feature_inventory(path)

        assert registry is not None
        assert registry.product == "TestProduct"
        assert len(registry.capabilities) == 1
        cap = registry.capabilities[0]
        assert cap.id == "CAP-LEARNING-SEARCH"
        assert cap.name == "Learning Search"
        assert cap.status == "complete"
        assert cap.feature_area == "Knowledge"
        assert cap.ui_page == "/workspace"
        assert len(cap.test_results) == 1
        assert cap.test_results[0].status == "pass"

    def test_status_mapping(self, tmp_path):
        inventory = {
            "product": "P",
            "features": [
                {"id": "a", "name": "A", "description": "", "status": "missing", "area": "X"},
                {"id": "b", "name": "B", "description": "", "status": "partial", "area": "X"},
                {"id": "c", "name": "C", "description": "", "status": "future", "area": "X"},
            ],
        }
        path = tmp_path / "fi.yaml"
        path.write_text(yaml.dump(inventory))
        registry = migrate_feature_inventory(path)

        statuses = {c.id.split("-", 2)[-1]: c.status for c in registry.capabilities}
        assert statuses["A"] == "planned"
        assert statuses["B"] == "partial"
        assert statuses["C"] == "future"

    def test_single_part_id_gets_misc_prefix(self, tmp_path):
        inventory = {
            "product": "P",
            "features": [{"id": "search", "name": "Search", "description": "", "status": "planned", "area": "X"}],
        }
        path = tmp_path / "fi.yaml"
        path.write_text(yaml.dump(inventory))
        registry = migrate_feature_inventory(path)
        assert registry.capabilities[0].id.startswith("CAP-")
