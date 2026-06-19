from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd

from src.features.feature_engineering import MASTER_SCHEMA, impute_master_schema, normalize_0_100, normalize_scale


COLUMN_ALIASES = {
    "sleep duration": "sleep_hours",
    "sleep_duration": "sleep_hours",
    "quality of sleep": "sleep_quality",
    "sleep quality": "sleep_quality",
    "stress level": "stress_level",
    "stress_level": "stress_level",
    "physical activity level": "activity_minutes",
    "physical_activity": "activity_minutes",
    "daily steps": "activity_minutes",
    "heart rate": "heart_rate",
    "mental fatigue score": "fatigue_score",
    "mental_fatigue_score": "fatigue_score",
    "burn rate": "burnout_score",
    "burnout score": "burnout_score",
    "resource allocation": "work_hours",
    "designation": "task_complexity",
    "work hours": "work_hours",
    "working hours": "work_hours",
    "meetings": "meeting_hours",
    "meeting hours": "meeting_hours",
    "productivity": "productivity_score",
    "productivity score": "productivity_score",
    "task completion rate": "productivity_score",
    "task_completion_rate": "productivity_score",
    "meetings count": "meeting_hours",
    "meetings_count": "meeting_hours",
    "study hours per day": "work_hours",
    "study_hours_per_day": "work_hours",
    "sleep hours per day": "sleep_hours",
    "sleep_hours_per_day": "sleep_hours",
    "physical activity hours per day": "activity_minutes",
    "physical_activity_hours_per_day": "activity_minutes",
    "gpa": "productivity_score",
}


STRESS_TEXT_SCALE = {
    "low": 3.0,
    "moderate": 5.5,
    "medium": 5.5,
    "high": 8.0,
}


def clean_column_name(column: str) -> str:
    return column.strip().lower().replace("-", " ").replace("_", " ")


def standardize_frame(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    renamed = {}
    for column in df.columns:
        cleaned = clean_column_name(column)
        renamed[column] = COLUMN_ALIASES.get(cleaned, cleaned.replace(" ", "_"))
    output = df.rename(columns=renamed).copy()
    if output.columns.duplicated().any():
        output = output.T.groupby(level=0).first().T

    if "employee_id" in output.columns and "user_id" not in output.columns:
        output["user_id"] = "employee_" + output["employee_id"].astype(str)
    elif "person_id" in output.columns and "user_id" not in output.columns:
        output["user_id"] = "sleep_" + output["person_id"].astype(str)
    elif "student_id" in output.columns and "user_id" not in output.columns:
        output["user_id"] = "student_" + output["student_id"].astype(str)
    elif "user_id" in output.columns:
        output["user_id"] = source_name + "_" + output["user_id"].astype(str)
    else:
        output["user_id"] = [f"{source_name}_{idx + 1:06d}" for idx in range(len(output))]

    if source_name.startswith("work_from_home") and "date" not in output.columns:
        day_index = output.groupby("user_id").cumcount()
        output["date"] = pd.Timestamp("2026-01-01") + pd.to_timedelta(day_index, unit="D")
    elif "date" not in output.columns:
        output["date"] = pd.Timestamp("2026-01-01")

    if "physical_activity_level" in output.columns and "activity_minutes" not in output.columns:
        output["activity_minutes"] = output["physical_activity_level"]
    if "daily_steps" in output.columns and "activity_minutes" not in output.columns:
        output["activity_minutes"] = pd.to_numeric(output["daily_steps"], errors="coerce") / 120
    if "physical_activity_hours_per_day" in output.columns:
        output["activity_minutes"] = pd.to_numeric(output["physical_activity_hours_per_day"], errors="coerce") * 60
    if "extracurricular_hours_per_day" in output.columns:
        output["task_complexity"] = pd.to_numeric(output["extracurricular_hours_per_day"], errors="coerce") * 2
    if "meetings_count" in output.columns:
        output["meeting_hours"] = pd.to_numeric(output["meetings_count"], errors="coerce") * 0.5
    if "screen_time_hours" in output.columns:
        screen_time = pd.to_numeric(output["screen_time_hours"], errors="coerce")
        output["fatigue_score"] = (screen_time / 12 * 10).clip(0, 10)
    if "breaks_taken" in output.columns:
        breaks = pd.to_numeric(output["breaks_taken"], errors="coerce")
        output["recovery_score"] = (45 + breaks * 8 + output.get("sleep_hours", 7) * 3).clip(0, 100)
    if "after_hours_work" in output.columns:
        output["stress_level"] = output.get("stress_level", 4) + pd.to_numeric(output["after_hours_work"], errors="coerce").fillna(0) * 1.5
    if "resource_allocation" in output.columns:
        output["work_hours"] = (pd.to_numeric(output["resource_allocation"], errors="coerce") * 1.6).clip(0, 16)
    if "designation" in output.columns:
        output["task_complexity"] = (pd.to_numeric(output["designation"], errors="coerce") * 2).clip(0, 10)
    if "mental_fatigue_score" in output.columns:
        output["fatigue_score"] = pd.to_numeric(output["mental_fatigue_score"], errors="coerce")
    if "burn_rate" in output.columns:
        output["burnout_score"] = pd.to_numeric(output["burn_rate"], errors="coerce") * 100
    if "gpa" in output.columns:
        output["productivity_score"] = (pd.to_numeric(output["gpa"], errors="coerce") / 4.0 * 100).clip(0, 100)
    if "study_hours_per_day" in output.columns:
        output["task_count"] = (pd.to_numeric(output["study_hours_per_day"], errors="coerce") / 1.5).round().clip(0, 16)
    if source_name.startswith("student") and "activity_minutes" in output.columns:
        output["activity_minutes"] = pd.to_numeric(output["activity_minutes"], errors="coerce") * 60
    if source_name.startswith("work_from_home") and "meeting_hours" in output.columns:
        output["meeting_hours"] = pd.to_numeric(output["meeting_hours"], errors="coerce") * 0.5
    if source_name == "train" and "work_hours" in output.columns:
        output["work_hours"] = (pd.to_numeric(output["work_hours"], errors="coerce") * 1.6).clip(0, 16)

    scale_10_columns = ["sleep_quality", "energy_level", "mood_score", "stress_level", "fatigue_score", "task_complexity"]
    for column in scale_10_columns:
        if column in output.columns:
            if output[column].dtype == "object":
                output[column] = output[column].astype(str).str.lower().map(STRESS_TEXT_SCALE)
            output[column] = normalize_scale(output[column], 0, 10, 10)

    for column in ["productivity_score", "burnout_score", "recovery_score"]:
        if column in output.columns:
            values = pd.to_numeric(output[column], errors="coerce")
            if values.max(skipna=True) is not None and values.max(skipna=True) <= 1.0:
                output[column] = values * 100
            elif values.max(skipna=True) is not None and values.max(skipna=True) <= 10.0:
                output[column] = normalize_scale(values, 0, 10, 100)
            else:
                output[column] = values.clip(0, 100)

    if "productivity_score" not in output.columns:
        output["productivity_score"] = normalize_0_100(
            70
            + output.get("sleep_hours", 7) * 3
            - output.get("stress_level", 5) * 4
            - output.get("fatigue_score", 5) * 3
        )
    if "recovery_score" not in output.columns:
        output["recovery_score"] = normalize_0_100(
            60
            + output.get("sleep_hours", 7) * 4
            + output.get("activity_minutes", 30) * 0.1
            - output.get("stress_level", 5) * 5
            - output.get("fatigue_score", 5) * 3
        )
    if "burnout_score" not in output.columns:
        output["burnout_score"] = normalize_0_100(
            output.get("stress_level", 5) * 8 + output.get("fatigue_score", 5) * 7 + output.get("work_hours", 8) * 3
        )

    standardized = impute_master_schema(output)
    for column in [column for column in standardized.columns if column in output.columns and column not in {"user_id", "date"}]:
        source_values = pd.to_numeric(output[column], errors="coerce")
        if source_values.notna().any():
            standardized[column] = standardized[column].where(source_values.notna(), source_values.median())
    return impute_master_schema(standardized)


def load_raw_csvs(raw_root: Path) -> list[pd.DataFrame]:
    frames = []
    for csv_path in raw_root.rglob("*.csv"):
        if "download_manifest" in csv_path.name:
            continue
        try:
            frames.append(standardize_frame(pd.read_csv(csv_path), csv_path.parent.name))
        except Exception as exc:
            print(f"Skipping {csv_path}: {exc}")
    return frames


def load_kaggle_archives(kaggle_root: Path) -> list[pd.DataFrame]:
    frames = []
    if not kaggle_root.exists():
        return frames
    for zip_path in sorted(kaggle_root.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.namelist():
                lower = member.lower()
                if not lower.endswith(".csv") or "sample_submission" in lower or lower == "test.csv":
                    continue
                with archive.open(member) as file:
                    df = pd.read_csv(file)
                source_name = Path(member).stem.lower()
                frames.append(standardize_frame(df, source_name))
    return frames


def build_master(project_root: Path) -> pd.DataFrame:
    raw_frames = load_kaggle_archives(project_root / "kaggle data") + load_raw_csvs(project_root / "data" / "raw")
    synthetic_path = project_root / "data" / "synthetic" / "synthetic_productivity_dataset.csv"
    if raw_frames:
        master = pd.concat(raw_frames, ignore_index=True)
    elif synthetic_path.exists():
        master = impute_master_schema(pd.read_csv(synthetic_path))
    else:
        master = pd.DataFrame(columns=MASTER_SCHEMA)

    master = impute_master_schema(master)
    output_path = project_root / "data" / "processed" / "master_dataset.csv"
    root_output_path = project_root / "master_dataset.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(output_path, index=False)
    master.to_csv(root_output_path, index=False)
    return master


def main() -> None:
    parser = argparse.ArgumentParser(description="Build unified master dataset.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    master = build_master(args.project_root)
    print(f"Wrote {len(master):,} rows to data/processed/master_dataset.csv")


if __name__ == "__main__":
    main()
