"""Shared test fixtures for Voice of Agents."""

import pytest

from voice_of_agents.config import VoAConfig
from voice_of_agents.contracts.personas import Persona, Objective, PainPoint, Voice
from voice_of_agents.contracts.backlog import BacklogItem
from voice_of_agents.contracts.inventory import Feature, FeatureInventory, TestResult
from voice_of_agents.explorer.browser import NavLink


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
        id="UXW-01",
        name="Maria Gutierrez",
        role="Immigration Paralegal",
        industry="Legal",
        experience_years=15,
        income=52000,
        team_size=1,
        tier="DEVELOPER",
        objectives=[
            Objective(
                id="OBJ-01",
                goal="Retrieve Past Visa Strategy for Similar Case",
                trigger="New client intake with a case type handled before",
                success_definition="Found prior petition strategy in under 60 seconds",
                efficiency_baseline="45 min searching Google Drive",
                target_efficiency="30 seconds via search",
            ),
            Objective(
                id="OBJ-02",
                goal="Capture New USCIS Requirement Change as Learning",
                trigger="Unexpected RFE reveals a policy change",
                success_definition="Policy change auto-surfaces on future similar cases",
                efficiency_baseline="Sticky note, lost in 2 weeks",
            ),
        ],
        pain_points=[
            PainPoint(description="800 files in Google Drive, can't find anything", severity=9, frequency="daily", theme="A"),
            PainPoint(description="Policy changes discovered via rejections", severity=8, frequency="monthly", theme="D"),
        ],
        trust_requirements=["Must surface MY prior work, not generic AI answers"],
        voice=Voice(skepticism="high", vocabulary="legal", motivation="fear", price_sensitivity="moderate"),
    )


@pytest.fixture
def rachel():
    """Rachel Okafor — Dir People Ops (B2B team, TEAM tier)."""
    return Persona(
        id="UXW-20",
        name="Rachel Okafor",
        role="Director of People Operations",
        industry="HR",
        experience_years=12,
        income=130000,
        team_size=8,
        tier="TEAM",
        objectives=[
            Objective(
                id="OBJ-01",
                goal="Create HR Policy Domain Agent to Deflect Manager Questions",
                trigger="15th Slack DM today asking about PTO carryover",
                success_definition="Manager DMs drop from 20/day to 5/day",
                efficiency_baseline="2 hours/day answering DMs",
                target_efficiency="30 min reviewing escalations",
            ),
        ],
        pain_points=[
            PainPoint(description="20+ policy questions daily from managers", severity=9, theme="B"),
        ],
        trust_requirements=["Only answer approved policies, never fabricate"],
        voice=Voice(skepticism="moderate", vocabulary="general", motivation="efficiency", price_sensitivity="low"),
    )


@pytest.fixture
def james():
    """James Washington — small business bookkeeper (FREE, skeptical)."""
    return Persona(
        id="UXW-04",
        name="James Washington",
        role="Small Business Bookkeeper",
        industry="Finance",
        experience_years=25,
        income=45000,
        team_size=1,
        tier="FREE",
        objectives=[
            Objective(
                id="OBJ-01",
                goal="Retrieve past categorization decision",
                trigger="Categorizing an expense similar to one handled 3 months ago",
                success_definition="Prior decision surfaces with rationale in under 30 seconds",
                efficiency_baseline="15 min searching QuickBooks + phone call",
            ),
        ],
        pain_points=[
            PainPoint(description="Categorization errors repeat every quarter", severity=7, theme="A"),
        ],
        trust_requirements=["Wants HIS reasoning, not AI opinions"],
        voice=Voice(skepticism="high", vocabulary="financial", motivation="fear", price_sensitivity="high"),
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
        "persona_id": "UXW-01",
        "persona_name": "Maria Gutierrez",
        "run_timestamp": "20260402_120000",
        "target_url": "http://localhost:3000",
        "objectives_attempted": 2,
        "objectives": [
            {
                "persona_id": "UXW-01",
                "persona_name": "Maria Gutierrez",
                "run_timestamp": "20260402_120000",
                "objective": "Retrieve Past Visa Strategy for Similar Case",
                "objective_trigger": "New client intake",
                "objective_success": "Found prior strategy in 30 seconds",
                "outcome": "partial",
                "pages_visited": ["http://localhost:3000/", "http://localhost:3000/pro/workspace"],
                "journey": [
                    {"action": "Open http://localhost:3000", "observation": "Landed on /pro/workspace",
                     "reaction": "Good, workspace loaded.", "page_url": "http://localhost:3000/pro/workspace",
                     "latency_ms": 800},
                    {"action": "Navigate to 'Workspace'", "observation": "Headings: ['Workspace']. Input fields: ['e.g. H-1B visa petition']. Empty state: 'No learnings yet'",
                     "reaction": "It's empty.", "page_url": "http://localhost:3000/pro/workspace",
                     "latency_ms": 500},
                    {"action": "Type 'H-1B petition for data scientist'", "observation": "After typing: still empty sidebar",
                     "reaction": "Nothing came back.", "page_url": "http://localhost:3000/pro/workspace",
                     "latency_ms": 2100},
                ],
                "friction_points": [
                    {"type": "empty_state", "description": "Workspace page is empty — No learnings yet",
                     "severity": "medium", "persona_quote": "Everything is empty."},
                ],
                "surprises": [],
                "missing_capabilities": [],
            },
            {
                "persona_id": "UXW-01",
                "persona_name": "Maria Gutierrez",
                "run_timestamp": "20260402_120000",
                "objective": "Capture New USCIS Requirement Change",
                "objective_trigger": "Unexpected RFE reveals policy change",
                "objective_success": "Policy change auto-surfaces on future cases",
                "outcome": "blocked",
                "pages_visited": ["http://localhost:3000/"],
                "journey": [
                    {"action": "Open http://localhost:3000", "observation": "Landed on /",
                     "reaction": "Main page.", "page_url": "http://localhost:3000/",
                     "latency_ms": 600},
                ],
                "friction_points": [
                    {"type": "gap", "description": "No sidebar link matches objective",
                     "severity": "high", "persona_quote": "I can't find where to capture learnings."},
                ],
                "surprises": [],
                "missing_capabilities": ["Direct navigation for learning capture"],
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
        score=78.0,
        finding_id="F-012",
        personas=["UXW-01", "UXW-34"],
        pain_themes=["A", "F"],
        effort="large",
        status="open",
        acceptance_criteria=["Import from CSV", "Import from Google Drive"],
        persona_quotes=[{"persona": "UXW-01", "quote": "I can't type 15 years of cases one by one"}],
        type="new_feature",
    )
