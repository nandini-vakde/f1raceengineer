from __future__ import annotations

import pandas as pd

from openf1_client import fetch
from openf1_sessions import SESSION_TYPE_TO_NAME, get_session_by_id
from serialize import dataframe_preview

DEFAULT_SESSION_ID = "2024-monaco-r"
DEFAULT_DRIVER = "VER"


def _drivers_for_session(session_key: int) -> list[dict]:
    rows = fetch("drivers", session_key=session_key)
    drivers = [
        {
            "code": row["name_acronym"],
            "name": row.get("broadcast_name") or row.get("full_name") or row["name_acronym"],
            "team": row.get("team_name") or "",
            "driver_number": row["driver_number"],
        }
        for row in rows
        if row.get("name_acronym")
    ]
    drivers.sort(key=lambda d: d["name"])
    return drivers


def _driver_number_for_code(drivers: list[dict], code: str | None) -> int:
    codes = {d["code"]: d["driver_number"] for d in drivers}
    if code and code in codes:
        return int(codes[code])
    if DEFAULT_DRIVER in codes:
        return int(codes[DEFAULT_DRIVER])
    if drivers:
        return int(drivers[0]["driver_number"])
    raise ValueError("No drivers found for this session")


def _build_results_df(session_key: int, drivers: list[dict]) -> pd.DataFrame:
    by_number = {d["driver_number"]: d for d in drivers}
    results = fetch("session_result", session_key=session_key)
    rows = []
    for r in results:
        dn = r.get("driver_number")
        info = by_number.get(dn, {})
        rows.append(
            {
                "Position": r.get("position"),
                "BroadcastName": info.get("name"),
                "Abbreviation": info.get("code"),
                "TeamName": info.get("team"),
                "DriverNumber": dn,
                "Points": r.get("points"),
                "NumberOfLaps": r.get("number_of_laps"),
                "GapToLeader": r.get("gap_to_leader"),
                "DNF": r.get("dnf"),
            }
        )
    return pd.DataFrame(rows)


def _build_laps_df(session_key: int, driver_number: int) -> pd.DataFrame:
    laps = fetch("laps", session_key=session_key, driver_number=driver_number)
    rows = []
    for lap in laps:
        rows.append(
            {
                "Driver": lap.get("driver_number"),
                "LapNumber": lap.get("lap_number"),
                "LapTime": lap.get("lap_duration"),
                "Sector1Time": lap.get("duration_sector_1"),
                "Sector2Time": lap.get("duration_sector_2"),
                "Sector3Time": lap.get("duration_sector_3"),
                "Compound": lap.get("compound"),
                "TyreLife": lap.get("tyre_life"),
                "IsPitOutLap": lap.get("is_pit_out_lap"),
                "DateStart": lap.get("date_start"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty and "LapNumber" in df.columns:
        df = df.sort_values("LapNumber")
    return df


def _telemetry_sample_df(session_key: int, driver_number: int, limit: int = 25) -> pd.DataFrame:
    car = fetch("car_data", session_key=session_key, driver_number=driver_number)
    loc = fetch("location", session_key=session_key, driver_number=driver_number)
    if not car:
        return pd.DataFrame()

    car_df = pd.DataFrame(car).head(limit * 4)
    if loc:
        loc_df = pd.DataFrame(loc)
        car_df = car_df.merge(
            loc_df[["date", "x", "y"]],
            on="date",
            how="left",
        )
    car_df = car_df.rename(
        columns={
            "speed": "Speed",
            "rpm": "RPM",
            "throttle": "Throttle",
            "brake": "Brake",
            "n_gear": "nGear",
            "x": "X",
            "y": "Y",
            "drs": "DRS",
            "date": "Time",
        }
    )
    return car_df.head(limit)


def extract_drivers_from_list(drivers: list[dict]) -> list[dict]:
    return [{"code": d["code"], "name": d["name"], "team": d["team"]} for d in drivers]


def load_session_overview(
    session_key: int,
    year: int,
    location: str,
    session_type: str,
    session_name: str,
    date_start: str | None,
    driver: str | None = None,
    preview_rows: int = 25,
    session_id: str | None = None,
) -> dict:
    drivers = _drivers_for_session(session_key)
    selected_code = None
    if driver:
        match = next((d for d in drivers if d["code"] == driver), None)
        selected_code = match["code"] if match else driver
    driver_number = _driver_number_for_code(drivers, selected_code)
    selected_driver = next(d["code"] for d in drivers if d["driver_number"] == driver_number)

    results_df = _build_results_df(session_key, drivers)
    driver_results = results_df[results_df["Abbreviation"] == selected_driver]
    laps_df = _build_laps_df(session_key, driver_number)
    telemetry_df = _telemetry_sample_df(session_key, driver_number, preview_rows)

    datasets: dict = {
        "results": {
            "id": "results",
            "title": "Session Result",
            "description": f"Result row for {selected_driver} (OpenF1 session_result).",
            "source": f"GET /v1/session_result?session_key={session_key}",
            **dataframe_preview(driver_results, preview_rows),
        },
        "laps": {
            "id": "laps",
            "title": "Lap Times",
            "description": f"Per-lap data for {selected_driver} from OpenF1 /v1/laps.",
            "source": f"GET /v1/laps?session_key={session_key}&driver_number={driver_number}",
            **dataframe_preview(laps_df, preview_rows),
        },
        "telemetry": {
            "id": "telemetry",
            "title": "Telemetry",
            "description": (
                f"Car + location samples for {selected_driver} "
                "(OpenF1 car_data + location)."
            ),
            "source": (
                f"GET /v1/car_data + /v1/location "
                f"?session_key={session_key}&driver_number={driver_number}"
            ),
            **dataframe_preview(telemetry_df, preview_rows),
        },
    }

    if session_type == "R" and session_id:
        race_laps_df = _race_laps_preview_df(session_id, preview_rows)
        if race_laps_df is not None:
            datasets["raceLaps"] = {
                "id": "raceLaps",
                "title": "Race Laps (merged)",
                "description": (
                    "All drivers' lap data merged by lap number — one row per driver "
                    "per lap with position, gaps, and sector times."
                ),
                "source": f"GET /api/race/simulation (built from /v1/laps?session_key={session_key})",
                **dataframe_preview(race_laps_df, preview_rows),
            }

    return {
        "session": {
            "year": year,
            "location": location,
            "sessionType": session_type,
            "name": session_name,
            "eventName": location,
            "date": date_start,
            "session_key": session_key,
        },
        "drivers": extract_drivers_from_list(drivers),
        "selectedDriver": selected_driver,
        "datasets": datasets,
    }


def _race_laps_preview_df(session_id: str, preview_rows: int) -> pd.DataFrame | None:
    try:
        from race_simulation import load_race_simulation_by_session_id, race_simulation_to_dataframe

        simulation = load_race_simulation_by_session_id(session_id)
        df = race_simulation_to_dataframe(simulation)
        return df if not df.empty else None
    except Exception:
        return None


def load_overview_by_session_id(
    session_id: str,
    driver: str | None = None,
    preview_rows: int = 25,
) -> dict:
    entry = get_session_by_id(session_id)
    if entry is None:
        raise ValueError(f"Unknown session id: {session_id}")

    overview = load_session_overview(
        session_key=int(entry["session_key"]),
        year=entry["year"],
        location=entry["location"],
        session_type=entry["sessionType"],
        session_name=entry.get("session_name") or SESSION_TYPE_TO_NAME.get(entry["sessionType"], "Session"),
        date_start=entry.get("date_start"),
        driver=driver,
        preview_rows=preview_rows,
        session_id=session_id,
    )
    overview["session"]["id"] = session_id
    return overview
