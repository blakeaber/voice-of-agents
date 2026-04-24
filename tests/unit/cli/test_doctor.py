"""Unit tests for `voa doctor` — pre-flight diagnostic command."""

from __future__ import annotations

import sys

from click.testing import CliRunner

from voice_of_agents.cli.doctor_cli import (
    FAIL,
    OK,
    WARN,
    CheckResult,
    _check_api_key,
    _check_disk_space,
    _check_path_conflicts,
    _check_python_version,
    doctor,
)


def _strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── Unit-level checks ──────────────────────────────────────────────


def test_check_python_version_passes_on_current_interpreter():
    result = _check_python_version()
    assert isinstance(result, CheckResult)
    assert result.name == "Python ≥ 3.11"
    # The test runner itself must satisfy the pyproject requires-python.
    assert result.status == OK
    assert str(sys.version_info.major) in result.detail


def test_check_api_key_passes_with_valid_prefix(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-deadbeefdeadbeefdeadbeefdeadbeef")
    result = _check_api_key()
    assert result.status == OK
    # Redaction: should not include the middle of the key.
    assert "deadbeef" not in result.detail


def test_check_api_key_fails_when_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = _check_api_key()
    assert result.status == FAIL
    assert "ANTHROPIC_API_KEY" in result.detail
    # Must include an actionable fix command
    assert "export ANTHROPIC_API_KEY" in result.detail


def test_check_api_key_fails_on_bad_prefix(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    result = _check_api_key()
    assert result.status == FAIL
    assert "sk-ant-" in result.detail


def test_check_disk_space_returns_result():
    result = _check_disk_space()
    assert result.status in (OK, WARN, FAIL)
    assert "GB free" in result.detail


def test_check_path_conflicts_with_empty_path(monkeypatch):
    monkeypatch.setenv("PATH", "")
    result = _check_path_conflicts()
    assert result.status == FAIL


# ── CLI-level integration via Click runner ─────────────────────────


def test_doctor_command_exits_1_when_api_key_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(doctor, ["--offline"])
    assert result.exit_code == 1
    # Fix command must be surfaced in the rendered output
    assert "export ANTHROPIC_API_KEY" in _strip_ansi(result.output)


def test_doctor_offline_skips_api_roundtrip(monkeypatch):
    """--offline must not attempt an Anthropic API call."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-deadbeefdeadbeefdeadbeefdeadbeef")
    # If the roundtrip check ran, it would raise on a fake key; with
    # --offline, the check is skipped entirely and the table doesn't
    # include a "round-trip" row.
    runner = CliRunner()
    result = runner.invoke(doctor, ["--offline"])
    out = _strip_ansi(result.output)
    assert (
        "round-trip" not in out.lower()
        or "round-trip" in out.lower()
        and "Anthropic API" not in out
    )
    # Specifically the roundtrip check's name
    assert "Anthropic API round-trip" not in out


def test_doctor_help_lists_offline_flag():
    runner = CliRunner()
    result = runner.invoke(doctor, ["--help"])
    assert result.exit_code == 0
    assert "--offline" in result.output


def test_doctor_always_emits_table_header(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-deadbeefdeadbeefdeadbeefdeadbeef")
    runner = CliRunner()
    result = runner.invoke(doctor, ["--offline"])
    out = _strip_ansi(result.output)
    # Title row of the Rich table
    assert "voa doctor" in out
    # Every check should appear by its name
    assert "Python" in out
    assert "ANTHROPIC_API_KEY" in out
    assert "Playwright" in out
    assert "Disk space" in out
    assert "`voa` on $PATH" in out or "voa` on $PATH" in out
