# Burnout Model Report

## Target
`burnout_risk` classification from `burnout_score`: Low 0-33, Medium 34-66, High 67-100.

## Class Distribution
{'Medium': 15725, 'High': 2999, 'Low': 1276}

## Model Comparison
| model                              |   Accuracy |   Precision_macro |   Recall_macro |   F1_macro |
|:-----------------------------------|-----------:|------------------:|---------------:|-----------:|
| Majority Baseline                  |   0.784971 |          0.261657 |       0.333333 |   0.293178 |
| Random Forest Classifier           |   0.918111 |          0.839767 |       0.873607 |   0.855532 |
| Gradient Boosting Classifier       |   0.932752 |          0.899441 |       0.847095 |   0.87139  |
| XGBoost Classifier                 |   0.921328 |          0.893783 |       0.806478 |   0.844596 |
| Tuned Random Forest Classifier     |   0.885378 |          0.768352 |       0.90355  |   0.819833 |
| Tuned Gradient Boosting Classifier |   0.930878 |          0.900121 |       0.83886  |   0.866932 |

Selected model: **Gradient Boosting Classifier**.

## Classification Report
```text
              precision    recall  f1-score   support

        High       0.90      0.83      0.86      9960
         Low       0.86      0.74      0.79      6680
      Medium       0.95      0.97      0.96     60745

    accuracy                           0.93     77385
   macro avg       0.90      0.85      0.87     77385
weighted avg       0.93      0.93      0.93     77385

```

## Confusion Matrix
|               |   Pred Low |   Pred Medium |   Pred High |
|:--------------|-----------:|--------------:|------------:|
| Actual Low    |       4948 |          1732 |           0 |
| Actual Medium |        836 |         58968 |         941 |
| Actual High   |          0 |          1695 |        8265 |

## Sanity Checks
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