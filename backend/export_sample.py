"""Export static JSON snapshots for offline frontend preview."""

import json
from pathlib import Path

from data_loader import load_overview_by_session_id
from sessions_catalog import list_sessions
from telemetry_replay import load_replay_by_session_id

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data"


def main() -> None:
    overview = load_overview_by_session_id("2024-monaco-r")
    replay = load_replay_by_session_id("2024-monaco-r")
    sessions = {"sessions": list_sessions()}

    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "overview.json").write_text(json.dumps(overview, indent=2), encoding="utf-8")
    (ROOT / "replay.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
    (ROOT / "sessions.json").write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    print(f"Wrote {ROOT / 'overview.json'}")
    print(f"Wrote {ROOT / 'replay.json'}")
    print(f"Wrote {ROOT / 'sessions.json'}")


if __name__ == "__main__":
    main()
