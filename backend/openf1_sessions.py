"""Discover and resolve F1 sessions via OpenF1."""

from __future__ import annotations

import re
from functools import lru_cache

from openf1_client import OpenF1Error, fetch

SESSION_TYPE_TO_NAME = {
    "R": "Race",
    "Q": "Qualifying",
    "S": "Sprint",
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _session_type_code(session_name: str) -> str:
    name = session_name.lower()
    if name == "race":
        return "R"
    if "qualifying" in name:
        return "Q"
    if name == "sprint":
        return "S"
    if name.startswith("practice"):
        return name.replace(" ", "").upper()[:3] if len(name) > 8 else "FP"
    return session_name[:1].upper()


@lru_cache(maxsize=1)
def list_sessions_catalog() -> list[dict]:
    """Build session dropdown from OpenF1 (2023-2024 race weekends)."""
    catalog: list[dict] = []
    for year in (2024, 2023):
        try:
            rows = fetch("sessions", **{"year": year})
        except OpenF1Error:
            continue
        for row in rows:
            name = row.get("session_name") or ""
            if name not in ("Race", "Qualifying", "Sprint"):
                continue
            country = row.get("country_name") or row.get("location") or "Unknown"
            st = _session_type_code(name)
            session_key = row["session_key"]
            sid = f"{year}-{_slug(country)}-{st.lower()}"
            catalog.append(
                {
                    "id": sid,
                    "label": f"{year} · {country} · {name}",
                    "year": year,
                    "location": country,
                    "sessionType": st,
                    "session_key": session_key,
                    "session_name": name,
                    "date_start": row.get("date_start"),
                    "circuit": row.get("circuit_short_name"),
                }
            )
    catalog.sort(key=lambda s: (s["year"], s["location"], s["sessionType"]), reverse=True)
    return catalog


def get_session_by_id(session_id: str) -> dict | None:
    return next((s for s in list_sessions_catalog() if s["id"] == session_id), None)


def resolve_session_key(year: int, location: str, session_type: str) -> int:
    session_name = SESSION_TYPE_TO_NAME.get(session_type, session_type)
    for loc_field, loc_value in (("country_name", location), ("location", location)):
        rows = fetch(
            "sessions",
            year=year,
            **{loc_field: loc_value, "session_name": session_name},
        )
        if rows:
            return int(rows[0]["session_key"])
    raise ValueError(
        f"No OpenF1 session for {year} {location} {session_name}. "
        "Check OPENF1_BASE_URL and that the session exists in the API."
    )
