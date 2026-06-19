from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {}
    for key, value in row.items():
        if isinstance(value, (dict, list, tuple)):
            serializable[key] = json.dumps(value)
        else:
            serializable[key] = value
    frame = pd.DataFrame([serializable])
    frame.to_csv(path, mode="a", header=not path.exists(), index=False)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_prediction(project_root: Path, profile: dict[str, Any], checkin: dict[str, Any], prediction: dict[str, Any], plan: dict[str, Any]) -> None:
    schedule = plan.get("schedule", [])
    breaks = [item for item in schedule if item.get("item_type") == "break"]
    focus_blocks = [item for item in schedule if item.get("task_category") in {"Deep Work", "Creative Work", "Learning"}]
    _append_csv(
        project_root / "logs" / "prediction_logs.csv",
        {
            "timestamp_utc": utc_now(),
            "user_id": profile.get("name", "user").lower().replace(" ", "_"),
            "date": checkin.get("date"),
            "productivity_score": prediction.get("productivity_score"),
            "burnout_risk": prediction.get("burnout_risk"),
            "recovery_score": prediction.get("recovery_score"),
            "sleep_debt": prediction.get("sleep_debt"),
            "productivity_confidence": prediction.get("productivity_confidence"),
            "burnout_confidence": prediction.get("burnout_confidence"),
            "recommendation_confidence": prediction.get("recommendation_confidence"),
            "schedule_items": len(schedule),
            "breaks": len(breaks),
            "focus_blocks": len(focus_blocks),
            "input_warnings": prediction.get("input_warnings", []),
        },
    )


def log_feedback(project_root: Path, user_id: str, date: str, feedback: dict[str, Any]) -> None:
    _append_csv(project_root / "logs" / "feedback_logs.csv", {"timestamp_utc": utc_now(), "user_id": user_id, "date": date, **feedback})


def log_system_event(project_root: Path, level: str, event: str, details: dict[str, Any] | None = None) -> None:
    _append_csv(project_root / "logs" / "system_logs.csv", {"timestamp_utc": utc_now(), "level": level, "event": event, "details": details or {}})
