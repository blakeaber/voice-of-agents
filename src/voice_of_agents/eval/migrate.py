"""Migration script: UXW-format YAML → canonical Persona + CapabilityRegistry."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

import yaml

from voice_of_agents.core.capability import Capability, CapabilityRegistry, TestResult
from voice_of_agents.core.io import save_capability_registry, save_persona
from voice_of_agents.core.persona import Persona


def _severity_to_intensity(severity: int) -> str:
    if severity <= 4:
        return "LOW"
    if severity <= 6:
        return "MEDIUM"
    if severity <= 8:
        return "HIGH"
    return "CRITICAL"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def migrate_persona_yaml(path: Path) -> tuple[dict, list]:
    """Convert a UXW-format YAML file to canonical Persona dict + objectives list."""
    with open(path) as f:
        data = yaml.safe_load(f)

    legacy_id = str(data.get("id", "UXW-00"))
    m = re.search(r"\d+", legacy_id)
    id_int = int(m.group()) if m else 0

    org_size = data.get("team_size", data.get("org_size", 1))
    segment = "b2c" if org_size <= 1 else "b2b"

    raw_themes: dict[str, int] = {}
    new_pain_points = []
    for pp in data.get("pain_points", []):
        desc = pp.get("description", "")
        severity = pp.get("severity", 5)
        frequency = pp.get("frequency", "")
        theme = pp.get("theme", "")
        impact = f"severity {severity}/10"
        if frequency:
            impact += f", {frequency}"
        new_pain_points.append({"description": desc, "impact": impact, "current_workaround": None})
        if theme:
            raw_themes[theme] = max(raw_themes.get(theme, 0), severity)

    new_pain_themes = [
        {"theme": code, "intensity": _severity_to_intensity(sev)}
        for code, sev in raw_themes.items()
    ]

    old_voice = data.get("voice", {})
    canonical = {
        "id": id_int,
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "industry": data.get("industry", ""),
        "segment": segment,
        "tier": data.get("tier", "FREE"),
        "age": data.get("age"),
        "income": data.get("income"),
        "org_size": org_size,
        "experience_years": data.get("experience_years"),
        "ai_history": data.get("ai_history"),
        "mindset": data.get("mindset"),
        "pain_points": new_pain_points,
        "pain_themes": new_pain_themes,
        "unmet_need": data.get("unmet_need"),
        "proof_point": data.get("proof_point"),
        "trust_requirements": data.get("trust_requirements", []),
        "voice": {
            "skepticism": old_voice.get("skepticism", "moderate"),
            "vocabulary": old_voice.get("vocabulary", "general"),
            "motivation": old_voice.get("motivation", "efficiency"),
            "price_sensitivity": old_voice.get("price_sensitivity", "moderate"),
        },
        "metadata": {
            "source": "manual",
            "validation_status": "draft",
            "legacy_id": legacy_id,
        },
    }
    return canonical, data.get("objectives", [])


def migrate_objectives_to_workflow(persona_id: int, persona_name: str, objectives: list) -> dict:
    """Wrap legacy objectives as a PersonaWorkflowMapping YAML dict."""
    goals = []
    for i, obj in enumerate(objectives, 1):
        goals.append(
            {
                "id": f"G-{persona_id:02d}-{i}",
                "title": obj.get("goal", f"Goal {i}"),
                "category": "knowledge",
                "priority": "primary",
                "trigger": obj.get("trigger", ""),
                "success_statement": obj.get("success_definition", ""),
                "value_metrics": {
                    "time_saved": obj.get("efficiency_baseline", ""),
                    "error_reduction": "",
                    "cost_impact": "",
                },
                "workflows": [],
            }
        )
    return {
        "persona_id": persona_id,
        "persona_name": persona_name,
        "persona_tier": "FREE",
        "goals": goals,
        "feature_recommendations": [],
    }


def migrate_feature_inventory(path: Path) -> Optional[CapabilityRegistry]:
    """Convert a legacy feature-inventory.yaml to CapabilityRegistry."""
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)

    capabilities = []
    for feat in data.get("features", []):
        raw_id = feat.get("id", "unknown")
        parts = raw_id.upper().replace("-", "_").split("_")
        if len(parts) >= 2:
            cap_id = f"CAP-{parts[0]}-{'_'.join(parts[1:])}"
        else:
            cap_id = f"CAP-MISC-{raw_id.upper()}"

        status_map = {
            "implemented": "complete",
            "partial": "partial",
            "missing": "planned",
            "planned": "planned",
            "future": "future",
        }
        status = status_map.get(feat.get("status", "planned"), "planned")

        test_results = [
            TestResult(
                run_date=tr.get("run_date", ""),
                status=tr.get("status", "not_tested"),
                personas_tested=tr.get("personas_tested", []),
            )
            for tr in feat.get("test_results", [])
        ]

        pages = feat.get("pages", [])
        capabilities.append(
            Capability(
                id=cap_id,
                name=feat.get("name", raw_id),
                description=feat.get("description", ""),
                status=status,
                feature_area=feat.get("area", "General"),
                ui_page=pages[0] if pages else None,
                test_results=test_results,
                requested_by=feat.get("requested_by", []),
                first_reported=feat.get("first_reported"),
            )
        )

    return CapabilityRegistry(
        product=data.get("product", "unknown"),
        version="1.0.0",
        capabilities=capabilities,
    )


def migrate_all(
    personas_dir: Path,
    workflows_dir: Path,
    data_dir: Path,
    backup: bool = True,
) -> dict:
    """Run full migration: personas + feature inventory.

    Returns a results dict with lists of created paths and any errors.
    """
    legacy_dir = personas_dir / "_legacy"
    results: dict = {"personas": [], "workflows": [], "capabilities": None, "errors": []}

    for path in sorted(personas_dir.glob("UXW-*.yaml")):
        try:
            canonical_dict, objectives = migrate_persona_yaml(path)
            persona = Persona(**canonical_dict)

            if backup:
                legacy_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, legacy_dir / path.name)

            saved = save_persona(persona, personas_dir)
            results["personas"].append(str(saved))

            if objectives:
                workflows_dir.mkdir(parents=True, exist_ok=True)
                wf = migrate_objectives_to_workflow(persona.id, persona.name, objectives)
                wf_path = workflows_dir / f"PWM-{persona.id:02d}-{_slugify(persona.name)}.yaml"
                with open(wf_path, "w") as fh:
                    yaml.dump(wf, fh, default_flow_style=False, allow_unicode=True)
                results["workflows"].append(str(wf_path))

            path.unlink()
        except Exception as e:
            results["errors"].append(f"{path.name}: {e}")

    inventory_path = data_dir / "feature-inventory.yaml"
    registry = migrate_feature_inventory(inventory_path)
    if registry:
        cap_path = data_dir / "capabilities.yaml"
        save_capability_registry(registry, cap_path)
        results["capabilities"] = str(cap_path)
        if backup and inventory_path.exists():
            shutil.copy2(inventory_path, data_dir / "feature-inventory.yaml.bak")

    return results
