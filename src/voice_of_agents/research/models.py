"""All Pydantic models for the research pipeline: stage inputs, outputs, and contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from voice_of_agents.core.enums import Tier


# ── Research-specific enums ────────────────────────────────────────────


class AdoptionStatus(str, Enum):
    ADOPTER = "adopter"
    PARTIAL_ADOPTER = "partial-adopter"
    ABANDONER = "abandoner"
    EVALUATED_AND_REJECTED = "evaluated-and-rejected"
    NEVER_TRIED_AWARE = "never-tried-aware"
    ACTIVELY_ANTI = "actively-anti"


class ContextSegment(str, Enum):
    B2B_SMALL = "B2B-small"
    B2B_MID = "B2B-mid"
    B2B_LARGE_REGULATED = "B2B-large-regulated"
    B2C_HIGH_AUTONOMY = "B2C-high-autonomy"
    B2C_LOW_AUTONOMY = "B2C-low-autonomy"


class HypothesisVerdict(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    ORTHOGONAL = "orthogonal"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


# ── Shared primitives ──────────────────────────────────────────────────


class VerbatimQuote(BaseModel):
    key: str  # Q1..Q8
    text: str  # ≤2 sentences


# ── 8-field SubjectRecord (shared by all 4 skills) ────────────────────


class SubjectRecord(BaseModel):
    """Mandatory 8-field subject schema used across all research stages."""

    subject_id: str  # "subject-01" through "subject-16"
    adoption_status: AdoptionStatus
    context_segment: ContextSegment

    jtbd: str
    adoption_trajectory: str
    last_concrete_episode: str
    constraint_profile: str
    failure_or_abandonment_mode: str  # blank string "" for pure adopters only
    decision_topology: str
    anti_model_of_success: str
    verbatim_quote_bank: list[VerbatimQuote] = Field(min_length=5, max_length=8)

    @model_validator(mode="after")
    def check_failure_mode(self) -> "SubjectRecord":
        requires_failure = {
            AdoptionStatus.PARTIAL_ADOPTER,
            AdoptionStatus.ABANDONER,
            AdoptionStatus.EVALUATED_AND_REJECTED,
            AdoptionStatus.ACTIVELY_ANTI,
        }
        if (
            self.adoption_status in requires_failure
            and not self.failure_or_abandonment_mode
        ):
            raise ValueError(
                f"failure_or_abandonment_mode is required for {self.adoption_status.value} subjects"
            )
        return self


# ── Hypothesis models ──────────────────────────────────────────────────


class Hypothesis(BaseModel):
    id: str  # H1, H2...
    statement: str
    falsification_condition: str


class HypothesisScore(BaseModel):
    hypothesis_id: str
    verdict: HypothesisVerdict
    supporting_subject_ids: list[str] = Field(default_factory=list)
    refuting_subject_ids: list[str] = Field(default_factory=list)
    key_quotes: list[str] = Field(default_factory=list)  # "S03/Q4: '...'"


# ── Sampling frame ─────────────────────────────────────────────────────


class SamplingCell(BaseModel):
    adoption_status: AdoptionStatus
    context_segment: ContextSegment
    subject_profile: str  # human-readable role/context description


# ── Behavioral segment ─────────────────────────────────────────────────


class BehavioralSegment(BaseModel):
    name: str  # behavioral descriptor, not demographic label
    description: str
    subject_ids: list[str]
    primary_jtbd: str
    adoption_trajectory_shape: str
    dominant_constraint_profile: str
    dominant_failure_mode: str
    gaps_vs_product_positioning: str  # mandatory section


# ══════════════════════════════════════════════════════════════════════
# Stage 1: Product Research
# ══════════════════════════════════════════════════════════════════════


class ProductResearchInput(BaseModel):
    question: str = Field(
        description="Falsifiable research question about a customer population"
    )
    scope: str = Field(
        description="Population boundary: region, firm-size, time window"
    )
    slug: str = Field(
        description="≤6 kebab-case words; used in artifact directory name"
    )
    product_context: str = Field(
        description="Brief description of the product being researched (not a target market)"
    )
    subject_count: int = Field(default=12, ge=10, le=16)
    ratified_hypotheses: Optional[list[Hypothesis]] = Field(
        default=None,
        description="Pre-ratified hypotheses. If None, Stage 1 generates and pauses for ratification.",
    )

    @model_validator(mode="after")
    def slug_max_six_words(self) -> "ProductResearchInput":
        if len(self.slug.split("-")) > 6:
            raise ValueError("slug must be ≤6 kebab-case words")
        return self


class ProductResearchOutput(BaseModel):
    slug: str
    run_date: str  # YYYY-MM-DD
    run_dir: str  # relative path
    hypotheses: list[Hypothesis]
    hypotheses_ratified: bool = False
    sampling_frame: list[SamplingCell]
    subjects: list[SubjectRecord]
    hypothesis_scores: list[HypothesisScore]
    segments: list[BehavioralSegment]
    all_hypotheses_supported_flag: bool = False
    cross_cutting_findings: str = ""


# ══════════════════════════════════════════════════════════════════════
# Stage 2: Personas from Research
# ══════════════════════════════════════════════════════════════════════


class PersonaResearchInput(BaseModel):
    product_research: ProductResearchOutput
    skip_topup: bool = False
    topup_subject_count_target: int = Field(default=6, ge=3, le=12)


class UXWPersonaSidecar(BaseModel):
    """8-field persona data schema with inline citations."""

    uxw_id: str  # UXW-01, UXW-02...
    name: str
    segment_source: str  # which BehavioralSegment this persona represents
    subject_ids: list[str]  # contributing subjects (min 2)

    # 8 fields with embedded citations as string suffixes
    jtbd: str
    adoption_trajectory: str
    last_concrete_episode: str
    constraint_profile: str
    failure_or_abandonment_mode: str
    decision_topology: str
    anti_model_of_success: str
    verbatim_quote_bank: list[VerbatimQuote] = Field(min_length=5, max_length=8)

    @model_validator(mode="after")
    def min_two_subjects(self) -> "UXWPersonaSidecar":
        if len(self.subject_ids) < 2:
            raise ValueError(
                f"Persona {self.uxw_id} requires at least 2 contributing subjects; "
                f"got {len(self.subject_ids)}"
            )
        return self


class UXWTaskCard(BaseModel):
    """Task-centric UXW card derived from the sidecar."""

    uxw_id: str
    name: str
    role: str
    intent: str
    trigger: str
    success_definition: str
    today_workaround: str
    preconditions: list[str]
    steps: list[str]
    success_criteria: list[str]
    persona_evaluation_rubric: str


class PersonaResearchOutput(BaseModel):
    topup_subjects: list[SubjectRecord] = Field(default_factory=list)
    persona_sidecars: list[UXWPersonaSidecar]
    task_cards: list[UXWTaskCard]
    archived_prior_personas: list[str] = Field(default_factory=list)
    coverage_map: dict[str, int]  # segment_name -> subject_count


# ══════════════════════════════════════════════════════════════════════
# Stage 3: Workflows from Interviews
# ══════════════════════════════════════════════════════════════════════


class EpisodeStep(BaseModel):
    step: str
    tool: str  # software tool or "none"
    input: str
    output: str
    time: str  # estimated minutes
    blocker: str  # friction or "none"


class EpisodeRecord(BaseModel):
    """Mandatory episode schema from workflows-from-interviews."""

    episode: str
    date: str  # relative anchor
    pre_state: str
    steps: list[EpisodeStep]
    post_state: str
    what_i_wished_existed: str

    @model_validator(mode="after")
    def require_all_fields(self) -> "EpisodeRecord":
        if not self.pre_state or not self.post_state:
            raise ValueError("pre_state and post_state are required in every episode")
        if not self.steps:
            raise ValueError("steps list cannot be empty")
        return self


class PWMWorkflowStep(BaseModel):
    number: int
    action: str
    tool: str
    input: str
    output: str
    time: str
    blocker: str
    friction_risk: str


class PWMWorkflow(BaseModel):
    """Persona Workflow Map — compatible with existing PWM YAML schema."""

    id: str  # UXW-{persona_id}-{seq}
    persona: int
    title: str
    intent_goal: str
    intent_trigger: str
    success_definition: str
    preconditions: list[str]
    steps: list[PWMWorkflowStep]
    success_criteria: list[dict]  # {criterion, measurement}
    satisfaction_drivers: list[str]
    dealbreakers: list[str]
    efficiency_baseline_method: str
    efficiency_baseline_time: str
    value_time_saved: str
    value_errors_prevented: str
    value_knowledge_preserved: str


class WorkflowResearchInput(BaseModel):
    persona_research: PersonaResearchOutput
    target_uxw_id: str  # "UXW-01" — one per invocation; group mode refused
    episode_count: int = Field(default=4, ge=3, le=5)


class WorkflowResearchOutput(BaseModel):
    uxw_id: str
    episodes: list[EpisodeRecord]
    workflow_maps: list[PWMWorkflow]  # 2-3 per persona
    archived_prior_pwm: list[str] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════
# Stage 4: Journey Redesign
# ══════════════════════════════════════════════════════════════════════


class FocusGroupResponse(BaseModel):
    persona_name: str
    uxw_id: str
    score: int = Field(ge=1, le=10)
    what_i_loved: list[str] = Field(min_length=2, max_length=4)
    what_made_me_quit: list[str] = Field(min_length=2, max_length=4)
    top_3_must_fixes: list[str] = Field(min_length=3, max_length=3)
    segment_specific_concern: str
    would_pay: Literal["yes", "no", "conditional"]
    would_pay_reason: str


class JourneyDesignStep(BaseModel):
    step_number: int
    screen_or_route: str
    affordance: str
    copy_sample: str
    principle_reference: str
    must_fix_numbers: list[int] = Field(default_factory=list)


class MustFix(BaseModel):
    number: int
    description: str
    raised_by_persona_ids: list[str]
    is_cross_cutting: bool  # True if raised by ≥3 personas


class JourneyRedesignInput(BaseModel):
    workflow_research: WorkflowResearchOutput
    persona_research: PersonaResearchOutput
    anchor_segment: str  # "FREE→DEVELOPER", "DEVELOPER→TEAM", etc.
    journeys_in_scope: list[str] = Field(min_length=1, max_length=3)
    build_form: Literal["full_rewrite", "mockups_only", "frontend_only"]
    focus_panel_uxw_ids: list[str] = Field(min_length=3, max_length=6)


class JourneyRedesignOutput(BaseModel):
    v0_journey_steps: list[JourneyDesignStep]
    focus_group_responses: list[FocusGroupResponse]
    average_score: float
    cross_cutting_must_fixes: list[MustFix]
    secondary_asks: list[MustFix]
    revised_journey_steps: list[JourneyDesignStep]
    plan_dir: str  # docs/plans/NNN-name/
    plan_slug: str  # NNN-name
