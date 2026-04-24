"""`voa doctor` — pre-flight diagnostic for the library's runtime dependencies.

Runs a sequence of read-only checks and prints a Rich-formatted table.
Every failure includes an actionable fix command. Never modifies state.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

OK = "✓"  # ✓
WARN = "⚠"  # ⚠
FAIL = "✗"  # ✗

MIN_PYTHON = (3, 11)
DISK_WARN_GB = 1.0
DISK_FAIL_GB = 0.1

# Playwright browser cache location follows the library's default
# ($HOME/Library/Caches/ms-playwright on macOS,
#  $HOME/.cache/ms-playwright on Linux).
_PLAYWRIGHT_CACHES = [
    Path.home() / ".cache" / "ms-playwright",
    Path.home() / "Library" / "Caches" / "ms-playwright",
]


@dataclass
class CheckResult:
    name: str
    status: str  # OK / WARN / FAIL
    detail: str


def _check_python_version() -> CheckResult:
    current = sys.version_info
    actual = f"{current.major}.{current.minor}.{current.micro}"
    if current >= MIN_PYTHON:
        return CheckResult("Python ≥ 3.11", OK, actual)
    return CheckResult(
        "Python ≥ 3.11",
        FAIL,
        f"{actual} (too old)\nFix: install Python 3.11+ via https://www.python.org/downloads/",
    )


def _check_api_key() -> CheckResult:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return CheckResult(
            "ANTHROPIC_API_KEY set",
            FAIL,
            "unset\nFix: export ANTHROPIC_API_KEY=sk-ant-... "
            "(get a key at https://console.anthropic.com/settings/keys)",
        )
    if not key.startswith("sk-ant-"):
        return CheckResult(
            "ANTHROPIC_API_KEY set",
            FAIL,
            "format looks wrong (should start with sk-ant-)\n"
            "Fix: export ANTHROPIC_API_KEY=sk-ant-...",
        )
    redacted = f"{key[:16]}…{key[-4:]}"
    return CheckResult("ANTHROPIC_API_KEY set", OK, redacted)


def _check_api_roundtrip() -> CheckResult:
    """Make a 1-token test call to claude-haiku. Cost: ~$0.0001."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return CheckResult(
            "Anthropic API round-trip",
            FAIL,
            "skipped (no API key; see prior check)",
        )
    try:
        # Imported lazily so the check can be skipped with --offline
        # without importing the SDK at module load.
        import time

        from anthropic import Anthropic

        client = Anthropic(api_key=key)
        start = time.perf_counter()
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            "Anthropic API round-trip",
            OK,
            f"claude-haiku-4-5 OK ({elapsed_ms}ms)",
        )
    except Exception as exc:  # noqa: BLE001
        # Classify common errors for actionable detail
        msg = str(exc).splitlines()[0][:200]
        return CheckResult(
            "Anthropic API round-trip",
            FAIL,
            f"failed: {msg}\nFix: verify the key is active at https://console.anthropic.com/settings/keys",
        )


def _check_playwright() -> CheckResult:
    """Warn-only: Playwright browsers are needed for `voa eval`, not `voa research`."""
    if any(p.exists() and any(p.iterdir()) for p in _PLAYWRIGHT_CACHES):
        return CheckResult("Playwright browsers", OK, "Chromium cached (required for voa eval)")
    return CheckResult(
        "Playwright browsers",
        WARN,
        "not installed; only needed for `voa eval` paths\nFix: playwright install chromium",
    )


def _check_disk_space() -> CheckResult:
    free_gb = shutil.disk_usage(Path.home()).free / (1024**3)
    human = f"{free_gb:.1f} GB free in {Path.home()}"
    if free_gb < DISK_FAIL_GB:
        return CheckResult(
            "Disk space in ~",
            FAIL,
            f"{human} (too low)\nFix: free up space; sessions won't save",
        )
    if free_gb < DISK_WARN_GB:
        return CheckResult("Disk space in ~", WARN, f"{human} (low)")
    return CheckResult("Disk space in ~", OK, human)


def _check_path_conflicts() -> CheckResult:
    # shutil.which returns the first hit. Look up all $PATH entries for `voa`.
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    found: list[str] = []
    for p in path_entries:
        candidate = Path(p) / "voa"
        if candidate.is_file() and os.access(candidate, os.X_OK) and str(candidate) not in found:
            found.append(str(candidate))
    if len(found) == 0:
        # Unreachable if the user is running `voa doctor`, but handle gracefully
        return CheckResult("Single `voa` on $PATH", FAIL, "no voa binary found on PATH")
    if len(found) == 1:
        return CheckResult("Single `voa` on $PATH", OK, found[0])
    # Multiple entries — usually benign (pyenv creates both a shim and a
    # versioned bin; virtualenv layering does the same). Warn, don't fail.
    return CheckResult(
        "Single `voa` on $PATH",
        WARN,
        f"{len(found)} voa binaries on PATH ({found[0]} resolves first). "
        "Usually benign (pyenv / virtualenv layering). Run `which -a voa` "
        "if you see unexpected CLI behavior.",
    )


def _render(results: list[CheckResult]) -> None:
    table = Table(title="voa doctor", show_lines=False, title_justify="left")
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center", width=8)
    table.add_column("Detail")

    for r in results:
        color = {OK: "green", WARN: "yellow", FAIL: "red"}[r.status]
        table.add_row(r.name, f"[{color}]{r.status}[/{color}]", r.detail)

    console.print(table)

    warns = sum(1 for r in results if r.status == WARN)
    fails = sum(1 for r in results if r.status == FAIL)
    if fails:
        console.print(f"\n[red]{fails} required check(s) failed.[/red] See fix commands above.")
    elif warns:
        console.print(f"\n[yellow]All required checks passed.[/yellow] {warns} warning(s).")
    else:
        console.print("\n[green]All checks passed.[/green]")


@click.command()
@click.option(
    "--offline",
    is_flag=True,
    help="Skip the live Anthropic API round-trip check (useful in CI or air-gapped environments).",
)
def doctor(offline: bool) -> None:
    """Run pre-flight diagnostic checks."""
    checks: list[CheckResult] = [
        _check_python_version(),
        _check_api_key(),
    ]
    if not offline:
        checks.append(_check_api_roundtrip())
    checks.extend(
        [
            _check_playwright(),
            _check_disk_space(),
            _check_path_conflicts(),
        ]
    )

    _render(checks)

    if any(r.status == FAIL for r in checks):
        raise SystemExit(1)
