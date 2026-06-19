# Model Selection Report

## Preprocessing Experiments
Scaler comparison on productivity quick model:
| scaler   |     MAE |    RMSE |       R2 |
|:---------|--------:|--------:|---------:|
| standard | 3.07978 | 3.97537 | 0.973896 |
| robust   | 3.07981 | 3.97532 | 0.973897 |
| minmax   | 3.0797  | 3.97527 | 0.973897 |

Encoder comparison on burnout quick model:
| encoder   |   Accuracy |   Precision_macro |   Recall_macro |   F1_macro |
|:----------|-----------:|------------------:|---------------:|-----------:|
| onehot    |   0.928681 |          0.896926 |       0.833324 |   0.862328 |
| ordinal   |   0.928126 |          0.896363 |       0.8313   |   0.860869 |

## Hyperparameter Search
| model                              |   best_score | best_params                                                                                                                               |
|:-----------------------------------|-------------:|:------------------------------------------------------------------------------------------------------------------------------------------|
| Tuned Random Forest Regressor      |    -3.42064  | {'model__n_estimators': 100, 'model__min_samples_split': 2, 'model__min_samples_leaf': 1, 'model__max_depth': 8}                          |
| Tuned Gradient Boosting Regressor  |    -3.31101  | {'model__n_estimators': 120, 'model__max_depth': 2, 'model__learning_rate': 0.1}                                                          |
| Tuned XGBoost Regressor            |    -3.28584  | {'model__subsample': 1.0, 'model__n_estimators': 120, 'model__max_depth': 3, 'model__learning_rate': 0.1, 'model__colsample_bytree': 0.8} |
| Tuned Random Forest Classifier     |     0.780669 | {'model__n_estimators': 100, 'model__min_samples_split': 2, 'model__min_samples_leaf': 1, 'model__max_depth': 8}                          |
| Tuned Gradient Boosting Classifier |     0.795211 | {'model__n_estimators': 120, 'model__max_depth': 2, 'model__learning_rate': 0.1}                                                          |

## Leakage Prevention
- Excluded target columns from features.
- Excluded productivity_trend and burnout_momentum from model features because they are target-derived current-period signals.
- Used chronological train/test split and TimeSeriesSplit cross-validation.
- Kept sleep_debt and cumulative_load because they are rolling features available up to the prediction date.

## SMOTE Note
SMOTE was not applied because `imblearn` is not installed and the time-series structure makes synthetic neighbor sampling risky. Class imbalance is addressed with class weights for Random Forest and macro-averaged metrics for selection.