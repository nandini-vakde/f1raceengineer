"""Build full-session telemetry timeline for live replay."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_loader import DEFAULT_DRIVER, _pick_driver, extract_drivers
from session_cache import get_loaded_session
from sessions_catalog import get_session_by_id

CACHE_DIR = Path(__file__).resolve().parent / "f1_cache"
REPLAY_CACHE_DIR = CACHE_DIR / "replays"
MAX_POINTS = 12_000


def _replay_cache_path(session_id: str, driver: str) -> Path:
    safe = f"{session_id}_{driver}".replace("/", "-")
    return REPLAY_CACHE_DIR / f"{safe}.json"


def _driver_number(results: pd.DataFrame, abbreviation: str) -> str:
    rows = results.loc[results["Abbreviation"] == abbreviation, "DriverNumber"]
    if rows.empty:
        raise ValueError(f"Driver {abbreviation} not found in session results")
    return str(int(rows.iloc[0]))


def _series_to_points(
    df: pd.DataFrame,
    lap_markers: list[dict],
    total_laps: int,
    session_meta: dict,
    selected: str,
    driver_info: dict | None,
) -> dict:
    if df.empty:
        raise ValueError(f"No telemetry available for driver {selected}")

    points: list[dict] = []
    for row in df.itertuples(index=False):
        points.append(
            {
                "t": round(float(row.t), 3),
                "lap": int(row.LapNumber) if pd.notna(row.LapNumber) else None,
                "speed": None if pd.isna(row.Speed) else float(row.Speed),
                "rpm": None if pd.isna(row.RPM) else float(row.RPM),
                "throttle": None if pd.isna(row.Throttle) else float(row.Throttle),
                "brake": bool(row.Brake) if not pd.isna(row.Brake) else False,
                "gear": None if pd.isna(row.nGear) else int(row.nGear),
                "x": None if pd.isna(row.X) else float(row.X),
                "y": None if pd.isna(row.Y) else float(row.Y),
                "drs": None if pd.isna(row.DRS) else int(row.DRS),
            }
        )

    xs = [p["x"] for p in points if p["x"] is not None]
    ys = [p["y"] for p in points if p["y"] is not None]
    bounds = (
        {"minX": min(xs), "maxX": max(xs), "minY": min(ys), "maxY": max(ys)}
        if xs and ys
        else None
    )

    return {
        "session": session_meta,
        "driver": selected,
        "driverInfo": driver_info,
        "totalSeconds": round(float(df["t"].iloc[-1]), 3),
        "totalLaps": total_laps,
        "pointCount": len(points),
        "lapMarkers": lap_markers,
        "bounds": bounds,
        "points": points,
    }


def build_driver_replay(
    year: int,
    location: str,
    session_type: str,
    driver: str | None = None,
) -> dict:
    session = get_loaded_session(year, location, session_type)

    results = session.results
    laps = session.laps
    selected = _pick_driver(results, laps, driver)
    driver_info = next((d for d in extract_drivers(results) if d["code"] == selected), None)
    driver_number = _driver_number(results, selected)

    car = session.car_data[driver_number].copy()
    pos = session.pos_data[driver_number].copy()
    driver_laps = laps.pick_drivers(selected)

    car["t"] = car["SessionTime"].dt.total_seconds()
    pos["t"] = pos["SessionTime"].dt.total_seconds()

    car = car.sort_values("t").dropna(subset=["t"])
    pos = pos.sort_values("t").dropna(subset=["t", "X", "Y"])

    merged = pd.merge_asof(
        car,
        pos[["t", "X", "Y"]],
        on="t",
        direction="nearest",
        tolerance=0.15,
    )

    lap_times = driver_laps[["LapNumber", "LapStartTime"]].dropna().copy()
    lap_times["t"] = lap_times["LapStartTime"].dt.total_seconds()
    lap_times = lap_times.sort_values("t")

    merged = pd.merge_asof(
        merged,
        lap_times.rename(columns={"LapNumber": "LapNumber"}),
        on="t",
        direction="backward",
    )

    if len(merged) > MAX_POINTS:
        idx = np.linspace(0, len(merged) - 1, MAX_POINTS, dtype=int)
        merged = merged.iloc[idx]

    lap_markers = [
        {"lap": int(row.LapNumber), "t": round(float(row.t), 3)}
        for row in lap_times.itertuples(index=False)
    ]
    total_laps = (
        int(driver_laps["LapNumber"].max())
        if driver_laps["LapNumber"].notna().any()
        else len(lap_markers)
    )

    session_meta = {
        "year": year,
        "location": location,
        "sessionType": session_type,
        "name": session.name,
        "eventName": getattr(session.event, "EventName", location),
    }

    return _series_to_points(
        merged,
        lap_markers,
        total_laps,
        session_meta,
        selected,
        driver_info,
    )


def load_replay_by_session_id(session_id: str, driver: str | None = None) -> dict:
    entry = get_session_by_id(session_id)
    if entry is None:
        raise ValueError(f"Unknown session id: {session_id}")

    selected = driver or DEFAULT_DRIVER
    cache_path = _replay_cache_path(session_id, selected)
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["session"]["id"] = session_id
        return payload

    payload = build_driver_replay(
        year=entry["year"],
        location=entry["location"],
        session_type=entry["sessionType"],
        driver=selected,
    )
    payload["session"]["id"] = session_id

    REPLAY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    return payload
