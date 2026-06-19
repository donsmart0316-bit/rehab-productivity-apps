from __future__ import annotations

import hashlib

import pandas as pd

from app.services.feedback_service import load_feedback
from app.services.history_service import load_daily_history


def anonymized_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]


def period_summary(history: pd.DataFrame, period: str) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame()
    frame = history.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["period"] = frame["date"].dt.to_period(period).astype(str)
    risk_map = {"Low": 1, "Medium": 2, "High": 3}
    frame["burnout_index"] = frame["burnout_risk"].map(risk_map).fillna(2)
    return (
        frame.groupby("period", as_index=False)
        .agg(
            productivity_score=("productivity_score", "mean"),
            recovery_score=("recovery_score", "mean"),
            sleep_debt=("sleep_debt", "mean"),
            burnout_index=("burnout_index", "mean"),
            records=("date", "count"),
        )
        .round(2)
    )


def habit_consistency(history: pd.DataFrame) -> dict[str, float]:
    if history.empty:
        return {"sleep_consistency": 0.0, "activity_consistency": 0.0, "checkin_days": 0}
    sleep_std = float(history["sleep_hours"].std()) if "sleep_hours" in history else 2.0
    activity_std = float(history["activity_minutes"].std()) if "activity_minutes" in history else 80.0
    return {
        "sleep_consistency": round(max(0, 100 - sleep_std * 22), 1),
        "activity_consistency": round(max(0, 100 - activity_std * 0.9), 1),
        "checkin_days": int(len(history)),
    }


def adherence_score(user_id: str) -> float | None:
    feedback = load_feedback()
    if feedback.empty or "actual_plan_followed" not in feedback.columns:
        return None
    user_feedback = feedback[feedback["user_id"] == user_id] if "user_id" in feedback.columns else feedback
    if user_feedback.empty:
        return None
    followed = user_feedback["actual_plan_followed"].astype(str).str.contains("true", case=False, regex=False)
    return round(float(followed.mean() * 100), 1)


def aggregate_insights(history: pd.DataFrame) -> list[str]:
    if history.empty or len(history) < 3:
        return ["More records are needed before aggregate insights become reliable."]
    insights: list[str] = []
    high_sleep = history[history["sleep_quality"] >= 8]
    lower_sleep = history[history["sleep_quality"] < 8]
    if len(high_sleep) >= 2 and len(lower_sleep) >= 2:
        lift = high_sleep["productivity_score"].mean() - lower_sleep["productivity_score"].mean()
        insights.append(f"Days with sleep quality above 8 averaged {lift:.1f} productivity points higher than other days.")
    low_debt = history[history["sleep_debt"] <= 2]
    high_debt = history[history["sleep_debt"] > 2]
    if len(low_debt) >= 2 and len(high_debt) >= 2:
        lift = low_debt["recovery_score"].mean() - high_debt["recovery_score"].mean()
        insights.append(f"Low sleep-debt days averaged {lift:.1f} recovery points higher than higher-debt days.")
    if not insights:
        insights.append("Current history is directionally useful, but more varied records are needed for robust patterns.")
    return insights
