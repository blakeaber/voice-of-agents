# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2026-04-25

Initial stable release on PyPI. Promoted from `0.1.0a1` (which validated
the trusted-publisher pipeline on TestPyPI). See `[0.1.0a1]` below for
the full feature list.

Versioning policy: follows SemVer. The `0.x` major signals an evolving
public API — minor bumps may include breaking changes. Stable
guarantees begin at `1.0.0`.

### Changed (vs. 0.1.0a1)
- `voa research demo` preset bumps `subject_count` from 10 to 12. The
  sampling-frame methodology guard requires 9 minimums across 6
  adoption-status rows; 10 left only 1 slot of LLM allocation
  flexibility, causing intermittent first-stage validation failures.
  12 gives 3 free slots and dramatically improves demo reliability.

### Fixed (vs. 0.1.0a1)
- `subject_schema.j2` prompt: clarify that `failure_or_abandonment_mode`
  is REQUIRED (not just "for non-adopters") for `partial-adopter`,
  `abandoner`, `evaluated-and-rejected`, and `actively-anti` statuses.
  Previous wording was ambiguous about partial-adopters; less robust
  models (e.g., Haiku) intermittently left the field blank, tripping
  the Pydantic validator. Now includes concrete examples per status.

## [0.1.0a1] - 2026-04-25

Initial alpha release on TestPyPI. Establishes the public OSS shell around the
existing `voice_of_agents.research` and `voice_of_agents.eval` libraries.

### Added
- `voa doctor` pre-flight diagnostic command (Python version, API key,
  Playwright browsers, disk space, $PATH conflicts)
- `voa research demo --offline` zero-API-key path using a bundled YAML
  fixture
- `.env.example` template; pre-commit `gitleaks` hook
- LICENSE (MIT, Copyright 2026 Blake Aber), SECURITY.md, CONTRIBUTING.md,
  CODE_OF_CONDUCT.md, CHANGELOG.md, GitHub issue + PR templates
- GitHub Actions CI matrix (Python 3.11/3.12/3.13 × ubuntu/macos)
- GitHub Actions release workflow using PyPI trusted publishing (OIDC)
- Dockerfile (`python:3.12-slim` + Playwright Chromium); `docs/DOCKER.md`
- README rewrite: POV hero linked to the "Beta Users Are Lying" article,
  embedded demo SVG, audience routing to `examples/`, link to
  `demo/multi-agent-adoption/` worked artifact, 4 status badges
- `py.typed` marker so consumers receive the library's type hints
- `examples/eval-harness/voa-config.example.json` template
- `docs/RELEASE.md` documenting the trusted-publisher setup and tag flow

### Changed
- `pyproject.toml`: full PyPI metadata (license, authors, classifiers,
  project.urls including the thesis-article link, keywords); dynamic
  versioning sourced from `src/voice_of_agents/__init__.py`
- Repository layout: `voa-config.json` moved from repo root to
  `examples/eval-harness/voa-config.example.json`
- Codebase-wide: ruff auto-fixes (76 errors) + ruff format (58 files
  reformatted) to align with CI rule set; no behavioral changes (359 →
  379 tests, +20 from the 002-G/H test suites; all green)

### Removed
- `.claude/skills/` directory (4 pre-library methodology SKILL.md files
  obsoleted by the Python `voice_of_agents.research` module; archived to
  `~/.claude/skills-voa-archive/` on the maintainer's machine)
- `voa-config.json` at repo root (relocated to `examples/eval-harness/`)
- Orphaned `GITHUB_CLIENT_*` and `GOOGLE_CLIENT_*` OAuth secrets from
  the local-only `.env` (never tracked; unused by any code in this repo)

### Security
- All tracked files scanned clean via `gitleaks` across 25 commits / 1.47 MB
- Pre-commit `gitleaks` hook prevents future reintroduction of
  secret-shaped strings
- Live `ANTHROPIC_API_KEY`, GitHub OAuth client secret, and Google OAuth
  client secret rotated at their provider consoles before public release;
  old keys revoked
- `python-dotenv>=1.0` added to runtime dependencies (closes a pre-existing
  latent `ImportError` in `cli/main.py` on fresh-venv installs)
