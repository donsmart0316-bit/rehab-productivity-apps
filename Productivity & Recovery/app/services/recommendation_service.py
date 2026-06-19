from __future__ import annotations

from src.recommendation_engine.scheduler import generate_alternative_plans
from src.recommendation_engine.schemas import Task, UserState


def build_tasks(task_rows: list[dict]) -> list[Task]:
    return [
        Task(
            name=row["name"],
            estimated_minutes=int(row.get("estimated_minutes", 60)),
            complexity=int(row.get("complexity", 5)),
            priority=int(row.get("priority", 3)),
        )
        for row in task_rows
    ]


def generate_plan(profile: dict, checkin: dict, prediction: dict, task_rows: list[dict]) -> dict:
    state = UserState(
        user_id=profile["name"].lower().replace(" ", "_"),
        date=checkin["date"],
        sleep_hours=checkin["sleep_hours"],
        sleep_quality=checkin["sleep_quality"],
        stress_level=checkin["stress_level"],
        fatigue_score=checkin["fatigue_score"],
        energy_level=checkin["energy_level"],
        mood_score=checkin["mood_score"],
        activity_minutes=checkin["activity_minutes"],
        work_hours=checkin["work_hours"],
        meeting_hours=checkin["meeting_hours"],
        task_count=checkin["task_count"],
        task_complexity=checkin["task_complexity"],
        chronotype=profile["chronotype"],
        predicted_productivity_score=prediction["productivity_score"],
        predicted_burnout_risk=prediction["burnout_risk"],
        predicted_recovery_score=prediction["recovery_score"],
        tasks=build_tasks(task_rows),
        start_hour=int(profile.get("start_hour", 8)),
        end_hour=int(profile.get("end_hour", 18)),
    )
    return generate_alternative_plans(state)
