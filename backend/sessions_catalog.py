"""Session list backed by OpenF1 (replaces hard-coded FastF1 catalog)."""

from __future__ import annotations

from openf1_sessions import get_session_by_id, list_sessions_catalog

DEFAULT_SESSION_ID = "2024-monaco-r"


def list_sessions() -> list[dict]:
    return list_sessions_catalog()
