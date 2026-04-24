"""Integration tests: Canonical Persona YAML save/load roundtrip."""

from voice_of_agents.core.io import load_persona, load_personas_dir, save_persona


class TestPersonaRoundtrip:
    def test_save_load_preserves_fields(self, maria, tmp_data_dir):
        personas_dir = tmp_data_dir / "personas"
        path = save_persona(maria, personas_dir)
        loaded = load_persona(path)
        assert loaded.id == maria.id
        assert loaded.name == maria.name
        assert loaded.role == maria.role
        assert loaded.industry == maria.industry
        assert loaded.tier == maria.tier
        assert loaded.income == maria.income
        assert loaded.experience_years == maria.experience_years
        assert loaded.org_size == maria.org_size
        assert len(loaded.pain_points) == len(maria.pain_points)
        assert loaded.voice.skepticism == maria.voice.skepticism
        assert loaded.voice.vocabulary == maria.voice.vocabulary
        assert loaded.trust_requirements == maria.trust_requirements

    def test_save_multiple_load_all(self, maria, rachel, tmp_data_dir):
        personas_dir = tmp_data_dir / "personas"
        save_persona(maria, personas_dir)
        save_persona(rachel, personas_dir)
        loaded = load_personas_dir(personas_dir)
        assert len(loaded) == 2
        ids = {p.id for p in loaded}
        assert 1 in ids
        assert 20 in ids

    def test_loaded_persona_has_correct_slug(self, maria, tmp_data_dir):
        personas_dir = tmp_data_dir / "personas"
        path = save_persona(maria, personas_dir)
        loaded = load_persona(path)
        assert loaded.slug == "01-maria-gutierrez"

    def test_load_empty_dir(self, tmp_data_dir):
        loaded = load_personas_dir(tmp_data_dir / "personas")
        assert loaded == []
