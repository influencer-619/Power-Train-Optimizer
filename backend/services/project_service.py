"""Project CRUD, inputs, scenarios, backup/restore."""

from __future__ import annotations

import json
import re
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from backend.database.init_db import sync_project_sections
from backend.database.session import SessionLocal
from backend.models import db_models as m
from backend.paths import data_dir
from config.defaults import (
    MODEL_VERSION,
    flatten_assumptions,
    get_default_config,
    has_default_assumptions,
    recompute_calculated,
)


def _sanitize_name(name: str) -> str:
    name = (name or "").strip() or "Untitled Project"
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return name[:200]


def list_projects() -> list[dict]:
    session = SessionLocal()
    try:
        rows = session.execute(select(m.Project).order_by(m.Project.id)).scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_default": r.is_default,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


def get_project(project_id: int) -> dict:
    session = SessionLocal()
    try:
        p = session.get(m.Project, project_id)
        if not p:
            raise KeyError(f"Project {project_id} not found")
        inp = session.execute(select(m.ProjectInput).where(m.ProjectInput.project_id == project_id)).scalar_one()
        config = json.loads(inp.payload_json)
        return {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "is_default": p.is_default,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
            "input_version": inp.input_version,
            "config": config,
            "has_default_assumptions": has_default_assumptions(config),
            "model_version": MODEL_VERSION,
            "assumptions": flatten_assumptions(config),
        }
    finally:
        session.close()


def create_project(name: str | None = None, from_defaults: bool = True, clone_id: int | None = None) -> dict:
    session = SessionLocal()
    try:
        if clone_id is not None:
            src = get_project(clone_id)
            cfg = deepcopy(src["config"])
            pname = name or f"{src['name']} (copy)"
        else:
            cfg = recompute_calculated(get_default_config())
            pname = name or cfg["general"]["project_name"]["value"]
            if not from_defaults:
                cfg["general"]["project_name"]["value"] = _sanitize_name(pname)
        pname = _sanitize_name(pname)
        cfg["general"]["project_name"]["value"] = pname
        recompute_calculated(cfg)
        p = m.Project(name=pname, description="", is_default=False)
        session.add(p)
        session.flush()
        session.add(m.ProjectInput(project_id=p.id, input_version=1, payload_json=json.dumps(cfg)))
        sync_project_sections(session, p.id, cfg)
        session.commit()
        return get_project(p.id)
    finally:
        session.close()


def update_project_meta(project_id: int, name: str | None = None, description: str | None = None) -> dict:
    session = SessionLocal()
    try:
        p = session.get(m.Project, project_id)
        if not p:
            raise KeyError(f"Project {project_id} not found")
        if name is not None:
            p.name = _sanitize_name(name)
        if description is not None:
            p.description = description
        p.updated_at = datetime.utcnow()
        session.commit()
        return get_project(project_id)
    finally:
        session.close()


def update_inputs(project_id: int, config: dict) -> dict:
    session = SessionLocal()
    try:
        p = session.get(m.Project, project_id)
        if not p:
            raise KeyError(f"Project {project_id} not found")
        cfg = recompute_calculated(deepcopy(config))
        inp = session.execute(select(m.ProjectInput).where(m.ProjectInput.project_id == project_id)).scalar_one()
        inp.payload_json = json.dumps(cfg)
        inp.input_version += 1
        inp.updated_at = datetime.utcnow()
        p.name = _sanitize_name(str(cfg["general"]["project_name"]["value"]))
        p.updated_at = datetime.utcnow()
        sync_project_sections(session, project_id, cfg)
        session.commit()
        return get_project(project_id)
    finally:
        session.close()


def delete_project(project_id: int) -> None:
    session = SessionLocal()
    try:
        p = session.get(m.Project, project_id)
        if not p:
            raise KeyError(f"Project {project_id} not found")
        if p.is_default:
            raise ValueError("Cannot delete the seeded default project. Duplicate it instead.")
        for model in (
            m.Assumption,
            m.LoadConfig,
            m.SolarConfig,
            m.WindConfig,
            m.BessConfig,
            m.GridConfig,
            m.CommercialStructure,
            m.ComplianceConfig,
            m.FinancialConfig,
            m.Scenario,
            m.ProjectInput,
        ):
            session.execute(delete(model).where(model.project_id == project_id))
        session.delete(p)
        session.commit()
    finally:
        session.close()


def list_scenarios(project_id: int) -> list[dict]:
    session = SessionLocal()
    try:
        rows = session.execute(select(m.Scenario).where(m.Scenario.project_id == project_id)).scalars().all()
        return [
            {"id": r.id, "project_id": r.project_id, "name": r.name, "updated_at": r.updated_at.isoformat()}
            for r in rows
        ]
    finally:
        session.close()


def get_scenario(scenario_id: int) -> dict:
    session = SessionLocal()
    try:
        r = session.get(m.Scenario, scenario_id)
        if not r:
            raise KeyError("Scenario not found")
        return {
            "id": r.id,
            "project_id": r.project_id,
            "name": r.name,
            "config": json.loads(r.payload_json),
            "updated_at": r.updated_at.isoformat(),
        }
    finally:
        session.close()


def save_scenario(project_id: int, name: str, config: dict, scenario_id: int | None = None) -> dict:
    session = SessionLocal()
    try:
        cfg = recompute_calculated(deepcopy(config))
        if scenario_id:
            r = session.get(m.Scenario, scenario_id)
            if not r or r.project_id != project_id:
                raise KeyError("Scenario not found")
            r.name = _sanitize_name(name)
            r.payload_json = json.dumps(cfg)
            r.updated_at = datetime.utcnow()
            session.commit()
            return get_scenario(r.id)
        r = m.Scenario(project_id=project_id, name=_sanitize_name(name), payload_json=json.dumps(cfg))
        session.add(r)
        session.commit()
        return get_scenario(r.id)
    finally:
        session.close()


def delete_scenario(scenario_id: int) -> None:
    session = SessionLocal()
    try:
        r = session.get(m.Scenario, scenario_id)
        if not r:
            raise KeyError("Scenario not found")
        session.delete(r)
        session.commit()
    finally:
        session.close()


def backup_project(project_id: int) -> Path:
    proj = get_project(project_id)
    scenarios = [get_scenario(s["id"]) for s in list_scenarios(project_id)]
    package = {
        "model_version": MODEL_VERSION,
        "project": proj,
        "scenarios": scenarios,
        "exported_at": datetime.utcnow().isoformat(),
    }
    out = data_dir() / "exports" / f"project_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pto.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(package, indent=2))
    return out


def restore_project(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path, "r") as zf:
        package = json.loads(zf.read("project.json"))
    name = package["project"]["name"] + " (restored)"
    created = create_project(name=name, from_defaults=False)
    update_inputs(created["id"], package["project"]["config"])
    for sc in package.get("scenarios", []):
        save_scenario(created["id"], sc["name"], sc["config"])
    return get_project(created["id"])
