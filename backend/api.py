from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import OPENF1_BASE_URL
from data_loader import DEFAULT_SESSION_ID, load_overview_by_session_id
from openf1_client import OpenF1Error
from race_simulation import DEFAULT_RACE_SESSION_ID, load_race_simulation_by_session_id
from telemetry_replay import load_replay_by_session_id

app = FastAPI(title="F1 Race Engineer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "dataSource": "openf1", "openf1BaseUrl": OPENF1_BASE_URL}


@app.get("/api/sessions")
def sessions() -> dict:
    from openf1_sessions import _list_sessions_catalog_cached, list_sessions_catalog

    catalog = list_sessions_catalog()
    if not catalog:
        _list_sessions_catalog_cached.cache_clear()
        catalog = list_sessions_catalog()
    return {"sessions": catalog}


@app.get("/api/overview")
def overview(
    session_id: str = Query(DEFAULT_SESSION_ID, min_length=1),
    driver: str | None = Query(None, min_length=1),
    preview_rows: int = Query(25, ge=5, le=100),
) -> dict:
    try:
        return load_overview_by_session_id(
            session_id=session_id,
            driver=driver,
            preview_rows=preview_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session data: {exc}",
        ) from exc


@app.get("/api/race/simulation")
def race_simulation(
    session_id: str = Query(DEFAULT_RACE_SESSION_ID, min_length=1),
) -> dict:
    try:
        return load_race_simulation_by_session_id(session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build race simulation: {exc}",
        ) from exc


@app.get("/api/telemetry/replay")
def telemetry_replay(
    session_id: str = Query(DEFAULT_SESSION_ID, min_length=1),
    driver: str | None = Query(None, min_length=1),
) -> dict:
    try:
        return load_replay_by_session_id(session_id=session_id, driver=driver)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build telemetry replay: {exc}",
        ) from exc
