"""Curated sessions available in the data explorer."""

from __future__ import annotations

SESSIONS: list[dict] = [
  {"id": "2024-monaco-r", "label": "2024 · Monaco · Race", "year": 2024, "location": "Monaco", "sessionType": "R"},
  {"id": "2024-monaco-q", "label": "2024 · Monaco · Qualifying", "year": 2024, "location": "Monaco", "sessionType": "Q"},
  {"id": "2024-bahrain-r", "label": "2024 · Bahrain · Race", "year": 2024, "location": "Bahrain", "sessionType": "R"},
  {"id": "2024-bahrain-q", "label": "2024 · Bahrain · Qualifying", "year": 2024, "location": "Bahrain", "sessionType": "Q"},
  {"id": "2024-silverstone-r", "label": "2024 · Silverstone · Race", "year": 2024, "location": "Silverstone", "sessionType": "R"},
  {"id": "2024-silverstone-q", "label": "2024 · Silverstone · Qualifying", "year": 2024, "location": "Silverstone", "sessionType": "Q"},
  {"id": "2024-monza-r", "label": "2024 · Monza · Race", "year": 2024, "location": "Monza", "sessionType": "R"},
  {"id": "2024-singapore-r", "label": "2024 · Singapore · Race", "year": 2024, "location": "Singapore", "sessionType": "R"},
  {"id": "2023-monaco-r", "label": "2023 · Monaco · Race", "year": 2023, "location": "Monaco", "sessionType": "R"},
]


def get_session_by_id(session_id: str) -> dict | None:
    return next((s for s in SESSIONS if s["id"] == session_id), None)


def list_sessions() -> list[dict]:
    return SESSIONS
