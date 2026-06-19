from __future__ import annotations

from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.bootstrap import PROJECT_ROOT
from app.services.history_service import read_daily_records


FEATURE_PATH = PROJECT_ROOT / "models" / "model_metadata.json"
REASONABLE_RANGES = {
    "sleep_hours": (3.0, 10.5, 7.0),
    "sleep_quality": (0.0, 10.0, 6.0),
    "energy_level": (0.0, 10.0, 6.0),
    "mood_score": (0.0, 10.0, 6.0),
    "stress_level": (0.0, 10.0, 5.0),
    "fatigue_score": (0.0, 10.0, 5.0),
    "activity_minutes": (0.0, 240.0, 35.0),
    "work_hours": (0.0, 14.0, 8.0),
    "meeting_hours": (0.0, 8.0, 1.5),
    "task_count": (0, 30, 4),
    "task_complexity": (0.0, 10.0, 5.0),
}


@lru_cache(maxsize=1)
def _productivity_model():
    return joblib.load(PROJECT_ROOT / "models" / "productivity_model.joblib")


def _last_sleep_debt(user_id: str) -> float:
    path = PROJECT_ROOT / "data" / "history" / "daily_records.csv"
    if not path.exists():
        return 0.0
    frame = read_daily_records()
    if frame.empty or "user_id" not in frame.columns or "sleep_debt" not in frame.columns:
        return 0.0
    user_rows = frame[frame["user_id"] == user_id]
    if user_rows.empty:
        return 0.0
    return float(pd.to_numeric(user_rows.iloc[-1]["sleep_debt"], errors="coerce") or 0.0)


def _history_count(user_id: str) -> int:
    path = PROJECT_ROOT / "data" / "history" / "daily_records.csv"
    if not path.exists():
        return 0
    frame = read_daily_records()
    if frame.empty or "user_id" not in frame.columns:
        return 0
    return int((frame["user_id"] == user_id).sum())


def sanitize_checkin(checkin: dict[str, Any]) -> tuple[dict[str, Any], list[str], float]:
    sanitized = dict(checkin)
    warnings: list[str] = []
    provided = 0
    for key, (low, high, default) in REASONABLE_RANGES.items():
        raw = sanitized.get(key)
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            sanitized[key] = default
            warnings.append(f"{key} was missing and was filled with {default}.")
            continue
        provided += 1
        value = float(raw)
        clipped = float(np.clip(value, low, high))
        if clipped != value:
            warnings.append(f"{key} was outside the expected range and was clipped to {clipped}.")
        sanitized[key] = int(clipped) if key in {"task_count"} else clipped
    if sanitized["meeting_hours"] > sanitized["work_hours"]:
        sanitized["meeting_hours"] = sanitized["work_hours"]
        warnings.append("meeting_hours exceeded work_hours and was capped at work_hours.")
    completeness = provided / len(REASONABLE_RANGES)
    return sanitized, warnings, completeness


def consistency_warnings(row: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if row["sleep_hours"] <= 4.5 and row["energy_level"] >= 8:
        warnings.append("Energy is very high despite severe sleep loss; confidence is reduced.")
    if row["stress_level"] <= 2 and row["fatigue_score"] >= 8:
        warnings.append("Fatigue is very high despite low stress; confidence is reduced.")
    if row["sleep_quality"] <= 3 and row["mood_score"] >= 8:
        warnings.append("Mood is very high despite poor sleep quality; confidence is reduced.")
    if row["work_hours"] >= 12 and row["stress_level"] <= 2:
        warnings.append("Very high workload with very low stress may indicate underreported stress.")
    return warnings


def confidence_label(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    return "Low"


def confidence_scores(profile: dict[str, Any], checkin: dict[str, Any], row: dict[str, Any], completeness: float, warnings: list[str]) -> dict[str, Any]:
    user_id = profile["name"].lower().replace(" ", "_")
    history_count = _history_count(user_id)
    history_bonus = min(history_count, 14) / 14 * 15
    consistency_penalty = min(len(warnings) * 8, 28)
    edge_penalty = 0
    if row["sleep_hours"] <= 4 or row["stress_level"] >= 9 or row["work_hours"] >= 13:
        edge_penalty = 8
    base = 55 + completeness * 25 + history_bonus - consistency_penalty - edge_penalty
    productivity_confidence = float(np.clip(base, 35, 95))
    burnout_confidence = float(np.clip(base + (8 if row["stress_level"] >= 7 or row["sleep_debt"] >= 5 else 0), 35, 95))
    recommendation_confidence = float(np.clip((productivity_confidence + burnout_confidence) / 2 + 5, 35, 95))
    return {
        "productivity_confidence": round(productivity_confidence, 1),
        "productivity_confidence_label": confidence_label(productivity_confidence),
        "burnout_confidence": round(burnout_confidence, 1),
        "burnout_confidence_label": confidence_label(burnout_confidence),
        "recommendation_confidence": round(recommendation_confidence, 1),
        "recommendation_confidence_label": confidence_label(recommendation_confidence),
        "history_records": history_count,
        "input_completeness": round(completeness, 2),
        "input_warnings": warnings,
    }


def recovery_formula(row: dict[str, Any]) -> float:
    return float(
        np.clip(
            38
            + row["sleep_hours"] * 4.1
            + row["sleep_quality"] * 3.0
            + row["activity_minutes"] * 0.11
            - row["stress_level"] * 3.4
            - row["fatigue_score"] * 2.6
            - row.get("sleep_debt", 0) * 2.2
            - max(row.get("work_hours", 8) - 8, 0) * 1.5,
            0,
            100,
        )
    )


def calibrated_burnout_risk(row: dict[str, Any]) -> str:
    burnout_pressure = (
        0.22 * np.clip(row.get("sleep_debt", 0) / 12 * 100, 0, 100)
        + 0.20 * row.get("stress_level", 0) * 10
        + 0.18 * row.get("fatigue_score", 0) * 10
        + 0.15 * np.clip(row.get("cumulative_load", 0) / 20 * 100, 0, 100)
        + 0.10 * np.clip(row.get("work_hours", 0) / 14 * 100, 0, 100)
        + 0.25 * (100 - row.get("recovery_score", 50))
    )
    if burnout_pressure < 45:
        return "Low"
    if burnout_pressure < 62:
        return "Medium"
    return "High"


def adjusted_productivity(raw_prediction: float, row: dict[str, Any]) -> float:
    sleep_debt = row.get("sleep_debt", 0)
    stress = row.get("stress_level", 0)
    fatigue = row.get("fatigue_score", 0)
    recovery = row.get("recovery_score", 50)
    penalty = max(sleep_debt - 1.0, 0) * 2.35 + max(stress - 7.0, 0) * 1.15 + max(fatigue - 7.0, 0) * 1.35
    support = max(recovery - 70, 0) * 0.08
    return float(np.clip(raw_prediction + 8.0 - penalty + support, 0, 100))


def build_feature_row(profile: dict, checkin: dict) -> dict[str, Any]:
    user_id = profile["name"].lower().replace(" ", "_")
    date = pd.Timestamp(checkin["date"])
    sleep_need = float(checkin.get("sleep_need", profile.get("sleep_need", 8.0)))
    sleep_deficit = max(sleep_need - float(checkin["sleep_hours"]), 0)
    previous_debt = _last_sleep_debt(user_id)
    sleep_debt = float(np.clip(previous_debt * 0.72 + sleep_deficit, 0, 30))
    task_load = float(
        np.clip(
            checkin["task_count"] * 2.2
            + checkin["work_hours"] * 6
            + checkin["meeting_hours"] * 4.5
            + checkin["task_complexity"] * 6.5,
            0,
            100,
        )
    )
    cumulative_load = task_load / 5
    row = {
        "sleep_need": sleep_need,
        "sleep_hours": checkin["sleep_hours"],
        "sleep_quality": checkin["sleep_quality"],
        "sleep_deficit": sleep_deficit,
        "sleep_debt": sleep_debt,
        "energy_level": checkin["energy_level"],
        "mood_score": checkin["mood_score"],
        "stress_level": checkin["stress_level"],
        "fatigue_score": checkin["fatigue_score"],
        "activity_minutes": checkin["activity_minutes"],
        "work_hours": checkin["work_hours"],
        "meeting_hours": checkin["meeting_hours"],
        "task_count": checkin["task_count"],
        "task_complexity": checkin["task_complexity"],
        "task_load_score": task_load,
        "cumulative_load": cumulative_load,
        "is_weekend": int(date.dayofweek >= 5),
        "chronotype": profile["chronotype"],
        "day_of_week": date.day_name(),
        "source_dataset": "streamlit_user",
    }
    row["recovery_score"] = recovery_formula(row)
    return row


def predict_daily(profile: dict, checkin: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    clean_checkin, validation_warnings, completeness = sanitize_checkin(checkin)
    row = build_feature_row(profile, clean_checkin)
    warnings = validation_warnings + consistency_warnings(row)
    raw = float(_productivity_model().predict(pd.DataFrame([row]))[0])
    prediction = {
        "productivity_score": round(adjusted_productivity(raw, row), 2),
        "burnout_risk": calibrated_burnout_risk(row),
        "recovery_score": round(float(row["recovery_score"]), 2),
        "sleep_debt": round(float(row["sleep_debt"]), 2),
        "task_load_score": round(float(row["task_load_score"]), 2),
    }
    prediction.update(confidence_scores(profile, clean_checkin, row, completeness, warnings))
    return prediction, row
