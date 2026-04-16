"""Shared test fixtures for Voice of Agents."""

import pytest

from voice_of_agents.core.backlog import BacklogItem
from voice_of_agents.core.pain import PainPoint, PainTheme
from voice_of_agents.core.persona import Persona, VoiceProfile
from voice_of_agents.eval.browser import NavLink
from voice_of_agents.eval.config import VoAConfig


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory with standard structure."""
    (tmp_path / "personas").mkdir()
    (tmp_path / "results").mkdir()
    return tmp_path


@pytest.fixture
def config(tmp_data_dir):
    """VoAConfig pointing at temporary directories."""
    return VoAConfig(
        data_dir=str(tmp_data_dir),
        target_url="http://test:3000",
        api_url="http://test:8420",
    )


@pytest.fixture
def maria():
    """Maria Gutierrez — immigration paralegal (B2C solo, DEVELOPER)."""
    return Persona(
        id=1,
        name="Maria Gutierrez",
        role="Immigration Paralegal",
        industry="Legal",
        segment="b2c",
        tier="DEVELOPER",
        experience_years=15,
        income=52000,
        org_size=1,
        pain_points=[
            PainPoint(description="800 files in Google Drive, can't find anything", impact="severity 9/10, daily"),
            PainPoint(description="Policy changes discovered via rejections", impact="severity 8/10, monthly"),
        ],
        pain_themes=[
            PainTheme(theme="A", intensity="CRITICAL"),
            PainTheme(theme="D", intensity="HIGH"),
        ],
        trust_requirements=["Must surface MY prior work, not generic AI answers"],
        voice=VoiceProfile(skepticism="high", vocabulary="legal", motivation="fear", price_sensitivity="moderate"),
    )


@pytest.fixture
def rachel():
    """Rachel Okafor — Dir People Ops (B2B team, TEAM tier)."""
    return Persona(
        id=20,
        name="Rachel Okafor",
        role="Director of People Operations",
        industry="HR",
        segment="b2b",
        tier="TEAM",
        experience_years=12,
        income=130000,
        org_size=8,
        pain_points=[
            PainPoint(description="20+ policy questions daily from managers", impact="severity 9/10, daily"),
        ],
        pain_themes=[
            PainTheme(theme="B", intensity="CRITICAL"),
        ],
        trust_requirements=["Only answer approved policies, never fabricate"],
        voice=VoiceProfile(skepticism="moderate", vocabulary="general", motivation="efficiency", price_sensitivity="low"),
    )


@pytest.fixture
def james():
    """James Washington — small business bookkeeper (FREE, skeptical)."""
    return Persona(
        id=4,
        name="James Washington",
        role="Small Business Bookkeeper",
        industry="Finance",
        segment="b2c",
        tier="FREE",
        experience_years=25,
        income=45000,
        org_size=1,
        pain_points=[
            PainPoint(description="Categorization errors repeat every quarter", impact="severity 7/10, quarterly"),
        ],
        pain_themes=[
            PainTheme(theme="A", intensity="HIGH"),
        ],
        trust_requirements=["Wants HIS reasoning, not AI opinions"],
        voice=VoiceProfile(skepticism="high", vocabulary="financial", motivation="fear", price_sensitivity="high"),
    )


@pytest.fixture
def sample_nav_links():
    """Realistic sidebar nav links."""
    return [
        NavLink(text="Past Runs", href="/"),
        NavLink(text="Create New", href="/workflows/new"),
        NavLink(text="Integrations", href="/integrations"),
        NavLink(text="Settings", href="/settings"),
        NavLink(text="Workspace", href="/pro/workspace"),
        NavLink(text="Knowledge Library", href="/pro/learnings"),
        NavLink(text="My Agent Profile", href="/pro/agents/profile"),
        NavLink(text="Agent Directory", href="/pro/agents"),
        NavLink(text="Find Expert", href="/pro/route"),
        NavLink(text="Delegation Inbox", href="/pro/delegations"),
        NavLink(text="Org Dashboard", href="/pro/org-dashboard"),
    ]


@pytest.fixture
def sample_exploration():
    """Exploration result with mixed outcomes."""
    return {
        "persona_id": 1,
        "persona_name": "Maria Gutierrez",
        "run_timestamp": "20260402_120000",
        "target_url": "http://localhost:3000",
        "objectives_attempted": 1,
        "objectives": [
            {
                "persona_id": "1",
                "persona_name": "Maria Gutierrez",
                "run_timestamp": "20260402_120000",
                "objective": "Retrieve Past Visa Strategy for Similar Case",
                "objective_trigger": "New client intake",
                "objective_success": "Found prior strategy in 30 seconds",
                "outcome": "partial",
                "pages_visited": ["http://localhost:3000/", "http://localhost:3000/pro/workspace"],
                "journey": [],
                "friction_points": [
                    {"type": "empty_state", "description": "Workspace page is empty",
                     "severity": "medium", "persona_quote": "Everything is empty."},
                ],
                "surprises": [],
                "missing_capabilities": [],
            },
        ],
    }


@pytest.fixture
def sample_backlog_item():
    """A realistic backlog item."""
    return BacklogItem(
        id="B-001",
        title="Bulk knowledge import",
        description="Users need to import existing knowledge from files",
        source="eval",
        score=78.0,
        finding_id="F-012",
        personas=[1, 34],
        pain_themes=["A", "F"],
        effort="large",
        status="open",
        acceptance_criteria=["Import from CSV", "Import from Google Drive"],
        persona_quotes=["I can't type 15 years of cases one by one"],
    )
