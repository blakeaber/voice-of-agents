"""voice_of_agents.research — Primary research pipeline as a standalone Python library.

The four research stages (formerly Claude Code SKILL.md files) are exposed as
importable async functions with synchronous wrappers.

ONE-LINER QUICK START (recommended for first-time users):

    from voice_of_agents.research import quick_research_sync

    result = quick_research_sync(
        what="a coding assistant that helps developers write tests",
        who="senior developers at startups",
        understand="why developers abandon AI coding tools after the first week",
    )

    print(result.build_this_first)     # single highest-signal recommendation
    print(result.top_findings)         # 3-5 behavioral findings
    print(result.validate_with)        # 3 questions to ask a real user

FULL PIPELINE (for complete research sessions):

    from voice_of_agents.research import run_full_pipeline_sync
    from voice_of_agents.research.config import ResearchConfig
    from pathlib import Path

    config = ResearchConfig.from_file(Path("research-config.yaml"))
    session = run_full_pipeline_sync(config)
    session.export_summary(Path("RESEARCH-SUMMARY.md"))

PLAIN-ENGLISH CONFIG (no methodology vocabulary required):

    config = asyncio.run(ResearchConfig.from_plain_english(
        what="a Slack bot that tracks action items",
        who="engineering managers at startups",
        understand="why teams stop using action item trackers",
    ))

COST ESTIMATE (before any API calls):

    from voice_of_agents.research.cost import estimate_run_cost
    estimate = estimate_run_cost("claude-opus-4-7", subject_count=12)
    print(estimate.display())
    # Estimated cost: $1.20–$2.10 | Estimated time: 8–15 minutes

REAL SIGNAL INGESTION (augment with real user data):

    from voice_of_agents.research.signals import from_transcripts, from_csv, from_json
    signals = from_transcripts(["interview1.txt", "interview2.txt"])
    signals2 = from_csv("nps_responses.csv", text_column="comment")
    signals3 = from_json("tickets.json", text_field="body")

RESEARCH → EVAL BRIDGE (seed your eval pipeline from research personas):

    from voice_of_agents.research.bridge import session_to_personas
    personas = session_to_personas(session)  # list[Persona] for eval

DECISION REPORT (transform session into actionable founder output):

    from voice_of_agents.research.decisions import generate_decision_report
    report = asyncio.run(generate_decision_report(session, client, model))
    print(report.build_this_first)
"""

from voice_of_agents.research.config import ResearchConfig
from voice_of_agents.research.journey_redesign import (
    run_journey_redesign,
    run_journey_redesign_sync,
)
from voice_of_agents.research.personas_from_research import (
    run_personas_from_research,
    run_personas_from_research_sync,
)
from voice_of_agents.research.pipeline import (
    run_full_pipeline,
    run_full_pipeline_sync,
)
from voice_of_agents.research.product_research import (
    run_product_research,
    run_product_research_sync,
)
from voice_of_agents.research.quick import (
    QuickPersona,
    QuickResearchResult,
    quick_research,
    quick_research_sync,
)
from voice_of_agents.research.session import ResearchSession
from voice_of_agents.research.workflows_from_interviews import (
    run_workflows_from_interviews,
    run_workflows_from_interviews_sync,
)

__all__ = [
    # Primary API
    "quick_research",
    "quick_research_sync",
    "QuickResearchResult",
    "QuickPersona",
    # Full pipeline
    "run_full_pipeline",
    "run_full_pipeline_sync",
    # Individual stages
    "run_product_research",
    "run_product_research_sync",
    "run_personas_from_research",
    "run_personas_from_research_sync",
    "run_workflows_from_interviews",
    "run_workflows_from_interviews_sync",
    "run_journey_redesign",
    "run_journey_redesign_sync",
    # Core objects
    "ResearchSession",
    "ResearchConfig",
]
