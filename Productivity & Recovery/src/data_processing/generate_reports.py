from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd


DATA_DICTIONARY = {
    "user_id": "Stable anonymized user identifier.",
    "date": "Daily record date.",
    "chronotype": "Morning, Intermediate, or Evening productivity timing profile.",
    "sleep_need": "Estimated individual sleep requirement in hours.",
    "sleep_hours": "Total sleep duration for the previous night, hours.",
    "sleep_quality": "Sleep quality on a 0-10 scale.",
    "sleep_deficit": "Daily sleep shortfall relative to sleep need.",
    "sleep_debt": "Rolling sleep deficit over the recent window.",
    "energy_level": "Perceived energy on a 0-10 scale.",
    "mood_score": "Mood on a 0-10 scale.",
    "stress_level": "Stress on a 0-10 scale.",
    "fatigue_score": "Fatigue on a 0-10 scale.",
    "activity_minutes": "Daily physical activity minutes.",
    "work_hours": "Daily working hours.",
    "meeting_hours": "Daily meeting hours.",
    "task_count": "Number of planned or completed work tasks.",
    "task_complexity": "Average task complexity on a 0-10 scale.",
    "task_load_score": "Combined workload pressure score from task count, work hours, meetings, and complexity.",
    "cumulative_load": "Rolling workload over the recent window.",
    "productivity_score": "Productivity outcome score on a 0-100 scale.",
    "productivity_trend": "Rolling productivity change rate.",
    "burnout_score": "Burnout risk/severity score on a 0-100 scale.",
    "burnout_momentum": "Rolling burnout change rate.",
    "recovery_score": "Recovery capacity score on a 0-100 scale.",
    "day_of_week": "Calendar day name.",
    "is_weekend": "Weekend indicator, 1 for Saturday/Sunday and 0 otherwise.",
}


def markdown_table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=True)


def generate_reports(project_root: Path) -> None:
    reports_root = project_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    master = pd.read_csv(project_root / "data" / "processed" / "master_dataset.csv", parse_dates=["date"])
    synthetic = pd.read_csv(project_root / "data" / "synthetic" / "synthetic_productivity_dataset.csv", parse_dates=["date"])
    manifest_path = project_root / "data" / "raw" / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    local_archives = []
    for zip_path in sorted((project_root / "kaggle data").glob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            csv_files = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        local_archives.append({"archive": zip_path.name, "csv_files": csv_files})

    missing = pd.DataFrame({"missing_count": master.isna().sum(), "missing_percent": master.isna().mean() * 100})
    numeric = master.select_dtypes(include="number")
    correlations = numeric[
        ["sleep_hours", "sleep_quality", "stress_level", "fatigue_score", "activity_minutes", "work_hours", "productivity_score", "burnout_score", "recovery_score"]
    ].corr()

    report = [
        "# Dataset Analysis",
        "",
        "## Source Datasets",
        "",
        "The project is configured for three Kaggle datasets: Sleep Health & Lifestyle, Employee Burnout, and Work From Home Employee Burnout. The downloader writes a manifest to `data/raw/download_manifest.json` so authentication or dataset availability issues are auditable.",
        "",
        "Current Kaggle download status:",
        "",
    ]
    if local_archives:
        report.append("Local Kaggle archives found in `kaggle data` and used by the master dataset builder:")
        report.append("")
        for archive in local_archives:
            report.append(f"- `{archive['archive']}`: {', '.join(archive['csv_files'])}")
        report.append("")
        report.append("Downloader manifest status, kept for reproducibility:")
        report.append("")
    for item in manifest:
        report.append(f"- `{item.get('slug')}`: {'ok' if item.get('ok') else 'not downloaded'}; files={len(item.get('files', []))}; detail={item.get('stderr', '')[:120]}")

    report.extend(
        [
            "",
            "## Unified Master Dataset",
            "",
            f"- Rows: {len(master):,}",
            f"- Users: {master['user_id'].nunique():,}",
            f"- Date range: {master['date'].min().date()} to {master['date'].max().date()}",
            "- Schema: daily user-level records aligned to recovery, workload, productivity, and burnout modeling.",
            "",
            "## Missing Values",
            "",
            markdown_table(missing),
            "",
            "## Numeric Summary",
            "",
            markdown_table(numeric.describe().T.round(2)),
            "",
            "## Data Dictionary",
            "",
        ]
    )
    for column, description in DATA_DICTIONARY.items():
        report.append(f"- `{column}`: {description}")

    report.extend(
        [
            "",
            "## Modeling Readiness",
            "",
            "- Numerical features are clipped to documented ranges.",
            "- Missing values are imputed with conservative defaults.",
            "- Duplicate rows are removed during master dataset construction.",
            "- Synthetic daily records preserve realistic directional relationships among sleep, energy, stress, activity, work, productivity, recovery, and burnout.",
        ]
    )
    (reports_root / "dataset_analysis.md").write_text("\n".join(report), encoding="utf-8")

    summary = [
        "# EDA Summary",
        "",
        "## Key Relationships",
        "",
        f"- Sleep vs productivity correlation: {correlations.loc['sleep_hours', 'productivity_score']:.3f}",
        f"- Sleep vs recovery correlation: {correlations.loc['sleep_hours', 'recovery_score']:.3f}",
        f"- Stress vs burnout correlation: {correlations.loc['stress_level', 'burnout_score']:.3f}",
        f"- Recovery vs productivity correlation: {correlations.loc['recovery_score', 'productivity_score']:.3f}",
        f"- Work hours vs burnout correlation: {correlations.loc['work_hours', 'burnout_score']:.3f}",
        f"- Activity vs recovery correlation: {correlations.loc['activity_minutes', 'recovery_score']:.3f}",
        "",
        "## Synthetic Longitudinal Dataset",
        "",
        f"- Rows: {len(synthetic):,}",
        f"- Users: {synthetic['user_id'].nunique():,}",
        f"- Chronotypes: {synthetic['chronotype'].value_counts().to_dict()}",
        "- Includes sleep debt, cumulative load, task load score, burnout momentum, productivity trend, focus block length, break duration, cognitive load, and chronotype.",
        "",
        "## Recommended Imputation",
        "",
        "- Median imputation for continuous model features when training tabular models.",
        "- User-level forward fill for longitudinal app telemetry.",
        "- Add missingness indicators for future real-world sparse inputs.",
    ]
    (reports_root / "eda_summary.md").write_text("\n".join(summary), encoding="utf-8")

    dictionary_lines = ["# Data Dictionary", ""]
    for column, description in DATA_DICTIONARY.items():
        dictionary_lines.append(f"- `{column}`: {description}")
    (reports_root / "data_dictionary.md").write_text("\n".join(dictionary_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Markdown reports for Phase 1.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    generate_reports(args.project_root)
    print("Wrote reports/dataset_analysis.md, reports/eda_summary.md, and reports/data_dictionary.md")


if __name__ == "__main__":
    main()
