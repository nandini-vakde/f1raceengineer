"""Export static JSON snapshots for offline frontend preview (from OpenF1)."""

import json
from pathlib import Path

from data_loader import load_overview_by_session_id
from openf1_sessions import list_sessions_catalog
from race_simulation import load_race_simulation_by_session_id
from telemetry_replay import load_replay_by_session_id

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data"
DEFAULT_SESSION = "2024-monaco-r"
DEMO_LAPS = 5


def _trim_simulation_for_demo(simulation: dict) -> dict:
    laps_merged = simulation["lapsMerged"][:DEMO_LAPS]
    driver_laps = {
        code: records[:DEMO_LAPS]
        for code, records in simulation["driverLaps"].items()
    }
    training_rows = [
        {**entry, "lap": lap_frame["lap"]}
        for lap_frame in laps_merged
        for entry in lap_frame["entries"]
    ]
    return {
        **simulation,
        "totalLaps": DEMO_LAPS,
        "driverLaps": driver_laps,
        "lapsMerged": laps_merged,
        "trainingRows": training_rows,
    }


def main() -> None:
    overview = load_overview_by_session_id(DEFAULT_SESSION)
    replay = load_replay_by_session_id(DEFAULT_SESSION)
    simulation = _trim_simulation_for_demo(load_race_simulation_by_session_id(DEFAULT_SESSION))
    sessions = {"sessions": list_sessions_catalog()}

    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")
    (ROOT / "replay.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
    (ROOT / "race_simulation.json").write_text(json.dumps(simulation, indent=2), encoding="utf-8")
    (ROOT / "sessions.json").write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    print(f"Wrote {ROOT / 'overview.json'}")
    print(f"Wrote {ROOT / 'replay.json'}")
    print(f"Wrote {ROOT / 'race_simulation.json'}")
    print(f"Wrote {ROOT / 'sessions.json'}")


if __name__ == "__main__":
    main()
