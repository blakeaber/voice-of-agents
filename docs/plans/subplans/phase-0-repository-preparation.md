# Phase 0: Repository Preparation

## Goal
Establish the structural scaffolding so both packages coexist during refactoring and the unified module landing zones are ready to receive code.

## Context
The refactoring moves code from two separate packages into a unified namespace. Before any code moves, the target directories must exist and the root package must declare the dependencies that the unified codebase needs (pydantic, rich, jinja2). A git tag preserves the pre-unification state as a checkpoint.

## Dependencies
None — this is the first phase.

## Scope

### Files to Create
- `src/voice_of_agents/core/__init__.py` — empty stub
- `src/voice_of_agents/design/__init__.py` — empty stub
- `src/voice_of_agents/eval/__init__.py` — empty stub
- `src/voice_of_agents/cli/__init__.py` — empty stub
- `tests/__init__.py` — empty stub (if not present)
- `tests/unit/__init__.py` — empty stub (if not present)
- `tests/integration/__init__.py` — empty stub (if not present)
- `tests/fixtures/` — directory (create if not present)

### Files to Modify
- `pyproject.toml` — add `pydantic>=2.0`, `rich>=13.0`, `jinja2>=3.1` to `[project.dependencies]`
- `.gitignore` — add `pro-package/**/__pycache__/`, `pro-package/**/*.egg-info/`, `pro-package/**/.venv/`

### Explicitly Out of Scope
- Moving or renaming any existing source files
- Changing any import paths in existing code
- Installing packages (user handles their venv)

## Implementation Notes
- The root `pyproject.toml` is at `/Users/blakeaber/Documents/voice-of-agents/pyproject.toml`
- Check what dependencies are already declared before adding; avoid duplicates
- The stub `__init__.py` files are empty — no imports, no content
- Do NOT create `src/voice_of_agents/core/`, `design/`, `eval/`, or `cli/` themselves as directories without the `__init__.py` — Python won't treat them as packages

## Acceptance Criteria
- [x] `src/voice_of_agents/core/__init__.py` exists (even if empty)
- [x] `src/voice_of_agents/design/__init__.py` exists (even if empty)
- [x] `src/voice_of_agents/eval/__init__.py` exists (even if empty)
- [x] `src/voice_of_agents/cli/__init__.py` exists (even if empty)
- [x] `pyproject.toml` contains `pydantic>=2.0` in dependencies
- [x] `pyproject.toml` contains `rich>=13.0` in dependencies
- [x] `pyproject.toml` contains `jinja2>=3.1` in dependencies
- [x] Existing `src/voice_of_agents/cli.py` still imports correctly (no import paths broken)
- [x] `python -c "import voice_of_agents"` succeeds

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
ls src/voice_of_agents/core/__init__.py
ls src/voice_of_agents/design/__init__.py
ls src/voice_of_agents/eval/__init__.py
ls src/voice_of_agents/cli/__init__.py
grep "pydantic" pyproject.toml
grep "rich" pyproject.toml
grep "jinja2" pyproject.toml
python -c "import voice_of_agents; print('ok')"
```

## Status
COMPLETE

## Completed Notes
- cli.py moved into cli/__init__.py to resolve package/module namespace conflict (both cannot coexist; package takes precedence). This is a minor scope expansion but necessary for Phase 0 correctness.
