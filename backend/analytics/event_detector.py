# analytics/event_detector.py

class EventDetector:

    def detect(self, features):

        events = []

        if features["drs_active"]:
            events.append("DRS_ACTIVE")

        if features["speed"] and features["speed"] > 300:
            events.append("HIGH_SPEED")

        if features["brake"]:
            events.append("BRAKING_ZONE")

        return events