from __future__ import annotations

import fastf1

from data_loader import _ensure_cache

_sessions: dict[tuple[int, str, str], fastf1.core.Session] = {}


def get_loaded_session(year: int, location: str, session_type: str):
    key = (year, location, session_type)
    if key not in _sessions:
        _ensure_cache()
        session = fastf1.get_session(year, location, session_type)
        session.load()
        _sessions[key] = session
    return _sessions[key]
