from __future__ import annotations

from pathlib import Path

import pandas as pd

from serialize import dataframe_preview
from session_cache import get_loaded_session
from sessions_catalog import get_session_by_id

CACHE_DIR = Path(__file__).resolve().parent / "f1_cache"
DEFAULT_SESSION_ID = "2024-monaco-r"
DEFAULT_DRIVER = "VER"


def _ensure_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def extract_drivers(results: pd.DataFrame) -> list[dict]:
    code_col = "Abbreviation" if "Abbreviation" in results.columns else None
    if code_col is None:
        return []

    drivers: list[dict] = []
    seen: set[str] = set()
    for _, row in results.iterrows():
        code = row.get(code_col)
        if pd.isna(code) or code in seen:
            continue
        seen.add(code)
        drivers.append(
            {
                "code": str(code),
                "name": str(row.get("BroadcastName") or row.get("FullName") or code),
                "team": str(row.get("TeamName") or ""),
            }
        )
    drivers.sort(key=lambda d: d["name"])
    return drivers


def _pick_driver(results: pd.DataFrame, laps: pd.DataFrame, driver: str | None) -> str:
    drivers = extract_drivers(results)
    codes = [d["code"] for d in drivers]
    if driver and driver in codes:
        return driver
    if DEFAULT_DRIVER in codes:
        return DEFAULT_DRIVER
    if codes:
        return codes[0]
    raise ValueError("No drivers found for this session")


def load_session_overview(
    year: int,
    location: str,
    session_type: str,
    driver: str | None = None,
    preview_rows: int = 25,
) -> dict:
    session = get_loaded_session(year, location, session_type)

    results = session.results
    laps = session.laps
    selected_driver = _pick_driver(results, laps, driver)
    drivers = extract_drivers(results)

    driver_results = results[results["Abbreviation"] == selected_driver]
    driver_laps = laps.pick_drivers(selected_driver)
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
        "drivers": drivers,
        "selectedDriver": selected_driver,
        "datasets": {
            "results": {
                "id": "results",
                "title": "Session Result",
                "description": f"Result row for {selected_driver} in this session.",
                "source": f"session.results[session.results['Abbreviation'] == '{selected_driver}']",
                **dataframe_preview(driver_results, preview_rows),
            },
            "laps": {
                "id": "laps",
                "title": "Lap Times",
                "description": f"Per-lap data for {selected_driver} (timing, sectors, compounds).",
                "source": f"session.laps.pick_drivers('{selected_driver}')",
                **dataframe_preview(driver_laps, preview_rows),
            },
            "telemetry": {
                "id": "telemetry",
                "title": "Telemetry",
                "description": (
                    f"Car telemetry from {selected_driver}'s fastest lap "
                    "(speed, throttle, brake, gear, track position)."
                ),
                "source": (
                    f"session.laps.pick_drivers('{selected_driver}')"
                    ".pick_fastest().get_telemetry()"
                ),
                **dataframe_preview(telemetry, preview_rows),
            },
        },
    }


def load_overview_by_session_id(
    session_id: str,
    driver: str | None = None,
    preview_rows: int = 25,
) -> dict:
    entry = get_session_by_id(session_id)
    if entry is None:
        raise ValueError(f"Unknown session id: {session_id}")
    overview = load_session_overview(
        year=entry["year"],
        location=entry["location"],
        session_type=entry["sessionType"],
        driver=driver,
        preview_rows=preview_rows,
    )
    overview["session"]["id"] = session_id
    return overview
