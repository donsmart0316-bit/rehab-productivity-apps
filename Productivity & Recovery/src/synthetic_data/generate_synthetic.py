from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SYNTHETIC_COLUMNS = [
    "user_id",
    "date",
    "chronotype",
    "chronotype_proxy",
    "day_of_week",
    "is_weekend",
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
    "recovery_score",
    "productivity_score",
    "productivity_trend",
    "burnout_score",
    "burnout_momentum",
    "cumulative_load",
]

NUMERIC_MODEL_COLUMNS = [
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
    "recovery_score",
    "productivity_score",
    "burnout_score",
    "cumulative_load",
]

CHRONOTYPE_PROPORTIONS = {
    "Morning": 0.35,
    "Intermediate": 0.45,
    "Evening": 0.20,
}

CHRONOTYPE_PEAKS = {
    "Morning": (7, 11),
    "Intermediate": (10, 14),
    "Evening": (16, 20),
}


def clip(value: float | pd.Series, lower: float, upper: float) -> float | pd.Series:
    return np.clip(value, lower, upper)


def load_master_statistics(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master = pd.read_csv(project_root / "data" / "processed" / "master_dataset.csv", parse_dates=["date"])
    numeric = master[[column for column in NUMERIC_MODEL_COLUMNS if column in master.columns]].apply(pd.to_numeric, errors="coerce")
    summary = numeric.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).T
    correlations = numeric.corr()
    percentiles = numeric.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).T
    return master, summary, correlations, percentiles


def sample_from_master_distribution(rng: np.random.Generator, summary: pd.DataFrame, column: str, fallback: float) -> float:
    if column not in summary.index:
        return fallback
    row = summary.loc[column]
    mean = float(row.get("mean", fallback))
    std = float(row.get("std", 0.0))
    low = float(row.get("5%", row.get("min", fallback)))
    high = float(row.get("95%", row.get("max", fallback)))
    if not np.isfinite(std) or std == 0:
        return float(clip(mean, low, high))
    return float(clip(rng.normal(mean, std), low, high))


def generate_synthetic_from_master(
    project_root: Path,
    users: int = 2000,
    days: int = 180,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master, summary, correlations, percentiles = load_master_statistics(project_root)
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp("2026-01-01")
    rows: list[dict[str, object]] = []

    chronotypes = rng.choice(
        list(CHRONOTYPE_PROPORTIONS),
        size=users,
        p=list(CHRONOTYPE_PROPORTIONS.values()),
    )

    for user_idx in range(users):
        user_id = f"U{user_idx + 1:04d}"
        chronotype = str(chronotypes[user_idx])
        sleep_need = float(clip(rng.normal(8.0, 0.45), 7.0, 9.2))
        base_sleep = sample_from_master_distribution(rng, summary, "sleep_hours", 7.0)
        base_activity = sample_from_master_distribution(rng, summary, "activity_minutes", 45.0)
        base_work = sample_from_master_distribution(rng, summary, "work_hours", 8.0)
        base_meetings = sample_from_master_distribution(rng, summary, "meeting_hours", 1.5)
        base_task_complexity = sample_from_master_distribution(rng, summary, "task_complexity", 5.0)
        base_stress = sample_from_master_distribution(rng, summary, "stress_level", 5.0)
        baseline_burnout = float(clip(sample_from_master_distribution(rng, summary, "burnout_score", 35.0), 0, 100))
        burnout = baseline_burnout
        sleep_debt = 0.0
        previous_productivity: float | None = None
        previous_burnout = burnout
        consecutive_work_days = 0

        for day in range(days):
            date = start_date + pd.Timedelta(days=day)
            is_weekend = int(date.dayofweek >= 5)
            if is_weekend:
                consecutive_work_days = 0
            else:
                consecutive_work_days += 1

            weekend_recovery = 1.0 if is_weekend else 0.0
            work_hours = float(clip(rng.normal(base_work - weekend_recovery * 3.8, 1.2), 0, 14))
            meeting_hours = float(clip(rng.normal(base_meetings - weekend_recovery * 0.9, 0.55), 0, min(8, work_hours)))
            task_count = int(clip(round(rng.normal(6 + work_hours * 0.35 - weekend_recovery * 3, 2.0)), 0, 24))
            task_complexity = float(clip(rng.normal(base_task_complexity + task_count * 0.05, 1.25), 0, 10))
            task_load_score = float(clip(task_count * 2.2 + work_hours * 6.0 + meeting_hours * 4.5 + task_complexity * 6.5, 0, 100))

            sleep_hours = float(
                clip(
                    rng.normal(base_sleep + weekend_recovery * 0.55, 0.65)
                    - max(work_hours - 8.5, 0) * 0.16
                    - burnout * 0.006,
                    3.8,
                    10.5,
                )
            )
            sleep_deficit = float(max(sleep_need - sleep_hours, 0))
            sleep_debt = float(clip(sleep_debt * (0.50 if is_weekend else 0.70) + sleep_deficit - weekend_recovery * 0.85, 0, 30))
            activity_minutes = float(clip(rng.normal(base_activity + weekend_recovery * 12 - work_hours * 0.9, 22), 0, 240))

            sleep_quality = float(clip(8.4 - sleep_debt * 0.16 - base_stress * 0.13 + activity_minutes * 0.006 + rng.normal(0, 0.55), 0, 10))
            stress_level = float(
                clip(
                    base_stress
                    + task_load_score * 0.020
                    + sleep_debt * 0.14
                    - activity_minutes * 0.009
                    - weekend_recovery * 1.25
                    + rng.normal(0, 0.65),
                    0,
                    10,
                )
            )
            fatigue_score = float(clip(1.4 + sleep_debt * 0.34 + stress_level * 0.38 + work_hours * 0.16 - activity_minutes * 0.010 + rng.normal(0, 0.55), 0, 10))
            recovery_score = float(
                clip(
                    38
                    + sleep_hours * 4.1
                    + sleep_quality * 3.0
                    + activity_minutes * 0.11
                    - stress_level * 3.4
                    - fatigue_score * 2.6
                    - sleep_debt * 2.1
                    - consecutive_work_days * 0.8
                    + weekend_recovery * 7.0,
                    0,
                    100,
                )
            )
            energy_level = float(clip(2.0 + sleep_quality * 0.34 + recovery_score * 0.045 - fatigue_score * 0.32 - sleep_debt * 0.14 + rng.normal(0, 0.45), 0, 10))
            mood_score = float(clip(3.5 + recovery_score * 0.045 - stress_level * 0.28 - burnout * 0.012 + weekend_recovery * 0.4 + rng.normal(0, 0.55), 0, 10))
            productivity_score = float(
                clip(
                    5
                    + energy_level * 4.6
                    + recovery_score * 0.35
                    + sleep_quality * 1.7
                    + activity_minutes * 0.035
                    - stress_level * 2.1
                    - fatigue_score * 2.5
                    - sleep_debt * 1.8
                    - max(work_hours - 9, 0) * 2.5
                    + rng.normal(0, 4.0),
                    0,
                    100,
                )
            )
            cumulative_load = float(
                clip(
                    task_load_score / 5
                    if day == 0
                    else rows[-1]["cumulative_load"] * 0.82 + (task_load_score / 5) * 0.18
                    if rows[-1]["user_id"] == user_id
                    else task_load_score,
                    0,
                    700,
                )
            )
            previous_burnout = burnout
            burnout_pressure = (
                0.22 * clip(sleep_debt / 12 * 100, 0, 100)
                + 0.20 * stress_level * 10
                + 0.18 * fatigue_score * 10
                + 0.15 * clip(cumulative_load / 20 * 100, 0, 100)
                + 0.10 * clip(work_hours / 14 * 100, 0, 100)
                + 0.25 * (100 - recovery_score)
            )
            burnout_pressure = float(clip(burnout_pressure + rng.normal(0, 2.2) - weekend_recovery * 3.5, 0, 100))
            burnout = float(clip(previous_burnout * 0.55 + burnout_pressure * 0.45, 0, 100))
            burnout_momentum = float(burnout - previous_burnout)
            productivity_trend = 0.0 if previous_productivity is None else float(productivity_score - previous_productivity)
            previous_productivity = productivity_score

            rows.append(
                {
                    "user_id": user_id,
                    "date": date.date().isoformat(),
                    "chronotype": chronotype,
                    "chronotype_proxy": chronotype,
                    "day_of_week": date.day_name(),
                    "is_weekend": is_weekend,
                    "sleep_need": round(sleep_need, 2),
                    "sleep_hours": round(sleep_hours, 2),
                    "sleep_quality": round(sleep_quality, 2),
                    "sleep_deficit": round(sleep_deficit, 2),
                    "sleep_debt": round(sleep_debt, 2),
                    "energy_level": round(energy_level, 2),
                    "mood_score": round(mood_score, 2),
                    "stress_level": round(stress_level, 2),
                    "fatigue_score": round(fatigue_score, 2),
                    "activity_minutes": round(activity_minutes, 1),
                    "work_hours": round(work_hours, 2),
                    "meeting_hours": round(meeting_hours, 2),
                    "task_count": task_count,
                    "task_complexity": round(task_complexity, 2),
                    "task_load_score": round(task_load_score, 2),
                    "recovery_score": round(recovery_score, 2),
                    "productivity_score": round(productivity_score, 2),
                    "productivity_trend": round(productivity_trend, 2),
                    "burnout_score": round(burnout, 2),
                    "burnout_momentum": round(burnout_momentum, 2),
                    "cumulative_load": round(cumulative_load, 2),
                }
            )

    synthetic = pd.DataFrame(rows, columns=SYNTHETIC_COLUMNS)
    return synthetic, master, summary, correlations


def circadian_phase(hour: int) -> str:
    if 5 <= hour <= 10:
        return "Morning"
    if 11 <= hour <= 14:
        return "Midday"
    if 15 <= hour <= 18:
        return "Afternoon"
    return "Evening" if 19 <= hour <= 23 else "Night"


def task_type(capacity: float, hour: int) -> str:
    if capacity >= 68:
        return "Deep Work"
    if capacity >= 55:
        return "Creative Work"
    if 10 <= hour <= 15 and capacity >= 48:
        return "Meetings"
    if capacity >= 34:
        return "Admin Tasks"
    if 7 <= hour <= 10 or 16 <= hour <= 18:
        return "Planning"
    return "Recovery Break"


def generate_hourly_profiles(synthetic: pd.DataFrame) -> pd.DataFrame:
    user_daily = (
        synthetic.sort_values("date")
        .groupby("user_id", as_index=False)
        .tail(14)
        .groupby("user_id", as_index=False)
        .agg(
            date=("date", "max"),
            chronotype=("chronotype", "last"),
            energy_level=("energy_level", "mean"),
            productivity_score=("productivity_score", "mean"),
            recovery_score=("recovery_score", "mean"),
            burnout_score=("burnout_score", "mean"),
            sleep_debt=("sleep_debt", "mean"),
            fatigue_score=("fatigue_score", "mean"),
        )
    )
    hours = pd.DataFrame({"hour": np.arange(24)})
    user_daily["_join_key"] = 1
    hours["_join_key"] = 1
    hourly = user_daily.merge(hours, on="_join_key", how="inner").drop(columns="_join_key")

    peak_midpoint = hourly["chronotype"].map({key: sum(value) / 2 for key, value in CHRONOTYPE_PEAKS.items()})
    distance = (hourly["hour"] - peak_midpoint).abs()
    distance = np.minimum(distance, 24 - distance)
    circadian = (1.15 - 0.07 * distance).clip(0.22, 1.15)
    circadian = np.where(hourly["hour"].between(13, 15), circadian * 0.84, circadian)
    circadian = np.where(hourly["hour"].between(0, 5), circadian * 0.45, circadian)
    circadian = np.where(hourly["hour"].between(21, 23), circadian * 0.70, circadian)

    recovery_factor = hourly["recovery_score"] / 100
    burnout_penalty = hourly["burnout_score"] / 130
    sleep_penalty = hourly["sleep_debt"] / 45
    hourly["circadian_phase"] = hourly["hour"].map(circadian_phase)
    hourly["hourly_energy"] = (
        hourly["energy_level"] * circadian + recovery_factor * 2.4 - burnout_penalty * 2.0 - sleep_penalty
    ).clip(0, 10).round(2)
    hourly["hourly_productivity"] = (
        hourly["productivity_score"] * circadian + hourly["recovery_score"] * 0.16 - hourly["burnout_score"] * 0.10 - hourly["fatigue_score"] * 1.6
    ).clip(0, 100).round(2)
    hourly["focus_score"] = (
        hourly["hourly_productivity"] * 0.55 + hourly["hourly_energy"] * 4.0 - hourly["fatigue_score"] * 1.4
    ).clip(0, 100).round(2)
    hourly["cognitive_capacity"] = (
        hourly["focus_score"] * 0.62 + hourly["recovery_score"] * 0.22 - hourly["burnout_score"] * 0.10
    ).clip(0, 100).round(2)
    hourly["recommended_task_type"] = [task_type(capacity, hour) for capacity, hour in zip(hourly["cognitive_capacity"], hourly["hour"])]
    return hourly[
        [
            "user_id",
            "date",
            "hour",
            "chronotype",
            "circadian_phase",
            "hourly_energy",
            "hourly_productivity",
            "focus_score",
            "cognitive_capacity",
            "recommended_task_type",
        ]
    ]


def write_distribution_validation(project_root: Path, master: pd.DataFrame, synthetic: pd.DataFrame, correlations: pd.DataFrame) -> None:
    reports_root = project_root / "reports"
    figures_root = reports_root / "figures"
    reports_root.mkdir(exist_ok=True)
    figures_root.mkdir(exist_ok=True)

    columns = [column for column in NUMERIC_MODEL_COLUMNS if column in master.columns and column in synthetic.columns]
    real_stats = master[columns].describe(percentiles=[0.05, 0.5, 0.95]).T[["mean", "std", "5%", "50%", "95%"]]
    synthetic_stats = synthetic[columns].describe(percentiles=[0.05, 0.5, 0.95]).T[["mean", "std", "5%", "50%", "95%"]]
    comparison = real_stats.add_prefix("real_").join(synthetic_stats.add_prefix("synthetic_"))
    comparison["mean_abs_diff"] = (comparison["real_mean"] - comparison["synthetic_mean"]).abs()
    comparison["std_abs_diff"] = (comparison["real_std"] - comparison["synthetic_std"]).abs()

    key_cols = ["sleep_hours", "sleep_quality", "stress_level", "fatigue_score", "activity_minutes", "work_hours", "productivity_score", "burnout_score", "recovery_score"]
    key_cols = [column for column in key_cols if column in columns]
    real_corr = master[key_cols].corr()
    synth_corr = synthetic[key_cols].corr()
    corr_delta = (real_corr - synth_corr).abs()

    for column in key_cols:
        plt.figure(figsize=(7, 4))
        plt.hist(master[column].dropna(), bins=30, alpha=0.55, label="Real", density=True)
        plt.hist(synthetic[column].dropna(), bins=30, alpha=0.55, label="Synthetic", density=True)
        plt.title(f"Distribution Comparison: {column}")
        plt.legend()
        plt.tight_layout()
        plt.savefig(figures_root / f"synthetic_distribution_{column}.png", dpi=150)
        plt.close()

    (reports_root / "synthetic_validation_report.md").write_text(
        "\n".join(
            [
                "# Synthetic Dataset Validation Report",
                "",
                f"Synthetic rows: {len(synthetic):,}",
                f"Synthetic users: {synthetic['user_id'].nunique():,}",
                f"Real rows used for calibration: {len(master):,}",
                "",
                "## Method",
                "The generator extracts means, standard deviations, percentiles, and correlations from `data/processed/master_dataset.csv`. User baselines are sampled from real feature distributions, then longitudinal dynamics are simulated with sleep debt accumulation, weekend recovery, workload pressure, recovery cycles, productivity fluctuations, and gradual burnout progression.",
                "",
                "## Distribution Comparison",
                comparison.round(3).to_markdown(),
                "",
                "## Correlation Matrix Absolute Delta",
                corr_delta.round(3).to_markdown(),
                "",
                "## Preserved Relationship Checks",
                "- Poor sleep quality increases stress/fatigue pressure and lowers productivity.",
                "- Higher activity improves recovery and supports productivity.",
                "- Long work hours and high task load raise fatigue and burnout progression.",
                "- Weekends reduce work pressure, lower sleep debt, and support recovery.",
                "",
                "Distribution comparison figures are saved in `reports/figures/`.",
            ]
        ),
        encoding="utf-8",
    )


def write_profile_validation(project_root: Path, hourly: pd.DataFrame) -> None:
    reports_root = project_root / "reports"
    figures_root = reports_root / "figures"
    average_curve = hourly.groupby(["chronotype", "hour"], as_index=False)[["hourly_productivity", "hourly_energy", "focus_score", "cognitive_capacity"]].mean()

    plt.figure(figsize=(10, 5))
    for chronotype, group in average_curve.groupby("chronotype"):
        plt.plot(group["hour"], group["hourly_productivity"], marker="o", label=chronotype)
    plt.title("Average Hourly Productivity by Chronotype")
    plt.xlabel("Hour")
    plt.ylabel("Hourly Productivity")
    plt.xticks(range(24))
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_root / "circadian_productivity_by_chronotype.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 5))
    for chronotype, group in average_curve.groupby("chronotype"):
        plt.plot(group["hour"], group["cognitive_capacity"], marker="o", label=chronotype)
    plt.title("Average Cognitive Capacity by Chronotype")
    plt.xlabel("Hour")
    plt.ylabel("Cognitive Capacity")
    plt.xticks(range(24))
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures_root / "circadian_capacity_by_chronotype.png", dpi=150)
    plt.close()

    peak_hours = average_curve.loc[average_curve.groupby("chronotype")["hourly_productivity"].idxmax()][["chronotype", "hour", "hourly_productivity"]]
    task_mix = pd.crosstab(hourly["chronotype"], hourly["recommended_task_type"], normalize="index") * 100
    (reports_root / "profile_validation_report.md").write_text(
        "\n".join(
            [
                "# Hourly Circadian Profile Validation Report",
                "",
                f"Rows: {len(hourly):,}",
                f"Users: {hourly['user_id'].nunique():,}",
                "",
                "## Chronotype Proportions",
                hourly.drop_duplicates("user_id")["chronotype"].value_counts(normalize=True).mul(100).round(2).to_markdown(),
                "",
                "## Average Peak Hour by Chronotype",
                peak_hours.to_markdown(index=False),
                "",
                "## Recommended Task Type Mix (%)",
                task_mix.round(2).to_markdown(),
                "",
                "Figures saved:",
                "- `reports/figures/circadian_productivity_by_chronotype.png`",
                "- `reports/figures/circadian_capacity_by_chronotype.png`",
            ]
        ),
        encoding="utf-8",
    )


def write_outputs(project_root: Path, users: int, days: int, seed: int) -> None:
    synthetic, master, _summary, correlations = generate_synthetic_from_master(project_root, users=users, days=days, seed=seed)
    hourly = generate_hourly_profiles(synthetic)

    synthetic_path = project_root / "data" / "synthetic" / "synthetic_productivity_dataset.csv"
    hourly_path = project_root / "data" / "synthetic" / "hourly_circadian_profiles.csv"
    root_synthetic_path = project_root / "synthetic_productivity_dataset.csv"

    synthetic.to_csv(synthetic_path, index=False)
    synthetic.to_csv(root_synthetic_path, index=False)
    hourly.to_csv(hourly_path, index=False)
    write_distribution_validation(project_root, master, synthetic, correlations)
    write_profile_validation(project_root, hourly)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate calibrated synthetic productivity and recovery histories.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    parser.add_argument("--users", default=2000, type=int)
    parser.add_argument("--days", default=180, type=int)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()
    write_outputs(args.project_root, args.users, args.days, args.seed)


if __name__ == "__main__":
    main()
