"""Tests for canonical Persona model (core/persona.py)."""

import pytest

from voice_of_agents.core.persona import Persona, PersonaMetadata, VoiceProfile


class TestPersonaSlug:
    """Persona.slug generates correct URL-safe string."""

    def test_slug_from_maria(self, maria):
        assert maria.slug == "01-maria-gutierrez"

    def test_slug_from_rachel(self, rachel):
        assert rachel.slug == "20-rachel-okafor"

    def test_slug_strips_special_chars(self):
        p = Persona(
            id=99,
            name="Jean-Luc O'Brien III",
            role="Tester",
            industry="Tech",
            segment="b2c",
            tier="FREE",
        )
        slug = p.slug
        assert slug.startswith("99-")
        assert "'" not in slug
        assert slug == "99-jean-luc-o-brien-iii"

    def test_slug_lowercases(self):
        p = Persona(
            id=5, name="ALICE SMITH", role="Dev", industry="Tech", segment="b2c", tier="FREE"
        )
        assert "alice-smith" in p.slug


class TestPersonaModelDump:
    """model_dump() returns all canonical fields."""

    def test_dump_has_core_keys(self, maria):
        d = maria.model_dump()
        for key in (
            "id",
            "name",
            "role",
            "industry",
            "segment",
            "tier",
            "org_size",
            "pain_points",
            "pain_themes",
            "voice",
            "metadata",
        ):
            assert key in d, f"Missing key: {key}"

    def test_dump_voice_is_flat_dict(self, maria):
        d = maria.model_dump()
        assert isinstance(d["voice"], dict)
        assert d["voice"]["skepticism"] == "high"
        assert d["voice"]["vocabulary"] == "legal"

    def test_dump_pain_themes_serialized(self, maria):
        d = maria.model_dump()
        assert len(d["pain_themes"]) == 2


class TestPersonaValidation:
    """Pydantic validation catches bad input."""

    def test_id_must_be_positive(self):
        with pytest.raises(Exception):
            Persona(id=0, name="X", role="Y", industry="Z", segment="b2c", tier="FREE")

    def test_org_size_must_be_positive(self):
        with pytest.raises(Exception):
            Persona(id=1, name="X", role="Y", industry="Z", segment="b2c", tier="FREE", org_size=0)

    def test_valid_persona_constructs(self, maria):
        assert maria.id == 1
        assert maria.name == "Maria Gutierrez"

    def test_valid_rachel_constructs(self, rachel):
        assert rachel.id == 20
        assert rachel.name == "Rachel Okafor"


class TestVoiceProfileDefaults:
    """VoiceProfile defaults are correct."""

    def test_defaults(self):
        v = VoiceProfile()
        assert v.skepticism == "moderate"
        assert v.vocabulary == "general"
        assert v.motivation == "efficiency"
        assert v.price_sensitivity == "moderate"

    def test_override_single_field(self):
        v = VoiceProfile(skepticism="high")
        assert v.skepticism == "high"
        assert v.motivation == "efficiency"


class TestPersonaMetadata:
    """PersonaMetadata preserves legacy_id for migration tracing."""

    def test_legacy_id_stored(self):
        meta = PersonaMetadata(legacy_id="UXW-01")
        assert meta.legacy_id == "UXW-01"

    def test_legacy_id_defaults_to_none(self):
        meta = PersonaMetadata()
        assert meta.legacy_id is None

    def test_maria_legacy_id_if_set(self, maria):
        assert maria.metadata.legacy_id is None  # conftest doesn't set it


class TestThemeIntensity:
    """Persona.theme_intensity() looks up pain theme by code."""

    def test_returns_intensity_for_present_theme(self, maria):
        assert maria.theme_intensity("A") == "CRITICAL"
        assert maria.theme_intensity("D") == "HIGH"

    def test_returns_none_for_absent_theme(self, maria):
        assert maria.theme_intensity("F") is None
