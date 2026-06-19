from __future__ import annotations

from dataclasses import dataclass


CHRONOTYPE_WINDOWS = {
    "Morning": {
        "deep_work": [(7, 11)],
        "creative": [(10, 12), (15, 16)],
        "meetings": [(11, 14)],
        "admin": [(14, 17)],
        "planning": [(7, 8), (16, 17)],
    },
    "Intermediate": {
        "deep_work": [(9, 13)],
        "creative": [(10, 14), (15, 16)],
        "meetings": [(13, 15)],
        "admin": [(8, 9), (15, 17)],
        "planning": [(8, 9), (16, 17)],
    },
    "Evening": {
        "deep_work": [(15, 20)],
        "creative": [(13, 16), (18, 20)],
        "meetings": [(10, 13)],
        "admin": [(8, 10), (13, 15)],
        "planning": [(10, 11), (14, 15)],
    },
}


@dataclass(frozen=True)
class CircadianSlot:
    hour: int
    circadian_phase: str
    hourly_energy: float
    hourly_productivity: float
    focus_score: float
    cognitive_capacity: float
    recommended_task_type: str


def normalize_chronotype(chronotype: str) -> str:
    value = (chronotype or "Intermediate").strip().lower()
    if value.startswith("morning"):
        return "Morning"
    if value.startswith("evening"):
        return "Evening"
    return "Intermediate"


def phase_for_hour(hour: int) -> str:
    if 5 <= hour <= 10:
        return "Morning"
    if 11 <= hour <= 14:
        return "Midday"
    if 15 <= hour <= 18:
        return "Afternoon"
    if 19 <= hour <= 23:
        return "Evening"
    return "Night"


def productivity_curve(hour: int, chronotype: str, recovery_score: float, burnout_risk: str, energy_level: float) -> CircadianSlot:
    chronotype = normalize_chronotype(chronotype)
    peak_ranges = {"Morning": (7, 11), "Intermediate": (10, 14), "Evening": (16, 20)}
    peak_start, peak_end = peak_ranges[chronotype]
    peak_midpoint = (peak_start + peak_end) / 2
    distance = min(abs(hour - peak_midpoint), 24 - abs(hour - peak_midpoint))
    multiplier = max(0.2, min(1.15, 1.15 - 0.075 * distance))
    if 13 <= hour <= 15:
        multiplier *= 0.86
    if hour <= 5:
        multiplier *= 0.45
    burnout_penalty = {"Low": 0.0, "Medium": 0.08, "High": 0.18}.get(burnout_risk, 0.08)
    recovery_factor = recovery_score / 100
    hourly_energy = max(0, min(10, energy_level * multiplier + recovery_factor * 1.3 - burnout_penalty * 4))
    hourly_productivity = max(0, min(100, 55 * multiplier + recovery_score * 0.25 - burnout_penalty * 25))
    focus_score = max(0, min(100, hourly_productivity * 0.62 + hourly_energy * 3.6))
    cognitive_capacity = max(0, min(100, focus_score * 0.68 + recovery_score * 0.20))
    if cognitive_capacity >= 75:
        task_type = "Deep Work"
    elif cognitive_capacity >= 62:
        task_type = "Creative Work"
    elif 10 <= hour <= 15 and cognitive_capacity >= 48:
        task_type = "Meetings"
    elif cognitive_capacity >= 35:
        task_type = "Admin Tasks"
    else:
        task_type = "Recovery Break"
    return CircadianSlot(hour, phase_for_hour(hour), round(hourly_energy, 2), round(hourly_productivity, 2), round(focus_score, 2), round(cognitive_capacity, 2), task_type)


def generate_circadian_profile(chronotype: str, recovery_score: float, burnout_risk: str, energy_level: float) -> list[CircadianSlot]:
    return [productivity_curve(hour, chronotype, recovery_score, burnout_risk, energy_level) for hour in range(24)]


def preferred_windows(chronotype: str) -> dict[str, list[tuple[int, int]]]:
    return CHRONOTYPE_WINDOWS[normalize_chronotype(chronotype)]

