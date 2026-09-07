"""FastAPI application factory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.database.init_db import initialize_database
from backend.logging_setup import setup_logging
from backend.paths import data_dir, frontend_dir
from backend.reports import export_excel, export_pdf
from backend.services import project_service as ps
from backend.services import run_service as rs
from config.defaults import (
    APPLICABILITY_BANNER,
    DISCLAIMER,
    MODEL_VERSION,
    PRESET_CFE_TARGETS,
    PRESET_RE_TARGETS,
    get_default_config,
    recompute_calculated,
)

log = setup_logging()


class ProjectCreate(BaseModel):
    name: str | None = None
    from_defaults: bool = True
    clone_id: int | None = None


class ProjectMetaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class InputsUpdate(BaseModel):
    config: dict[str, Any]


class SimulationRequest(BaseModel):
    project_id: int
    structure: str | None = None
    scenario_id: int | None = None


class ScenarioBody(BaseModel):
    project_id: int
    name: str
    config: dict[str, Any]
    scenario_id: int | None = None


class SensitivityBody(BaseModel):
    project_id: int
    parameters: list[str] | None = None


class ReportBody(BaseModel):
    project_id: int
    simulation_id: int | None = None


def create_app(init_db: bool = True) -> FastAPI:
    if init_db:
        initialize_database()
    app = FastAPI(title="PowerTrain Optimizer", version=MODEL_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model_version": MODEL_VERSION}

    @app.post("/api/heartbeat")
    def heartbeat():
        fn = getattr(app.state, "launcher_note_heartbeat", None)
        if callable(fn):
            fn()
        return {"ok": True}

    @app.post("/api/shutdown")
    def shutdown():
        fn = getattr(app.state, "launcher_request_shutdown", None)
        if callable(fn):
            fn()
        return {"ok": True, "message": "Shutting down"}

    @app.get("/api/defaults")
    def defaults():
        return {
            "config": recompute_calculated(get_default_config()),
            "preset_re_targets": PRESET_RE_TARGETS,
            "preset_cfe_targets": PRESET_CFE_TARGETS,
            "disclaimer": DISCLAIMER,
            "applicability_banner": APPLICABILITY_BANNER,
            "model_version": MODEL_VERSION,
        }

    @app.get("/api/projects")
    def projects():
        return ps.list_projects()

    @app.post("/api/projects")
    def create_project(body: ProjectCreate):
        return ps.create_project(name=body.name, from_defaults=body.from_defaults, clone_id=body.clone_id)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: int):
        try:
            return ps.get_project(project_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.put("/api/projects/{project_id}")
    def put_project(project_id: int, body: ProjectMetaUpdate):
        try:
            return ps.update_project_meta(project_id, body.name, body.description)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: int):
        try:
            ps.delete_project(project_id)
            return {"ok": True}
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/projects/{project_id}/inputs")
    def get_inputs(project_id: int):
        return ps.get_project(project_id)

    @app.put("/api/projects/{project_id}/inputs")
    def put_inputs(project_id: int, body: InputsUpdate):
        try:
            return ps.update_inputs(project_id, body.config)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/simulation/run")
    def sim_run(body: SimulationRequest):
        try:
            return rs.run_project_simulation(body.project_id, structure=body.structure, scenario_id=body.scenario_id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Simulation failed")
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/simulation/{run_id}")
    def sim_get(run_id: int):
        try:
            return rs.get_simulation(run_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/simulation/{run_id}/series")
    def sim_series(run_id: int, view: str = "year", month: int = 1, day: int = 1):
        try:
            return rs.get_series(run_id, view=view, month=month, day=day)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/simulation/{run_id}/ledger")
    def sim_ledger(run_id: int):
        try:
            return rs.get_energy_ledger(run_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/projects/{project_id}/profiles")
    def profiles_list(project_id: int):
        try:
            return rs.list_profiles(project_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/projects/{project_id}/profiles/{kind}")
    async def profiles_upload(project_id: int, kind: str, file: UploadFile = File(...)):
        if kind not in ("load", "solar", "wind"):
            raise HTTPException(400, "kind must be load, solar, or wind")
        text = (await file.read()).decode("utf-8", errors="replace")
        try:
            result = rs.upload_profile(project_id, kind, text)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, str(exc)) from exc
        if not result.get("ok"):
            raise HTTPException(400, result)
        return result

    @app.delete("/api/projects/{project_id}/profiles/{kind}")
    def profiles_clear(project_id: int, kind: str):
        if kind not in ("load", "solar", "wind"):
            raise HTTPException(400, "kind must be load, solar, or wind")
        try:
            return rs.clear_profile(project_id, kind)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/analysis/marginal")
    def marginal(body: dict = Body(...)):
        try:
            return rs.run_marginal_analysis(int(body["project_id"]))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/optimization/run")
    def opt_run(body: dict = Body(...)):
        project_id = int(body.get("project_id"))
        return {"id": rs.start_optimization(project_id)}

    @app.get("/api/optimization/{run_id}")
    def opt_get(run_id: int):
        try:
            return rs.get_optimization(run_id)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e

    @app.post("/api/optimization/{run_id}/cancel")
    def opt_cancel(run_id: int):
        rs.cancel_optimization(run_id)
        return {"ok": True}

    @app.get("/api/scenarios")
    def scenarios(project_id: int = Query(...)):
        return ps.list_scenarios(project_id)

    @app.post("/api/scenarios")
    def scenario_save(body: ScenarioBody):
        return ps.save_scenario(body.project_id, body.name, body.config, body.scenario_id)

    @app.get("/api/scenarios/{scenario_id}")
    def scenario_get(scenario_id: int):
        try:
            return ps.get_scenario(scenario_id)
        except KeyError as e:
            raise HTTPException(404, str(e)) from e

    @app.put("/api/scenarios/{scenario_id}")
    def scenario_put(scenario_id: int, body: ScenarioBody):
        return ps.save_scenario(body.project_id, body.name, body.config, scenario_id)

    @app.delete("/api/scenarios/{scenario_id}")
    def scenario_del(scenario_id: int):
        try:
            ps.delete_scenario(scenario_id)
            return {"ok": True}
        except KeyError as e:
            raise HTTPException(404, str(e)) from e

    @app.post("/api/sensitivity/run")
    def sensitivity(body: SensitivityBody):
        return rs.run_sensitivity(body.project_id, body.parameters)

    @app.post("/api/compare/architectures")
    def compare(body: dict = Body(...)):
        return rs.compare_architectures(int(body["project_id"]))

    @app.get("/api/results/{run_id}")
    def results(run_id: int):
        return rs.get_simulation(run_id)

    @app.post("/api/reports/excel")
    def report_excel(body: ReportBody):
        path = export_excel(body.project_id, body.simulation_id)
        return FileResponse(path, filename=path.name)

    @app.post("/api/reports/pdf")
    def report_pdf(body: ReportBody):
        path = export_pdf(body.project_id, body.simulation_id)
        return FileResponse(path, filename=path.name)

    @app.post("/api/projects/{project_id}/backup")
    def backup(project_id: int):
        path = ps.backup_project(project_id)
        return FileResponse(path, filename=path.name)

    @app.post("/api/projects/restore")
    async def restore(file: UploadFile = File(...)):
        dest = data_dir() / "exports" / (file.filename or "restore.pto.zip")
        dest.write_bytes(await file.read())
        return ps.restore_project(dest)

    @app.get("/api/settings")
    def settings():
        from sqlalchemy import select

        from backend.database.session import SessionLocal
        from backend.models import db_models as m

        session = SessionLocal()
        try:
            rows = session.execute(select(m.ApplicationSetting)).scalars().all()
            stored = {r.key: json.loads(r.value_json) for r in rows}
        finally:
            session.close()
        runtime = getattr(app.state, "runtime_info", None) or {}
        return {
            **stored,
            "runtime": runtime,
            "model_version": MODEL_VERSION,
        }

    @app.get("/api/runtime")
    def runtime():
        """Local + LAN URLs for sharing the running app on the office network."""
        info = getattr(app.state, "runtime_info", None)
        if not info:
            try:
                from backend.launcher import get_runtime_info

                info = get_runtime_info()
            except Exception:
                info = {}
        return info or {
            "host": "unknown",
            "port": None,
            "local_url": "/",
            "lan_urls": [],
            "lan_share": False,
            "keep_alive": False,
        }

    # Static frontend
    fe = frontend_dir()
    if (fe / "index.html").exists():
        assets = fe / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

        @app.get("/")
        def index():
            return FileResponse(fe / "index.html")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(404)
            candidate = fe / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(fe / "index.html")

    return app


app = create_app()
