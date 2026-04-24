# Release procedure

This document covers:

1. One-time setup of PyPI trusted publishers (required before the first publish)
2. The tag-and-publish flow for cutting a new release

## One-time setup: PyPI trusted publishers

Trusted publishing uses GitHub Actions' OIDC tokens to authenticate PyPI
uploads without long-lived API tokens. Setup is done on the PyPI side and
the GitHub side and must happen once per repository.

### TestPyPI (used for pre-release tags: `v*a*`, `v*b*`, `v*rc*`, `v*dev*`)

1. Sign in at https://test.pypi.org/
2. Go to **Your account → Publishing** (or https://test.pypi.org/manage/account/publishing/)
3. Click **Add a new pending publisher**
4. Fill in:
   - **PyPI Project Name:** `voice-of-agents`
   - **Owner:** `blakeaber`
   - **Repository name:** `voice-of-agents`
   - **Workflow name:** `release.yml`
   - **Environment name:** `testpypi`
5. Click **Add**

### PyPI (used for stable tags: `v1.0.0`, `v1.1.2`, etc.)

Same steps as above, at https://pypi.org/manage/account/publishing/, with
environment name **`pypi`**.

### GitHub Environments

1. Go to `https://github.com/blakeaber/voice-of-agents/settings/environments`
2. Click **New environment** → name it `testpypi` → Configure → (no
   required reviewers needed for TestPyPI) → Save
3. Click **New environment** → name it `pypi` → Configure → **Add
   required reviewer: blakeaber** (this adds a belt-and-suspenders human
   approval step before any production PyPI publish) → Save

After both environments exist and the trusted publishers are registered,
the first `v*a*` tag push will successfully publish to TestPyPI.

## Cutting a release

### Pre-release (alpha / beta / rc)

```bash
# From main, with all phases of the release plan Complete and CI green:
git tag -a v0.1.0a1 -m "Release 0.1.0a1 — alpha on TestPyPI"
git push origin v0.1.0a1
```

The `release.yml` workflow triggers on the tag push. Because the version
contains `a1`, the `target` step routes to `testpypi`. After the job
finishes, the package appears at:

    https://test.pypi.org/project/voice-of-agents/0.1.0a1/

### Stable release

```bash
# After soak period on the last pre-release:
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

The same workflow routes to `pypi` because `0.1.0` has no pre-release
suffix. The `pypi` environment's required-reviewer rule (if configured)
will pause the workflow for human approval before the upload step.

### Dry run

To preview what the workflow *would* do without uploading:

1. Go to the **Actions** tab → **Release** → **Run workflow**
2. Choose branch `main`, mode `dry-run`
3. The workflow builds the package and prints `DRY RUN — would publish
   voice_of_agents-<version> to <nowhere>` without uploading

## Version number conventions

The project uses PEP 440 version identifiers:

- **Alpha:** `0.1.0a1`, `0.1.0a2`, … (API may break; for internal
  validation)
- **Beta:** `0.1.0b1` (feature-complete; collecting bug reports)
- **Release candidate:** `0.1.0rc1` (bug-fix-only before stable)
- **Stable:** `0.1.0`

Version source of truth: `src/voice_of_agents/__init__.py` `__version__`.
Hatch reads it via `[tool.hatch.version] path` in `pyproject.toml`.

## Troubleshooting

### "Duplicate upload" error on TestPyPI

TestPyPI (like PyPI) rejects re-upload of the same version. If the first
publish attempt fails partway, you cannot re-run with the same tag. Bump
to the next alpha (`v0.1.0a2`) and tag again.

### Badge cache

`img.shields.io` caches PyPI-version badges for up to 10 minutes. If
README badges still say "no package" immediately after publish, wait.

### OIDC token minting fails

If the publish step fails with an OIDC-related error, verify:

1. The job has `permissions: id-token: write`
2. The job is running inside the correct `environment:` (name must match
   the trusted publisher registration exactly)
3. The trusted publisher on PyPI side lists the correct workflow filename
   (`release.yml`) and environment name

## After each release

- [ ] Move `## [Unreleased]` content in `CHANGELOG.md` to `## [<version>] -
      YYYY-MM-DD`
- [ ] Add a fresh empty `## [Unreleased]` section above it
- [ ] If stable release: announce on LinkedIn with a link to the thesis
      article and `pip install voice-of-agents`
