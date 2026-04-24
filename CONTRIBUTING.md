# Contributing to voice-of-agents

Thanks for considering a contribution. The library is small and opinionated;
PRs that reinforce the worldview in [`docs/MANIFESTO.md`](docs/MANIFESTO.md)
are the most welcome.

## Quickstart

```bash
git clone https://github.com/blakeaber/voice-of-agents.git
cd voice-of-agents
pip install -e ".[dev]"
pre-commit install
pytest
```

`pre-commit install` wires the `gitleaks` hook that blocks accidental secret
commits. Do not skip it.

## Branch naming

- `feat/<short-name>` — new feature
- `fix/<short-name>` — bug fix
- `docs/<short-name>` — docs only
- `chore/<short-name>` — tooling, CI, build config

## Pull requests

- Keep PRs focused. Under 400 lines of diff is the sweet spot.
- Add a test for any bug fix.
- Update `CHANGELOG.md` under `## [Unreleased]` if your change is
  user-visible.
- Run `pytest` and `ruff check .` locally before pushing.
- The CI matrix (`ubuntu`, `macos` × Python 3.11/3.12/3.13) must pass before
  merge.

## Security

Do not report security issues as public GitHub issues. See
[`SECURITY.md`](SECURITY.md) for the private reporting channel.

## Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By
participating, you agree to uphold it.

## Questions before opening a PR?

Open a draft PR or a GitHub Discussion. For deeper methodology questions,
read the [Manifesto](docs/MANIFESTO.md) and the
[Bridge Workflow](docs/BRIDGE-WORKFLOW.md) first.
