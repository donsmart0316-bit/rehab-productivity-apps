from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from src.recommendation_engine.burnout_rules import burnout_adjustments
from src.recommendation_engine.circadian_rules import CircadianSlot, generate_circadian_profile, preferred_windows
from src.recommendation_engine.recovery_rules import recovery_interventions, recovery_status
from src.recommendation_engine.schemas import RecommendationPlan, ScheduleItem, Task, UserState
from src.recommendation_engine.ultradian_rules import ultradian_recommendation


TASK_KEYWORDS = {
    "Deep Work": ["research", "analysis", "write", "writing", "paper", "strategy", "code", "coding", "model", "project", "proposal"],
    "Creative Work": ["brainstorm", "draft", "creative", "concept", "ideate", "outline", "design", "compose"],
    "Learning": ["learn", "course", "read", "study", "practice", "tutorial", "exam", "lecture", "class"],
    "Meetings": ["meeting", "call", "sync", "review", "standup", "1:1", "interview"],
    "Admin": ["email", "emails", "admin", "forms", "invoice", "documentation", "paperwork", "cleanup", "reply"],
    "Exercise": ["gym", "workout", "exercise", "run", "running", "lift", "yoga", "training", "swim", "bike"],
    "Recovery": ["meditation", "breathing", "stretch", "mobility", "walk", "walking", "massage", "mindfulness"],
    "Rest": ["rest", "nap", "sleep", "break", "relax", "recharge"],
    "Social": ["friends", "movie", "date", "party", "wedding", "social", "hangout", "church service"],
    "Spiritual": ["prayer", "pray", "bible", "church", "mosque", "temple", "fasting", "devotional", "worship"],
    "Personal": ["family", "dinner", "cooking", "cleaning", "laundry", "funeral", "visit", "errand"],
    "Health": ["doctor", "therapy", "therapist", "hospital", "clinic", "dentist", "medical", "physio"],
    "Appointments": ["appointment", "reservation", "consultation"],
    "Travel": ["travel", "airport", "flight", "commute", "drive", "train", "bus", "trip", "vacation"],
    "Planning": ["plan", "prioritize", "schedule", "roadmap", "weekly review"],
}

DEMANDING_CATEGORIES = {"Deep Work", "Creative Work", "Learning"}
RESTORATIVE_CATEGORIES = {"Recovery", "Rest", "Spiritual", "Exercise"}
LOW_COGNITIVE_CATEGORIES = {"Admin", "Personal", "Social", "Travel", "Appointments", "Health", "Planning"}


def minutes_to_time(minutes: int) -> str:
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def classify_task_with_confidence(task: Task) -> tuple[str, float, str]:
    if task.category:
        return task.category, 1.0, "User-provided category."
    name = task.name.lower()
    scores: dict[str, int] = {}
    for category, keywords in TASK_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in name)
        if score:
            scores[category] = score
    if scores:
        category, score = max(scores.items(), key=lambda item: (item[1], item[0] != "Planning"))
        confidence = min(0.95, 0.55 + score * 0.18)
        return category, confidence, f"Matched task language to {category.lower()} cues."
    if task.complexity >= 8:
        return "Deep Work", 0.58, "No keyword match; high complexity suggests demanding cognitive work."
    if task.complexity >= 6:
        return "Creative Work", 0.52, "No keyword match; moderate-high complexity suggests creative work."
    if task.complexity <= 3:
        return "Admin", 0.50, "No keyword match; low complexity suggests administrative work."
    return "Personal", 0.35, "Ambiguous task; using a conservative personal-task category rather than forcing planning."


def classify_task(task: Task) -> str:
    return classify_task_with_confidence(task)[0]


def slot_score(slot: CircadianSlot, category: str) -> float:
    if category == "Deep Work":
        return slot.cognitive_capacity * 1.25 + slot.focus_score
    if category == "Creative Work":
        return slot.cognitive_capacity + slot.hourly_energy * 4
    if category == "Meetings":
        return 100 - abs(slot.cognitive_capacity - 55)
    if category == "Admin":
        return 100 - abs(slot.cognitive_capacity - 35)
    if category == "Learning":
        return slot.cognitive_capacity * 0.9 + slot.focus_score * 0.5
    if category == "Exercise":
        return 100 - abs(slot.hour - 16) + slot.hourly_energy * 2
    if category in {"Recovery", "Rest", "Spiritual"}:
        return 100 - abs(slot.cognitive_capacity - 35)
    if category in {"Health", "Appointments", "Travel", "Social", "Personal"}:
        return 100 - abs(slot.cognitive_capacity - 45)
    return 100 - abs(slot.hour - 8)


def task_priority(task: Task) -> tuple[int, int, int]:
    return (-task.priority, -task.complexity, -task.estimated_minutes)


def available_start_minutes(start_hour: int, end_hour: int, occupied: list[tuple[int, int]], duration: int, preferred_hours: list[int]) -> int | None:
    day_start = start_hour * 60
    day_end = end_hour * 60
    candidates = [hour * 60 for hour in preferred_hours] + list(range(day_start, max(day_start, day_end - duration + 1), 15))
    for start in candidates:
        end = start + duration
        if start < day_start or end > day_end:
            continue
        if all(end <= busy_start or start >= busy_end for busy_start, busy_end in occupied):
            return start
    return None


def preferred_hours_for_category(category: str, profile: list[CircadianSlot], chronotype: str) -> list[int]:
    window_key = {
        "Deep Work": "deep_work",
        "Creative Work": "creative",
        "Meetings": "meetings",
        "Admin": "admin",
        "Planning": "planning",
        "Learning": "creative",
        "Exercise": "admin",
        "Recovery": "admin",
        "Rest": "admin",
        "Spiritual": "planning",
        "Social": "admin",
        "Personal": "admin",
        "Health": "meetings",
        "Appointments": "meetings",
        "Travel": "admin",
    }.get(category, "planning")
    hours = []
    for start, end in preferred_windows(chronotype).get(window_key, []):
        hours.extend(range(start, end))
    ranked = sorted(profile, key=lambda slot: slot_score(slot, category), reverse=True)
    for slot in ranked:
        if slot.hour not in hours:
            hours.append(slot.hour)
    return hours


def _interval(schedule_item: ScheduleItem) -> tuple[int, int]:
    start_hour, start_minute = [int(part) for part in schedule_item.start.split(":")]
    end_hour, end_minute = [int(part) for part in schedule_item.end.split(":")]
    return start_hour * 60 + start_minute, end_hour * 60 + end_minute


def _slot_is_free(schedule: list[ScheduleItem], start: int, end: int) -> bool:
    return all(end <= busy_start or start >= busy_end for busy_start, busy_end in (_interval(item) for item in schedule))


def _task_reason(task_name: str, category: str, slot: CircadianSlot, user_state: UserState) -> str:
    recovery = user_state.predicted_recovery_score
    risk = user_state.predicted_burnout_risk
    phase = slot.circadian_phase.lower()
    if category == "Deep Work":
        if risk == "High":
            return (
                f"This demanding task is placed in your strongest {phase} window, but the block is kept short because burnout risk is high "
                "and recovery needs protection."
            )
        if recovery >= 70:
            return (
                f"Because your recovery is strong and your chronotype favors this {phase} period, this is the best time for demanding focus work."
            )
        return (
            f"This task uses your best available {phase} focus window while leaving room for recovery so fatigue does not build too quickly."
        )
    if category in {"Creative Work", "Learning"}:
        return f"This is scheduled when energy and mental flexibility are favorable, making it a good window for {category.lower()} without overloading deep-focus capacity."
    if category == "Meetings":
        return "Meetings are placed in a moderate-energy window so your strongest focus periods stay protected for harder work."
    if category == "Admin":
        return "Lower-demand work is placed outside peak focus time so you can use high-energy periods for more important tasks."
    if category == "Exercise":
        return "Exercise is scheduled away from the deepest cognitive window so it supports physical health and recovery without displacing priority focus work."
    if category == "Recovery":
        return "This restorative activity is placed as deliberate recovery support; no extra recovery break is needed afterward because the task itself lowers load."
    if category == "Rest":
        return "Rest is treated as recovery time, not as a work block, so the schedule protects it without adding another recovery break afterward."
    if category == "Spiritual":
        return f"{task_name} is scheduled in a calm {phase} period to support grounding and reflection without requiring high cognitive load."
    if category == "Social":
        return "Social time is placed outside peak cognitive-demand periods so connection does not compete with deep work."
    if category == "Personal":
        return "This personal task is scheduled in a lower-load window to keep the day realistic and avoid crowding demanding work."
    if category == "Health":
        return "Health-related time is protected as a priority appointment because wellbeing takes precedence over productivity optimization."
    if category == "Appointments":
        return "Appointment time is protected in a moderate-energy window with buffer around higher-demand work."
    if category == "Travel":
        return "Travel is scheduled with lower cognitive expectations because transitions and movement create practical load."
    if category == "Planning":
        return "Planning is placed early enough to guide the day without consuming your highest cognitive window."
    return "This slot balances task demand with your predicted energy, recovery, and burnout signals."


def insert_breaks(schedule: list[ScheduleItem], focus_minutes: int, break_minutes: int, user_state: UserState) -> list[ScheduleItem]:
    breaks: list[ScheduleItem] = []
    for item in schedule:
        if item.item_type != "task":
            continue
        if item.task_category in RESTORATIVE_CATEGORIES:
            continue
        if item.task_category not in DEMANDING_CATEGORIES | {"Meetings"}:
            continue
        start_hour, start_minute = [int(part) for part in item.start.split(":")]
        end_hour, end_minute = [int(part) for part in item.end.split(":")]
        duration = (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
        if duration >= focus_minutes - 5 or (item.task_category == "Meetings" and duration >= 90):
            break_start = item.end
            start_total = end_hour * 60 + end_minute
            breaks.append(
                ScheduleItem(
                    start=break_start,
                    end=minutes_to_time(start_total + break_minutes),
                    item_type="break",
                    title="Recovery Break",
                    reason=f"After a {duration}-minute work block, this break helps restore attention and prevents fatigue from accumulating.",
                )
            )
    baseline_candidates = [
        (10 * 60 + 50, 11 * 60, "Posture and Eye Reset", "A short posture reset and 20-20-20 eye break keeps screen work from becoming physical strain."),
        (15 * 60, 15 * 60 + 10, "Standing / Walking Break", "A brief movement break supports circulation, alertness, and recovery even on a good day."),
    ]
    combined = schedule + breaks
    for start, end, title, reason in baseline_candidates:
        if _slot_is_free(combined, start, end):
            preventive = ScheduleItem(minutes_to_time(start), minutes_to_time(end), "break", title, reason)
            breaks.append(preventive)
            combined.append(preventive)
    if user_state.predicted_burnout_risk == "High":
        midday_start = 12 * 60 + 30
        midday_end = 13 * 60
        if _slot_is_free(schedule + breaks, midday_start, midday_end):
            midday = ScheduleItem("12:30", "13:00", "break", "Protected Recovery Window", "High burnout risk requires a non-negotiable recovery buffer before more cognitive demand.")
            breaks.append(midday)
    return breaks


def _remove_incoherent_breaks(schedule: list[ScheduleItem]) -> list[ScheduleItem]:
    cleaned: list[ScheduleItem] = []
    previous: ScheduleItem | None = None
    for item in sorted(schedule, key=lambda entry: entry.start):
        if (
            item.item_type == "break"
            and previous is not None
            and previous.item_type == "task"
            and previous.task_category in RESTORATIVE_CATEGORIES
            and previous.end == item.start
        ):
            previous.reason = f"{previous.reason} No extra recovery break is added afterward because this is already a restorative activity."
            continue
        cleaned.append(item)
        previous = item
    return cleaned


def validate_schedule(schedule: list[ScheduleItem], user_state: UserState, classification_audit: list[dict[str, object]]) -> dict[str, object]:
    issues: list[str] = []
    score = 100
    intervals = [(_interval(item), item) for item in schedule]
    for idx, ((start, end), item) in enumerate(intervals):
        if end <= start:
            issues.append(f"Impossible timing for {item.title}.")
            score -= 15
        for (other_start, other_end), other in intervals[idx + 1 :]:
            if start < other_end and end > other_start:
                issues.append(f"Overlap between {item.title} and {other.title}.")
                score -= 12

    task_items = [item for item in schedule if item.item_type == "task"]
    reasons = [item.reason for item in task_items]
    if reasons:
        duplicate_count = max(Counter(reasons).values())
        if duplicate_count / len(reasons) > 0.5:
            issues.append("Most task explanations are identical.")
            score -= 18

    for previous, current in zip(schedule, schedule[1:]):
        if (
            previous.item_type == "task"
            and previous.task_category in RESTORATIVE_CATEGORIES
            and current.item_type == "break"
            and previous.end == current.start
        ):
            issues.append(f"{previous.title} is restorative but is followed by an unnecessary recovery break.")
            score -= 20

    bad_categories = {
        "prayer": "Spiritual",
        "gym": "Exercise",
        "workout": "Exercise",
        "nap": "Rest",
        "rest": "Rest",
        "therapy": "Health",
        "doctor": "Health",
        "funeral": "Personal",
    }
    for item in task_items:
        lower = item.title.lower()
        for keyword, expected in bad_categories.items():
            if keyword in lower and item.task_category != expected:
                issues.append(f"{item.title} should be classified as {expected}, not {item.task_category}.")
                score -= 15

    high_risk = user_state.predicted_burnout_risk == "High" or user_state.sleep_hours < 5 or user_state.predicted_recovery_score < 35
    demanding_minutes = 0
    for item in task_items:
        if item.task_category in DEMANDING_CATEGORIES:
            start, end = _interval(item)
            demanding_minutes += end - start
    if high_risk and demanding_minutes > 150:
        issues.append("Recovery-priority mode should reduce demanding cognitive work below 150 minutes.")
        score -= 20
    if high_risk and len([item for item in schedule if item.item_type == "break"]) < 2:
        issues.append("High burnout or low recovery requires additional protected recovery opportunities.")
        score -= 14

    low_confidence = [row for row in classification_audit if float(row["confidence"]) < 0.45]
    if low_confidence:
        issues.append("Some task classifications are low confidence and should be reviewed.")
        score -= min(15, 5 * len(low_confidence))

    reviewers = {
        "Productivity Coach": score >= 80 and not any("Overlap" in issue for issue in issues),
        "Physiotherapist": not any("restorative but is followed" in issue for issue in issues),
        "Psychologist": not (high_risk and demanding_minutes > 150),
        "Ordinary User": score >= 80,
    }
    if not all(reviewers.values()):
        score -= 10
    return {
        "passed": score >= 80 and all(reviewers.values()),
        "score": max(0, min(100, score)),
        "issues": issues,
        "reviewers": reviewers,
        "classification_audit": classification_audit,
    }


def generate_daily_plan(user_state: UserState, plan_type: str = "primary") -> RecommendationPlan:
    profile = generate_circadian_profile(
        user_state.chronotype,
        user_state.predicted_recovery_score,
        user_state.predicted_burnout_risk,
        user_state.energy_level,
    )
    ultra = ultradian_recommendation(user_state.fatigue_score, user_state.predicted_burnout_risk, user_state.predicted_recovery_score, plan_type)
    burnout = burnout_adjustments(user_state.predicted_burnout_risk, user_state.predicted_recovery_score, plan_type)
    recovery = recovery_interventions(user_state.work_hours, user_state.fatigue_score, user_state.predicted_recovery_score, user_state.predicted_burnout_risk)
    focus_minutes = int(ultra["focus_block_minutes"])
    break_minutes = int(ultra["break_minutes"])
    max_deep_work = int(burnout["max_deep_work_blocks"])
    recovery_priority_mode = user_state.predicted_burnout_risk == "High" or user_state.sleep_hours < 5 or user_state.predicted_recovery_score < 35
    if recovery_priority_mode:
        max_deep_work = min(max_deep_work, 1)
        burnout["reduce_workload"] = True
        burnout["notes"].append("Recovery-priority mode activated because burnout risk, sleep loss, or low recovery indicates reduced capacity today.")

    tasks = [Task(**asdict(task)) for task in user_state.tasks]
    classification_audit: list[dict[str, object]] = []
    for task in tasks:
        category, confidence, rationale = classify_task_with_confidence(task)
        task.category = category
        classification_audit.append({"task": task.name, "category": category, "confidence": round(confidence, 2), "rationale": rationale})
    tasks = sorted(tasks, key=task_priority)
    if bool(burnout["reduce_workload"]):
        essential = [task for task in tasks if task.priority >= 4 or task.category in RESTORATIVE_CATEGORIES | {"Health", "Appointments"}]
        tasks = essential[: max(2, min(len(essential), 5))] if essential else tasks[: max(2, min(len(tasks), 3))]
    if plan_type == "conservative":
        tasks = tasks[: max(2, min(len(tasks), 4))]
    elif plan_type == "high_performance" and user_state.predicted_burnout_risk == "Low":
        pass

    schedule: list[ScheduleItem] = []
    occupied: list[tuple[int, int]] = []
    deep_work_count = 0
    deferred_tasks: list[dict[str, str]] = []
    for task in tasks:
        category = task.category or classify_task(task)
        if category == "Deep Work" and deep_work_count >= max_deep_work:
            if recovery_priority_mode:
                deferred_tasks.append({"task": task.name, "reason": "Deferred because recovery-priority mode limits demanding cognitive work today."})
                continue
            category = "Creative Work" if task.complexity >= 6 and not recovery_priority_mode else "Admin"
        duration = min(task.estimated_minutes, focus_minutes) if category in DEMANDING_CATEGORIES else task.estimated_minutes
        if recovery_priority_mode and category in DEMANDING_CATEGORIES:
            duration = min(duration, 45)
        elif recovery_priority_mode and category in {"Admin", "Planning"}:
            duration = min(duration, 45)
        elif recovery_priority_mode and category in {"Meetings", "Health", "Appointments"}:
            duration = min(duration, 60)
        preferred_hours = preferred_hours_for_category(category, profile, user_state.chronotype)
        start = available_start_minutes(user_state.start_hour, user_state.end_hour, occupied, duration, preferred_hours)
        if start is None:
            continue
        end = start + duration
        buffer_minutes = 0 if category in RESTORATIVE_CATEGORIES else break_minutes
        occupied.append((start, end + buffer_minutes))
        if category == "Deep Work":
            deep_work_count += 1
        best_slot = min(profile, key=lambda slot: abs(slot.hour * 60 - start))
        schedule.append(
            ScheduleItem(
                start=minutes_to_time(start),
                end=minutes_to_time(end),
                item_type="task",
                title=task.name,
                reason=_task_reason(task.name, category, best_slot, user_state),
                energy_window=best_slot.recommended_task_type,
                task_category=category,
            )
        )

    breaks = insert_breaks(schedule, focus_minutes, break_minutes, user_state)
    schedule = _remove_incoherent_breaks(sorted(schedule + breaks, key=lambda item: item.start))
    validation = validate_schedule(schedule, user_state, classification_audit)
    summary = (
        f"{plan_type.replace('_', ' ').title()} plan using {ultra['pattern']} with "
        f"{recovery_status(user_state.predicted_recovery_score).lower()} recovery status and {user_state.predicted_burnout_risk.lower()} burnout risk."
    )
    notes = [
        f"Predicted productivity score: {user_state.predicted_productivity_score:.1f}.",
        f"Predicted recovery score: {user_state.predicted_recovery_score:.1f}.",
        f"Burnout risk: {user_state.predicted_burnout_risk}.",
        *[str(note) for note in burnout["notes"]],
    ]
    return RecommendationPlan(
        plan_type=plan_type,
        user_id=user_state.user_id,
        date=user_state.date,
        summary=summary,
        focus_blocks=[item for item in schedule if item.task_category in {"Deep Work", "Creative Work", "Learning"}],
        breaks=[item for item in schedule if item.item_type == "break"],
        recovery_interventions=recovery,
        schedule=schedule,
        rule_outputs={
            "circadian_profile": [asdict(slot) for slot in profile],
            "ultradian": ultra,
            "burnout": burnout,
            "recovery_status": recovery_status(user_state.predicted_recovery_score),
            "validation": validation,
            "recommendation_quality_score": validation["score"],
            "recovery_priority_mode": recovery_priority_mode,
            "deferred_tasks": deferred_tasks,
        },
        reasoning_notes=notes,
    )


def generate_alternative_plans(user_state: UserState) -> dict[str, dict]:
    return {
        "primary": generate_daily_plan(user_state, "primary").to_dict(),
        "conservative": generate_daily_plan(user_state, "conservative").to_dict(),
        "high_performance": generate_daily_plan(user_state, "high_performance").to_dict(),
    }


def save_plan(plan: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
