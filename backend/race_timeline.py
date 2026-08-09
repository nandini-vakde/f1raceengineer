"""Phase 3 + 4: branch from historical race state via player decisions.

Given historical lap tables from race_simulation, apply decisions like
"pit on lap 18 onto Hard". From that lap onward the affected driver's
timeline is physics-simulated instead of copied from history.
"""

from __future__ import annotations

from copy import deepcopy
from statistics import median
from typing import Any

from race_physics import (
    estimate_lap_time,
    normalize_compound,
    pit_loss_seconds,
)


def _historical_rows_by_driver(simulation: dict) -> dict[str, list[dict]]:
    by_driver: dict[str, list[dict]] = {}
    for row in simulation["trainingRows"]:
        code = row["code"]
        by_driver.setdefault(code, []).append(dict(row))
    for code in by_driver:
        by_driver[code].sort(key=lambda r: r["lap"])
    return by_driver


def _base_pace_for_driver(rows: list[dict]) -> float:
    """Clean flying-lap median used as the driver's underlying pace."""
    times = []
    for row in rows:
        lt = row.get("lapTime")
        if lt is None:
            continue
        if row.get("isPitOutLap") or row.get("pitted"):
            continue
        times.append(float(lt))
    if not times:
        times = [float(r["lapTime"]) for r in rows if r.get("lapTime") is not None]
    if not times:
        return 96.0
    # Drop obvious outliers (safety cars / traffic) above 1.08x median.
    mid = median(times)
    clean = [t for t in times if t <= mid * 1.08]
    return float(median(clean or times))


def _rank_field(entries: list[dict]) -> list[dict]:
    ranked = sorted(
        entries,
        key=lambda e: (
            e.get("cumulativeTime") is None,
            e["cumulativeTime"] if e.get("cumulativeTime") is not None else float("inf"),
        ),
    )
    leader_time = next((e["cumulativeTime"] for e in ranked if e.get("cumulativeTime") is not None), None)
    for i, entry in enumerate(ranked):
        entry["position"] = i + 1
        if leader_time is not None and entry.get("cumulativeTime") is not None:
            entry["gapToLeader"] = round(entry["cumulativeTime"] - leader_time, 3)
        else:
            entry["gapToLeader"] = None
        if i == 0 or entry.get("cumulativeTime") is None or ranked[i - 1].get("cumulativeTime") is None:
            entry["interval"] = None
        else:
            entry["interval"] = round(entry["cumulativeTime"] - ranked[i - 1]["cumulativeTime"], 3)
    return ranked


def simulate_branch(
    historical: dict,
    decisions: list[dict[str, Any]],
) -> dict:
    """Replay history until decisions fire, then physics-simulate the rest.

    Each decision:
      {
        "driver": "VER",
        "pitLap": 18,
        "compound": "HARD",   # optional, default HARD
        "pitLoss": 22.0       # optional override seconds
      }
    """
    if not decisions:
        out = deepcopy(historical)
        out["branched"] = False
        out["decisions"] = []
        return out

    decision_map: dict[str, dict] = {}
    for d in decisions:
        code = d.get("driver") or d.get("code")
        if not code or d.get("pitLap") is None:
            raise ValueError("Each decision needs driver and pitLap")
        decision_map[str(code).upper()] = {
            "pitLap": int(d["pitLap"]),
            "compound": normalize_compound(d.get("compound") or "HARD"),
            "pitLoss": d.get("pitLoss"),
        }

    by_driver = _historical_rows_by_driver(historical)
    base_pace = {code: _base_pace_for_driver(rows) for code, rows in by_driver.items()}
    total_laps = int(historical["totalLaps"])

    # Live state once a driver has branched off history.
    live: dict[str, dict] = {}
    branched_rows: dict[str, list[dict]] = {code: [] for code in by_driver}

    hist_index = {code: {r["lap"]: r for r in rows} for code, rows in by_driver.items()}

    for lap in range(1, total_laps + 1):
        # First pass: produce each driver's lap row for this lap number.
        lap_entries: list[dict] = []

        for code, hist_by_lap in hist_index.items():
            hist = hist_by_lap.get(lap)
            if hist is None:
                continue

            decision = decision_map.get(code)
            state = live.get(code)

            # Still on the historical timeline?
            if state is None and (decision is None or lap < decision["pitLap"]):
                row = dict(hist)
                row["source"] = "history"
                branched_rows[code].append(row)
                lap_entries.append(row)
                continue

            # Branch starts on pit lap.
            if state is None and decision is not None and lap == decision["pitLap"]:
                compound = decision["compound"]
                loss = pit_loss_seconds(decision.get("pitLoss"))
                # Base the in-lap / pit-exit lap on history if present, else pace model.
                in_lap = hist.get("lapTime")
                if in_lap is None:
                    in_lap = estimate_lap_time(
                        base_pace[code],
                        hist.get("compound"),
                        hist.get("tyreLife") or hist.get("tireAge") or 0,
                        lap,
                        total_laps,
                    )
                # Cumulative: continue from previous historical cumulative if available.
                prev = branched_rows[code][-1] if branched_rows[code] else None
                prev_cum = prev["cumulativeTime"] if prev and prev.get("cumulativeTime") is not None else 0.0
                # Pit loss applied as added race time this lap.
                lap_time = round(float(in_lap) + loss, 3)
                cumulative = round(prev_cum + lap_time, 3)
                row = {
                    **{k: hist.get(k) for k in ("driverNumber", "code", "name", "team")},
                    "lap": lap,
                    "lapTime": lap_time,
                    "sector1": hist.get("sector1"),
                    "sector2": hist.get("sector2"),
                    "sector3": hist.get("sector3"),
                    "compound": compound,
                    "tyreLife": 0,
                    "stintNumber": (hist.get("stintNumber") or 1) + 1,
                    "isPitOutLap": True,
                    "pitted": True,
                    "pitDuration": loss,
                    "cumulativeTime": cumulative,
                    "sessionTimeStart": hist.get("sessionTimeStart"),
                    "sessionTimeEnd": hist.get("sessionTimeEnd"),
                    "source": "decision",
                    "branched": True,
                }
                live[code] = {
                    "compound": compound,
                    "tyreAge": 0,
                    "cumulativeTime": cumulative,
                    "stintNumber": row["stintNumber"],
                }
                branched_rows[code].append(row)
                lap_entries.append(row)
                continue

            # Already branched: physics for remaining laps.
            assert state is not None
            state["tyreAge"] = int(state["tyreAge"]) + 1
            gap_ahead = None  # filled after ranking if needed; use prior lap gaps
            if branched_rows[code]:
                gap_ahead = branched_rows[code][-1].get("interval")

            lap_time = estimate_lap_time(
                base_pace[code],
                state["compound"],
                state["tyreAge"],
                lap,
                total_laps,
                gap_ahead=gap_ahead,
            )
            cumulative = round(float(state["cumulativeTime"]) + lap_time, 3)
            state["cumulativeTime"] = cumulative
            row = {
                "driverNumber": hist.get("driverNumber"),
                "code": code,
                "name": hist.get("name"),
                "team": hist.get("team"),
                "lap": lap,
                "lapTime": lap_time,
                "sector1": None,
                "sector2": None,
                "sector3": None,
                "compound": state["compound"],
                "tyreLife": state["tyreAge"],
                "stintNumber": state["stintNumber"],
                "isPitOutLap": False,
                "pitted": False,
                "pitDuration": None,
                "cumulativeTime": cumulative,
                "sessionTimeStart": None,
                "sessionTimeEnd": None,
                "source": "physics",
                "branched": True,
            }
            branched_rows[code].append(row)
            lap_entries.append(row)

        # Re-rank this lap for positions / gaps (complete race state).
        ranked = _rank_field([dict(e) for e in lap_entries])
        by_code = {e["code"]: e for e in ranked}
        for code, rows in branched_rows.items():
            if rows and rows[-1]["lap"] == lap and code in by_code:
                rows[-1]["position"] = by_code[code]["position"]
                rows[-1]["gapToLeader"] = by_code[code]["gapToLeader"]
                rows[-1]["interval"] = by_code[code]["interval"]

    # Assemble export-shaped payload.
    laps_by_number: dict[int, list[dict]] = {}
    for code, rows in branched_rows.items():
        for row in rows:
            laps_by_number.setdefault(row["lap"], []).append(dict(row))

    laps_merged = []
    for lap_num in sorted(laps_by_number.keys()):
        entries = _rank_field(laps_by_number[lap_num])
        leader = entries[0] if entries else None
        laps_merged.append(
            {
                "lap": lap_num,
                "leaderCode": leader["code"] if leader else None,
                "leaderLapTime": leader.get("lapTime") if leader else None,
                "entries": entries,
            }
        )

    training_rows = [
        {**entry, "lap": frame["lap"]}
        for frame in laps_merged
        for entry in frame["entries"]
    ]

    return {
        "schemaVersion": historical.get("schemaVersion", 3),
        "branched": True,
        "decisions": [
            {"driver": code, **meta} for code, meta in decision_map.items()
        ],
        "session": deepcopy(historical.get("session", {})),
        "drivers": deepcopy(historical.get("drivers", [])),
        "sources": deepcopy(historical.get("sources", {})),
        "totalLaps": total_laps,
        "driverCount": len(branched_rows),
        "driverLaps": branched_rows,
        "lapsMerged": laps_merged,
        "trainingRows": training_rows,
        "basePace": {code: round(pace, 3) for code, pace in base_pace.items()},
        "physics": {
            "tireDegPerLap": {
                "SOFT": 0.06,
                "MEDIUM": 0.04,
                "HARD": 0.025,
            },
            "defaultPitLoss": pit_loss_seconds(None),
        },
    }
