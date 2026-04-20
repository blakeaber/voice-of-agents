"""Product engineer example: quick_research() one-liner with output parsing.

Demonstrates the primary public API — no config files, no CLI required.
Run with: python run.py
Requires: ANTHROPIC_API_KEY

Cost: ~$0.30 with opus | Time: ~5-10 minutes
"""

from voice_of_agents.research import quick_research_sync


def main():
    print("=== Product Engineer Quick Research Example ===")
    print("Running synthetic research on roadmap tool abandonment...\n")

    result = quick_research_sync(
        what="a roadmap prioritization tool that connects user research signals to engineering cost estimates",
        who="product engineers and engineering managers at B2B SaaS companies",
        understand="why product engineers stop using roadmap tools after the first quarter",
    )

    print("=" * 60)
    print("RESEARCH COMPLETE")
    print("=" * 60)

    print(f"\nBUILD THIS FIRST:\n  {result.build_this_first}")

    print("\nTOP FINDINGS:")
    for i, finding in enumerate(result.top_findings, 1):
        print(f"  {i}. {finding}")

    print("\nUSER ARCHETYPES:")
    for persona in result.personas:
        print(f"\n  [{persona.uxw_id}] {persona.archetype}")
        print(f"    Top concern:   {persona.top_concern}")
        print(f"    Would pay if:  {persona.would_pay_if}")

    print("\nCHURN TRIGGERS:")
    for trigger in result.churn_triggers:
        print(f"  • {trigger}")

    print("\nVALIDATE WITH REAL USERS — ASK THESE 3 QUESTIONS:")
    for i, q in enumerate(result.validate_with, 1):
        print(f"  {i}. {q}")

    print("\n" + "=" * 60)
    print("POWER USER ACCESS: full typed session available at result.session")
    print(f"  Session ID:        {result.session.session_id}")
    print(f"  Stages completed:  {', '.join(result.session.stages_completed)}")
    if result.session.product_research_output:
        pr = result.session.product_research_output
        print(f"  Subjects:          {len(pr.subjects)}")
        print(f"  Segments:          {len(pr.segments)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
