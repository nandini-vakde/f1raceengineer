"""Export Phase 1 race-state datasets, optionally with Phase 3 decisions.

Usage:
  cd backend
  python export_race_state.py
  python export_race_state.py --session-id 2024-bahrain-r
  python export_race_state.py --pit VER:18:HARD
"""

from __future__ import annotations

import argparse

from race_simulation import (
    DEFAULT_RACE_SESSION_ID,
    export_race_simulation,
    load_race_simulation_by_session_id,
)
from race_timeline import simulate_branch


def _parse_pit(spec: str) -> dict:
    # VER:18:HARD  or  VER:18
    parts = spec.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("Use DRIVER:LAP or DRIVER:LAP:COMPOUND")
    out = {"driver": parts[0].upper(), "pitLap": int(parts[1])}
    if len(parts) >= 3:
        out["compound"] = parts[2].upper()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Export race-state tables for model training")
    parser.add_argument("--session-id", default=DEFAULT_RACE_SESSION_ID)
    parser.add_argument("--parquet", action="store_true")
    parser.add_argument(
        "--pit",
        action="append",
        default=[],
        type=_parse_pit,
        help="Player decision, e.g. VER:18:HARD (repeatable)",
    )
    args = parser.parse_args()

    formats = ("csv", "parquet") if args.parquet else ("csv",)
    sim = load_race_simulation_by_session_id(args.session_id)
    if args.pit:
        sim = simulate_branch(sim, args.pit)

    written = export_race_simulation(sim, formats=formats)
    print(
        f"Session: {sim['session'].get('id')} · {sim['totalLaps']} laps · "
        f"{sim['driverCount']} drivers · branched={sim.get('branched', False)}"
    )
    if sim.get("decisions"):
        print(f"Decisions: {sim['decisions']}")
    print(f"Training rows: {len(sim['trainingRows'])}")
    for fmt, paths in written.items():
        if paths:
            print(f"\n{fmt.upper()} ({len(paths)} files):")
            for path in paths[:6]:
                print(f"  {path}")
            if len(paths) > 6:
                print(f"  ... +{len(paths) - 6} more")


if __name__ == "__main__":
    main()
