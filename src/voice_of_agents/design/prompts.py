"""Jinja2 prompt templates for LLM-assisted persona and workflow generation."""

from __future__ import annotations

PERSONA_GENERATION_PROMPT = """\
You are a product researcher creating market-grounded user personas for {{ product_name }}.

## Context
{{ product_description }}

## Target Segment
Industry: {{ industry }}
Organization size: {{ org_size_range }}
Roles to explore: {{ roles | join(', ') }}

## Existing Personas (avoid duplicates)
{% for p in existing_personas %}
- #{{ p.id }} {{ p.name }} — {{ p.role }} ({{ p.industry }})
{% endfor %}

## Instructions
Generate {{ count }} new personas. For each persona, output valid YAML matching this structure:

```yaml
id: {{ next_id }}
name: "<realistic full name>"
role: "<specific job title>"
segment: "{{ segment }}"
industry: "<specific industry>"
tier: "<FREE|DEVELOPER|TEAM|ENTERPRISE based on willingness/ability to pay>"
age: <18-80>
income: <annual USD, grounded in BLS data>
org_size: <1 for solo, otherwise team/org size>
experience_years: <years in role>
ai_history: "<specific AI tools tried and why they failed>"
mindset: "<attitude toward AI, in their own voice, quoted>"
pain_points:
  - description: "<specific pain>"
    impact: "<quantified: hours, dollars, error frequency>"
    current_workaround: "<what they do today>"
unmet_need: "<the single capability that would transform their work>"
proof_point: "<what the product must demonstrate to earn trust>"
pain_themes:
  - theme: "<A|B|C|D|E|F>"
    intensity: "<LOW|MEDIUM|HIGH|CRITICAL>"
metadata:
  source: "generated"
  created_at: "{{ today }}"
  research_basis:
    - "<specific data source>"
```

## Rules
1. Every pain point MUST be quantified (hours, dollars, error frequency)
2. AI history must reference REAL tools (ChatGPT, Copilot, Jasper, etc.), not hypothetical
3. Income must be grounded in BLS/Census data for the role
4. Unmet need must be specific to their domain, not generic AI capability
5. Proof point must be a genuine barrier, not a feature wish
6. Pain themes: A=retrieval failure, B=bus factor, C=context failure, D=trust deficit, \
E=governance vacuum, F=integration failure
7. Do NOT duplicate existing personas in role or industry niche
"""

WORKFLOW_GENERATION_PROMPT = """\
You are a product designer creating workflow specifications for {{ persona_name }} \
(#{{ persona_id }}), a {{ persona_role }} in {{ persona_industry }}.

## Persona Profile
{{ persona_yaml }}

## Available Platform Capabilities
{% for cap in capabilities %}
- {{ cap.id }}: {{ cap.name }} ({{ cap.status }})
  {%- if cap.api_endpoint %} API: {{ cap.api_endpoint }}{% endif %}
  {%- if cap.ui_page %} UI: {{ cap.ui_page }}{% endif %}
{% endfor %}

## Existing Goals (preserve these)
{% for g in existing_goals %}
- {{ g.id }}: {{ g.title }} [{{ g.priority }}]
{% endfor %}

## Instructions
Generate {{ goal_count }} additional goals that expand this persona's use of the platform. \
Each goal should exercise capabilities NOT covered by existing goals.

For each goal, output valid YAML:

```yaml
- id: "G-{{ '%02d' % persona_id }}-{{ next_goal_seq }}"
  title: "<goal title>"
  category: "<knowledge|delegation|governance|marketplace|automation|collaboration>"
  priority: "<primary|secondary|aspirational>"
  trigger: "<what event activates this goal>"
  success_statement: "<success in the persona's own words>"
  value_metrics:
    time_saved: "<e.g., 2 hours → 10 minutes>"
    error_reduction: "<e.g., 3 errors/month → 0>"
    cost_impact: "<e.g., saves $500/month>"
  workflows:
    - id: "W-{{ '%02d' % persona_id }}-{{ next_goal_seq }}-a"
      title: "<workflow title>"
      preconditions:
        - "<what must be true before this workflow>"
      steps:
        - seq: 1
          action: "<what the user does>"
          capability_id: "<CAP-XXX-YYY from registry>"
          api_endpoint: "<from capability>"
          ui_page: "<from capability>"
          success_criteria: "<observable result>"
          friction_risk: "<what could go wrong>"
      capabilities_used:
        - "<list all CAP IDs used>"
      capabilities_missing:
        - "<list any needed but unavailable CAP IDs>"
```

## Rules
1. Every step MUST reference a capability_id from the registry above
2. If a needed capability doesn't exist, list it in capabilities_missing and note it
3. Success statements must be in the persona's voice and vocabulary
4. Priority: primary=day-1 value, secondary=month-1, aspirational=quarter-1
5. B2C personas: focus on knowledge, automation, marketplace goals
6. B2B personas: include at least one governance or delegation goal
7. Value metrics must be quantified and realistic for the persona's context
"""

GAP_ANALYSIS_PROMPT = """\
You are a product strategist analyzing workflow gaps for {{ product_name }}.

## Capability Registry
{% for cap in capabilities %}
- {{ cap.id }}: {{ cap.name }} ({{ cap.status }})
{% endfor %}

## Workflow Gap Summary
The following capabilities are referenced as "missing" across persona workflows:

{% for gap_id, personas in gaps.items() %}
- {{ gap_id }}: needed by personas {{ personas | join(', ') }}
{% endfor %}

## Instructions
For each gap, propose a feature recommendation. Output valid YAML:

```yaml
- id: "FR-00-{{ loop.index }}"
  title: "<feature name>"
  description: "<what it does, 2-3 sentences>"
  complexity: "<trivial|small|medium>"
  extends_capability: "<existing CAP-ID this builds on, if any>"
  personas_benefited: [<list of persona IDs>]
  value_statement: "<why this matters, in a representative persona's voice>"
```

## Rules
1. Complexity MUST be trivial (<1 day), small (1-3 days), or medium (1-2 weeks)
2. Features that would take longer than 2 weeks should be flagged as "out of scope" \
and excluded
3. Prefer extending existing capabilities over building new systems
4. Value statement should be in a specific persona's voice, not generic
"""
