# Feature Importance Report

## Productivity Native Importance
| feature                 |   importance |
|:------------------------|-------------:|
| recovery_score          |  0.460852    |
| energy_level            |  0.336125    |
| mood_score              |  0.114876    |
| fatigue_score           |  0.0552642   |
| sleep_debt              |  0.0189727   |
| work_hours              |  0.00341914  |
| sleep_need              |  0.00135651  |
| sleep_quality           |  0.001286    |
| cumulative_load         |  0.00116454  |
| day_of_week_Saturday    |  0.000982035 |
| stress_level            |  0.000942394 |
| is_weekend              |  0.000935941 |
| day_of_week_Thursday    |  0.000811784 |
| activity_minutes        |  0.000611527 |
| task_load_score         |  0.000456485 |
| sleep_hours             |  0.000424787 |
| sleep_deficit           |  0.000311573 |
| task_count              |  0.000304273 |
| chronotype_Morning      |  0.000284665 |
| meeting_hours           |  0.000212533 |
| task_complexity         |  0.00020829  |
| chronotype_Intermediate |  0.000198532 |
| chronotype_Evening      |  0           |
| day_of_week_Monday      |  0           |
| day_of_week_Friday      |  0           |

## Productivity Permutation Importance
| feature          |   importance |         std |
|:-----------------|-------------:|------------:|
| recovery_score   |  9.08767     | 0.197732    |
| energy_level     |  7.96473     | 0.218258    |
| fatigue_score    |  1.40979     | 0.0308703   |
| sleep_debt       |  0.312116    | 0.0090926   |
| work_hours       |  0.304981    | 0.0118939   |
| stress_level     |  0.193161    | 0.00645337  |
| mood_score       |  0.180071    | 0.00835109  |
| sleep_quality    |  0.0702653   | 0.0122375   |
| is_weekend       |  0.0664853   | 0.00576807  |
| sleep_need       |  0.0243244   | 0.00539073  |
| sleep_hours      |  0.0215874   | 0.00450068  |
| activity_minutes |  0.0151616   | 0.00471742  |
| day_of_week      |  0.0127903   | 0.00363535  |
| sleep_deficit    |  0.00360919  | 0.0021839   |
| cumulative_load  |  0.0034482   | 0.0011516   |
| task_load_score  |  0.00284147  | 0.000114609 |
| task_complexity  |  5.53115e-05 | 9.66911e-05 |
| source_dataset   |  0           | 0           |
| meeting_hours    | -0.000235778 | 0.000289077 |
| task_count       | -0.000327181 | 0.000217791 |
| chronotype       | -0.000891954 | 0.000264768 |

## Burnout Native Importance
| feature                 |   importance |
|:------------------------|-------------:|
| fatigue_score           |  0.397421    |
| cumulative_load         |  0.213668    |
| recovery_score          |  0.151324    |
| sleep_debt              |  0.139451    |
| energy_level            |  0.0240836   |
| mood_score              |  0.0204707   |
| day_of_week_Saturday    |  0.0107522   |
| sleep_deficit           |  0.00770928  |
| is_weekend              |  0.00647498  |
| day_of_week_Monday      |  0.00619272  |
| stress_level            |  0.00412368  |
| activity_minutes        |  0.00393359  |
| work_hours              |  0.00343076  |
| task_complexity         |  0.00252309  |
| sleep_hours             |  0.00238185  |
| day_of_week_Tuesday     |  0.00193289  |
| task_load_score         |  0.00121925  |
| day_of_week_Friday      |  0.00105313  |
| sleep_quality           |  0.000945131 |
| meeting_hours           |  0.000370623 |
| sleep_need              |  0.00032725  |
| task_count              |  9.56402e-05 |
| chronotype_Evening      |  8.66191e-05 |
| day_of_week_Thursday    |  2.9276e-05  |
| chronotype_Intermediate |  0           |

## Burnout Permutation Importance
| feature          |   importance |         std |
|:-----------------|-------------:|------------:|
| sleep_debt       |  0.233912    | 0.00869343  |
| cumulative_load  |  0.227519    | 0.0116333   |
| fatigue_score    |  0.0783843   | 0.00586589  |
| day_of_week      |  0.0222507   | 0.00360447  |
| recovery_score   |  0.0137981   | 0.00238698  |
| mood_score       |  0.0126461   | 0.0023876   |
| activity_minutes |  0.0117135   | 0.00143889  |
| energy_level     |  0.0111942   | 0.000712303 |
| is_weekend       |  0.0107465   | 0.002893    |
| sleep_deficit    |  0.00767723  | 0.00215668  |
| work_hours       |  0.00452934  | 0.00071174  |
| task_load_score  |  0.00432453  | 0.00100087  |
| task_complexity  |  0.00105954  | 0.00131734  |
| chronotype       |  0.000207362 | 0.000293254 |
| sleep_need       |  0.000201799 | 0.000285387 |
| task_count       |  0           | 0           |
| source_dataset   |  0           | 0           |
| stress_level     | -0.000310715 | 0.00417326  |
| sleep_hours      | -0.000404482 | 0.00135694  |
| meeting_hours    | -0.000469193 | 0.00117018  |
| sleep_quality    | -0.00146776  | 0.00168044  |

Figures are saved under `reports/figures/`.