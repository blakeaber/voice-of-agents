"""Tests for helper functions in voice_of_agents.eval.phase5_prioritize."""

from pathlib import Path

import pytest
import yaml

from voice_of_agents.eval.phase5_prioritize import (
    _load_findings,
    _load_persona_tiers,
    _to_int_ids,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestLoadFindings:
    def test_returns_empty_for_missing_file(self, tmp_path):
        findings = _load_findings(tmp_path / "nonexistent.md")
        assert findings == []

    def test_parses_finding_ids(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        ids = [f["id"] for f in findings]
        assert "F-001" in ids
        assert "F-002" in ids
        assert "F-003" in ids

    def test_parses_severity(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        assert f001["impact"]["severity"] == pytest.approx(8.0)

    def test_parses_theme(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        assert f001["classification"]["pain_theme"] == "A"

    def test_parses_personas(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        personas = f001["evidence"]["personas_affected"]
        assert "UXW-01" in personas
        assert "UXW-02" in personas

    def test_parses_status(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        resolved = next(f for f in findings if f["id"] == "F-003")
        assert resolved["status"] == "resolved"

    def test_open_status_default(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        assert f001["status"] == "open"

    def test_parses_quotes(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        quotes = f001["evidence"]["representative_quotes"]
        assert any("past decisions" in q["quote"] for q in quotes)

    def test_parses_title(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        f001 = next(f for f in findings if f["id"] == "F-001")
        assert "Cannot Retrieve Past Work" in f001.get("title", "")

    def test_all_findings_count(self):
        findings = _load_findings(FIXTURES / "sample_findings.md")
        assert len(findings) == 3


class TestLoadPersonaTiers:
    def test_returns_empty_for_missing_dir(self, tmp_path):
        tiers = _load_persona_tiers(tmp_path / "nonexistent")
        assert tiers == {}

    def test_loads_tier_from_evaluation_yaml(self, tmp_path):
        persona_dir = tmp_path / "01-maria-gutierrez"
        run_dir = persona_dir / "20260402_120000"
        run_dir.mkdir(parents=True)
        eval_data = {"persona": {"id": "UXW-01", "tier": "DEVELOPER"}}
        (run_dir / "003-evaluation.yaml").write_text(yaml.dump(eval_data))
        tiers = _load_persona_tiers(tmp_path)
        assert tiers.get("UXW-01") == "DEVELOPER"

    def test_uses_latest_run(self, tmp_path):
        persona_dir = tmp_path / "01-maria-gutierrez"
        old_run = persona_dir / "20260401_000000"
        new_run = persona_dir / "20260402_000000"
        old_run.mkdir(parents=True)
        new_run.mkdir(parents=True)
        (old_run / "003-evaluation.yaml").write_text(
            yaml.dump({"persona": {"id": "UXW-01", "tier": "FREE"}})
        )
        (new_run / "003-evaluation.yaml").write_text(
            yaml.dump({"persona": {"id": "UXW-01", "tier": "ENTERPRISE"}})
        )
        tiers = _load_persona_tiers(tmp_path)
        assert tiers.get("UXW-01") == "ENTERPRISE"

    def test_skips_dir_without_evaluation(self, tmp_path):
        persona_dir = tmp_path / "01-maria-gutierrez"
        run_dir = persona_dir / "20260402_120000"
        run_dir.mkdir(parents=True)
        tiers = _load_persona_tiers(tmp_path)
        assert tiers == {}

    def test_ignores_non_directory_entries(self, tmp_path):
        (tmp_path / "some-file.yaml").write_text("data: 1")
        tiers = _load_persona_tiers(tmp_path)
        assert tiers == {}


class TestToIntIds:
    def test_int_passthrough(self):
        assert _to_int_ids([1, 2, 3]) == [1, 2, 3]

    def test_uxw_string_parsed(self):
        assert _to_int_ids(["UXW-01", "UXW-20"]) == [1, 20]

    def test_mixed_types(self):
        assert _to_int_ids([1, "UXW-05", 3]) == [1, 5, 3]

    def test_invalid_string_skipped(self):
        assert _to_int_ids(["no-digits-here"]) == []

    def test_empty_list(self):
        assert _to_int_ids([]) == []
