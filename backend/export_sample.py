"""Export a static JSON snapshot for offline frontend preview."""

import json
from pathlib import Path

from data_loader import load_session_overview

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data" / "overview.json"


def main() -> None:
    payload = load_session_overview()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
