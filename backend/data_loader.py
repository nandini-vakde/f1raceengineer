from __future__ import annotations

from pathlib import Path

import fastf1

from serialize import dataframe_preview

CACHE_DIR = Path(__file__).resolve().parent / "f1_cache"
DEFAULT_YEAR = 2024
DEFAULT_LOCATION = "Monaco"
DEFAULT_SESSION_TYPE = "R"
DEFAULT_DRIVER = "VER"


def _ensure_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session_overview(
    year: int = DEFAULT_YEAR,
    location: str = DEFAULT_LOCATION,
    session_type: str = DEFAULT_SESSION_TYPE,
    preview_rows: int = 25,
) -> dict:
    _ensure_cache()
    session = fastf1.get_session(year, location, session_type)
    session.load()

    results = session.results
    laps = session.laps

    driver_laps = laps.pick_driver(DEFAULT_DRIVER)
    fastest = driver_laps.pick_fastest()
    telemetry = fastest.get_telemetry()

    return {
        "session": {
            "year": year,
            "location": location,
            "sessionType": session_type,
            "name": session.name,
            "eventName": getattr(session.event, "EventName", location),
            "date": str(session.date) if session.date is not None else None,
        },
        "datasets": {
            "results": {
                "id": "results",
                "title": "Race Results",
                "description": "Finishing order, grid, points, and driver metadata for the session.",
                "source": "session.results",
                **dataframe_preview(results, preview_rows),
            },
            "laps": {
                "id": "laps",
                "title": "Lap Times",
                "description": "Per-lap timing, sectors, compounds, and stint data for all drivers.",
                "source": "session.laps",
                **dataframe_preview(laps, preview_rows),
            },
            "telemetry": {
                "id": "telemetry",
                "title": "Telemetry (sample)",
                "description": (
                    f"Car telemetry sampled from {DEFAULT_DRIVER}'s fastest lap "
                    "(speed, throttle, brake, gear, track position)."
                ),
                "source": f"session.laps.pick_driver('{DEFAULT_DRIVER}').pick_fastest().get_telemetry()",
                **dataframe_preview(telemetry, preview_rows),
            },
        },
    }
