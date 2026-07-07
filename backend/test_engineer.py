"""Smoke test for the race engineer.

Usage:
  # Hardcoded sample point (no OpenF1 / replay required):
  python test_engineer.py

  # Real telemetry from a cached or live replay:
  python test_engineer.py <session_id> <driver> <point_index>
  python test_engineer.py 2024-monaco-r VER 5000
"""

import sys

from ai.engineer import RaceEngineer
from analytics.event_detector import EventDetector
from analytics.feature_builder import FeatureBuilder
from telemetry_replay import load_replay_by_session_id

engineer = RaceEngineer()
feature_builder = FeatureBuilder()
event_detector = EventDetector()

if len(sys.argv) >= 4:
    session_id = sys.argv[1]
    driver = sys.argv[2]
    point_index = int(sys.argv[3])

    replay = load_replay_by_session_id(session_id=session_id, driver=driver)
    point = replay["points"][point_index]
    features = feature_builder.build(point)
    events = event_detector.detect(features)

    print(f"Session: {session_id}, driver: {driver}, point: {point_index}")
    print(f"Events: {events}")
    print(f"Telemetry: {point}")
else:
    point = {
        "lap": 18,
        "speed": 302,
        "rpm": 11800,
        "throttle": 100,
        "brake": False,
        "gear": 8,
        "drs": 12,
    }
    events = ["HIGH_SPEED", "DRS_ACTIVE"]

message = engineer.process(point, events=events)
print(message)
