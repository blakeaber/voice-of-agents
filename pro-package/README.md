# Voice of Agents

Persona management and workflow generation for product development. Define market-grounded user personas, map them to platform capabilities via composable workflows, and identify feature gaps through automated analysis.

## Quick Start

```bash
pip install voice-of-agents

# Initialize a project
voa init my-product --product "My Product"

# List personas
voa persona list --dir my-product

# Validate everything
voa validate --dir my-product
```

## Concepts

**Persona** — A market-grounded user profile with quantified pain points, AI history, and pain theme classifications (A-F). Personas are the input to workflow generation.

**Capability** — A single platform feature (API endpoint + UI page) registered in a capability registry. Capabilities are the building blocks that workflows compose.

**Workflow** — A sequence of capability-backed steps that achieve a persona's goal. Workflows map `persona goal → steps → capabilities used → gaps identified`.

**Goal** — A persona-specific objective with priority (primary/secondary/aspirational), trigger event, success statement, and one or more workflows.

## Project Structure

```
my-product/
├── personas/           # Persona YAML files (P-01-name.yaml)
├── workflows/          # Workflow mapping files (PWM-01-name.yaml)
└── capabilities.yaml   # Capability registry
```

## CLI Commands

### Project

```bash
voa init <dir> --product "Name"     # Initialize project
voa validate --dir <dir>            # Validate all files + cross-references
```

### Personas

```bash
voa persona list --dir <dir>                    # List all personas
voa persona validate --dir <dir>                # Validate persona files
voa persona generate-prompt --dir <dir> \       # Generate LLM prompt
    --product "Name" --description "..." \
    --industry "Legal" --roles "Paralegal,Attorney"
voa persona import response.yaml --dir <dir>    # Import from LLM response
```

### Workflows

```bash
voa workflow list --dir <dir>                   # List all mappings
voa workflow generate-prompt 1 --dir <dir>      # Generate prompt for persona #1
voa workflow import response.yaml 1 --dir <dir> # Import workflows for persona #1
```

### Analysis

```bash
voa analyze gaps --dir <dir>        # Gap analysis across all workflows
voa analyze coverage --dir <dir>    # Capability coverage matrix
```

## LLM-Assisted Pipeline

Voice of Agents generates structured prompts for LLM-assisted persona and workflow creation:

1. `voa persona generate-prompt` → produces a prompt → feed to Claude/GPT → save response
2. `voa persona import response.yaml` → validates and saves personas
3. `voa workflow generate-prompt <id>` → produces a prompt → feed to Claude/GPT → save response
4. `voa workflow import response.yaml <id>` → validates and saves workflows
5. `voa analyze gaps` → identifies missing capabilities and unused features

The LLM does the creative work; VoA handles structure, validation, and analysis.

## Pain Themes

| Code | Theme | Description |
|------|-------|-------------|
| A | Knowledge Retrieval Failure | "I've solved this before but can't find it" |
| B | Bus Factor / SPOF | "When I'm not there, work stops" |
| C | Contextual Failure | "AI gives generic output that doesn't fit my context" |
| D | Trust Deficit | "I can't trust it enough to put my name on it" |
| E | Governance Vacuum | "I have no visibility into what's happening" |
| F | Integration Failure | "AI tools don't talk to each other" |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

## License

MIT
