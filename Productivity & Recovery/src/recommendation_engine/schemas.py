from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Task:
    name: str
    estimated_minutes: int
    complexity: int
    category: str | None = None
    deadline: str | None = None
    priority: int = 3


@dataclass
class UserState:
    user_id: str
    date: str
    sleep_hours: float
    sleep_quality: float
    stress_level: float
    fatigue_score: float
    energy_level: float
    mood_score: float
    activity_minutes: float
    work_hours: float
    meeting_hours: float
    task_count: int
    task_complexity: float
    chronotype: str
    predicted_productivity_score: float
    predicted_burnout_risk: str
    predicted_recovery_score: float
    tasks: list[Task] = field(default_factory=list)
    start_hour: int = 7
    end_hour: int = 18


@dataclass
class ScheduleItem:
    start: str
    end: str
    item_type: str
    title: str
    reason: str
    energy_window: str | None = None
    task_category: str | None = None


@dataclass
class RecommendationPlan:
    plan_type: str
    user_id: str
    date: str
    summary: str
    focus_blocks: list[ScheduleItem]
    breaks: list[ScheduleItem]
    recovery_interventions: list[dict[str, Any]]
    schedule: list[ScheduleItem]
    rule_outputs: dict[str, Any]
    reasoning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

