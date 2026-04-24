"""Integration tests: Click CLI commands."""

import pytest
from click.testing import CliRunner

from voice_of_agents.cli.main import cli
from voice_of_agents.cli.eval_cli import _select_personas
from voice_of_agents.eval.config import VoAConfig
from voice_of_agents.core.io import save_persona


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def init_project(runner, tmp_path):
    """Initialize a VoA project in a temp directory."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "eval",
                "init",
                "--target",
                "http://localhost:3000",
                "--api",
                "http://localhost:8420",
                "--data",
                "./data",
            ],
        )
        assert result.exit_code == 0
        assert "Initialized" in result.output
        yield tmp_path


class TestInit:
    def test_creates_config_and_dirs(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(cli, ["eval", "init", "--data", "./data"])
            assert result.exit_code == 0
            assert "Initialized" in result.output
            from pathlib import Path

            assert (Path(td) / "voa-config.json").exists()


class TestStatus:
    def test_no_personas(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["eval", "init", "--data", "./data"])
            result = runner.invoke(cli, ["eval", "status"])
            assert result.exit_code == 0
            assert "0" in result.output

    def test_with_personas(self, runner, tmp_path, maria, rachel):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ["eval", "init", "--data", "./data"])
            config = VoAConfig.load()
            save_persona(maria, config.personas_path)
            save_persona(rachel, config.personas_path)
            result = runner.invoke(cli, ["eval", "status"])
            assert result.exit_code == 0
            assert "2 loaded" in result.output or "Personas: 2" in result.output


class TestSelectPersonas:
    def test_by_id(self, maria, rachel):
        selected = _select_personas([maria, rachel], "1", None, False)
        assert len(selected) == 1
        assert selected[0].id == 1

    def test_by_batch(self, maria, rachel):
        selected = _select_personas([maria, rachel], None, 1, False)
        assert len(selected) == 2

    def test_all_flag(self, maria, rachel):
        selected = _select_personas([maria, rachel], None, None, True)
        assert len(selected) == 2

    def test_no_flags_raises(self, maria):
        import click

        with pytest.raises(click.exceptions.ClickException):
            _select_personas([maria], None, None, False)
