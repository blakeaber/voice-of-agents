"""Research → Eval bridge: convert UXWPersonaSidecar to canonical Persona for eval seeding."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from voice_of_agents.core.enums import Segment, Tier, ValidationStatus
from voice_of_agents.core.pain import PainPoint, PainTheme
from voice_of_agents.core.persona import Persona, PersonaMetadata, VoiceProfile
from voice_of_agents.research.models import (
    AdoptionStatus,
    ContextSegment,
    UXWPersonaSidecar,
)


_CONTEXT_TO_SEGMENT: dict[ContextSegment, Segment] = {
    ContextSegment.B2B_SMALL: Segment.B2B,
    ContextSegment.B2B_MID: Segment.B2B,
    ContextSegment.B2B_LARGE_REGULATED: Segment.B2B,
    ContextSegment.B2C_HIGH_AUTONOMY: Segment.B2C,
    ContextSegment.B2C_LOW_AUTONOMY: Segment.B2C,
}

_CONTEXT_TO_ORG_SIZE: dict[ContextSegment, int] = {
    ContextSegment.B2B_SMALL: 20,
    ContextSegment.B2B_MID: 200,
    ContextSegment.B2B_LARGE_REGULATED: 2000,
    ContextSegment.B2C_HIGH_AUTONOMY: 1,
    ContextSegment.B2C_LOW_AUTONOMY: 1,
}

_ADOPTION_TO_PRICE_SENSITIVITY = {
    AdoptionStatus.ADOPTER: "low",
    AdoptionStatus.PARTIAL_ADOPTER: "moderate",
    AdoptionStatus.ABANDONER: "high",
    AdoptionStatus.EVALUATED_AND_REJECTED: "high",
    AdoptionStatus.NEVER_TRIED_AWARE: "moderate",
    AdoptionStatus.ACTIVELY_ANTI: "high",
}


def _infer_tier(sidecar: UXWPersonaSidecar) -> Tier:
    """Heuristic: map adoption trajectory to a Tier for eval seeding."""
    traj = sidecar.adoption_trajectory.lower()
    if "enterprise" in traj or "team" in traj:
        return Tier.TEAM
    if "paid" in traj or "developer" in traj:
        return Tier.DEVELOPER
    return Tier.FREE


def _infer_segment(sidecar: UXWPersonaSidecar) -> Segment:
    """Infer segment from segment_source if context segment is unavailable."""
    if "b2b" in sidecar.segment_source.lower():
        return Segment.B2B
    return Segment.B2C


def sidecar_to_canonical_persona(
    sidecar: UXWPersonaSidecar,
    persona_id: int,
    role: str = "Research-Derived Persona",
    industry: str = "Technology",
    context_segment: Optional[ContextSegment] = None,
    adoption_status: Optional[AdoptionStatus] = None,
    session_slug: Optional[str] = None,
) -> Persona:
    """Convert a UXWPersonaSidecar into a canonical Persona for eval seeding.

    The resulting Persona has validation_status=DRAFT and legacy_id pointing
    back to the UXW ID so the lineage is traceable.

    Args:
        sidecar: The persona sidecar from a research session.
        persona_id: Integer ID for the new Persona (must be ≥ 1).
        role: Job role label (defaults to research segment source).
        industry: Industry label.
        context_segment: The ContextSegment this persona came from.
        adoption_status: The AdoptionStatus this persona represents.
        session_slug: The research session slug for metadata tracing.

    Returns:
        A Persona ready for eval use with metadata.source="generated".
    """
    segment = (
        _CONTEXT_TO_SEGMENT.get(context_segment, Segment.B2B)
        if context_segment
        else _infer_segment(sidecar)
    )
    org_size = (
        _CONTEXT_TO_ORG_SIZE.get(context_segment, 50)
        if context_segment
        else 50
    )
    tier = _infer_tier(sidecar)
    price_sensitivity = (
        _ADOPTION_TO_PRICE_SENSITIVITY.get(adoption_status, "moderate")
        if adoption_status
        else "moderate"
    )

    pain_points = [
        PainPoint(
            description=sidecar.constraint_profile,
            impact="Derived from synthetic research — quantify with real users",
        )
    ]
    if sidecar.failure_or_abandonment_mode:
        pain_points.append(
            PainPoint(
                description=sidecar.failure_or_abandonment_mode,
                impact="Leads to abandonment — high severity",
            )
        )

    research_basis = [f"research:{session_slug}:{sidecar.uxw_id}"] if session_slug else [sidecar.uxw_id]

    return Persona(
        id=persona_id,
        name=sidecar.name,
        role=role or sidecar.segment_source,
        industry=industry,
        segment=segment,
        tier=tier,
        org_size=org_size,
        mindset=sidecar.jtbd,
        unmet_need=sidecar.anti_model_of_success,
        ai_history=sidecar.adoption_trajectory,
        pain_points=pain_points,
        voice=VoiceProfile(
            price_sensitivity=price_sensitivity,
        ),
        metadata=PersonaMetadata(
            source="generated",
            research_basis=research_basis,
            validation_status=ValidationStatus.DRAFT,
            legacy_id=sidecar.uxw_id,
        ),
    )


def session_to_personas(
    session,
    starting_id: int = 1,
    session_slug: Optional[str] = None,
) -> list[Persona]:
    """Convert all persona sidecars from a ResearchSession into canonical Personas.

    Args:
        session: A ResearchSession with persona_research_output populated.
        starting_id: Integer ID for the first persona (increments for each).
        session_slug: Override for session slug in metadata (defaults to session.slug).

    Returns:
        List of Persona objects ready for eval seeding.
    """
    if not session.persona_research_output:
        return []

    slug = session_slug or session.slug
    personas = []
    for i, sidecar in enumerate(session.persona_research_output.persona_sidecars):
        persona = sidecar_to_canonical_persona(
            sidecar=sidecar,
            persona_id=starting_id + i,
            session_slug=slug,
        )
        personas.append(persona)
    return personas


def write_bridge_workflow(directory: Path) -> Path:
    """Write BRIDGE-WORKFLOW.md explaining how to seed eval from research output."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "BRIDGE-WORKFLOW.md"
    path.write_text("""# Research → Eval Bridge

This document explains how to use synthetic research output to seed the eval pipeline.

## What the bridge does

The `voice_of_agents.research.bridge` module converts `UXWPersonaSidecar` objects
(research output) into canonical `Persona` objects (eval input). This closes the
loop between "what users need" (research) and "does our product serve them" (eval).

## Basic usage

```python
from voice_of_agents.research.session import ResearchSession
from voice_of_agents.research.bridge import session_to_personas
from pathlib import Path

# Load a completed research session
session = ResearchSession.load(Path("research-sessions/my-research.yaml"))

# Convert research personas to eval-ready Personas
personas = session_to_personas(session)

# Use in eval
from voice_of_agents.eval import run_eval
results = run_eval(personas=personas)
```

## CLI usage

```bash
# Seed the eval pipeline from a research session
voa research seed-eval research-sessions/my-research.yaml

# This writes personas to data/personas/ in the standard format
voa research seed-eval research-sessions/my-research.yaml --output data/personas/
```

## What gets mapped

| Research field | Eval field |
|---|---|
| `UXWPersonaSidecar.name` | `Persona.name` |
| `UXWPersonaSidecar.jtbd` | `Persona.mindset` |
| `UXWPersonaSidecar.constraint_profile` | `Persona.pain_points[0]` |
| `UXWPersonaSidecar.failure_or_abandonment_mode` | `Persona.pain_points[1]` |
| `UXWPersonaSidecar.anti_model_of_success` | `Persona.unmet_need` |
| `UXWPersonaSidecar.adoption_trajectory` | `Persona.ai_history` |
| `UXWPersonaSidecar.uxw_id` | `Persona.metadata.legacy_id` |

All bridged personas have `metadata.source="generated"` and `validation_status=DRAFT`.
Promote to `validated` after a real user confirms the archetype.
""")
    return path
