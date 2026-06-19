# Productivity & Recovery Coach

Data, modeling, recommendation, and reasoning foundation for an AI-powered productivity, recovery, and burnout prevention coach.

## What Is Included

- Kaggle downloader for the requested public datasets.
- Unified master schema and raw-to-processed dataset builder.
- Calibrated synthetic longitudinal dataset generator for 2,000 users across 180 days.
- Hourly circadian productivity profiles with 24 records per synthetic user.
- Reusable feature engineering pipeline.
- Phase 2 ML training pipeline for productivity regression and burnout-risk classification.
- Phase 3 hybrid recommendation engine with physiology rules, scheduling logic, LLM explanations, and feedback storage.
- Phase 4 Streamlit MVP with daily planning, analytics, history, feedback, and export workflows.
- Phase 5 product maturity layer with simulation testing, confidence scoring, monitoring logs, robustness reports, and personalization foundations.
- EDA notebook and Markdown reports.

## Project Structure

```text
data/
  raw/
  processed/master_dataset.csv
  synthetic/synthetic_productivity_dataset.csv
  synthetic/hourly_circadian_profiles.csv
  feedback/feedback_log.csv
models/
  productivity_model.joblib
  burnout_model.joblib
  burnout_model_improved.joblib
  preprocessing_pipeline.joblib
outputs/
  sample_daily_plan.json
  sample_weekly_plan.json
  sample_llm_outputs.md
app/
  Home.py
  pages/
    Daily_Planner.py
    Weekly_Overview.py
    Analytics.py
    History.py
    Feedback.py
  components/
  services/
.streamlit/config.toml
notebooks/eda.ipynb
notebooks/productivity_model_training.ipynb
notebooks/burnout_model_training.ipynb
reports/dataset_analysis.md
reports/eda_summary.md
reports/data_dictionary.md
reports/synthetic_validation_report.md
reports/profile_validation_report.md
reports/productivity_model_report.md
reports/burnout_model_report.md
reports/model_selection_report.md
reports/feature_importance_report.md
reports/shap_analysis.md
reports/burnout_diagnostic_report.md
src/data_processing/
src/synthetic_data/
src/features/
src/models/
src/recommendation_engine/
src/llm/
src/feedback/
src/monitoring/
src/validation/phase5_maturity.py
analytics/
logs/
dashboards/
monitoring/
mobile/
master_dataset.csv
synthetic_productivity_dataset.csv
```

## Run The Streamlit MVP

From this folder:

```powershell
$env:PYTHONPATH="$PWD"
streamlit run app/Home.py
```

The app includes:

- Persistent sidebar profile settings.
- Daily check-in form for sleep, stress, energy, workload, and tasks.
- Productivity, burnout, recovery, sleep debt, and task-load predictions.
- Optimized daily schedule with focus blocks, meetings, admin work, posture resets, eye-strain prevention, and recovery breaks.
- AI coaching panel using Groq/LangChain when `GROQ_API_KEY` or `GROK_API_KEY` is configured, with deterministic fallback text otherwise.
- Energy and productivity curves, burnout gauge, recovery/productivity trends, plan history, feedback storage, and Markdown/TXT/PDF export.

## Streamlit Community Cloud Deployment

1. Push the project to a GitHub repository.
2. In Streamlit Community Cloud, choose `app/Home.py` as the entrypoint.
3. Ensure `requirements.txt` is present at the project root.
4. Add optional secrets for LLM coaching:

```toml
GROQ_API_KEY = "your_key_here"
```

5. Keep the saved `models/` and required `data/` artifacts in the repository or attach them through your deployment storage workflow.

## Run The Pipeline

From this folder:

```powershell
$env:PYTHONPATH="$PWD"
python -m src.data_processing.download_datasets --project-root .
python -m src.synthetic_data.generate_synthetic --project-root . --users 2000 --days 180
python -m src.data_processing.build_master_dataset --project-root .
python -m src.data_processing.generate_reports --project-root .
python -m src.models.train_phase2_models --project-root .
python -m src.models.burnout_diagnostics --project-root .
python -m src.recommendation_engine.sample_runner --project-root .
python -m src.validation.phase5_maturity --project-root . --users 500
```

Kaggle downloads require authentication. Run `kaggle auth login` or configure a Kaggle token before the download step. If raw Kaggle CSVs are present under `data/raw`, the master builder uses them.

You can also place downloaded Kaggle ZIP archives in `kaggle data/`. The current pipeline reads those ZIPs directly, skips `sample_submission.csv` and `test.csv`, and builds the master dataset from the real training/source files. If no real raw files or ZIPs are available, it falls back to the generated longitudinal dataset so downstream modeling can begin immediately.

## Modeling Targets

- `productivity_score`: productivity prediction target.
- `burnout_score`: burnout risk target.
- `recovery_score`: recovery readiness target.

## Current Phase 2 Results

- Productivity model: Tuned XGBoost Regressor, MAE about 3.23, R2 about 0.96 on the chronological holdout.
- Improved burnout model: Logistic Regression using physiologic formula + quantile labels, macro F1 about 0.99 on the diagnostic holdout.
- Explainability: SHAP and permutation importance reports are in `reports/`.

## Phase 3 Recommendation Engine

The recommendation engine turns user inputs and model predictions into structured coaching outputs:

- Circadian scheduling rules by chronotype.
- Ultradian focus and break cycles adjusted by fatigue, recovery, and burnout risk.
- Physiotherapy-informed posture, mobility, walking, and eye-strain interventions.
- Burnout protection rules that reduce workload and cognitive demand when risk is elevated.
- Task scheduling for deep work, creative work, meetings, admin, planning, and learning.
- Alternative plans: primary, conservative, and high-performance.
- LLM explanation layer using LangChain/Groq when credentials are available, with deterministic fallback text otherwise.
- Feedback storage for future personalization and reinforcement learning.

## Phase 4 MVP Application

The Streamlit product layer wraps the existing pipeline into a practical user workflow:

- `app/services/prediction_service.py` prepares model features, applies 0-100 productivity bounds, estimates sleep debt, calibrates burnout risk, and computes recovery.
- `app/services/recommendation_service.py` converts user tasks into scheduler inputs and generates primary, conservative, and high-performance plans.
- `app/services/llm_service.py` produces daily and weekly coaching text.
- `app/services/history_service.py` stores daily predictions and plans under `data/history/`.
- `app/services/feedback_service.py` writes user feedback to `data/feedback/feedback_log.csv`.
- `app/services/export_service.py` creates Markdown, TXT, and PDF plan exports.

## Phase 5 Product Maturity

Phase 5 adds reliability and personalization infrastructure:

- Large-scale simulated user testing across students, remote workers, executives, founders, shift workers, new parents, high performers, and recovery-limited users.
- Edge-case testing for sleep deprivation, extreme stress, high workload, chronotype shifts, and contradictory self-reported inputs.
- Input validation, reasonableness checks, confidence scores, and warning messages.
- Monitoring logs in `logs/prediction_logs.csv`, `logs/feedback_logs.csv`, and `logs/system_logs.csv`.
- Longitudinal analytics for weekly, monthly, and quarterly trends.
- RLHF-ready feedback records for adherence, satisfaction, perceived productivity, fatigue, and comments.
- Reports in `reports/user_simulation_report.md`, `reports/edge_case_report.md`, `reports/confidence_scoring_report.md`, `reports/robustness_report.md`, `reports/personalization_report.md`, `reports/mobile_readiness_report.md`, `reports/professional_version_roadmap.md`, and `reports/final_product_evaluation.md`.

## Engineered Features

- `sleep_debt`: rolling 7-day sleep deficit.
- `cumulative_load`: rolling workload pressure.
- `task_load_score`: combined task, work hour, meeting, and complexity load.
- `burnout_momentum`: recent burnout trajectory.
- `productivity_trend`: recent productivity trajectory.
- `circadian_phase`, `time_of_day_bin`, `chronotype_proxy`: time-aware recommendation features.
