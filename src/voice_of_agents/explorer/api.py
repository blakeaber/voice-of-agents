"""API client for target application — data seeding and verification."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TargetAPI:
    """HTTP client for the target application's API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=15)
        self._session_token: str | None = None

    def health_check(self) -> bool:
        try:
            resp = self._client.get("/api/health")
            return resp.status_code == 200
        except Exception:
            return False

    def signup(self, email: str, org_name: str, display_name: str) -> dict:
        """Create a new user account. Returns user_id, org_id, api_key, session_token."""
        resp = self._client.post("/api/auth/signup", json={
            "email": email,
            "org_name": org_name,
            "display_name": display_name,
        })
        resp.raise_for_status()
        data = resp.json()
        self._session_token = data.get("session_token")
        return data

    def login(self, email: str, api_key: str) -> dict:
        """Login with email + API key. Returns session_token."""
        resp = self._client.post("/api/auth/login", json={
            "email": email,
            "api_key": api_key,
        })
        resp.raise_for_status()
        data = resp.json()
        self._session_token = data.get("session_token")
        return data

    def get_me(self) -> dict:
        """Get current user profile."""
        return self._authed_get("/api/auth/me")

    def save_onboarding_step(self, step: str, data: dict) -> dict:
        """Save an onboarding step (goals, provider, complete)."""
        return self._authed_post("/api/auth/onboarding", {"step": step, "data": data})

    def create_agent_profile(self, name: str, description: str, specializations: list[str],
                             agent_type: str = "personal") -> dict:
        """Publish an agent profile."""
        return self._authed_post("/api/org/agents", {
            "name": name,
            "description": description,
            "specializations": specializations,
            "agent_type": agent_type,
        })

    def create_learning(self, content: str, keywords: list[str]) -> dict:
        """Create a learning entry."""
        return self._authed_post("/api/org/learnings", {
            "content": content,
            "keywords": keywords,
        })

    def search_learnings(self, query: str) -> list[dict]:
        """Search learnings by query."""
        return self._authed_get(f"/api/learnings/search?q={query}")

    def list_agents(self) -> list[dict]:
        """List all agents in the org."""
        return self._authed_get("/api/org/agents")

    def route_task(self, description: str) -> dict:
        """Find best agent for a task description."""
        return self._authed_post("/api/org/agents/route", {"description": description})

    def _authed_get(self, path: str) -> dict | list:
        headers = {}
        if self._session_token:
            headers["Authorization"] = f"Bearer {self._session_token}"
        resp = self._client.get(path, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def _authed_post(self, path: str, data: dict) -> dict:
        headers = {}
        if self._session_token:
            headers["Authorization"] = f"Bearer {self._session_token}"
        resp = self._client.post(path, json=data, headers=headers)
        resp.raise_for_status()
        return resp.json()
