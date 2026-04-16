# Phase 6: Test Coverage and Cleanup

## Goal
Add baseline unit test coverage for all critical eval-layer components, finalize directory cleanup, and update the README with the unified CLI reference.

## Context
The Main package had zero unit tests. This phase adds coverage for the pure-logic components (backlog event sourcing, prioritization scoring, evaluation template logic), ports remaining Pro tests, and does the final sweep to confirm all legacy directories and files are gone.

## Dependencies
Phase 5 must be COMPLETE: bridge layer done, all modules in final locations.

## Scope

### Files to Create
- `tests/unit/test_eval_migrate.py` — migration function tests (may already exist from Phase 4; verify/complete)
- `tests/unit/test_eval_prioritize.py` — `_load_findings`, `_revenue_score`, `_estimate_effort`
- `tests/unit/test_eval_evaluate.py` — voice calibration defaults, `_validate_evaluation`, `_fix_consistency`, template scoring
- `tests/fixtures/sample_exploration.yaml` — mock Phase 2 output
- `tests/fixtures/sample_evaluation.yaml` — mock Phase 3 output
- `tests/fixtures/sample_findings.md` — mock Phase 4 output (for prioritize tests)

### Files to Modify
- `tests/unit/test_core_backlog.py` — ensure unified BacklogItem with all three source values is tested
- `tests/unit/test_core_capability.py` — ensure TestResult and test_results list are tested
- `README.md` — replace old CLI reference with unified `voa design` / `voa eval` / `voa bridge` structure

### Files to Delete (confirm gone)
- `src/voice_of_agents/contracts/` — should be deleted in Phase 4
- `src/voice_of_agents/explorer/` — should be deleted in Phase 3
- `src/voice_of_agents/phases/` — should be deleted in Phase 3
- `src/voice_of_agents/reporting/` — should be deleted in Phase 3
- `src/voice_of_agents/cli.py` — should be deleted in Phase 3
- `src/voice_of_agents/config.py` — should be deleted in Phase 3
- `pro-package/` — should be deleted in Phase 2

### Explicitly Out of Scope
- Unit tests for `eval/browser.py` and `eval/api.py` (require live infrastructure)
- Integration tests beyond `test_cli_design.py`

## Implementation Notes

### `tests/unit/test_eval_prioritize.py`
Test the pure scoring functions from `eval/phase5_prioritize.py`. These are all deterministic math — no external calls.

```python
# Test _estimate_effort() heuristic
from voice_of_agents.eval.phase5_prioritize import _estimate_effort
assert _estimate_effort("empty state message") == "trivial"
assert _estimate_effort("add a button for navigation") == "small"
assert _estimate_effort("integrate with external API") == "large"
assert _estimate_effort("bulk migration infrastructure") == "epic"

# Test _revenue_score() with tier map
from voice_of_agents.eval.phase5_prioritize import _revenue_score
from voice_of_agents.core.enums import Tier
assert _revenue_score([Tier.ENTERPRISE]) == 1.0
assert _revenue_score([Tier.FREE, Tier.DEVELOPER]) == 0.3
assert _revenue_score([]) == 0.0

# Test _load_findings() with sample_findings.md fixture
from pathlib import Path
from voice_of_agents.eval.phase5_prioritize import _load_findings
findings = _load_findings(Path("tests/fixtures/sample_findings.md"))
assert len(findings) > 0
assert findings[0].get("id", "").startswith("F-")
```

### `tests/unit/test_eval_evaluate.py`
Test pure logic from `eval/phase3_evaluate.py`:

```python
# Voice calibration always works (no None guard needed)
from voice_of_agents.core.persona import Persona, VoiceProfile
p = Persona(id=1, name="Test", role="Dev", industry="Tech", segment="b2c", tier="FREE")
assert p.voice.skepticism == "moderate"  # default

# _validate_evaluation: overall cannot exceed goal_achievement + 3
from voice_of_agents.eval.phase3_evaluate import _validate_evaluation
scores = {"overall": 9, "goal_achievement": 3, "efficiency": 5, "trust": 5, "learnability": 5, "value_for_price": 5}
issues = _validate_evaluation(scores)
assert len(issues) > 0  # should flag the inconsistency

# _fix_consistency: corrects the scores
from voice_of_agents.eval.phase3_evaluate import _fix_consistency
fixed = _fix_consistency(scores.copy())
assert fixed["overall"] <= fixed["goal_achievement"] + 3

# Template scoring produces valid score range
from voice_of_agents.eval.phase3_evaluate import _template_generate_evaluation
result = _template_generate_evaluation(p, mock_exploration_result)
assert 1 <= result["scores"]["overall"] <= 10
```

Note: `_template_generate_evaluation` and `_validate_evaluation` need to be extractable as standalone functions. If they're embedded in larger functions, refactor them into private helpers that tests can call directly.

### `tests/unit/test_core_backlog.py` additions
```python
# Test all three source values
from voice_of_agents.core.backlog import BacklogItem
for source in ["eval", "design", "bridge"]:
    item = BacklogItem(id=f"B-{source}", title="T", description="D", source=source)
    assert item.source == source

# Test design-layer fields
item = BacklogItem(id="B-001", title="T", description="D", source="design",
                   extends_capability="CAP-LEARN-SEARCH",
                   value_statement="In my voice, this matters.")
assert item.extends_capability == "CAP-LEARN-SEARCH"
```

### Sample fixtures needed

**`tests/fixtures/sample_findings.md`** — a minimal 004-findings.md format:
```markdown
## Findings — 2026-04-02 (3 personas evaluated)

### F-001: Cannot Retrieve Past Work
**Type:** gap | **Theme:** A | **Severity:** 7.5 | **Breadth:** 0.8
**Personas:** UXW-01, UXW-02 (2/3)
**Status:** open
> "I can't find my past decisions" — UXW-01
```

**`tests/fixtures/sample_exploration.yaml`** — minimal 002-exploration.yaml output

**`tests/fixtures/sample_evaluation.yaml`** — minimal 003-evaluation.yaml output

### README update
Replace the old CLI table with the new structure:
```markdown
## CLI Reference

### Design phase
voa design persona list --dir .
voa design persona generate-prompt --product X --description Y --industry Z --roles A,B
voa design workflow generate-prompt 1 --dir .
voa design analyze gaps --dir .
voa design validate --dir .

### Eval phase
voa eval init --target http://localhost:3000 --api http://localhost:8420
voa eval migrate          # convert UXW-format personas to canonical format
voa eval run --all        # full pipeline (phases 2-5)
voa eval status
voa eval backlog
voa eval capabilities
voa eval diff

### Bridge (cross-layer)
voa bridge status
voa bridge sync-gaps --dir .
```

### Coverage targets
Run with `pytest --cov=voice_of_agents --cov-report=term-missing`:
- `core/backlog.py` ≥ 80%
- `eval/phase5_prioritize.py` ≥ 60%
- `eval/phase3_evaluate.py` ≥ 60% (template path)
- `core/persona.py` ≥ 90%

### Final cleanup sweep
Check each of these returns "not found":
```bash
ls src/voice_of_agents/contracts/ 2>/dev/null
ls src/voice_of_agents/explorer/ 2>/dev/null
ls src/voice_of_agents/phases/ 2>/dev/null
ls src/voice_of_agents/reporting/ 2>/dev/null
ls src/voice_of_agents/cli.py 2>/dev/null
ls src/voice_of_agents/config.py 2>/dev/null
ls pro-package/ 2>/dev/null
```

## Acceptance Criteria
- [ ] `pytest tests/ -v --tb=short` passes with zero failures
- [ ] `pytest tests/unit/test_eval_prioritize.py -v` passes
- [ ] `pytest tests/unit/test_eval_evaluate.py -v` passes
- [ ] `pytest tests/unit/test_core_backlog.py -v` passes (including source field tests)
- [ ] `pytest tests/unit/test_eval_migrate.py -v` passes
- [ ] All migrated Pro tests pass (`test_design_workflow.py`, `test_design_validators.py`)
- [ ] `pytest --cov=voice_of_agents.core.backlog --cov-report=term-missing` shows ≥ 80% coverage
- [ ] `pytest --cov=voice_of_agents.core.persona --cov-report=term-missing` shows ≥ 90% coverage
- [ ] `src/voice_of_agents/contracts/` does NOT exist
- [ ] `src/voice_of_agents/explorer/` does NOT exist
- [ ] `src/voice_of_agents/phases/` does NOT exist
- [ ] `src/voice_of_agents/reporting/` does NOT exist
- [ ] `src/voice_of_agents/cli.py` does NOT exist
- [ ] `pro-package/` does NOT exist
- [ ] README contains `voa design`, `voa eval`, and `voa bridge` sections

## Verification Steps
```bash
cd /Users/blakeaber/Documents/voice-of-agents
pip install -e ".[dev]" -q  # or pip install pytest pytest-cov

# Full test suite
pytest tests/ -v --tb=short

# Coverage
pytest --cov=voice_of_agents.core --cov=voice_of_agents.eval.phase5_prioritize \
       --cov=voice_of_agents.eval.phase3_evaluate \
       --cov-report=term-missing tests/unit/

# Cleanup verification
for d in contracts explorer phases reporting; do
  ls src/voice_of_agents/$d/ 2>/dev/null && echo "FAIL: $d still exists" || echo "PASS: $d gone"
done
ls src/voice_of_agents/cli.py 2>/dev/null && echo "FAIL: cli.py still exists" || echo "PASS: cli.py gone"
ls pro-package/ 2>/dev/null && echo "FAIL: pro-package still exists" || echo "PASS: pro-package gone"

# End-to-end smoke test
voa --help
voa eval status
voa design --help
voa bridge status
```

## Status
PENDING
