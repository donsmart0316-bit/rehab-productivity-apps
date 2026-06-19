# Dataset Analysis

## Source Datasets

The project is configured for three Kaggle datasets: Sleep Health & Lifestyle, Employee Burnout, and Work From Home Employee Burnout. The downloader writes a manifest to `data/raw/download_manifest.json` so authentication or dataset availability issues are auditable.

Current Kaggle download status:

Local Kaggle archives found in `kaggle data` and used by the master dataset builder:

- `archive(3).zip`: Sleep_health_and_lifestyle_dataset.csv
- `archive(4).zip`: sample_submission.csv, test.csv, train.csv
- `archive(5).zip`: work_from_home_burnout_dataset.csv
- `archive(6).zip`: student_lifestyle_dataset.csv

Downloader manifest status, kept for reproducibility:

- `uom190346a/sleep-health-and-lifestyle-dataset`: not downloaded; files=0; detail=Kaggle authentication is not configured. Run `kaggle auth login` or add a Kaggle API token.
- `blurredmachine/are-your-employees-burning-out`: not downloaded; files=0; detail=Kaggle authentication is not configured. Run `kaggle auth login` or add a Kaggle API token.
- `sonalshinde123/work-from-home-employee-burnout-dataset`: not downloaded; files=0; detail=Kaggle authentication is not configured. Run `kaggle auth login` or add a Kaggle API token.

## Unified Master Dataset

- Rows: 26,924
- Users: 25,304
- Date range: 2026-01-01 to 2026-01-10
- Schema: daily user-level records aligned to recovery, workload, productivity, and burnout modeling.

## Missing Values

|                    |   missing_count |   missing_percent |
|:-------------------|----------------:|------------------:|
| user_id            |               0 |                 0 |
| date               |               0 |                 0 |
| chronotype         |               0 |                 0 |
| sleep_need         |               0 |                 0 |
| sleep_hours        |               0 |                 0 |
| sleep_quality      |               0 |                 0 |
| sleep_deficit      |               0 |                 0 |
| sleep_debt         |               0 |                 0 |
| energy_level       |               0 |                 0 |
| mood_score         |               0 |                 0 |
| stress_level       |               0 |                 0 |
| fatigue_score      |               0 |                 0 |
| activity_minutes   |               0 |                 0 |
| work_hours         |               0 |                 0 |
| meeting_hours      |               0 |                 0 |
| task_count         |               0 |                 0 |
| task_complexity    |               0 |                 0 |
| task_load_score    |               0 |                 0 |
| cumulative_load    |               0 |                 0 |
| productivity_score |               0 |                 0 |
| productivity_trend |               0 |                 0 |
| burnout_score      |               0 |                 0 |
| burnout_momentum   |               0 |                 0 |
| recovery_score     |               0 |                 0 |
| day_of_week        |               0 |                 0 |
| is_weekend         |               0 |                 0 |

## Numeric Summary

|                    |   count |   mean |   std |    min |   25% |   50% |   75% |    max |
|:-------------------|--------:|-------:|------:|-------:|------:|------:|------:|-------:|
| sleep_need         |   26924 |   8    |  0    |   8    |   8   |  8    |   8   |   8    |
| sleep_hours        |   26924 |   7.04 |  0.51 |   4.5  |   7   |  7    |   7   |  10.8  |
| sleep_quality      |   26924 |   6    |  0    |   6    |   6   |  6    |   6   |   6    |
| sleep_deficit      |   26924 |   1    |  0.37 |   0    |   1   |  1    |   1   |   3.5  |
| sleep_debt         |   26924 |   1.29 |  1.41 |   0    |   1   |  1    |   1   |  15.91 |
| energy_level       |   26924 |   6    |  0    |   6    |   6   |  6    |   6   |   6    |
| mood_score         |   26924 |   6    |  0    |   6    |   6   |  6    |   6   |   6    |
| stress_level       |   26924 |   5.07 |  0.66 |   3    |   5   |  5    |   5   |   8    |
| fatigue_score      |   26924 |   5.8  |  1.83 |   0    |   5   |  5.9  |   6.9 |  10    |
| activity_minutes   |   26924 |  46.7  | 44.67 |   0    |  35   | 35    |  35   | 240    |
| work_hours         |   26924 |   7.12 |  3.01 |   1.6  |   4.8 |  6.4  |   9.6 |  16    |
| meeting_hours      |   26924 |   1.46 |  0.26 |   0    |   1.5 |  1.5  |   1.5 |   5    |
| task_count         |   26924 |   6    |  0    |   6    |   6   |  6    |   6   |   6    |
| task_complexity    |   26924 |   2.54 |  1.5  |   0    |   1.4 |  2    |   3   |   8    |
| task_load_score    |   26924 |  78.9  | 20.12 |  32.1  |  65.3 | 83.87 | 100   | 100    |
| cumulative_load    |   26924 |  14.4  | 15.03 |   3.1  |   8.3 | 11.5  |  14.1 | 114.39 |
| productivity_score |   26924 |  43.8  | 19.15 |   0    |  31   | 41    |  54   | 100    |
| productivity_trend |   26924 |  -0.23 |  1.01 | -10.72 |   0   |  0    |   0   |   2.93 |
| burnout_score      |   26924 |  46.5  | 21.28 |   0    |  33   | 45    |  59   | 100    |
| burnout_momentum   |   26924 |   0.39 |  1.58 |   0    |   0   |  0    |   0   |  13.98 |
| recovery_score     |   26924 |  45.69 | 21.2  |   0    |  32   | 41    |  57   | 100    |
| is_weekend         |   26924 |   0.02 |  0.14 |   0    |   0   |  0    |   0   |   1    |

## Data Dictionary

- `user_id`: Stable anonymized user identifier.
- `date`: Daily record date.
- `chronotype`: Morning, Intermediate, or Evening productivity timing profile.
- `sleep_need`: Estimated individual sleep requirement in hours.
- `sleep_hours`: Total sleep duration for the previous night, hours.
- `sleep_quality`: Sleep quality on a 0-10 scale.
- `sleep_deficit`: Daily sleep shortfall relative to sleep need.
- `sleep_debt`: Rolling sleep deficit over the recent window.
- `energy_level`: Perceived energy on a 0-10 scale.
- `mood_score`: Mood on a 0-10 scale.
- `stress_level`: Stress on a 0-10 scale.
- `fatigue_score`: Fatigue on a 0-10 scale.
- `activity_minutes`: Daily physical activity minutes.
- `work_hours`: Daily working hours.
- `meeting_hours`: Daily meeting hours.
- `task_count`: Number of planned or completed work tasks.
- `task_complexity`: Average task complexity on a 0-10 scale.
- `task_load_score`: Combined workload pressure score from task count, work hours, meetings, and complexity.
- `cumulative_load`: Rolling workload over the recent window.
- `productivity_score`: Productivity outcome score on a 0-100 scale.
- `productivity_trend`: Rolling productivity change rate.
- `burnout_score`: Burnout risk/severity score on a 0-100 scale.
- `burnout_momentum`: Rolling burnout change rate.
- `recovery_score`: Recovery capacity score on a 0-100 scale.
- `day_of_week`: Calendar day name.
- `is_weekend`: Weekend indicator, 1 for Saturday/Sunday and 0 otherwise.

## Modeling Readiness

- Numerical features are clipped to documented ranges.
- Missing values are imputed with conservative defaults.
- Duplicate rows are removed during master dataset construction.
- Synthetic daily records preserve realistic directional relationships among sleep, energy, stress, activity, work, productivity, recovery, and burnout.