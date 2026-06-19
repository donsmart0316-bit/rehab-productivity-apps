# EDA Summary

## Key Relationships

- Sleep vs productivity correlation: -0.046
- Sleep vs recovery correlation: 0.017
- Stress vs burnout correlation: 0.441
- Recovery vs productivity correlation: 0.913
- Work hours vs burnout correlation: 0.716
- Activity vs recovery correlation: 0.018

## Synthetic Longitudinal Dataset

- Rows: 59,889
- Users: 1,000
- Chronotypes: {'Intermediate': 27344, 'Morning': 18700, 'Evening': 13845}
- Includes sleep debt, cumulative load, task load score, burnout momentum, productivity trend, focus block length, break duration, cognitive load, and chronotype.

## Recommended Imputation

- Median imputation for continuous model features when training tabular models.
- User-level forward fill for longitudinal app telemetry.
- Add missingness indicators for future real-world sparse inputs.