from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import OPENF1_BASE_URL
from data_loader import DEFAULT_SESSION_ID, load_overview_by_session_id
from openf1_client import OpenF1Error
from sessions_catalog import list_sessions
from telemetry_replay import load_replay_by_session_id

from ai.engineer import RaceEngineer
from ai.memory import EngineerMemory
from analytics.event_detector import EventDetector
from analytics.feature_builder import FeatureBuilder
from ai.personalities import get_personality, list_personalities

engineer = RaceEngineer()
feature_builder = FeatureBuilder()
event_detector = EventDetector()
engineer_memories: dict[str, EngineerMemory] = {}


def _get_engineer_memory(session_id: str, driver: str) -> EngineerMemory:
    key = f"{session_id}:{driver}"
    if key not in engineer_memories:
        engineer_memories[key] = EngineerMemory()
    return engineer_memories[key]

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
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
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
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build telemetry replay: {exc}",
        ) from exc


@app.get("/api/personalities")
def personalities() -> dict:
    return {"personalities": list_personalities()}


@app.get("/api/engineer")
def engineer_message(
    session_id: str = Query(DEFAULT_SESSION_ID, min_length=1),
    driver: str | None = Query(None, min_length=1),
    point_index: int = Query(..., ge=0),
    personality: str | None = Query(None, min_length=1),
) -> dict:
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
    features = feature_builder.build(point)
    events = event_detector.detect(features)
    memory = _get_engineer_memory(session_id, resolved_driver)

    if not events or not memory.should_generate(events):
        return {"message": None, "events": events, "skipped": True}

    try:
        personality_obj = get_personality(personality)
        message = engineer.process(point, events=events, personality=personality_obj)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Engineer LLM failed: {exc}",
        ) from exc

    return {"message": message, "events": events, "skipped": False}