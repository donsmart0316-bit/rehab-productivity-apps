from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.bootstrap import PROJECT_ROOT
from src.monitoring.logger import log_prediction


HISTORY_DIR = PROJECT_ROOT / "data" / "history"
DAILY_PATH = HISTORY_DIR / "daily_records.csv"
PLAN_PATH = HISTORY_DIR / "plan_history.jsonl"
HISTORY_COLUMNS = [
    "user_id",
    "name",
    "date",
    "sleep_hours",
    "sleep_quality",
    "energy_level",
    "mood_score",
    "stress_level",
    "fatigue_score",
    "activity_minutes",
    "work_hours",
    "meeting_hours",
    "task_count",
    "task_complexity",
    "chronotype",
    "sleep_need",
    "sleep_debt",
    "task_load_score",
    "productivity_score",
    "burnout_risk",
    "recovery_score",
    "productivity_confidence",
    "burnout_confidence",
    "recommendation_confidence",
    "input_warnings",
]


def read_daily_records() -> pd.DataFrame:
    if not DAILY_PATH.exists():
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    try:
        frame = pd.read_csv(DAILY_PATH, names=HISTORY_COLUMNS, header=None, skiprows=1, engine="python", on_bad_lines="skip")
    except pd.errors.ParserError:
        frame = pd.read_csv(DAILY_PATH, names=HISTORY_COLUMNS, header=None, skiprows=1, engine="python", on_bad_lines="skip")
    for column in HISTORY_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[HISTORY_COLUMNS]


def repair_daily_history() -> None:
    if not DAILY_PATH.exists():
        return
    frame = read_daily_records()
    frame.to_csv(DAILY_PATH, index=False)


def append_daily_record(profile: dict, checkin: dict, prediction: dict, features: dict, primary_plan: dict, coaching_text: str) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "user_id": profile["name"].lower().replace(" ", "_"),
        "name": profile["name"],
        "date": checkin["date"],
        **{key: checkin[key] for key in checkin if key != "date"},
        "sleep_debt": prediction["sleep_debt"],
        "task_load_score": prediction["task_load_score"],
        "productivity_score": prediction["productivity_score"],
        "burnout_risk": prediction["burnout_risk"],
        "recovery_score": prediction["recovery_score"],
        "productivity_confidence": prediction.get("productivity_confidence"),
        "burnout_confidence": prediction.get("burnout_confidence"),
        "recommendation_confidence": prediction.get("recommendation_confidence"),
        "input_warnings": json.dumps(prediction.get("input_warnings", [])),
        "chronotype": profile["chronotype"],
    }
    frame = pd.DataFrame([row])
    for column in HISTORY_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[HISTORY_COLUMNS]
    if DAILY_PATH.exists():
        existing = read_daily_records()
        pd.concat([existing, frame], ignore_index=True).to_csv(DAILY_PATH, index=False)
    else:
        frame.to_csv(DAILY_PATH, index=False)
    with PLAN_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"profile": profile, "checkin": checkin, "prediction": prediction, "features": features, "plan": primary_plan, "coaching": coaching_text}) + "\n")
    log_prediction(PROJECT_ROOT, profile, checkin, prediction, primary_plan)


def load_daily_history(user_id: str | None = None) -> pd.DataFrame:
    if not DAILY_PATH.exists():
        return pd.DataFrame()
    frame = read_daily_records()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if user_id and "user_id" in frame.columns:
        frame = frame[frame["user_id"] == user_id]
    return frame.sort_values("date")


def load_plan_history() -> list[dict[str, Any]]:
    if not PLAN_PATH.exists():
        return []
    records = []
    with PLAN_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records
