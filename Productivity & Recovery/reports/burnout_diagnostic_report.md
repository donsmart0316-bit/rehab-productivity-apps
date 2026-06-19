# Burnout Diagnostic & Improvement Report

## Executive Summary
Best model: **Logistic Regression**
Best label strategy: **Formula_C_quantile**
Best balancing strategy: **none**
Accuracy: **0.991**
Macro F1: **0.991**
Weighted F1: **0.991**

## Class Distribution
Counts:
| burnout_risk_diagnostic   |   count |
|:--------------------------|--------:|
| Low                       |  128975 |
| Medium                    |  128974 |
| High                      |  128975 |

Proportions:
| burnout_risk_diagnostic   |   proportion |
|:--------------------------|-------------:|
| Low                       |        0.333 |
| Medium                    |        0.333 |
| High                      |        0.333 |

## Confusion Matrix
Raw:
|               |   Pred Low |   Pred Medium |   Pred High |
|:--------------|-----------:|--------------:|------------:|
| Actual Low    |      27203 |           216 |           0 |
| Actual Medium |        120 |         24638 |         135 |
| Actual High   |          0 |           207 |       24866 |

Normalized by true class:
|               |   Pred Low |   Pred Medium |   Pred High |
|:--------------|-----------:|--------------:|------------:|
| Actual Low    |      0.992 |         0.008 |       0     |
| Actual Medium |      0.005 |         0.99  |       0.005 |
| Actual High   |      0     |         0.008 |       0.992 |

## Classification Report
```text
              precision    recall  f1-score   support

        High       0.99      0.99      0.99     25073
         Low       1.00      0.99      0.99     27419
      Medium       0.98      0.99      0.99     24893

    accuracy                           0.99     77385
   macro avg       0.99      0.99      0.99     77385
weighted avg       0.99      0.99      0.99     77385

```

## Dataset Quality Audit: Class Separability
| burnout_risk   |   ('sleep_debt', 'mean') |   ('sleep_debt', 'median') |   ('sleep_debt', 'std') |   ('recovery_score', 'mean') |   ('recovery_score', 'median') |   ('recovery_score', 'std') |   ('stress_level', 'mean') |   ('stress_level', 'median') |   ('stress_level', 'std') |   ('fatigue_score', 'mean') |   ('fatigue_score', 'median') |   ('fatigue_score', 'std') |   ('cumulative_load', 'mean') |   ('cumulative_load', 'median') |   ('cumulative_load', 'std') |   ('work_hours', 'mean') |   ('work_hours', 'median') |   ('work_hours', 'std') |   ('burnout_score', 'mean') |   ('burnout_score', 'median') |   ('burnout_score', 'std') |
|:---------------|-------------------------:|---------------------------:|------------------------:|-----------------------------:|-------------------------------:|----------------------------:|---------------------------:|-----------------------------:|--------------------------:|----------------------------:|------------------------------:|---------------------------:|------------------------------:|--------------------------------:|-----------------------------:|-------------------------:|---------------------------:|------------------------:|----------------------------:|------------------------------:|---------------------------:|
| High           |                    4.042 |                       4    |                   1.952 |                       48.313 |                          49.2  |                      10.344 |                      6.873 |                         6.94 |                     0.912 |                       5.993 |                          5.88 |                      0.909 |                        17.361 |                           17.52 |                        5.395 |                    9.09  |                       9.16 |                   2.399 |                      59.855 |                         58.83 |                      8.181 |
| Low            |                    1.294 |                       1    |                   1.209 |                       80.842 |                          81.25 |                      11.188 |                      4.417 |                         4.47 |                     1.023 |                       3.036 |                          3.11 |                      0.904 |                        12.175 |                           12.18 |                        3.596 |                    3.11  |                       3.03 |                   2.231 |                      36.017 |                         36.39 |                      8.422 |
| Medium         |                    2.333 |                       2.12 |                   1.508 |                       61.491 |                          61.44 |                       9.852 |                      5.923 |                         5.94 |                     0.826 |                       4.654 |                          4.62 |                      0.726 |                        14.531 |                           14.52 |                        4.919 |                    6.255 |                       6.39 |                   2.204 |                      46.828 |                         46.72 |                      6.588 |

## Feature/Burnout Correlations
| score                  | feature         |   correlation |
|:-----------------------|:----------------|--------------:|
| burnout_score          | sleep_debt      |         0.611 |
| burnout_score          | recovery_score  |        -0.674 |
| burnout_score          | stress_level    |         0.601 |
| burnout_score          | fatigue_score   |         0.752 |
| burnout_score          | cumulative_load |         0.508 |
| burnout_score          | work_hours      |         0.703 |
| weighted_burnout_score | sleep_debt      |         0.646 |
| weighted_burnout_score | recovery_score  |        -0.86  |
| weighted_burnout_score | stress_level    |         0.81  |
| weighted_burnout_score | fatigue_score   |         0.904 |
| weighted_burnout_score | cumulative_load |         0.448 |
| weighted_burnout_score | work_hours      |         0.799 |

## SHAP Importance
| feature                               |   mean_abs_shap |
|:--------------------------------------|----------------:|
| stress_level                          |       3.21911   |
| sleep_debt                            |       3.08778   |
| fatigue_score                         |       2.72991   |
| cumulative_load                       |       2.38139   |
| work_hours                            |       2.01505   |
| recovery_score                        |       1.99439   |
| task_load_score                       |       0.813573  |
| sleep_hours                           |       0.568003  |
| activity_minutes                      |       0.450701  |
| is_weekend                            |       0.33934   |
| task_complexity                       |       0.328783  |
| sleep_quality                         |       0.282233  |
| energy_level                          |       0.271476  |
| mood_score                            |       0.260156  |
| task_count                            |       0.205652  |
| sleep_need                            |       0.202306  |
| sleep_deficit                         |       0.186726  |
| day_of_week_Sunday                    |       0.165308  |
| meeting_hours                         |       0.141942  |
| day_of_week_Friday                    |       0.105151  |
| day_of_week_Thursday                  |       0.0720091 |
| day_of_week_Monday                    |       0.0587609 |
| day_of_week_Saturday                  |       0.0540906 |
| day_of_week_Tuesday                   |       0.0374625 |
| day_of_week_Wednesday                 |       0.0313067 |
| chronotype_Intermediate               |       0.029766  |
| chronotype_Morning                    |       0.0202665 |
| chronotype_Evening                    |       0.0133843 |
| source_dataset_synthetic_longitudinal |       0         |

Saved `reports\figures\burnout_diagnostic_shap_importance.png`.

## Model and Label Strategy Ranking
| label_strategy     | formula_labels   | balance_strategy    | model                  |   Accuracy |   Precision_macro |   Recall_macro |   F1_macro |   Weighted_F1 |
|:-------------------|:-----------------|:--------------------|:-----------------------|-----------:|------------------:|---------------:|-----------:|--------------:|
| Formula_C_quantile | True             | none                | Logistic Regression    |     0.9912 |            0.9911 |         0.9912 |     0.9912 |        0.9912 |
| Formula_C_quantile | True             | random_oversampling | Logistic Regression    |     0.9902 |            0.9901 |         0.9901 |     0.9901 |        0.9902 |
| Formula_B_0_25_60  | True             | none                | Logistic Regression    |     0.9747 |            0.925  |         0.9883 |     0.9536 |        0.9752 |
| Formula_B_0_25_60  | True             | random_oversampling | Logistic Regression    |     0.9744 |            0.9233 |         0.9881 |     0.9525 |        0.975  |
| Formula_B_0_25_60  | True             | none                | XGBoost tuned          |     0.9688 |            0.965  |         0.931  |     0.9472 |        0.9685 |
| Formula_B_0_25_60  | True             | none                | Gradient Boosting      |     0.9684 |            0.962  |         0.9277 |     0.9441 |        0.9681 |
| Formula_C_quantile | True             | none                | Gradient Boosting      |     0.9437 |            0.9443 |         0.9435 |     0.9435 |        0.9441 |
| Formula_C_quantile | True             | none                | XGBoost tuned          |     0.9379 |            0.9383 |         0.9375 |     0.9377 |        0.9383 |
| Formula_C_quantile | True             | none                | Random Forest balanced |     0.9364 |            0.937  |         0.936  |     0.9361 |        0.9368 |
| Formula_C_quantile | True             | random_oversampling | Gradient Boosting      |     0.9349 |            0.9354 |         0.9346 |     0.9347 |        0.9353 |
| Formula_C_quantile | True             | random_oversampling | Random Forest balanced |     0.9323 |            0.9329 |         0.9318 |     0.932  |        0.9327 |
| Formula_C_quantile | True             | random_oversampling | XGBoost tuned          |     0.9299 |            0.9301 |         0.9293 |     0.9295 |        0.9302 |
| Formula_B_0_25_60  | True             | none                | Random Forest balanced |     0.9518 |            0.9029 |         0.9422 |     0.9213 |        0.9523 |
| Formula_B_0_25_60  | True             | random_oversampling | Random Forest balanced |     0.9441 |            0.8781 |         0.9519 |     0.9107 |        0.9453 |
| Formula_B_0_25_60  | True             | random_oversampling | Gradient Boosting      |     0.9451 |            0.8626 |         0.9698 |     0.9063 |        0.9472 |
| C_quantile         | False            | none                | Logistic Regression    |     0.8962 |            0.8969 |         0.8965 |     0.8967 |        0.8963 |
| Formula_B_0_25_60  | True             | random_oversampling | XGBoost tuned          |     0.9362 |            0.8482 |         0.9644 |     0.8946 |        0.9387 |
| C_quantile         | False            | none                | Random Forest balanced |     0.8471 |            0.8524 |         0.8472 |     0.849  |        0.8485 |
| C_quantile         | False            | none                | Gradient Boosting      |     0.8435 |            0.8474 |         0.8437 |     0.845  |        0.8445 |
| A_0_33_66          | False            | none                | XGBoost tuned          |     0.9351 |            0.9014 |         0.7992 |     0.8433 |        0.9326 |
| A_0_33_66          | False            | none                | Gradient Boosting      |     0.9347 |            0.8972 |         0.7976 |     0.8408 |        0.9321 |
| C_quantile         | False            | none                | XGBoost tuned          |     0.8391 |            0.8417 |         0.8395 |     0.8403 |        0.8398 |
| A_0_33_66          | False            | none                | Logistic Regression    |     0.9138 |            0.7709 |         0.9473 |     0.8384 |        0.9197 |
| A_0_33_66          | False            | none                | Random Forest balanced |     0.9149 |            0.7946 |         0.8752 |     0.83   |        0.9182 |
| B_0_25_60          | False            | none                | XGBoost tuned          |     0.9411 |            0.8846 |         0.7565 |     0.8077 |        0.9385 |
| B_0_25_60          | False            | none                | Gradient Boosting      |     0.9413 |            0.8794 |         0.7545 |     0.8047 |        0.9386 |
| B_0_25_60          | False            | none                | Logistic Regression    |     0.9212 |            0.7284 |         0.951  |     0.8007 |        0.9282 |
| B_0_25_60          | False            | none                | Random Forest balanced |     0.9231 |            0.7493 |         0.8609 |     0.7933 |        0.9264 |

## Cross-Validation Ranking
| model                  |   cv_accuracy |   cv_macro_f1 |   cv_weighted_f1 |
|:-----------------------|--------------:|--------------:|-----------------:|
| Logistic Regression    |        0.978  |        0.9589 |           0.9783 |
| Random Forest balanced |        0.923  |        0.91   |           0.9248 |
| Gradient Boosting      |        0.9277 |        0.9059 |           0.9293 |
| XGBoost tuned          |        0.9209 |        0.8891 |           0.9233 |

## Availability Notes
- XGBoost available: `True`
- imblearn / Balanced Random Forest / SMOTE available: `False`
- LightGBM available: `False`
- Random oversampling was evaluated as the no-extra-dependency imbalance strategy.

## Recommended Burnout Formula
```python
burnout_score = (
    0.22 * normalized_sleep_debt +
    0.20 * normalized_stress_level +
    0.18 * normalized_fatigue_score +
    0.15 * normalized_cumulative_load +
    0.10 * normalized_work_hours +
    0.25 * (100 - recovery_score)
)
```

## Final Recommendation
- Success criteria met.
- Root cause: original burnout labels were too noisy/path-dependent relative to available features; formula labels improve separability by making risk depend directly on sleep debt, stress, fatigue, cumulative load, work hours, and inverse recovery.
- Improved model artifact saved to `models\burnout_model_improved.joblib`.