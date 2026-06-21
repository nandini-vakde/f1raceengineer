# analytics/feature_builder.py

class FeatureBuilder:

    def build(self, point: dict):

        speed = point.get("speed")
        throttle = point.get("throttle")
        brake = point.get("brake")
        drs = point.get("drs")

        return {
            "lap": point.get("lap"),
            "speed": speed,
            "throttle": throttle,
            "brake": brake,
            "drs_active": drs is not None and drs > 0,
        }