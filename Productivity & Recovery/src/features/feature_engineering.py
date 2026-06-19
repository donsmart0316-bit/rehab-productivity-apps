from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


MASTER_SCHEMA = [
    "user_id",
    "date",
    "chronotype",
    "sleep_need",
    "sleep_hours",
    "sleep_quality",
    "sleep_deficit",
    "sleep_debt",
    "energy_level",
    "mood_score",
    "stress_level",
    "fatigue_score",
    "activity_minutes",
    "work_hours",
    "meeting_hours",
    "task_count",
    "task_complexity",
    "task_load_score",
    "cumulative_load",
    "productivity_score",
    "productivity_trend",
    "burnout_score",
    "burnout_momentum",
    "recovery_score",
    "day_of_week",
    "is_weekend",
]


NON_NUMERIC_COLUMNS = {"user_id", "date", "chronotype", "day_of_week"}
NUMERIC_COLUMNS = [column for column in MASTER_SCHEMA if column not in NON_NUMERIC_COLUMNS]


@dataclass(frozen=True)
class FeatureConfig:
    target_sleep_hours: float = 8.0
    rolling_window_days: int = 7


def clip_series(series: pd.Series, lower: float, upper: float) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").clip(lower, upper)


def normalize_0_100(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    minimum = values.min()
    maximum = values.max()
    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(np.full(len(values), 50.0), index=values.index)
    return ((values - minimum) / (maximum - minimum) * 100).clip(0, 100)


def normalize_scale(series: pd.Series, source_min: float, source_max: float, target_max: float = 100.0) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    scaled = (values - source_min) / (source_max - source_min) * target_max
    return scaled.clip(0, target_max)


def infer_circadian_phase(hour: pd.Series | Iterable[int]) -> pd.Series:
    values = pd.Series(hour).astype(int)
    return pd.cut(
        values,
        bins=[-1, 10, 14, 18, 23],
        labels=["Morning", "Midday", "Afternoon", "Evening"],
    ).astype(str)


def estimate_chronotype(df: pd.DataFrame) -> pd.Series:
    if "chronotype" in df.columns:
        return df["chronotype"].fillna("Intermediate")
    if "peak_productivity_hour" in df.columns:
        hour = pd.to_numeric(df["peak_productivity_hour"], errors="coerce")
        return pd.cut(
            hour,
            bins=[0, 10, 15, 24],
            labels=["Morning", "Intermediate", "Evening"],
            include_lowest=True,
        ).astype(str).fillna("Intermediate")
    return pd.Series("Intermediate", index=df.index)


def add_engineered_features(df: pd.DataFrame, config: FeatureConfig | None = None) -> pd.DataFrame:
    config = config or FeatureConfig()
    output = df.copy()
    output["_original_order"] = np.arange(len(output))
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output = output.sort_values(["user_id", "date"]).reset_index(drop=True)

    for column in NUMERIC_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")

    if "sleep_need" not in output.columns:
        output["sleep_need"] = config.target_sleep_hours
    output["sleep_need"] = pd.to_numeric(output["sleep_need"], errors="coerce").fillna(config.target_sleep_hours)

    output["day_of_week"] = output["date"].dt.day_name()
    output["is_weekend"] = output["date"].dt.dayofweek.ge(5).astype(int)

    daily_deficit = (output["sleep_need"] - output["sleep_hours"]).clip(lower=0)
    output["sleep_deficit"] = output.get("sleep_deficit", daily_deficit)
    output["sleep_deficit"] = pd.to_numeric(output["sleep_deficit"], errors="coerce").fillna(daily_deficit)
    output["sleep_debt"] = (
        output["sleep_deficit"].groupby(output["user_id"])
        .rolling(config.rolling_window_days, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
        .clip(0, 30)
    )

    output["cumulative_load"] = (
        (output["work_hours"].fillna(0) + output["meeting_hours"].fillna(0) + output["task_complexity"].fillna(0))
        .groupby(output["user_id"])
        .rolling(config.rolling_window_days, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
    )

    output["task_load_score"] = (
        output["task_count"].fillna(0) * 2.5
        + output["work_hours"].fillna(0) * 6
        + output["meeting_hours"].fillna(0) * 5
        + output["task_complexity"].fillna(0) * 7
    ).clip(0, 100)

    output["recovery_score"] = (
        output.get("recovery_score", pd.Series(np.nan, index=output.index)).fillna(
            45
            + output["sleep_quality"].fillna(5) * 4
            + output["activity_minutes"].fillna(30) * 0.12
            - output["stress_level"].fillna(5) * 3.5
            - output["fatigue_score"].fillna(5) * 2.2
            - output["sleep_debt"].fillna(0) * 1.8
        )
    ).clip(0, 100)

    output["burnout_momentum"] = (
        output.groupby("user_id")["burnout_score"]
        .diff()
        .rolling(config.rolling_window_days, min_periods=1)
        .mean()
        .fillna(0)
    )
    output["productivity_trend"] = (
        output.groupby("user_id")["productivity_score"]
        .diff()
        .rolling(config.rolling_window_days, min_periods=1)
        .mean()
        .fillna(0)
    )

    if "hour" in output.columns:
        output["circadian_phase"] = infer_circadian_phase(output["hour"])
    else:
        output["circadian_phase"] = "Daily"
    output["time_of_day_bin"] = output["circadian_phase"]
    output["chronotype"] = estimate_chronotype(output)
    output["chronotype_proxy"] = output["chronotype"]

    return output.sort_values("_original_order").drop(columns="_original_order").reset_index(drop=True)


def impute_master_schema(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    for column in MASTER_SCHEMA:
        if column not in output.columns:
            output[column] = np.nan

    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["date"] = output["date"].fillna(pd.Timestamp("2026-01-01"))
    fallback_user_ids = pd.Series(pd.RangeIndex(1, len(output) + 1).astype(str), index=output.index)
    output["user_id"] = output["user_id"].fillna(fallback_user_ids)
    output["chronotype"] = output.get("chronotype", pd.Series("Intermediate", index=output.index)).fillna("Intermediate")
    output["day_of_week"] = output.get("day_of_week", output["date"].dt.day_name()).fillna(output["date"].dt.day_name())

    defaults = {
        "sleep_need": 8.0,
        "sleep_hours": 7.0,
        "sleep_quality": 6.0,
        "sleep_deficit": np.nan,
        "sleep_debt": np.nan,
        "energy_level": 6.0,
        "mood_score": 6.0,
        "stress_level": 5.0,
        "fatigue_score": 5.0,
        "activity_minutes": 35.0,
        "work_hours": 8.0,
        "meeting_hours": 1.5,
        "task_count": 6.0,
        "task_complexity": 5.0,
        "task_load_score": np.nan,
        "cumulative_load": np.nan,
        "productivity_score": 65.0,
        "productivity_trend": np.nan,
        "burnout_score": 25.0,
        "burnout_momentum": np.nan,
        "recovery_score": 65.0,
        "is_weekend": np.nan,
    }
    for column, default in defaults.items():
        output[column] = pd.to_numeric(output[column], errors="coerce").fillna(default)

    output["is_weekend"] = output["is_weekend"].fillna(output["date"].dt.dayofweek.ge(5).astype(int)).astype(int)
    engineered = add_engineered_features(output)
    for column in ["sleep_deficit", "sleep_debt", "task_load_score", "cumulative_load", "productivity_trend", "burnout_momentum", "day_of_week", "is_weekend", "chronotype"]:
        output[column] = engineered[column]

    output["sleep_need"] = clip_series(output["sleep_need"], 4, 12)
    output["sleep_hours"] = clip_series(output["sleep_hours"], 0, 14)
    output["sleep_quality"] = clip_series(output["sleep_quality"], 0, 10)
    output["sleep_deficit"] = clip_series(output["sleep_deficit"], 0, 12)
    output["sleep_debt"] = clip_series(output["sleep_debt"], 0, 30)
    output["energy_level"] = clip_series(output["energy_level"], 0, 10)
    output["mood_score"] = clip_series(output["mood_score"], 0, 10)
    output["stress_level"] = clip_series(output["stress_level"], 0, 10)
    output["fatigue_score"] = clip_series(output["fatigue_score"], 0, 10)
    output["activity_minutes"] = clip_series(output["activity_minutes"], 0, 240)
    output["work_hours"] = clip_series(output["work_hours"], 0, 16)
    output["meeting_hours"] = clip_series(output["meeting_hours"], 0, 12)
    output["task_count"] = clip_series(output["task_count"], 0, 30)
    output["task_complexity"] = clip_series(output["task_complexity"], 0, 10)
    output["task_load_score"] = clip_series(output["task_load_score"], 0, 100)
    output["cumulative_load"] = clip_series(output["cumulative_load"], 0, 700)
    output["productivity_score"] = clip_series(output["productivity_score"], 0, 100)
    output["productivity_trend"] = clip_series(output["productivity_trend"], -100, 100)
    output["burnout_score"] = clip_series(output["burnout_score"], 0, 100)
    output["burnout_momentum"] = clip_series(output["burnout_momentum"], -100, 100)
    output["recovery_score"] = clip_series(output["recovery_score"], 0, 100)
    return output[MASTER_SCHEMA].drop_duplicates().reset_index(drop=True)
