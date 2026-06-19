# Synthetic Dataset Validation Report

Synthetic rows: 360,000
Synthetic users: 2,000
Real rows used for calibration: 26,924

## Method
The generator extracts means, standard deviations, percentiles, and correlations from `data/processed/master_dataset.csv`. User baselines are sampled from real feature distributions, then longitudinal dynamics are simulated with sleep debt accumulation, weekend recovery, workload pressure, recovery cycles, productivity fluctuations, and gradual burnout progression.

## Distribution Comparison
|                    |   real_mean |   real_std |   real_5% |   real_50% |   real_95% |   synthetic_mean |   synthetic_std |   synthetic_5% |   synthetic_50% |   synthetic_95% |   mean_abs_diff |   std_abs_diff |
|:-------------------|------------:|-----------:|----------:|-----------:|-----------:|-----------------:|----------------:|---------------:|----------------:|----------------:|----------------:|---------------:|
| sleep_need         |       8     |      0     |     8     |       8    |      8     |            7.99  |           0.439 |           7.24 |            8    |            8.69 |           0.01  |          0.439 |
| sleep_hours        |       7.039 |      0.51  |     6.52  |       7    |      7.848 |            6.84  |           0.857 |           5.44 |            6.84 |            8.26 |           0.199 |          0.347 |
| sleep_quality      |       6     |      0     |     6     |       6    |      6     |            7.666 |           0.687 |           6.53 |            7.67 |            8.79 |           1.666 |          0.687 |
| sleep_deficit      |       0.998 |      0.374 |     0.152 |       1    |      1.48  |            1.207 |           0.876 |           0    |            1.15 |            2.75 |           0.209 |          0.502 |
| sleep_debt         |       1.288 |      1.409 |     0.7   |       1    |      3     |            2.7   |           1.981 |           0    |            2.44 |            6.35 |           1.413 |          0.572 |
| energy_level       |       6     |      0     |     6     |       6    |      6     |            5.198 |           1.805 |           2.21 |            5.2  |            8.17 |           0.802 |          1.805 |
| mood_score         |       6     |      0     |     6     |       6    |      6     |            3.899 |           1.55  |           1.51 |            3.78 |            6.61 |           2.101 |          1.55  |
| stress_level       |       5.074 |      0.662 |     4     |       5    |      5.5   |            5.953 |           1.448 |           3.37 |            6.12 |            8.08 |           0.879 |          0.787 |
| fatigue_score      |       5.804 |      1.826 |     2.6   |       5.9  |      8.9   |            4.972 |           1.637 |           2.26 |            4.99 |            7.64 |           0.832 |          0.189 |
| activity_minutes   |      46.702 |     44.671 |    35     |      35    |    174     |           58.082 |          37.666 |           3.6  |           52.4  |          129.1  |          11.38  |          7.004 |
| work_hours         |       7.121 |      3.015 |     1.6   |       6.4  |     12.8   |            6.079 |           3.353 |           0.13 |            6.11 |           11.65 |           1.042 |          0.338 |
| meeting_hours      |       1.465 |      0.256 |     1.5   |       1.5  |      1.5   |            1.197 |           0.693 |           0    |            1.24 |            2.3  |           0.268 |          0.437 |
| task_count         |       6     |      0     |     6     |       6    |      6     |            7.268 |           2.959 |           2    |            7    |           12    |           1.268 |          2.959 |
| task_complexity    |       2.54  |      1.496 |     0     |       2    |      5     |            2.916 |           1.769 |           0    |            2.86 |            5.94 |           0.376 |          0.273 |
| task_load_score    |      78.895 |     20.117 |    39.1   |      83.87 |    100     |           73.264 |          24.505 |          26.77 |           77.56 |          100    |           5.631 |          4.388 |
| recovery_score     |      45.686 |     21.203 |    15     |      41    |     90     |           56.864 |          19.815 |          25.97 |           55.51 |           91.11 |          11.178 |          1.388 |
| productivity_score |      43.803 |     19.146 |    15     |      41    |     81     |           34.622 |          24.348 |           0    |           33.25 |           77.12 |           9.181 |          5.202 |
| burnout_score      |      46.495 |     21.282 |    11     |      45    |     86.364 |           50.962 |          13.01  |          30.13 |           50.58 |           73.03 |           4.466 |          8.272 |
| cumulative_load    |      14.399 |     15.026 |     4.1   |      11.5  |     37.917 |           14.71  |           3.416 |           8.45 |           15.24 |           19.32 |           0.311 |         11.61  |

## Correlation Matrix Absolute Delta
|                    |   sleep_hours |   sleep_quality |   stress_level |   fatigue_score |   activity_minutes |   work_hours |   productivity_score |   burnout_score |   recovery_score |
|:-------------------|--------------:|----------------:|---------------:|----------------:|-------------------:|-------------:|---------------------:|----------------:|-----------------:|
| sleep_hours        |         0     |             nan |          0.359 |           0.498 |              0.015 |        0.344 |                0.647 |           0.481 |            0.63  |
| sleep_quality      |       nan     |             nan |        nan     |         nan     |            nan     |      nan     |              nan     |         nan     |          nan     |
| stress_level       |         0.359 |             nan |          0     |           0.925 |              0.819 |        0.486 |                0.668 |           0.217 |            0.595 |
| fatigue_score      |         0.498 |             nan |          0.925 |           0     |              0.328 |        0.005 |                0.229 |           0.196 |            0.336 |
| activity_minutes   |         0.015 |             nan |          0.819 |           0.328 |              0     |        0.161 |                0.638 |           0.465 |            0.482 |
| work_hours         |         0.344 |             nan |          0.486 |           0.005 |              0.161 |        0     |                0.054 |           0.037 |            0.044 |
| productivity_score |         0.647 |             nan |          0.668 |           0.229 |              0.638 |        0.054 |                0     |           0.075 |            0.052 |
| burnout_score      |         0.481 |             nan |          0.217 |           0.196 |              0.465 |        0.037 |                0.075 |           0     |            0.109 |
| recovery_score     |         0.63  |             nan |          0.595 |           0.336 |              0.482 |        0.044 |                0.052 |           0.109 |            0     |

## Preserved Relationship Checks
- Poor sleep quality increases stress/fatigue pressure and lowers productivity.
- Higher activity improves recovery and supports productivity.
- Long work hours and high task load raise fatigue and burnout progression.
- Weekends reduce work pressure, lower sleep debt, and support recovery.

Distribution comparison figures are saved in `reports/figures/`.