# Productivity Model Report

## Target
`productivity_score` regression.

## Model Comparison
| model                             |      MAE |     RMSE |         R2 |
|:----------------------------------|---------:|---------:|-----------:|
| Mean Baseline                     | 20.7456  | 24.9974  | -0.0321519 |
| Random Forest Regressor           |  3.03902 |  3.98372 |  0.973786  |
| Gradient Boosting Regressor       |  3.0248  |  3.91428 |  0.974692  |
| XGBoost Regressor                 |  3.13386 |  4.02844 |  0.973194  |
| Tuned Random Forest Regressor     |  3.1081  |  4.07391 |  0.972586  |
| Tuned Gradient Boosting Regressor |  3.05793 |  3.92975 |  0.974492  |
| Tuned XGBoost Regressor           |  3.00253 |  3.88566 |  0.975061  |

Selected model: **Tuned XGBoost Regressor**.

## Sanity Checks
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