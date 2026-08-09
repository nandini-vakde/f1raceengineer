"""Build per-driver lap datasets merged by lap number for race simulation.

Phase 1 race-state dataset for later model training:
- driverLaps[code]: one sequence per driver
- lapsMerged: full field state per lap
- trainingRows: flat ML-ready rows

OpenF1 sources: laps, position, pit, stints (weather deferred).
"""

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
EXPORT_DIR = Path(CACHE_DIR) / "exports"
DEFAULT_RACE_SESSION_ID = "2024-bahrain-r"
SIM_SCHEMA_VERSION = 3


def _sim_cache_path(session_id: str) -> Path:
    safe = session_id.replace("/", "-")
    return SIM_CACHE_DIR / f"{safe}_v{SIM_SCHEMA_VERSION}.json"


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


def _safe_int(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_stint_lookup(stint_rows: list[dict]) -> dict[int, list[dict]]:
    by_driver: dict[int, list[dict]] = {}
    for row in stint_rows:
        dn = row.get("driver_number")
        if dn is None:
            continue
        by_driver.setdefault(int(dn), []).append(row)
    for dn in by_driver:
        by_driver[dn].sort(key=lambda r: (r.get("lap_start") or 0, r.get("stint_number") or 0))
    return by_driver


def _stint_for_lap(stints: list[dict], lap_number: int) -> dict | None:
    for stint in stints:
        start = stint.get("lap_start")
        end = stint.get("lap_end")
        if start is None:
            continue
        if int(start) <= lap_number and (end is None or lap_number <= int(end)):
            return stint
    return None


def _tyre_age(stint: dict | None, lap_number: int) -> int | None:
    if not stint:
        return None
    age_start = stint.get("tyre_age_at_start")
    lap_start = stint.get("lap_start")
    if age_start is None or lap_start is None:
        return None
    return int(age_start) + (lap_number - int(lap_start))


def _build_position_lookup(
    position_rows: list[dict],
    session_start: datetime,
) -> dict[int, pd.DataFrame]:
    if not position_rows:
        return {}
    df = pd.DataFrame(position_rows)
    df["t"] = df["date"].apply(lambda d: _to_session_seconds(d, session_start))
    df = df.dropna(subset=["t", "driver_number", "position"]).sort_values("t")
    by_driver: dict[int, pd.DataFrame] = {}
    for dn, group in df.groupby("driver_number"):
        by_driver[int(dn)] = group[["t", "position"]].reset_index(drop=True)
    return by_driver


def _position_at_time(timeline: pd.DataFrame | None, t: float | None) -> int | None:
    if timeline is None or timeline.empty or t is None:
        return None
    eligible = timeline[timeline["t"] <= t]
    if eligible.empty:
        return _safe_int(timeline.iloc[0]["position"])
    return _safe_int(eligible.iloc[-1]["position"])


def _is_valid_pit_stop(row: dict) -> bool:
    """Drop OpenF1 grid-to-flag artifacts (e.g. lap 1 lane_duration ~2400s)."""
    duration = row.get("pit_duration") or row.get("lane_duration")
    if duration is None:
        return False
    try:
        seconds = float(duration)
    except (TypeError, ValueError):
        return False
    # Real F1 pit lane times are roughly 18–45s; grid hold times are minutes.
    return 12.0 <= seconds <= 90.0


def _build_pit_lookup(pit_rows: list[dict]) -> dict[tuple[int, int], dict]:
    lookup: dict[tuple[int, int], dict] = {}
    for row in pit_rows:
        if not _is_valid_pit_stop(row):
            continue
        dn = row.get("driver_number")
        lap = row.get("lap_number")
        if dn is None or lap is None:
            continue
        lookup[(int(dn), int(lap))] = {
            "pitDuration": _safe_float(row.get("pit_duration")),
            "laneDuration": _safe_float(row.get("lane_duration")),
            "stopDuration": _safe_float(row.get("stop_duration")),
        }
    return lookup


def _driver_lap_record(
    lap: dict,
    driver_info: dict,
    session_start: datetime,
    cumulative_time: float,
    stint: dict | None,
    official_position: int | None,
    pit: dict | None,
) -> dict:
    lap_number = int(lap["lap_number"])
    lap_time = _safe_float(lap.get("lap_duration"))
    if lap_time is not None:
        cumulative_time = round(cumulative_time + lap_time, 3)

    compound = None
    if stint and stint.get("compound"):
        compound = stint["compound"]
    else:
        compound = lap.get("compound")

    tyre_life = _tyre_age(stint, lap_number)
    if tyre_life is None:
        tyre_life = _safe_int(lap.get("tyre_life"))

    record = {
        "lap": lap_number,
        "driverNumber": driver_info["driver_number"],
        "code": driver_info["code"],
        "name": driver_info["name"],
        "team": driver_info["team"],
        "lapTime": lap_time,
        "sector1": _safe_float(lap.get("duration_sector_1")),
        "sector2": _safe_float(lap.get("duration_sector_2")),
        "sector3": _safe_float(lap.get("duration_sector_3")),
        "compound": compound,
        "tyreLife": tyre_life,
        "stintNumber": _safe_int(stint.get("stint_number")) if stint else None,
        "isPitOutLap": bool(lap.get("is_pit_out_lap")),
        "pitted": pit is not None,
        "pitDuration": pit["pitDuration"] if pit else None,
        "position": official_position,
        "sessionTimeStart": _to_session_seconds(lap.get("date_start"), session_start),
        "cumulativeTime": cumulative_time if lap_time is not None else None,
    }
    if lap_time is not None and record["sessionTimeStart"] is not None:
        record["sessionTimeEnd"] = round(record["sessionTimeStart"] + lap_time, 3)
    else:
        record["sessionTimeEnd"] = None
    return record


def _rank_lap_entries(entries: list[dict]) -> list[dict]:
    ranked = sorted(
        entries,
        key=lambda e: (
            e["position"] is None,
            e["position"] if e["position"] is not None else 999,
            e["cumulativeTime"] is None,
            e["cumulativeTime"] if e["cumulativeTime"] is not None else float("inf"),
        ),
    )
    leader_time = next((e["cumulativeTime"] for e in ranked if e["cumulativeTime"] is not None), None)
    for i, entry in enumerate(ranked):
        if entry["position"] is None:
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

    position_rows = fetch("position", session_key=session_key) or []
    pit_rows = fetch("pit", session_key=session_key) or []
    stint_rows = fetch("stints", session_key=session_key) or []

    position_lookup = _build_position_lookup(position_rows, session_start)
    pit_lookup = _build_pit_lookup(pit_rows)
    stint_lookup = _build_stint_lookup(stint_rows)

    laps_df = pd.DataFrame(lap_rows)
    laps_df = laps_df[laps_df["driver_number"].isin(by_number.keys())]
    laps_df = laps_df.sort_values(["driver_number", "lap_number"])

    driver_laps: dict[str, list[dict]] = {}

    for driver_number, group in laps_df.groupby("driver_number"):
        info = by_number[int(driver_number)]
        dn = int(driver_number)
        records: list[dict] = []
        cumulative = 0.0
        stints = stint_lookup.get(dn, [])
        pos_timeline = position_lookup.get(dn)

        for lap in group.to_dict("records"):
            lap_number = int(lap["lap_number"])
            stint = _stint_for_lap(stints, lap_number)
            pit = pit_lookup.get((dn, lap_number))

            start_t = _to_session_seconds(lap.get("date_start"), session_start)
            lap_time = _safe_float(lap.get("lap_duration"))
            end_t = round(start_t + lap_time, 3) if start_t is not None and lap_time is not None else start_t
            official_pos = _position_at_time(pos_timeline, end_t)

            record = _driver_lap_record(
                lap, info, session_start, cumulative, stint, official_pos, pit
            )
            if record["cumulativeTime"] is not None:
                cumulative = record["cumulativeTime"]
            records.append(record)

        driver_laps[info["code"]] = records

    laps_by_number: dict[int, list[dict]] = {}
    for records in driver_laps.values():
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
        "schemaVersion": SIM_SCHEMA_VERSION,
        "session": {
            "year": year,
            "location": location,
            "sessionType": session_type,
            "name": session_name,
            "eventName": location,
            "session_key": session_key,
        },
        "drivers": [
            {
                "code": d["code"],
                "name": d["name"],
                "team": d["team"],
                "driverNumber": d["driver_number"],
            }
            for d in drivers
        ],
        "sources": {
            "laps": len(lap_rows),
            "position": len(position_rows),
            "pit": len(pit_rows),
            "stints": len(stint_rows),
        },
        "totalLaps": total_laps,
        "driverCount": len(driver_laps),
        "driverLaps": driver_laps,
        "lapsMerged": laps_merged,
        "trainingRows": training_rows,
        "pits": [
            {
                "driverNumber": row.get("driver_number"),
                "lap": row.get("lap_number"),
                "pitDuration": _safe_float(row.get("pit_duration")),
                "laneDuration": _safe_float(row.get("lane_duration")),
                "stopDuration": _safe_float(row.get("stop_duration")),
                "date": row.get("date"),
            }
            for row in pit_rows
            if row.get("driver_number") in by_number and _is_valid_pit_stop(row)
        ],
    }


def race_simulation_to_dataframe(simulation: dict) -> pd.DataFrame:
    rows = []
    for lap_frame in simulation["lapsMerged"]:
        for entry in lap_frame["entries"]:
            rows.append(
                {
                    "LapNumber": lap_frame["lap"],
                    "Driver": entry["code"],
                    "Position": entry["position"],
                    "GapToLeader": entry["gapToLeader"],
                    "Interval": entry["interval"],
                    "LapTime": entry["lapTime"],
                    "Sector1": entry["sector1"],
                    "Sector2": entry["sector2"],
                    "Sector3": entry["sector3"],
                    "Compound": entry["compound"],
                    "TireAge": entry["tyreLife"],
                    "StintNumber": entry.get("stintNumber"),
                    "IsPitOutLap": entry["isPitOutLap"],
                    "Pitted": entry.get("pitted"),
                    "PitDuration": entry.get("pitDuration"),
                    "CumulativeTime": entry["cumulativeTime"],
                    "Source": entry.get("source", "history"),
                }
            )
    return pd.DataFrame(rows)


def driver_laps_to_dataframe(simulation: dict, code: str) -> pd.DataFrame:
    records = simulation["driverLaps"].get(code, [])
    gap_by_lap = {
        (row["code"], row["lap"]): row.get("gapToLeader")
        for row in simulation["trainingRows"]
    }
    rows = []
    for r in records:
        rows.append(
            {
                "Lap": r["lap"],
                "Driver": r["code"],
                "Position": r.get("position"),
                "Gap": gap_by_lap.get((r["code"], r["lap"])),
                "Tire": r.get("compound"),
                "TireAge": r.get("tyreLife"),
                "LapTime": r.get("lapTime"),
                "Sector1": r.get("sector1"),
                "Sector2": r.get("sector2"),
                "Sector3": r.get("sector3"),
                "StintNumber": r.get("stintNumber"),
                "IsPitOutLap": r.get("isPitOutLap"),
                "Pitted": r.get("pitted"),
                "PitDuration": r.get("pitDuration"),
                "CumulativeTime": r.get("cumulativeTime"),
                "Source": r.get("source", "history"),
            }
        )
    return pd.DataFrame(rows)


def export_race_simulation(
    simulation: dict,
    out_dir: Path | None = None,
    formats: tuple[str, ...] = ("csv",),
) -> dict[str, list[str]]:
    session_id = simulation["session"].get("id") or (
        f"{simulation['session']['year']}-{simulation['session']['location']}"
    )
    safe = str(session_id).replace("/", "-").replace(" ", "-").lower()
    if simulation.get("branched"):
        safe = f"{safe}-branched"
    root = Path(out_dir) if out_dir else EXPORT_DIR / safe
    drivers_dir = root / "drivers"
    drivers_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, list[str]] = {"csv": [], "parquet": []}
    merged = race_simulation_to_dataframe(simulation)
    training = pd.DataFrame(simulation["trainingRows"])
    pits = pd.DataFrame(simulation.get("pits") or [])

    tables = {
        "race_state_merged": merged,
        "training_rows": training,
        "pits": pits,
    }
    for code in sorted(simulation["driverLaps"].keys()):
        tables[f"drivers/{code}"] = driver_laps_to_dataframe(simulation, code)

    for name, df in tables.items():
        path_stem = root / name if not name.startswith("drivers/") else drivers_dir / name.split("/", 1)[1]
        path_stem.parent.mkdir(parents=True, exist_ok=True)
        if "csv" in formats:
            csv_path = path_stem.with_suffix(".csv")
            df.to_csv(csv_path, index=False)
            written["csv"].append(str(csv_path))
        if "parquet" in formats:
            try:
                pq_path = path_stem.with_suffix(".parquet")
                df.to_parquet(pq_path, index=False)
                written["parquet"].append(str(pq_path))
            except ImportError:
                pass

    meta_path = root / "manifest.json"
    meta_path.write_text(
        json.dumps(
            {
                "session": simulation["session"],
                "schemaVersion": simulation.get("schemaVersion"),
                "branched": simulation.get("branched", False),
                "decisions": simulation.get("decisions"),
                "totalLaps": simulation["totalLaps"],
                "driverCount": simulation["driverCount"],
                "sources": simulation.get("sources"),
                "files": written,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    written["csv"].append(str(meta_path))
    return written


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
