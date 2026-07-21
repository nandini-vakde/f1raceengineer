from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import OPENF1_BASE_URL
from data_loader import DEFAULT_SESSION_ID, load_overview_by_session_id
from openf1_client import OpenF1Error
from race_simulation import DEFAULT_RACE_SESSION_ID, load_race_simulation_by_session_id
from race_timeline import simulate_branch
from telemetry_replay import load_replay_by_session_id

app = FastAPI(title="F1 Race Engineer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PitDecision(BaseModel):
    driver: str = Field(..., min_length=1, description="Driver code, e.g. VER")
    pitLap: int = Field(..., ge=1, description="Lap number to pit")
    compound: str = Field("HARD", description="Tyre compound after the stop")
    pitLoss: float | None = Field(None, description="Optional pit time loss override (seconds)")


class BranchRequest(BaseModel):
    session_id: str = DEFAULT_RACE_SESSION_ID
    decisions: list[PitDecision]


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


@app.post("/api/race/branch")
def race_branch(body: BranchRequest) -> dict:
    """Apply player pit decisions and physics-simulate the new timeline."""
    try:
        historical = load_race_simulation_by_session_id(session_id=body.session_id)
        decisions = [d.model_dump() for d in body.decisions]
        return simulate_branch(historical, decisions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to branch race timeline: {exc}",
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


def _ensure_ai():
    """Lazy-load AI stack so race simulation works without GenAI deps."""
    from ai.engineer import RaceEngineer
    from ai.memory import EngineerMemory
    from ai.personalities import get_personality, list_personalities
    from analytics.event_detector import EventDetector
    from analytics.feature_builder import FeatureBuilder

    if not hasattr(_ensure_ai, "_ready"):
        _ensure_ai.engineer = RaceEngineer()
        _ensure_ai.feature_builder = FeatureBuilder()
        _ensure_ai.event_detector = EventDetector()
        _ensure_ai.memories = {}
        _ensure_ai.get_personality = get_personality
        _ensure_ai.list_personalities = list_personalities
        _ensure_ai.EngineerMemory = EngineerMemory
        _ensure_ai._ready = True
    return _ensure_ai


@app.get("/api/personalities")
def personalities() -> dict:
    try:
        ai = _ensure_ai()
        return {"personalities": ai.list_personalities()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI module unavailable: {exc}") from exc


@app.get("/api/engineer")
def engineer_message(
    session_id: str = Query(DEFAULT_SESSION_ID, min_length=1),
    driver: str | None = Query(None, min_length=1),
    point_index: int = Query(..., ge=0),
    personality: str | None = Query(None, min_length=1),
) -> dict:
    try:
        ai = _ensure_ai()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI module unavailable: {exc}") from exc

    try:
        replay = load_replay_by_session_id(session_id=session_id, driver=driver)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load replay for engineer: {exc}",
        ) from exc

    points = replay["points"]
    if point_index >= len(points):
        raise HTTPException(
            status_code=400,
            detail=f"point_index must be less than {len(points)}",
        )

    resolved_driver = driver or replay.get("driver", "VER")
    point = points[point_index]
    features = ai.feature_builder.build(point)
    events = ai.event_detector.detect(features)
    key = f"{session_id}:{resolved_driver}"
    if key not in ai.memories:
        ai.memories[key] = ai.EngineerMemory()
    memory = ai.memories[key]

    if not events or not memory.should_generate(events):
        return {"message": None, "events": events, "skipped": True}

    try:
        personality_obj = ai.get_personality(personality)
        message = ai.engineer.process(point, events=events, personality=personality_obj)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Engineer LLM failed: {exc}",
        ) from exc

    return {"message": message, "events": events, "skipped": False}
