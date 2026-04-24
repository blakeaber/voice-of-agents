# Running `voice-of-agents` in Docker

The Docker image is an escape hatch for anyone who doesn't want to manage
Python 3.11+ and Playwright setup on their host. For regular use,
`pip install voice-of-agents` is the primary path — the image layers
on top.

## TL;DR

```bash
# Zero-config demo; no API key required (uses bundled fixture)
docker run --rm ghcr.io/blakeaber/voice-of-agents:0.1.0a1 research demo --offline
```

## Three canonical patterns

### 1. Zero-API-key offline demo

Uses the bundled fixture (see [src/voice_of_agents/fixtures/demo_result.yaml](../src/voice_of_agents/fixtures/demo_result.yaml))
and renders realistic output in under a second. Good for "try it before you
sign up for an Anthropic account."

```bash
docker run --rm ghcr.io/blakeaber/voice-of-agents:0.1.0a1 research demo --offline
```

### 2. Live demo (requires API key)

Passes the host's `ANTHROPIC_API_KEY` into the container without writing it
to a file or committing it anywhere.

```bash
docker run --rm \
  -e ANTHROPIC_API_KEY \
  ghcr.io/blakeaber/voice-of-agents:0.1.0a1 \
  research demo
```

### 3. Live research run with persisted sessions

Mounts the host's `research-sessions/` and `data/` directories so output
survives the container exiting.

```bash
docker run --rm \
  -e ANTHROPIC_API_KEY \
  -v "$(pwd)/research-sessions:/app/research-sessions" \
  -v "$(pwd)/data:/app/data" \
  ghcr.io/blakeaber/voice-of-agents:0.1.0a1 \
  research run my-config.yaml
```

## Building locally from source

The image is pulled from GHCR once it's published (see maintainer
procedure below). To build from source:

```bash
docker build -t voa:local .
docker run --rm voa:local research demo --offline
```

Cold-cache build time is 3–5 minutes (Playwright Chromium dominates).

## Debugging inside the container

The `ENTRYPOINT` is `voa`, so to get an interactive shell:

```bash
docker run -it --rm --entrypoint /bin/bash ghcr.io/blakeaber/voice-of-agents:0.1.0a1
```

From there you can run `voa doctor`, `voa --help`, or inspect installed
packages.

## Image size expectations

Target: **< 500 MB**. Breakdown on a recent build:

| Layer | Size |
|---|---|
| `python:3.12-slim` base | ~125 MB |
| System deps for Playwright | ~80 MB |
| Python deps (anthropic, pydantic, rich, playwright core, etc.) | ~60 MB |
| Playwright Chromium browser | ~130 MB |
| Library source (bundled fixture included) | < 1 MB |

## Maintainer: pushing to GHCR

GHCR (GitHub Container Registry) publishing is a manual one-time step;
it's not automated as part of the release workflow in
[docs/RELEASE.md](RELEASE.md). Procedure:

```bash
# Build locally
docker build -t voa:local .

# Tag for GHCR
docker tag voa:local ghcr.io/blakeaber/voice-of-agents:0.1.0a1
docker tag voa:local ghcr.io/blakeaber/voice-of-agents:latest

# Log in with a personal access token that has write:packages scope
echo "$GITHUB_TOKEN" | docker login ghcr.io -u blakeaber --password-stdin

# Push
docker push ghcr.io/blakeaber/voice-of-agents:0.1.0a1
docker push ghcr.io/blakeaber/voice-of-agents:latest
```

## Pitfalls

- **Running as root.** The image runs as root by default (standard Docker
  practice for CLI tools; Playwright browsers get installed to
  `/root/.cache/ms-playwright/`). Non-root is a future hardening item.
- **libc version skew.** The image uses Debian Bookworm via
  `python:3.12-slim`. If Playwright ever drops Bookworm support, pin to
  an explicit tag (e.g. `python:3.12-slim-bookworm`).
- **Apple Silicon.** Pull runs amd64 via emulation on arm64 Macs (Docker
  Desktop handles this transparently but it's slower). Multi-arch image
  publishing is deferred.
- **The `ENTRYPOINT` trap.** `docker run voa:local research demo` becomes
  `voa research demo` inside the container. To run anything else, use
  `--entrypoint`, e.g. `docker run --entrypoint /bin/bash voa:local`.
