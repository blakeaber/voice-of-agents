"""voice_of_agents.core — canonical shared data models."""

from voice_of_agents.core.enums import (
    GoalCategory,
    GoalPriority,
    Intensity,
    Segment,
    ThemeCode,
    Tier,
    ValidationStatus,
)
from voice_of_agents.core.pain import PainPoint, PainTheme
from voice_of_agents.core.persona import Persona, PersonaMetadata, VoiceProfile
from voice_of_agents.core.capability import Capability, CapabilityRegistry, TestResult
from voice_of_agents.core.backlog import BacklogItem, BacklogEvent, materialize_backlog
from voice_of_agents.core.io import (
    LoadError,
    load_capability_registry,
    load_persona,
    load_personas_dir,
    save_capability_registry,
    save_persona,
)

__all__ = [
    "GoalCategory", "GoalPriority", "Intensity", "Segment", "ThemeCode", "Tier", "ValidationStatus",
    "PainPoint", "PainTheme",
    "Persona", "PersonaMetadata", "VoiceProfile",
    "Capability", "CapabilityRegistry", "TestResult",
    "BacklogItem", "BacklogEvent", "materialize_backlog",
    "LoadError", "load_capability_registry", "load_persona", "load_personas_dir",
    "save_capability_registry", "save_persona",
]
