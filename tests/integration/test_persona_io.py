"""Integration tests: Persona YAML save/load roundtrip."""

import pytest

from voice_of_agents.contracts.personas import (
    load_persona, load_personas, save_persona, validate_persona,
)


class TestPersonaRoundtrip:
    def test_save_load_preserves_fields(self, maria, tmp_data_dir):
        path = save_persona(maria, tmp_data_dir / "personas")
        loaded = load_persona(path)
        assert loaded.id == maria.id
        assert loaded.name == maria.name
        assert loaded.role == maria.role
        assert loaded.industry == maria.industry
        assert loaded.tier == maria.tier
        assert loaded.income == maria.income
        assert loaded.experience_years == maria.experience_years
        assert loaded.team_size == maria.team_size
        assert len(loaded.objectives) == len(maria.objectives)
        assert loaded.objectives[0].goal == maria.objectives[0].goal
        assert loaded.objectives[0].trigger == maria.objectives[0].trigger
        assert len(loaded.pain_points) == len(maria.pain_points)
        assert loaded.voice.skepticism == maria.voice.skepticism
        assert loaded.voice.vocabulary == maria.voice.vocabulary
        assert loaded.trust_requirements == maria.trust_requirements

    def test_save_multiple_load_all(self, maria, rachel, tmp_data_dir):
        personas_dir = tmp_data_dir / "personas"
        save_persona(maria, personas_dir)
        save_persona(rachel, personas_dir)
        loaded = load_personas(personas_dir)
        assert len(loaded) == 2
        ids = {p.id for p in loaded}
        assert "UXW-01" in ids
        assert "UXW-20" in ids

    def test_loaded_persona_validates(self, maria, tmp_data_dir):
        path = save_persona(maria, tmp_data_dir / "personas")
        loaded = load_persona(path)
        issues = validate_persona(loaded)
        assert issues == []

    def test_load_empty_dir(self, tmp_data_dir):
        loaded = load_personas(tmp_data_dir / "personas")
        assert loaded == []
