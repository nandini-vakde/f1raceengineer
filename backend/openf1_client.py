"""HTTP client for the OpenF1 Query API (public or self-hosted)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from config import OPENF1_BASE_URL


class OpenF1Error(Exception):
    pass


def _build_url(resource: str, query: str | None = None) -> str:
    path = resource.strip("/")
    url = f"{OPENF1_BASE_URL}/{path}"
    if query:
        url = f"{url}?{query}"
    return url


def fetch(resource: str, **params: Any) -> list[dict]:
    """
    Fetch a collection from OpenF1.

    Params are passed as query filters, e.g. session_key=9523, year>=2024.
    Values are URL-encoded; include operators in the key (year>=2024) or value.
    """
    parts: list[str] = []
    for key, value in params.items():
        if value is None:
            continue
        parts.append(f"{key}={urllib.parse.quote(str(value), safe='>=<')}")

    url = _build_url(resource, "&".join(parts) if parts else None)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise OpenF1Error(f"OpenF1 HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OpenF1Error(
            f"Cannot reach OpenF1 at {OPENF1_BASE_URL}. "
            f"If running locally, start the query API and set OPENF1_BASE_URL. ({exc})"
        ) from exc

    data = json.loads(body)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise OpenF1Error(f"Unexpected OpenF1 response type from {url}")


def fetch_all_pages(resource: str, **params: Any) -> list[dict]:
    """OpenF1 returns full result sets in one response for most endpoints."""
    return fetch(resource, **params)
