from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from data_loader import DEFAULT_SESSION_ID, load_overview_by_session_id
from sessions_catalog import list_sessions
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
    return {"status": "ok"}


@app.get("/api/sessions")
def sessions() -> dict:
    return {"sessions": list_sessions()}


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
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session data: {exc}",
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
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build telemetry replay: {exc}",
        ) from exc
