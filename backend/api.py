from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from data_loader import (
    DEFAULT_LOCATION,
    DEFAULT_SESSION_TYPE,
    DEFAULT_YEAR,
    load_session_overview,
)

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


@app.get("/api/overview")
def overview(
    year: int = Query(DEFAULT_YEAR, ge=2018, le=2030),
    location: str = Query(DEFAULT_LOCATION, min_length=1),
    session_type: str = Query(DEFAULT_SESSION_TYPE, min_length=1),
    preview_rows: int = Query(25, ge=5, le=100),
) -> dict:
    try:
        return load_session_overview(
            year=year,
            location=location,
            session_type=session_type,
            preview_rows=preview_rows,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load session data: {exc}",
        ) from exc
