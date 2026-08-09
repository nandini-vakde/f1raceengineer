"""Simple race physics for post-branch lap simulation (Phase 4).

No AI — closed-form adjustments only:
  lap_time ≈ base_pace + tire_wear + fuel + traffic
"""

from __future__ import annotations

# Extra seconds added per lap of tyre age (approx).
TIRE_DEG_PER_LAP = {
    "SOFT": 0.06,
    "MEDIUM": 0.04,
    "HARD": 0.025,
    "INTERMEDIATE": 0.05,
    "WET": 0.05,
}

# Time lost vs staying out when the car pits (stationary + in/out lap penalty).
DEFAULT_PIT_LOSS_SECONDS = 22.0

# Heavy-fuel handicap at race start; linearly bleeds off to 0 by the finish.
FUEL_START_PENALTY = 0.8  # seconds on lap 1

# Extra time when running within this gap of the car ahead.
TRAFFIC_GAP_THRESHOLD = 1.2  # seconds
TRAFFIC_PENALTY = 0.25


def normalize_compound(compound: str | None) -> str:
    if not compound:
        return "MEDIUM"
    key = str(compound).strip().upper()
    aliases = {
        "S": "SOFT",
        "M": "MEDIUM",
        "H": "HARD",
        "I": "INTERMEDIATE",
        "W": "WET",
        "INTER": "INTERMEDIATE",
    }
    return aliases.get(key, key)


def tire_wear_penalty(compound: str | None, tire_age: int | None) -> float:
    age = max(0, int(tire_age or 0))
    deg = TIRE_DEG_PER_LAP.get(normalize_compound(compound), 0.04)
    return round(age * deg, 4)


def fuel_penalty(lap: int, total_laps: int) -> float:
    if total_laps <= 1:
        return 0.0
    # Remaining fuel fraction after completing (lap-1) flying laps.
    remaining = max(0.0, 1.0 - (max(lap, 1) - 1) / (total_laps - 1))
    return round(FUEL_START_PENALTY * remaining, 4)


def traffic_penalty(gap_ahead: float | None) -> float:
    if gap_ahead is None:
        return 0.0
    if gap_ahead < 0:
        return 0.0
    if gap_ahead <= TRAFFIC_GAP_THRESHOLD:
        return TRAFFIC_PENALTY
    return 0.0


def estimate_lap_time(
    base_pace: float,
    compound: str | None,
    tire_age: int | None,
    lap: int,
    total_laps: int,
    gap_ahead: float | None = None,
) -> float:
    """Predict a lap time from pace + simple compound / fuel / traffic terms."""
    total = (
        float(base_pace)
        + tire_wear_penalty(compound, tire_age)
        + fuel_penalty(lap, total_laps)
        + traffic_penalty(gap_ahead)
    )
    return round(total, 3)


def pit_loss_seconds(historical_pit_duration: float | None = None) -> float:
    if historical_pit_duration is not None and historical_pit_duration > 0:
        # OpenF1 pit_duration is often lane time (~20–40s). Use as-is if plausible.
        if 12.0 <= historical_pit_duration <= 45.0:
            return round(float(historical_pit_duration), 3)
    return DEFAULT_PIT_LOSS_SECONDS
