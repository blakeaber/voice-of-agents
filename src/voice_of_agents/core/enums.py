"""Shared enumerations used across core, design, and eval layers."""

from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    FREE = "FREE"
    DEVELOPER = "DEVELOPER"
    TEAM = "TEAM"
    ENTERPRISE = "ENTERPRISE"


class ThemeCode(str, Enum):
    A = "A"  # Knowledge Retrieval Failure
    B = "B"  # Bus Factor / SPOF
    C = "C"  # Contextual Failure of generic AI
    D = "D"  # Trust Deficit
    E = "E"  # Governance Vacuum
    F = "F"  # Integration Failure


class Segment(str, Enum):
    B2C = "b2c"
    B2B = "b2b"


class Intensity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    STALE = "stale"


class GoalCategory(str, Enum):
    KNOWLEDGE = "knowledge"
    DELEGATION = "delegation"
    GOVERNANCE = "governance"
    MARKETPLACE = "marketplace"
    AUTOMATION = "automation"
    COLLABORATION = "collaboration"


class GoalPriority(str, Enum):
    PRIMARY = "primary"  # Day-1 value
    SECONDARY = "secondary"  # Month-1 expansion
    ASPIRATIONAL = "aspirational"  # Quarter-1 advanced usage
