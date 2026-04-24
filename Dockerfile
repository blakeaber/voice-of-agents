# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

# System dependencies for Playwright headless Chromium.
# See https://playwright.dev/python/docs/docker for the canonical list.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libnspr4 \
        libnss3 \
        libx11-6 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        wget \
        xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only packaging metadata and source first — keeps the dependency-
# install layer cached when only source changes.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install the package (brings in click, rich, anthropic, pydantic,
# playwright-core, python-dotenv, etc.).
RUN pip install --no-cache-dir .

# Playwright Chromium only. Firefox/WebKit are not installed to keep the
# image under ~500 MB.
RUN playwright install --with-deps chromium

# Default user-facing entrypoint is the `voa` CLI.
ENTRYPOINT ["voa"]
CMD ["--help"]

LABEL org.opencontainers.image.source="https://github.com/blakeaber/voice-of-agents"
LABEL org.opencontainers.image.description="Synthetic user research and LLM eval harness"
LABEL org.opencontainers.image.licenses="MIT"
