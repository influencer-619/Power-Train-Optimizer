"""Schema init, versioning, backup-before-migrate, seed defaults."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from backend.database.session import SessionLocal, get_engine
from backend.logging_setup import setup_logging
from backend.models import db_models as m
from backend.paths import data_dir, db_path
from config.defaults import (
    DEFAULT_SCENARIOS,
    MODEL_VERSION,
    flatten_assumptions,
    get_default_config,
    recompute_calculated,
)

SCHEMA_VERSION = 1
log = setup_logging()


def _backup_db():
    path = db_path()
    if not path.exists():
        return None
    dest = data_dir() / "backups" / f"powertrain_pre_migrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    log.info("Database backup created at %s", dest)
    return dest


def _upsert_section(session, model, project_id: int, payload: dict):
    row = session.execute(select(model).where(model.project_id == project_id)).scalar_one_or_none()
    blob = json.dumps(payload)
    if row is None:
        session.add(model(project_id=project_id, payload_json=blob))
    else:
        row.payload_json = blob


def sync_project_sections(session, project_id: int, config: dict):
    mapping = [
        (m.LoadConfig, config["load"]),
        (m.SolarConfig, config["solar"]),
        (m.WindConfig, config["wind"]),
        (m.BessConfig, config["bess"]),
        (m.GridConfig, config["grid"]),
        (m.CommercialStructure, config["commercial"]),
        (m.ComplianceConfig, config["compliance"]),
        (m.FinancialConfig, config["financial"]),
    ]
    for model, payload in mapping:
        _upsert_section(session, model, project_id, payload)

    session.execute(delete(m.Assumption).where(m.Assumption.project_id == project_id))
    for row in flatten_assumptions(config):
        session.add(
            m.Assumption(
                project_id=project_id,
                parameter=row["parameter"],
                value_text=json.dumps(row["value"]),
                unit=row["unit"],
                source=row["source"],
                type=row["type"],
                description=row["description"],
                editable=row["editable"],
            )
        )


def seed_default_project(session):
    cfg = recompute_calculated(get_default_config())
    name = cfg["general"]["project_name"]["value"]
    description = (
        "DEFAULT ASSUMPTION — REPLACE WITH PROJECT DATA. Demonstration 250 MW data centre."
    )
    existing = session.execute(select(m.Project).where(m.Project.is_default.is_(True))).scalar_one_or_none()
    if existing:
        # Fast path: do not rewrite inputs on every launch (keeps startup quick).
        if existing.name != name:
            existing.name = name
            existing.description = description
        sc_count = session.execute(
            select(m.Scenario).where(m.Scenario.project_id == existing.id)
        ).scalars().first()
        if sc_count is None:
            for sc in DEFAULT_SCENARIOS:
                sc_cfg = recompute_calculated(get_default_config())
                sc_cfg["commercial"]["structure"]["value"] = sc["structure"]
                sc_cfg["compliance"]["annual_re_target_pct"]["value"] = sc["annual_re_target_pct"]
                sc_cfg["compliance"]["hourly_cfe_target_pct"]["value"] = sc["hourly_cfe_target_pct"]
                session.add(
                    m.Scenario(
                        project_id=existing.id,
                        name=sc["name"],
                        payload_json=json.dumps(sc_cfg),
                    )
                )
        return existing
    project = m.Project(
        name=name,
        description=description,
        is_default=True,
    )
    session.add(project)
    session.flush()
    session.add(
        m.ProjectInput(
            project_id=project.id,
            input_version=1,
            payload_json=json.dumps(cfg),
        )
    )
    sync_project_sections(session, project.id, cfg)
    for sc in DEFAULT_SCENARIOS:
        sc_cfg = recompute_calculated(get_default_config())
        sc_cfg["commercial"]["structure"]["value"] = sc["structure"]
        sc_cfg["compliance"]["annual_re_target_pct"]["value"] = sc["annual_re_target_pct"]
        sc_cfg["compliance"]["hourly_cfe_target_pct"]["value"] = sc["hourly_cfe_target_pct"]
        session.add(
            m.Scenario(
                project_id=project.id,
                name=sc["name"],
                payload_json=json.dumps(sc_cfg),
            )
        )
    log.info("Seeded default project id=%s", project.id)
    return project


_INITIALIZED = False


def initialize_database():
    global _INITIALIZED
    if _INITIALIZED:
        return
    engine = get_engine()
    path = db_path()
    first = not path.exists()
    m.Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        ver = session.get(m.SchemaMigration, SCHEMA_VERSION)
        needs_migrate = ver is None and not first
        if needs_migrate:
            session.close()
            _backup_db()
            session = SessionLocal()
            ver = session.get(m.SchemaMigration, SCHEMA_VERSION)
        if ver is None:
            session.add(m.SchemaMigration(version=SCHEMA_VERSION))
        mv = session.execute(select(m.ModelVersion).where(m.ModelVersion.version == MODEL_VERSION)).scalar_one_or_none()
        if mv is None:
            session.add(m.ModelVersion(version=MODEL_VERSION, notes="Initial release"))
        for key, value in {
            "currency": "INR",
            "theme": "industrial",
            "decimal_precision": 2,
            "model_version": MODEL_VERSION,
        }.items():
            row = session.get(m.ApplicationSetting, key)
            if row is None:
                session.add(m.ApplicationSetting(key=key, value_json=json.dumps(value)))
        seed_default_project(session)
        session.commit()
        log.info("Database initialized at %s (first_launch=%s)", path, first)
        _INITIALIZED = True
    finally:
        session.close()
