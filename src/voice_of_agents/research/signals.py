"""Real signal ingestion — augment synthetic research with real user data."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from voice_of_agents.research.models import AdoptionStatus, ContextSegment, VerbatimQuote


class RealSignal(BaseModel):
    """A real user signal to augment synthetic research."""

    source: str  # "transcript", "csv", "json", "manual"
    adoption_status: Optional[AdoptionStatus] = None
    context_segment: Optional[ContextSegment] = None
    verbatim: str
    metadata: dict = {}


class SignalSet(BaseModel):
    """A collection of real signals ready to inject into research prompts."""

    signals: list[RealSignal] = []
    source_files: list[str] = []

    def to_verbatim_quotes(self) -> list[VerbatimQuote]:
        """Convert signals to VerbatimQuote format for injection into prompts."""
        return [
            VerbatimQuote(key=f"RS{i+1}", text=signal.verbatim[:500])
            for i, signal in enumerate(self.signals[:8])
        ]

    def summary(self) -> str:
        n = len(self.signals)
        sources = ", ".join(set(s.source for s in self.signals))
        return f"{n} real signals from: {sources}"


def from_transcripts(paths: list[Path | str]) -> SignalSet:
    """Extract verbatim quotes from plain-text interview transcripts.

    Each line starting with 'P:' or 'User:' is treated as a participant quote.
    Filters for lines ≥ 20 chars (full sentences, not single words).

    Args:
        paths: List of paths to plain-text transcript files (.txt).

    Returns:
        SignalSet with one RealSignal per extracted quote.
    """
    signals: list[RealSignal] = []
    source_files: list[str] = []

    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        source_files.append(str(path))
        text = path.read_text(encoding="utf-8", errors="ignore")

        for line in text.splitlines():
            stripped = line.strip()
            is_participant = (
                stripped.startswith(("P:", "User:", "Participant:", "R:", "Respondent:"))
                or (len(stripped) > 20 and not stripped.startswith(("I:", "Q:", "Interviewer:")))
            )
            if is_participant and len(stripped) >= 20:
                quote = stripped.split(":", 1)[-1].strip() if ":" in stripped else stripped
                if len(quote) >= 15:
                    signals.append(
                        RealSignal(
                            source="transcript",
                            verbatim=quote,
                            metadata={"file": path.name},
                        )
                    )

    return SignalSet(signals=signals[:50], source_files=source_files)


def from_csv(
    path: Path | str,
    text_column: str,
    adoption_column: Optional[str] = None,
    segment_column: Optional[str] = None,
) -> SignalSet:
    """Load verbatim quotes from a CSV file.

    Args:
        path: Path to the CSV file.
        text_column: Column name containing the verbatim text.
        adoption_column: Optional column containing adoption status (mapped to AdoptionStatus).
        segment_column: Optional column containing context segment.

    Returns:
        SignalSet with one RealSignal per non-empty row.
    """
    path = Path(path)
    signals: list[RealSignal] = []

    _adoption_map: dict[str, AdoptionStatus] = {
        "adopter": AdoptionStatus.ADOPTER,
        "user": AdoptionStatus.ADOPTER,
        "active": AdoptionStatus.ADOPTER,
        "partial": AdoptionStatus.PARTIAL_ADOPTER,
        "churned": AdoptionStatus.ABANDONER,
        "abandoned": AdoptionStatus.ABANDONER,
        "rejected": AdoptionStatus.EVALUATED_AND_REJECTED,
        "anti": AdoptionStatus.ACTIVELY_ANTI,
        "aware": AdoptionStatus.NEVER_TRIED_AWARE,
    }

    with path.open(encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get(text_column, "").strip()
            if not text or len(text) < 10:
                continue

            adoption = None
            if adoption_column and adoption_column in row:
                raw_adoption = row[adoption_column].strip().lower()
                for key, status in _adoption_map.items():
                    if key in raw_adoption:
                        adoption = status
                        break

            signals.append(
                RealSignal(
                    source="csv",
                    verbatim=text[:500],
                    adoption_status=adoption,
                    metadata={"file": path.name, "row": dict(row)},
                )
            )

    return SignalSet(signals=signals[:50], source_files=[str(path)])


def from_json(
    path: Path | str,
    text_field: str,
    adoption_field: Optional[str] = None,
) -> SignalSet:
    """Load verbatim quotes from a JSON file (array of objects).

    Args:
        path: Path to a JSON file containing an array of objects.
        text_field: Key in each object containing the verbatim text.
        adoption_field: Optional key for adoption status.

    Returns:
        SignalSet with one RealSignal per array element with non-empty text.
    """
    path = Path(path)
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        # Allow wrapping object: {"results": [...]}
        for key in ("results", "data", "items", "responses"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break

    signals: list[RealSignal] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get(text_field, "")).strip()
        if not text or len(text) < 10:
            continue

        adoption = None
        if adoption_field and adoption_field in item:
            raw = str(item[adoption_field]).lower()
            try:
                adoption = AdoptionStatus(raw)
            except ValueError:
                pass

        signals.append(
            RealSignal(
                source="json",
                verbatim=text[:500],
                adoption_status=adoption,
                metadata={"file": path.name},
            )
        )

    return SignalSet(signals=signals[:50], source_files=[str(path)])


def merge_signal_sets(*sets: SignalSet) -> SignalSet:
    """Merge multiple SignalSets into one (deduplicating by verbatim text)."""
    seen: set[str] = set()
    merged: list[RealSignal] = []
    source_files: list[str] = []

    for s in sets:
        for sig in s.signals:
            if sig.verbatim not in seen:
                seen.add(sig.verbatim)
                merged.append(sig)
        source_files.extend(s.source_files)

    return SignalSet(signals=merged, source_files=list(set(source_files)))


def inject_signals_into_prompt(base_prompt: str, signal_set: SignalSet) -> str:
    """Append real signal quotes to a research prompt for hybrid mode.

    The signals appear after the main prompt content, labeled clearly as
    "Real User Verbatims" so the model can weight them appropriately.
    """
    if not signal_set.signals:
        return base_prompt

    quotes = "\n".join(
        f"- [{s.source}] {s.verbatim}" for s in signal_set.signals[:10]
    )
    return (
        base_prompt
        + f"\n\n## Real User Verbatims (augment your analysis with these)\n{quotes}\n"
    )
