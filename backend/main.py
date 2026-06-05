"""
CLI entry point for exploring OpenF1-backed data in the terminal.

Run the API for the React explorer:
  uvicorn api:app --reload --port 8000

Optional: point at a local OpenF1 query API (use port 8001, not 8000):
  OPENF1_BASE_URL=http://127.0.0.1:8001/v1 uvicorn api:app --reload --port 8000
"""

from data_loader import load_overview_by_session_id


def main() -> None:
    overview = load_overview_by_session_id("2024-monaco-r")
    session = overview["session"]
    print(
        f"Session: {session['name']} ({session['year']} {session['location']}) "
        f"[OpenF1 session_key={session.get('session_key')}]"
    )
    for key, dataset in overview["datasets"].items():
        print(f"\n{dataset['title']}: {dataset['rowCount']} rows, {len(dataset['columns'])} columns")
        print(f"  Source: {dataset['source']}")


if __name__ == "__main__":
    main()
