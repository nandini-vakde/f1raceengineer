"""Build full-session telemetry timeline from OpenF1 car_data + location."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from config import CACHE_DIR
from data_loader import DEFAULT_DRIVER, _driver_number_for_code, _drivers_for_session
from openf1_client import fetch
from openf1_sessions import get_session_by_id

REPLAY_CACHE_DIR = Path(CACHE_DIR) / "replays"
MAX_POINTS = 12_000
REPLAY_SCHEMA_VERSION = 2


def _replay_cache_path(session_id: str, driver: str) -> Path:
    safe = f"{session_id}_{driver}".replace("/", "-")
    return REPLAY_CACHE_DIR / f"{safe}_v{REPLAY_SCHEMA_VERSION}.json"


def _to_session_seconds(date_str: str, session_start: datetime) -> float:
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    start = session_start if session_start.tzinfo else session_start.replace(tzinfo=timezone.utc)
    return (dt - start).total_seconds()


def _build_track_outline(loc_df: pd.DataFrame, limit: int = 3_000) -> list[dict]:
    if loc_df.empty:
        return []
    outline = loc_df.dropna(subset=["x", "y"]).copy()
    outline = outline[(outline["x"].abs() > 1) | (outline["y"].abs() > 1)]
    if outline.empty:
        return []
    if len(outline) > limit:
        idx = np.linspace(0, len(outline) - 1, limit, dtype=int)
        outline = outline.iloc[idx]
    return [{"x": float(row.x), "y": float(row.y)} for row in outline.itertuples(index=False)]


def _trim_to_race_start(
    merged: pd.DataFrame,
    lap_markers: list[dict],
) -> tuple[pd.DataFrame, list[dict]]:
    if merged.empty:
        return merged, lap_markers
    if lap_markers:
        race_start = float(lap_markers[0]["t"]) - 5.0
    else:
        moving = merged[(merged["speed"].fillna(0) > 20) & merged["x"].notna()]
        race_start = float(moving["t"].iloc[0]) if not moving.empty else float(merged["t"].iloc[0])
    trimmed = merged[merged["t"] >= race_start].copy()
    if trimmed.empty:
        return merged, lap_markers
    t0 = float(trimmed["t"].iloc[0])
    trimmed["t"] = trimmed["t"] - t0
    rebased_markers = [
        {"lap": marker["lap"], "t": round(float(marker["t"]) - t0, 3)}
        for marker in lap_markers
        if float(marker["t"]) >= race_start
    ]
    return trimmed, rebased_markers


def _series_to_points(
    df: pd.DataFrame,
    lap_markers: list[dict],
    total_laps: int,
    session_meta: dict,
    selected: str,
    driver_info: dict | None,
    track_outline: list[dict] | None = None,
) -> dict:
    if df.empty:
        raise ValueError(f"No telemetry available for driver {selected}")

    points: list[dict] = []
    for row in df.itertuples(index=False):
        points.append(
            {
                "t": round(float(row.t), 3),
                "lap": int(row.lap) if pd.notna(getattr(row, "lap", None)) else None,
                "speed": None if pd.isna(row.speed) else float(row.speed),
                "rpm": None if pd.isna(row.rpm) else float(row.rpm),
                "throttle": None if pd.isna(row.throttle) else float(row.throttle),
                "brake": bool(row.brake) if not pd.isna(row.brake) else False,
                "gear": None if pd.isna(row.gear) else int(row.gear),
                "x": None if pd.isna(row.x) else float(row.x),
                "y": None if pd.isna(row.y) else float(row.y),
                "drs": None if pd.isna(row.drs) else int(row.drs),
            }
        )

    xs = [p["x"] for p in points if p["x"] is not None]
    ys = [p["y"] for p in points if p["y"] is not None]
    if not xs and track_outline:
        xs = [p["x"] for p in track_outline]
        ys = [p["y"] for p in track_outline]
    bounds = (
        {"minX": min(xs), "maxX": max(xs), "minY": min(ys), "maxY": max(ys)}
        if xs and ys
        else None
    )

    return {
        "session": session_meta,
        "driver": selected,
        "driverInfo": driver_info,
        "schemaVersion": REPLAY_SCHEMA_VERSION,
        "totalSeconds": round(float(df["t"].iloc[-1]), 3),
        "totalLaps": total_laps,
        "pointCount": len(points),
        "lapMarkers": lap_markers,
        "bounds": bounds,
        "trackOutline": track_outline or [],
        "points": points,
    }


def build_driver_replay(
    session_key: int,
    year: int,
    location: str,
    session_type: str,
    session_name: str,
    date_start: str | None,
    driver: str | None = None,
) -> dict:
    drivers = _drivers_for_session(session_key)
    driver_number = _driver_number_for_code(drivers, driver)
    selected = next(d["code"] for d in drivers if d["driver_number"] == driver_number)
    driver_info = next(
        ({"code": d["code"], "name": d["name"], "team": d["team"]} for d in drivers if d["code"] == selected),
        None,
    )

    if not date_start:
        sessions = fetch("sessions", session_key=session_key)
        date_start = sessions[0]["date_start"] if sessions else None
    if not date_start:
        raise ValueError("Session has no date_start in OpenF1")

    session_start = datetime.fromisoformat(date_start.replace("Z", "+00:00"))

    car_rows = fetch("car_data", session_key=session_key, driver_number=driver_number)
    loc_rows = fetch("location", session_key=session_key, driver_number=driver_number)
    if not car_rows:
        raise ValueError(f"No car_data for driver {selected} in session {session_key}")

    car_df = pd.DataFrame(car_rows)
    car_df["t"] = car_df["date"].apply(lambda d: _to_session_seconds(d, session_start))
    car_df = car_df.sort_values("t").dropna(subset=["t"])
    car_df["brake"] = car_df["brake"].astype(bool)

    if loc_rows:
        loc_df = pd.DataFrame(loc_rows)
        loc_df["t"] = loc_df["date"].apply(lambda d: _to_session_seconds(d, session_start))
        loc_df = loc_df.sort_values("t").dropna(subset=["t", "x", "y"])
        track_outline = _build_track_outline(loc_df)
        merged = pd.merge_asof(
            car_df.sort_values("t"),
            loc_df[["t", "x", "y"]],
            on="t",
            direction="nearest",
            tolerance=0.5,
        )
    else:
        merged = car_df.copy()
        merged["x"] = np.nan
        merged["y"] = np.nan
        track_outline = []

    lap_rows = fetch("laps", session_key=session_key, driver_number=driver_number)
    lap_markers: list[dict] = []
    laps_df = pd.DataFrame()
    if lap_rows:
        laps_df = pd.DataFrame(lap_rows).sort_values("lap_number")
        for row in laps_df.itertuples(index=False):
            if row.date_start:
                lap_markers.append(
                    {
                        "lap": int(row.lap_number),
                        "t": round(_to_session_seconds(row.date_start, session_start), 3),
                    }
                )
        lap_lookup = laps_df[["lap_number", "date_start"]].dropna(subset=["date_start"]).copy()
        lap_lookup["t"] = lap_lookup["date_start"].apply(
            lambda d: _to_session_seconds(d, session_start)
        )
        merged = pd.merge_asof(
            merged,
            lap_lookup[["t", "lap_number"]].rename(columns={"lap_number": "lap"}),
            on="t",
            direction="backward",
        )
    else:
        merged["lap"] = None

    merged, lap_markers = _trim_to_race_start(merged, lap_markers)

    if len(merged) > MAX_POINTS:
        idx = np.linspace(0, len(merged) - 1, MAX_POINTS, dtype=int)
        merged = merged.iloc[idx]

    total_laps = (
        int(laps_df["lap_number"].max())
        if not laps_df.empty and "lap_number" in laps_df.columns
        else len(lap_markers)
    )

    session_meta = {
        "year": year,
        "location": location,
        "sessionType": session_type,
        "name": session_name,
        "eventName": location,
        "session_key": session_key,
    }

    replay_df = merged.rename(
        columns={
            "speed": "speed",
            "rpm": "rpm",
            "throttle": "throttle",
            "brake": "brake",
            "n_gear": "gear",
            "drs": "drs",
        }
    )

    return _series_to_points(
        replay_df,
        lap_markers,
        total_laps,
        session_meta,
        selected,
        driver_info,
        track_outline=track_outline,
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
        session_key=int(entry["session_key"]),
        year=entry["year"],
        location=entry["location"],
        session_type=entry["sessionType"],
        session_name=entry.get("session_name", "Race"),
        date_start=entry.get("date_start"),
        driver=selected,
    )
    payload["session"]["id"] = session_id

    REPLAY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    return payload
