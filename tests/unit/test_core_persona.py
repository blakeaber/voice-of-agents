"""Unit tests for core/persona.py — Persona, VoiceProfile, PersonaMetadata."""

from __future__ import annotations

import pytest
from pathlib import Path
from pydantic import ValidationError

from voice_of_agents.core.persona import Persona, VoiceProfile, PersonaMetadata
from voice_of_agents.core.enums import Tier, Segment, ValidationStatus


FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestVoiceProfile:
    def test_all_defaults(self):
        v = VoiceProfile()
        assert v.skepticism == "moderate"
        assert v.vocabulary == "general"
        assert v.motivation == "efficiency"
        assert v.price_sensitivity == "moderate"

    def test_custom_values(self):
        v = VoiceProfile(skepticism="high", vocabulary="legal", motivation="fear", price_sensitivity="high")
        assert v.skepticism == "high"
        assert v.vocabulary == "legal"

    def test_invalid_skepticism(self):
        with pytest.raises(ValidationError):
            VoiceProfile(skepticism="extreme")

    def test_invalid_motivation(self):
        with pytest.raises(ValidationError):
            VoiceProfile(motivation="greed")


class TestPersonaMetadata:
    def test_defaults(self):
        m = PersonaMetadata()
        assert m.source == "manual"
        assert m.validation_status == ValidationStatus.DRAFT
        assert m.legacy_id is None

    def test_legacy_id(self):
        m = PersonaMetadata(legacy_id="UXW-01")
        assert m.legacy_id == "UXW-01"


class TestPersona:
    def _minimal(self, **kwargs):
        defaults = dict(id=1, name="Test User", role="Developer", industry="Tech",
                        segment="b2c", tier="FREE")
        defaults.update(kwargs)
        return Persona(**defaults)

    def test_minimal_creation(self):
        p = self._minimal()
        assert p.id == 1
        assert p.name == "Test User"

    def test_voice_defaults_always_present(self):
        p = self._minimal()
        # voice is always present — never None
        assert p.voice is not None
        assert p.voice.skepticism == "moderate"
        assert p.voice.motivation == "efficiency"

    def test_slug_property(self):
        p = self._minimal(id=1, name="Maria Gutierrez")
        assert p.slug == "01-maria-gutierrez"

    def test_slug_strips_special_chars(self):
        p = self._minimal(id=5, name="Dr. Anita Sharma")
        assert p.slug == "05-dr-anita-sharma"

    def test_slug_with_double_digit_id(self):
        p = self._minimal(id=10, name="Carlos Mendez")
        assert p.slug == "10-carlos-mendez"

    def test_id_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._minimal(id=0)

    def test_theme_intensity_found(self):
        from voice_of_agents.core.pain import PainTheme
        from voice_of_agents.core.enums import ThemeCode, Intensity
        p = self._minimal(pain_themes=[PainTheme(theme=ThemeCode.A, intensity=Intensity.HIGH)])
        assert p.theme_intensity("A") == "HIGH"

    def test_theme_intensity_not_found(self):
        p = self._minimal()
        assert p.theme_intensity("A") is None

    def test_is_regulated_true(self):
        from voice_of_agents.core.pain import PainTheme
        from voice_of_agents.core.enums import ThemeCode, Intensity
        p = self._minimal(pain_themes=[PainTheme(theme=ThemeCode.D, intensity=Intensity.HIGH)])
        assert p.is_regulated() is True

    def test_is_regulated_false_medium(self):
        from voice_of_agents.core.pain import PainTheme
        from voice_of_agents.core.enums import ThemeCode, Intensity
        p = self._minimal(pain_themes=[PainTheme(theme=ThemeCode.D, intensity=Intensity.MEDIUM)])
        assert p.is_regulated() is False

    def test_is_regulated_false_no_theme(self):
        p = self._minimal()
        assert p.is_regulated() is False

    def test_load_from_fixture(self):
        from voice_of_agents.core.io import load_persona
        p = load_persona(FIXTURES / "sample_persona.yaml")
        assert p.id == 1
        assert p.name == "Maria Gutierrez"
        assert p.voice.skepticism == "moderate"
        assert p.metadata.legacy_id == "UXW-01"
        assert len(p.pain_themes) == 2

    def test_legacy_id_preserved(self):
        p = self._minimal(metadata=PersonaMetadata(legacy_id="UXW-01"))
        assert p.metadata.legacy_id == "UXW-01"

    def test_tier_enum(self):
        p = self._minimal(tier="ENTERPRISE")
        assert p.tier == Tier.ENTERPRISE

    def test_segment_enum(self):
        p = self._minimal(segment="b2b")
        assert p.segment == Segment.B2B
