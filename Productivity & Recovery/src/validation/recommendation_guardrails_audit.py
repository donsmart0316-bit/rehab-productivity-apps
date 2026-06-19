from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.services.recommendation_service import generate_plan


def run_case(name: str, profile: dict, checkin: dict, prediction: dict, tasks: list[dict]) -> dict:
    plan = generate_plan(profile, checkin, prediction, tasks)["primary"]
    validation = plan["rule_outputs"]["validation"]
    categories = {item["title"]: item.get("task_category") for item in plan["schedule"] if item["item_type"] == "task"}
    return {
        "case": name,
        "quality_score": plan["rule_outputs"]["recommendation_quality_score"],
        "passed": validation["passed"],
        "issues": "; ".join(validation["issues"]),
        "recovery_priority_mode": plan["rule_outputs"]["recovery_priority_mode"],
        "deferred_tasks": len(plan["rule_outputs"].get("deferred_tasks", [])),
        "categories": categories,
        "schedule": plan["schedule"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit recommendation guardrails and schedule realism.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    normal_profile = {"name": "Guardrail Test", "chronotype": "Morning", "start_hour": 7, "end_hour": 20}
    normal_checkin = {
        "date": "2026-06-17",
        "sleep_hours": 7.5,
        "sleep_quality": 7,
        "stress_level": 4,
        "fatigue_score": 4,
        "energy_level": 7,
        "mood_score": 7,
        "activity_minutes": 45,
        "work_hours": 8,
        "meeting_hours": 1,
        "task_count": 8,
        "task_complexity": 5,
    }
    normal_prediction = {"productivity_score": 75, "burnout_risk": "Low", "recovery_score": 78}
    unusual_tasks = [
        {"name": "Prayer", "estimated_minutes": 30, "complexity": 1, "priority": 5},
        {"name": "Gym Workout", "estimated_minutes": 60, "complexity": 4, "priority": 4},
        {"name": "Going Out With Friends", "estimated_minutes": 90, "complexity": 2, "priority": 3},
        {"name": "Rest", "estimated_minutes": 45, "complexity": 1, "priority": 4},
        {"name": "Write Research Paper", "estimated_minutes": 120, "complexity": 9, "priority": 5},
        {"name": "Doctor Appointment", "estimated_minutes": 45, "complexity": 2, "priority": 5},
        {"name": "Travel to Airport", "estimated_minutes": 60, "complexity": 2, "priority": 3},
    ]
    burnout_profile = {"name": "Burnout Guardrail", "chronotype": "Intermediate", "start_hour": 8, "end_hour": 18}
    burnout_checkin = {
        "date": "2026-06-17",
        "sleep_hours": 3.5,
        "sleep_quality": 2,
        "stress_level": 9,
        "fatigue_score": 9,
        "energy_level": 3,
        "mood_score": 3,
        "activity_minutes": 5,
        "work_hours": 10,
        "meeting_hours": 4,
        "task_count": 8,
        "task_complexity": 8,
    }
    burnout_prediction = {"productivity_score": 12, "burnout_risk": "High", "recovery_score": 18}
    burnout_tasks = [
        {"name": "Emergency Work", "estimated_minutes": 180, "complexity": 9, "priority": 5},
        {"name": "Coding Project", "estimated_minutes": 180, "complexity": 9, "priority": 4},
        {"name": "Reply Emails", "estimated_minutes": 45, "complexity": 2, "priority": 2},
        {"name": "Nap", "estimated_minutes": 45, "complexity": 1, "priority": 5},
        {"name": "Therapy Session", "estimated_minutes": 60, "complexity": 2, "priority": 5},
    ]
    results = [
        run_case("Unusual human tasks", normal_profile, normal_checkin, normal_prediction, unusual_tasks),
        run_case("High burnout recovery priority", burnout_profile, burnout_checkin, burnout_prediction, burnout_tasks),
    ]
    summary = pd.DataFrame([{key: value for key, value in row.items() if key not in {"schedule", "categories"}} for row in results])
    lines = [
        "# Recommendation Guardrails & Realism Audit",
        "",
        summary.to_markdown(index=False),
        "",
        "## Classification Checks",
    ]
    for row in results:
        lines.extend([f"### {row['case']}", pd.Series(row["categories"]).to_markdown(), ""])
    lines.append("## Schedule Checks")
    for row in results:
        lines.append(f"### {row['case']}")
        for item in row["schedule"]:
            lines.append(f"- {item['start']}-{item['end']} | {item['title']} | Category: {item.get('task_category') or item['item_type']} | {item['reason']}")
        lines.append("")
    output = args.project_root / "reports" / "recommendation_guardrails_report.md"
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
