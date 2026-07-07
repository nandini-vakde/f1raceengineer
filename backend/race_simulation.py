"""Build per-driver lap datasets merged by lap number for race simulation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config import CACHE_DIR
from data_loader import _drivers_for_session
from openf1_client import fetch
from openf1_sessions import get_session_by_id

SIM_CACHE_DIR = Path(CACHE_DIR) / "simulations"
DEFAULT_RACE_SESSION_ID = "2024-monaco-r"


def _sim_cache_path(session_id: str) -> Path:
    safe = session_id.replace("/", "-")
    return SIM_CACHE_DIR / f"{safe}.json"


def _to_session_seconds(date_str: str | None, session_start: datetime) -> float | None:
    if not date_str:
        return None
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    start = session_start if session_start.tzinfo else session_start.replace(tzinfo=timezone.utc)
    return round((dt - start).total_seconds(), 3)


def _safe_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _driver_lap_record(
    lap: dict,
    driver_info: dict,
    session_start: datetime,
    cumulative_time: float,
) -> dict:
    lap_time = _safe_float(lap.get("lap_duration"))
    if lap_time is not None:
        cumulative_time = round(cumulative_time + lap_time, 3)

    return {
        "lap": int(lap["lap_number"]),
        "driverNumber": driver_info["driver_number"],
        "code": driver_info["code"],
        "name": driver_info["name"],
        "team": driver_info["team"],
        "lapTime": lap_time,
        "sector1": _safe_float(lap.get("duration_sector_1")),
        "sector2": _safe_float(lap.get("duration_sector_2")),
        "sector3": _safe_float(lap.get("duration_sector_3")),
        "compound": lap.get("compound"),
        "tyreLife": lap.get("tyre_life"),
        "isPitOutLap": bool(lap.get("is_pit_out_lap")),
        "sessionTimeStart": _to_session_seconds(lap.get("date_start"), session_start),
        "cumulativeTime": cumulative_time if lap_time is not None else None,
    }


def _rank_lap_entries(entries: list[dict]) -> list[dict]:
    ranked = sorted(
        entries,
        key=lambda e: (
            e["cumulativeTime"] is None,
            e["cumulativeTime"] if e["cumulativeTime"] is not None else float("inf"),
        ),
    )
    leader_time = ranked[0]["cumulativeTime"] if ranked else None
    for i, entry in enumerate(ranked):
        entry["position"] = i + 1
        if leader_time is not None and entry["cumulativeTime"] is not None:
            entry["gapToLeader"] = round(entry["cumulativeTime"] - leader_time, 3)
        else:
            entry["gapToLeader"] = None
        if i == 0:
            entry["interval"] = None
        elif entry["cumulativeTime"] is not None and ranked[i - 1]["cumulativeTime"] is not None:
            entry["interval"] = round(entry["cumulativeTime"] - ranked[i - 1]["cumulativeTime"], 3)
        else:
            entry["interval"] = None
    return ranked


def build_race_simulation(
    session_key: int,
    year: int,
    location: str,
    session_type: str,
    session_name: str,
    date_start: str | None,
) -> dict:
    drivers = _drivers_for_session(session_key)
    by_number = {d["driver_number"]: d for d in drivers}

    if not date_start:
        sessions = fetch("sessions", session_key=session_key)
        date_start = sessions[0]["date_start"] if sessions else None
    if not date_start:
        raise ValueError("Session has no date_start in OpenF1")

    session_start = datetime.fromisoformat(date_start.replace("Z", "+00:00"))
    lap_rows = fetch("laps", session_key=session_key)
    if not lap_rows:
        raise ValueError(f"No lap data for session {session_key}")

    laps_df = pd.DataFrame(lap_rows)
    laps_df = laps_df[laps_df["driver_number"].isin(by_number.keys())]
    laps_df = laps_df.sort_values(["driver_number", "lap_number"])

    driver_laps: dict[str, list[dict]] = {}
    cumulative_by_driver: dict[int, float] = {dn: 0.0 for dn in by_number}

    for driver_number, group in laps_df.groupby("driver_number"):
        info = by_number[int(driver_number)]
        records: list[dict] = []
        cumulative = 0.0
        for lap in group.to_dict("records"):
            record = _driver_lap_record(lap, info, session_start, cumulative)
            if record["cumulativeTime"] is not None:
                cumulative = record["cumulativeTime"]
            records.append(record)
        driver_laps[info["code"]] = records
        cumulative_by_driver[int(driver_number)] = cumulative

    laps_by_number: dict[int, list[dict]] = {}
    for code, records in driver_laps.items():
        for record in records:
            laps_by_number.setdefault(record["lap"], []).append(record.copy())

    laps_merged: list[dict] = []
    for lap_num in sorted(laps_by_number.keys()):
        entries = _rank_lap_entries(laps_by_number[lap_num])
        leader = entries[0] if entries else None
        leader_lap_time = leader["lapTime"] if leader else None
        session_starts = [e["sessionTimeStart"] for e in entries if e["sessionTimeStart"] is not None]
        session_start_t = min(session_starts) if session_starts else None
        session_end_t = (
            round(session_start_t + leader_lap_time, 3)
            if session_start_t is not None and leader_lap_time is not None
            else None
        )
        laps_merged.append(
            {
                "lap": lap_num,
                "leaderCode": leader["code"] if leader else None,
                "leaderLapTime": leader_lap_time,
                "sessionTimeStart": session_start_t,
                "sessionTimeEnd": session_end_t,
                "entries": entries,
            }
        )

    total_laps = max(laps_by_number.keys()) if laps_by_number else 0
    training_rows = [
        {**entry, "lap": lap_frame["lap"]}
        for lap_frame in laps_merged
        for entry in lap_frame["entries"]
    ]

    return {
        "session": {
            "year": year,
            "location": location,
            "sessionType": session_type,
            "name": session_name,
            "eventName": location,
            "session_key": session_key,
        },
        "drivers": [
            {"code": d["code"], "name": d["name"], "team": d["team"], "driverNumber": d["driver_number"]}
            for d in drivers
        ],
        "totalLaps": total_laps,
        "driverCount": len(driver_laps),
        "driverLaps": driver_laps,
        "lapsMerged": laps_merged,
        "trainingRows": training_rows,
    }


def race_simulation_to_dataframe(simulation: dict) -> pd.DataFrame:
    rows = []
    for lap_frame in simulation["lapsMerged"]:
        for entry in lap_frame["entries"]:
            rows.append(
                {
                    "LapNumber": lap_frame["lap"],
                    "Position": entry["position"],
                    "Driver": entry["code"],
                    "LapTime": entry["lapTime"],
                    "Sector1": entry["sector1"],
                    "Sector2": entry["sector2"],
                    "Sector3": entry["sector3"],
                    "Compound": entry["compound"],
                    "TyreLife": entry["tyreLife"],
                    "GapToLeader": entry["gapToLeader"],
                    "Interval": entry["interval"],
                    "CumulativeTime": entry["cumulativeTime"],
                }
            )
    return pd.DataFrame(rows)


def load_race_simulation_by_session_id(session_id: str) -> dict:
    entry = get_session_by_id(session_id)
    if entry is None:
        raise ValueError(f"Unknown session id: {session_id}")

    cache_path = _sim_cache_path(session_id)
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["session"]["id"] = session_id
        return payload

    payload = build_race_simulation(
        session_key=int(entry["session_key"]),
        year=entry["year"],
        location=entry["location"],
        session_type=entry["sessionType"],
        session_name=entry.get("session_name", "Race"),
        date_start=entry.get("date_start"),
    )
    payload["session"]["id"] = session_id

    SIM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload), encoding="utf-8")

    return payload
