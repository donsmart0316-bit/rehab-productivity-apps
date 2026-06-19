from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.feedback.feedback_store import FeedbackRecord, FeedbackStore
from src.llm.planner_chain import generate_daily_coaching_text, generate_weekly_coaching_text
from src.recommendation_engine.scheduler import generate_alternative_plans, save_plan
from src.recommendation_engine.schemas import Task, UserState


def sample_user_state() -> UserState:
    return UserState(
        user_id="sample_user_001",
        date="2026-06-16",
        sleep_hours=7.2,
        sleep_quality=7.1,
        stress_level=5.8,
        fatigue_score=5.6,
        energy_level=6.4,
        mood_score=6.1,
        activity_minutes=42,
        work_hours=8,
        meeting_hours=2,
        task_count=6,
        task_complexity=7.2,
        chronotype="Intermediate",
        predicted_productivity_score=72.5,
        predicted_burnout_risk="Medium",
        predicted_recovery_score=64.0,
        tasks=[
            Task("Write model evaluation memo", 90, 8, priority=5),
            Task("Research recommendation strategy", 100, 9, priority=5),
            Task("Team planning meeting", 45, 4, priority=4),
            Task("Email and admin follow-up", 40, 2, priority=2),
            Task("Review dashboard metrics", 60, 6, priority=3),
            Task("Learning block: LangChain prompt patterns", 60, 5, priority=3),
        ],
        start_hour=7,
        end_hour=18,
    )


def build_sample_outputs(project_root: Path) -> None:
    outputs = project_root / "outputs"
    outputs.mkdir(exist_ok=True)
    user = sample_user_state()
    plans = generate_alternative_plans(user)
    primary = plans["primary"]
    weekly = {
        "user_id": user.user_id,
        "week_start": user.date,
        "recommended_mode": "primary",
        "daily_plan_options": plans,
        "weekly_recovery_strategy": [
            "Use conservative plan after any night under 6.5 hours of sleep.",
            "Keep two low-cognitive evenings for recovery.",
            "Review sleep debt and fatigue every Friday.",
        ],
    }
    save_plan(primary, outputs / "sample_daily_plan.json")
    save_plan(weekly, outputs / "sample_weekly_plan.json")

    user_profile = {
        "chronotype": user.chronotype,
        "sleep_hours": user.sleep_hours,
        "sleep_quality": user.sleep_quality,
        "stress_level": user.stress_level,
        "fatigue_score": user.fatigue_score,
        "energy_level": user.energy_level,
        "mood_score": user.mood_score,
        "tasks": [task.__dict__ for task in user.tasks],
    }
    ml_predictions = {
        "productivity_score": user.predicted_productivity_score,
        "burnout_risk": user.predicted_burnout_risk,
        "recovery_score": user.predicted_recovery_score,
    }
    daily_text = generate_daily_coaching_text(user_profile, ml_predictions, primary)
    weekly_text = generate_weekly_coaching_text({"user_id": user.user_id, "week_start": user.date}, weekly)
    (outputs / "sample_llm_outputs.md").write_text(
        "\n\n".join(["# Sample Daily LLM Output", daily_text, "# Sample Weekly LLM Output", weekly_text]),
        encoding="utf-8",
    )

    store = FeedbackStore(project_root / "data" / "feedback" / "feedback_log.csv")
    store.append(
        FeedbackRecord(
            user_id=user.user_id,
            date=user.date,
            recommended_plan=primary,
            actual_plan_followed=None,
            user_satisfaction_rating=None,
            perceived_productivity=None,
            perceived_fatigue=None,
            comments="Sample placeholder record for future personalization.",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 3 sample recommendation outputs.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    build_sample_outputs(args.project_root)


if __name__ == "__main__":
    main()

