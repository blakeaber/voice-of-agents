"""E2E tests: Full pipeline against live rooben-pro.

Requires:
- rooben-pro running at localhost:3000 (dashboard) and localhost:8420 (API)
- Playwright chromium installed

Run with: pytest tests/e2e/ -v
"""

import pytest
import httpx
import yaml
from pathlib import Path

from voice_of_agents.config import VoAConfig
from voice_of_agents.contracts.personas import Persona, Objective, PainPoint, Voice, save_persona
from voice_of_agents.contracts.backlog import materialize_backlog


def _api_is_up() -> bool:
    try:
        r = httpx.get("http://localhost:8420/api/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _api_is_up(),
    reason="Rooben Pro API not running at localhost:8420",
)


@pytest.fixture
def e2e_config(tmp_path):
    """Config pointing at live rooben-pro with temporary data directory."""
    config = VoAConfig(
        target_url="http://localhost:3000",
        api_url="http://localhost:8420",
        data_dir=str(tmp_path),
    )
    config.save(tmp_path / "voa-config.json")
    (tmp_path / "personas").mkdir()
    (tmp_path / "results").mkdir()
    return config


@pytest.fixture
def e2e_persona():
    """A test persona for E2E testing."""
    return Persona(
        id="E2E-01",
        name="E2E Test User",
        role="Software Tester",
        industry="Technology",
        experience_years=5,
        income=80000,
        team_size=1,
        tier="DEVELOPER",
        objectives=[
            Objective(
                id="OBJ-01",
                goal="Find knowledge management workspace",
                trigger="Need to capture a decision from a recent project",
                success_definition="Workspace page loads with task input and learning sidebar",
                efficiency_baseline="Searching through email threads",
            ),
        ],
        pain_points=[
            PainPoint(description="Decision history scattered across tools", severity=7, theme="A"),
        ],
        trust_requirements=["Must be accurate"],
        voice=Voice(skepticism="moderate", vocabulary="technical"),
    )


class TestPhase2Exploration:
    def test_creates_exploration_yaml(self, e2e_config, e2e_persona):
        save_persona(e2e_persona, e2e_config.personas_path)

        from voice_of_agents.phases.phase2_explore import explore_personas
        explore_personas([e2e_persona], e2e_config)

        # Check that results directory was created
        persona_dir = e2e_config.results_path / e2e_persona.slug
        assert persona_dir.exists(), f"Results dir not created: {persona_dir}"

        runs = sorted(persona_dir.glob("*"))
        assert len(runs) >= 1, "No run directories created"

        exploration_path = runs[-1] / "002-exploration.yaml"
        assert exploration_path.exists(), "Exploration YAML not created"

        data = yaml.safe_load(exploration_path.read_text())
        assert data["persona_id"] == "E2E-01"
        assert data["objectives_attempted"] >= 1
        assert len(data["objectives"]) >= 1

        # Check that journey has actual steps
        obj = data["objectives"][0]
        assert len(obj["journey"]) >= 2, "Journey should have at least 2 steps (landing + nav scan)"
        assert obj["journey"][0]["latency_ms"] > 0, "Latency should be measured"

    def test_screenshots_created(self, e2e_config, e2e_persona):
        save_persona(e2e_persona, e2e_config.personas_path)

        from voice_of_agents.phases.phase2_explore import explore_personas
        explore_personas([e2e_persona], e2e_config)

        persona_dir = e2e_config.results_path / e2e_persona.slug
        runs = sorted(persona_dir.glob("*"))
        screenshot_dir = runs[-1] / "screenshots"
        assert screenshot_dir.exists(), "Screenshots directory not created"

        screenshots = list(screenshot_dir.glob("*.png"))
        assert len(screenshots) >= 1, "At least one screenshot should be taken"


class TestPhase3Evaluation:
    def test_creates_evaluation_yaml(self, e2e_config, e2e_persona):
        save_persona(e2e_persona, e2e_config.personas_path)

        # Run phase 2 first
        from voice_of_agents.phases.phase2_explore import explore_personas
        explore_personas([e2e_persona], e2e_config)

        # Then phase 3
        from voice_of_agents.phases.phase3_evaluate import evaluate_personas
        evaluate_personas([e2e_persona], e2e_config)

        persona_dir = e2e_config.results_path / e2e_persona.slug
        runs = sorted(persona_dir.glob("*"))
        eval_path = runs[-1] / "003-evaluation.yaml"
        assert eval_path.exists(), "Evaluation YAML not created"

        data = yaml.safe_load(eval_path.read_text())
        assert data["persona"]["id"] == "E2E-01"
        assert "scores" in data
        assert all(1 <= data["scores"][k] <= 10 for k in data["scores"])
        assert "narrative" in data
        assert "verdict" in data
        assert "unmet_needs" in data

    def test_scores_are_consistent(self, e2e_config, e2e_persona):
        save_persona(e2e_persona, e2e_config.personas_path)

        from voice_of_agents.phases.phase2_explore import explore_personas
        from voice_of_agents.phases.phase3_evaluate import evaluate_personas, _validate_evaluation

        explore_personas([e2e_persona], e2e_config)
        evaluate_personas([e2e_persona], e2e_config)

        persona_dir = e2e_config.results_path / e2e_persona.slug
        runs = sorted(persona_dir.glob("*"))
        eval_path = runs[-1] / "003-evaluation.yaml"
        data = yaml.safe_load(eval_path.read_text())

        issues = _validate_evaluation(data)
        assert issues == [], f"Score-narrative consistency issues: {issues}"


class TestFullPipeline:
    def test_run_produces_all_outputs(self, e2e_config, e2e_persona):
        save_persona(e2e_persona, e2e_config.personas_path)

        from voice_of_agents.phases.phase2_explore import explore_personas
        from voice_of_agents.phases.phase3_evaluate import evaluate_personas
        from voice_of_agents.phases.phase4_synthesize import synthesize_findings
        from voice_of_agents.phases.phase5_prioritize import prioritize_backlog
        from voice_of_agents.contracts.backlog import save_backlog_markdown

        explore_personas([e2e_persona], e2e_config)
        evaluate_personas([e2e_persona], e2e_config)
        synthesize_findings(e2e_config)
        prioritize_backlog(e2e_config)
        save_backlog_markdown(e2e_config.backlog_jsonl_path, e2e_config.backlog_md_path)

        # Verify all output files exist
        assert e2e_config.focus_group_path.exists(), "Focus group analysis not created"
        # Findings may or may not exist depending on whether unmet needs were found
        # Backlog may or may not have items depending on findings

        # Check persona results
        persona_dir = e2e_config.results_path / e2e_persona.slug
        runs = sorted(persona_dir.glob("*"))
        assert len(runs) >= 1
        assert (runs[-1] / "002-exploration.yaml").exists()
        assert (runs[-1] / "003-evaluation.yaml").exists()
