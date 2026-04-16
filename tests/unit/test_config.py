"""Tests for VoAConfig."""

import json
from pathlib import Path

from voice_of_agents.eval.config import VoAConfig


class TestVoAConfigDefaults:
    """Default instantiation has correct values."""

    def test_default_target_url(self):
        cfg = VoAConfig()
        assert cfg.target_url == "http://localhost:3000"

    def test_default_api_url(self):
        cfg = VoAConfig()
        assert cfg.api_url == "http://localhost:8420"

    def test_default_data_dir(self):
        cfg = VoAConfig()
        assert cfg.data_dir == "./data"

    def test_default_batch_size(self):
        cfg = VoAConfig()
        assert cfg.batch_size == 5

    def test_default_pain_themes_has_six_entries(self):
        cfg = VoAConfig()
        assert len(cfg.pain_themes) == 6
        assert "A" in cfg.pain_themes
        assert "F" in cfg.pain_themes


class TestVoAConfigPaths:
    """Path properties derive correctly from data_dir."""

    def test_data_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.data_path == Path("/tmp/voa")

    def test_personas_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.personas_path == Path("/tmp/voa/personas")

    def test_results_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.results_path == Path("/tmp/voa/results")

    def test_backlog_jsonl_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.backlog_jsonl_path == Path("/tmp/voa/backlog.jsonl")

    def test_inventory_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.inventory_path == Path("/tmp/voa/feature-inventory.yaml")

    def test_findings_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.findings_path == Path("/tmp/voa/004-findings.md")

    def test_backlog_md_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.backlog_md_path == Path("/tmp/voa/005-backlog.md")

    def test_diff_report_path(self):
        cfg = VoAConfig(data_dir="/tmp/voa")
        assert cfg.diff_report_path == Path("/tmp/voa/006-diff-report.md")


class TestVoAConfigWeights:
    """Scoring weights sum to 1.0."""

    def test_weights_sum_to_one(self):
        cfg = VoAConfig()
        total = cfg.weight_coverage + cfg.weight_pain + cfg.weight_revenue + cfg.weight_effort
        assert abs(total - 1.0) < 1e-9


class TestVoAConfigSaveLoad:
    """Save/load roundtrip works."""

    def test_save_creates_json_file(self, tmp_path):
        cfg = VoAConfig(target_url="http://example:9000", batch_size=10)
        out = tmp_path / "voa-config.json"
        cfg.save(out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["target_url"] == "http://example:9000"
        assert data["batch_size"] == 10

    def test_roundtrip_preserves_values(self, tmp_path):
        original = VoAConfig(
            target_url="http://custom:5000",
            api_url="http://custom:8000",
            data_dir="/custom/data",
            batch_size=20,
            weight_coverage=0.40,
            weight_pain=0.30,
            weight_revenue=0.20,
            weight_effort=0.10,
        )
        out = tmp_path / "cfg.json"
        original.save(out)
        loaded = VoAConfig.load(out)

        assert loaded.target_url == original.target_url
        assert loaded.api_url == original.api_url
        assert loaded.data_dir == original.data_dir
        assert loaded.batch_size == original.batch_size
        assert loaded.weight_coverage == original.weight_coverage
        assert loaded.weight_pain == original.weight_pain
        assert loaded.weight_revenue == original.weight_revenue
        assert loaded.weight_effort == original.weight_effort

    def test_load_missing_file_returns_defaults(self, tmp_path):
        loaded = VoAConfig.load(tmp_path / "nonexistent.json")
        default = VoAConfig()
        assert loaded.target_url == default.target_url
        assert loaded.batch_size == default.batch_size

    def test_load_ignores_unknown_keys(self, tmp_path):
        out = tmp_path / "cfg.json"
        out.write_text(json.dumps({"target_url": "http://x:1", "unknown_field": True}))
        loaded = VoAConfig.load(out)
        assert loaded.target_url == "http://x:1"
        assert not hasattr(loaded, "unknown_field") or loaded.__dict__.get("unknown_field") is None
