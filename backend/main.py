"""
CLI entry point for exploring FastF1 data in the terminal.

Run the API for the React explorer:
  uvicorn api:app --reload --port 8000
"""

from data_loader import load_overview_by_session_id


def main() -> None:
    overview = load_overview_by_session_id("2024-monaco-r")
    session = overview["session"]
    print(f"Session: {session['name']} ({session['year']} {session['location']} {session['sessionType']})")
    for key, dataset in overview["datasets"].items():
        print(f"\n{dataset['title']}: {dataset['rowCount']} rows, {len(dataset['columns'])} columns")
        print(f"  Source: {dataset['source']}")
        if dataset["previewRows"]:
            first = dataset["previewRows"][0]
            print(f"  Sample keys: {', '.join(list(first.keys())[:6])}…")


if __name__ == "__main__":
    main()