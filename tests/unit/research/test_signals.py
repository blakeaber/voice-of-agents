"""Tests for research/signals.py — real signal ingestion."""

import csv
import json
import tempfile


from voice_of_agents.research.signals import (
    RealSignal,
    SignalSet,
    from_csv,
    from_json,
    from_transcripts,
    inject_signals_into_prompt,
    merge_signal_sets,
)
from voice_of_agents.research.models import AdoptionStatus


class TestFromTranscripts:
    def test_extracts_participant_lines(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("I: How do you use the tool?\n")
            f.write("P: I open it every morning to check my tasks. It saves me time.\n")
            f.write("I: What would make you stop?\n")
            f.write("P: If it gave me wrong information consistently I would quit.\n")
            fname = f.name

        signals = from_transcripts([fname])
        assert len(signals.signals) >= 2
        for sig in signals.signals:
            assert sig.source == "transcript"

    def test_skips_short_lines(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("P: Yes\n")
            f.write("P: This is a longer response that should be captured as a quote.\n")
            fname = f.name

        signals = from_transcripts([fname])
        texts = [s.verbatim for s in signals.signals]
        assert not any("Yes" == t for t in texts)

    def test_handles_nonexistent_file(self):
        signals = from_transcripts(["/nonexistent/path.txt"])
        assert signals.signals == []

    def test_records_source_files(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("P: This is a participant quote with enough text.\n")
            fname = f.name

        signals = from_transcripts([fname])
        assert fname in signals.source_files


class TestFromCsv:
    def test_extracts_text_column(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["feedback", "status"])
            writer.writeheader()
            writer.writerow(
                {"feedback": "This tool changed how I work completely", "status": "user"}
            )
            writer.writerow({"feedback": "I stopped using it after two weeks", "status": "churned"})
            fname = f.name

        signals = from_csv(fname, text_column="feedback", adoption_column="status")
        assert len(signals.signals) == 2
        assert signals.signals[0].source == "csv"

    def test_maps_adoption_status(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "type"])
            writer.writeheader()
            writer.writerow(
                {"text": "I stopped after a month, it was not working for me", "type": "abandoned"}
            )
            fname = f.name

        signals = from_csv(fname, text_column="text", adoption_column="type")
        assert signals.signals[0].adoption_status == AdoptionStatus.ABANDONER

    def test_skips_short_rows(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["text"])
            writer.writeheader()
            writer.writerow({"text": "ok"})
            writer.writerow({"text": "This is a meaningful piece of feedback that is long enough."})
            fname = f.name

        signals = from_csv(fname, text_column="text")
        assert len(signals.signals) == 1


class TestFromJson:
    def test_extracts_text_field(self):
        data = [
            {
                "response": "The tool helped me dramatically reduce time spent on reports.",
                "type": "adopter",
            },
            {
                "response": "I tried it once and never went back because it was confusing.",
                "type": "abandoner",
            },
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            fname = f.name

        signals = from_json(fname, text_field="response", adoption_field="type")
        assert len(signals.signals) == 2
        assert signals.signals[0].source == "json"

    def test_maps_adoption_status(self):
        data = [
            {"text": "I abandoned it after week one it was too slow for me", "status": "abandoner"}
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            fname = f.name

        signals = from_json(fname, text_field="text", adoption_field="status")
        assert signals.signals[0].adoption_status == AdoptionStatus.ABANDONER

    def test_handles_wrapped_object(self):
        data = {
            "results": [{"quote": "A really long and meaningful user quote here", "type": "user"}]
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            fname = f.name

        signals = from_json(fname, text_field="quote")
        assert len(signals.signals) == 1


class TestMergeSignalSets:
    def test_merges_two_sets(self):
        s1 = SignalSet(signals=[RealSignal(source="csv", verbatim="quote one about the tool")])
        s2 = SignalSet(signals=[RealSignal(source="json", verbatim="quote two about the product")])
        merged = merge_signal_sets(s1, s2)
        assert len(merged.signals) == 2

    def test_deduplicates_by_verbatim(self):
        s1 = SignalSet(signals=[RealSignal(source="csv", verbatim="same quote here")])
        s2 = SignalSet(signals=[RealSignal(source="json", verbatim="same quote here")])
        merged = merge_signal_sets(s1, s2)
        assert len(merged.signals) == 1


class TestInjectSignalsIntoPrompt:
    def test_appends_signals_to_prompt(self):
        signals = SignalSet(
            signals=[
                RealSignal(source="transcript", verbatim="Users often say they feel overwhelmed"),
            ]
        )
        result = inject_signals_into_prompt("Base prompt.", signals)
        assert "Real User Verbatims" in result
        assert "Users often say they feel overwhelmed" in result

    def test_empty_signals_returns_base_unchanged(self):
        signals = SignalSet(signals=[])
        result = inject_signals_into_prompt("Base prompt.", signals)
        assert result == "Base prompt."


class TestSignalSetToVerbatimQuotes:
    def test_converts_to_verbatim_quotes(self):
        signals = SignalSet(
            signals=[
                RealSignal(source="csv", verbatim=f"User quote number {i} here") for i in range(5)
            ]
        )
        quotes = signals.to_verbatim_quotes()
        assert len(quotes) == 5
        for q in quotes:
            assert q.key.startswith("RS")

    def test_caps_at_eight_quotes(self):
        signals = SignalSet(
            signals=[RealSignal(source="csv", verbatim=f"Quote {i}") for i in range(20)]
        )
        quotes = signals.to_verbatim_quotes()
        assert len(quotes) <= 8
