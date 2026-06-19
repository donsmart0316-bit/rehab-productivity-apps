# SHAP Analysis

SHAP available: `True`.

SHAP was computed with `TreeExplainer` on a chronological holdout sample after applying the saved preprocessing pipeline.

## Productivity SHAP Importance
| feature                 |   mean_abs_shap |
|:------------------------|----------------:|
| recovery_score          |     8.55523     |
| energy_level            |     7.96288     |
| fatigue_score           |     2.32343     |
| sleep_debt              |     1.00959     |
| mood_score              |     0.955257    |
| work_hours              |     0.726025    |
| stress_level            |     0.609357    |
| sleep_quality           |     0.378994    |
| is_weekend              |     0.251174    |
| sleep_need              |     0.248092    |
| sleep_hours             |     0.187572    |
| activity_minutes        |     0.127259    |
| day_of_week_Saturday    |     0.101306    |
| cumulative_load         |     0.04016     |
| sleep_deficit           |     0.0284919   |
| task_load_score         |     0.0175897   |
| chronotype_Morning      |     0.0153337   |
| meeting_hours           |     0.00581112  |
| task_count              |     0.00523314  |
| day_of_week_Thursday    |     0.00490985  |
| task_complexity         |     0.00435019  |
| chronotype_Intermediate |     0.000538527 |
| chronotype_Evening      |     0           |
| day_of_week_Monday      |     0           |
| day_of_week_Friday      |     0           |

Saved `reports\figures\productivity_shap_importance.png`.

## Burnout SHAP Importance
SHAP failed for `GradientBoostingClassifier`: InvalidModelError('GradientBoostingClassifier is only supported for binary classification right now!').

SHAP failed for `GradientBoostingClassifier`: InvalidModelError('GradientBoostingClassifier is only supported for binary classification right now!').

## Relationship Validation
Productivity checks:
| feature         |   delta |   average_effect | expectation                                               |
|:----------------|--------:|-----------------:|:----------------------------------------------------------|
| sleep_quality   |       1 |       1.14526    | higher should improve productivity / reduce burnout risk  |
| sleep_debt      |       2 |      -2.01141    | higher should reduce productivity / increase burnout risk |
| recovery_score  |      10 |       9.52844    | higher should improve productivity / reduce burnout risk  |
| stress_level    |       1 |      -1.20775    | higher should reduce productivity / increase burnout risk |
| fatigue_score   |       1 |      -3.55538    | higher should reduce productivity / increase burnout risk |
| cumulative_load |      10 |      -0.207233   | higher should reduce productivity / increase burnout risk |
| task_load_score |      10 |      -0.00665732 | higher workload pressure should increase burnout risk     |
| work_hours      |       1 |      -0.480038   | higher workload should increase burnout risk              |

Burnout checks:
| feature         |   delta |   average_effect | expectation                                               |
|:----------------|--------:|-----------------:|:----------------------------------------------------------|
| sleep_quality   |       1 |      -0.00116082 | higher should improve productivity / reduce burnout risk  |
| sleep_debt      |       2 |       0.147271   | higher should reduce productivity / increase burnout risk |
| recovery_score  |      10 |      -0.0298229  | higher should improve productivity / reduce burnout risk  |
| stress_level    |       1 |       0.012267   | higher should reduce productivity / increase burnout risk |
| fatigue_score   |       1 |       0.0431019  | higher should reduce productivity / increase burnout risk |
| cumulative_load |      10 |       0.284999   | higher should reduce productivity / increase burnout risk |
| task_load_score |      10 |      -0.00213584 | higher workload pressure should increase burnout risk     |
| work_hours      |       1 |       0.00396608 | higher workload should increase burnout risk              |