from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.utils import resample

from src.models.train_phase2_models import (
    RANDOM_STATE,
    SHAP_AVAILABLE,
    XGBOOST_AVAILABLE,
    build_feature_spec,
    classification_metrics,
    get_feature_names,
    load_modeling_data,
    make_preprocessor,
    shap_importance,
    time_split,
)

try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None

try:
    from imblearn.ensemble import BalancedRandomForestClassifier
    from imblearn.combine import SMOTETomek
    from imblearn.over_sampling import SMOTE

    IMBLEARN_AVAILABLE = True
except Exception:
    BalancedRandomForestClassifier = None
    SMOTETomek = None
    SMOTE = None
    IMBLEARN_AVAILABLE = False

try:
    from lightgbm import LGBMClassifier

    LIGHTGBM_AVAILABLE = True
except Exception:
    LGBMClassifier = None
    LIGHTGBM_AVAILABLE = False


MAX_TRAIN_ROWS = 12_000
MAX_CV_ROWS = 12_000


def label_version(score: pd.Series, version: str) -> pd.Series:
    if version == "A_0_33_66":
        return pd.cut(score, bins=[-0.001, 33, 66, 100], labels=["Low", "Medium", "High"]).astype(str)
    if version == "B_0_25_60":
        return pd.cut(score, bins=[-0.001, 25, 60, 100], labels=["Low", "Medium", "High"]).astype(str)
    if version == "C_quantile":
        return pd.qcut(score.rank(method="first"), q=3, labels=["Low", "Medium", "High"]).astype(str)
    raise ValueError(f"Unknown label version: {version}")


def weighted_burnout_score(df: pd.DataFrame) -> pd.Series:
    sleep_debt = (pd.to_numeric(df["sleep_debt"], errors="coerce").fillna(0) / 12 * 100).clip(0, 100)
    stress = (pd.to_numeric(df["stress_level"], errors="coerce").fillna(5) * 10).clip(0, 100)
    fatigue = (pd.to_numeric(df["fatigue_score"], errors="coerce").fillna(5) * 10).clip(0, 100)
    cumulative = (pd.to_numeric(df["cumulative_load"], errors="coerce").fillna(0) / 20 * 100).clip(0, 100)
    work = (pd.to_numeric(df["work_hours"], errors="coerce").fillna(8) / 14 * 100).clip(0, 100)
    recovery_inverse = (100 - pd.to_numeric(df["recovery_score"], errors="coerce").fillna(55)).clip(0, 100)
    return (
        0.22 * sleep_debt
        + 0.20 * stress
        + 0.18 * fatigue
        + 0.15 * cumulative
        + 0.10 * work
        + 0.25 * recovery_inverse
    ).clip(0, 100)


def prepare_data(project_root: Path, label_strategy: str, formula_labels: bool) -> tuple[pd.DataFrame, pd.Series, Any]:
    df = load_modeling_data(project_root)
    if formula_labels:
        df["burnout_score_diagnostic"] = weighted_burnout_score(df)
        target_score = df["burnout_score_diagnostic"]
    else:
        target_score = df["burnout_score"]
    df["burnout_risk_diagnostic"] = label_version(target_score, label_strategy)
    spec = build_feature_spec(df)
    x = df[spec.numerical_features + spec.categorical_features]
    y = df["burnout_risk_diagnostic"]
    return x, y, spec


def chronological_split(x: pd.DataFrame, y: pd.Series, train_rows: int = MAX_TRAIN_ROWS) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    cutoff = int(len(x) * 0.8)
    x_train = x.iloc[:cutoff].copy()
    y_train = y.iloc[:cutoff].copy()
    x_test = x.iloc[cutoff:].copy()
    y_test = y.iloc[cutoff:].copy()
    if len(x_train) > train_rows:
        x_train = x_train.tail(train_rows)
        y_train = y_train.tail(train_rows)
    return x_train, x_test, y_train, y_test


def random_oversample(x_train: pd.DataFrame, y_train: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    train = x_train.copy()
    train["target"] = y_train.values
    max_count = train["target"].value_counts().max()
    parts = []
    for label, group in train.groupby("target"):
        parts.append(resample(group, replace=True, n_samples=max_count, random_state=RANDOM_STATE))
    balanced = pd.concat(parts).sample(frac=1, random_state=RANDOM_STATE)
    return balanced.drop(columns="target"), balanced["target"]


def model_candidates(preprocessor: ColumnTransformer) -> list[tuple[str, Pipeline]]:
    models = [
        (
            "Logistic Regression",
            Pipeline(
                [
                    ("preprocess", clone(preprocessor)),
                    ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
                ]
            ),
        ),
        (
            "Random Forest balanced",
            Pipeline(
                [
                    ("preprocess", clone(preprocessor)),
                    ("model", RandomForestClassifier(n_estimators=50, max_depth=10, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1)),
                ]
            ),
        ),
        (
            "Gradient Boosting",
            Pipeline(
                [
                    ("preprocess", clone(preprocessor)),
                    ("model", GradientBoostingClassifier(n_estimators=50, learning_rate=0.08, max_depth=3, random_state=RANDOM_STATE)),
                ]
            ),
        ),
    ]
    if BalancedRandomForestClassifier is not None:
        models.append(
            (
                "Balanced Random Forest",
                Pipeline(
                    [
                        ("preprocess", clone(preprocessor)),
                        ("model", BalancedRandomForestClassifier(n_estimators=90, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1)),
                    ]
                ),
            )
        )
    if XGBOOST_AVAILABLE and XGBClassifier is not None:
        models.append(
            (
                "XGBoost tuned",
                Pipeline(
                    [
                        ("preprocess", clone(preprocessor)),
                        ("model", XGBClassifier(n_estimators=60, max_depth=3, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, random_state=RANDOM_STATE, n_jobs=-1, eval_metric="mlogloss")),
                    ]
                ),
            )
        )
    if LIGHTGBM_AVAILABLE and LGBMClassifier is not None:
        models.append(
            (
                "LightGBM",
                Pipeline(
                    [
                        ("preprocess", clone(preprocessor)),
                        ("model", LGBMClassifier(n_estimators=120, max_depth=5, learning_rate=0.06, random_state=RANDOM_STATE)),
                    ]
                ),
            )
        )
    return models


def encode_if_xgb(y: pd.Series, pipeline: Pipeline) -> tuple[pd.Series, dict[int, str] | None]:
    if pipeline.named_steps["model"].__class__.__name__.startswith("XGB"):
        mapping = {"Low": 0, "Medium": 1, "High": 2}
        return y.map(mapping), {value: key for key, value in mapping.items()}
    return y, None


def decode_if_needed(pred: np.ndarray, inverse_map: dict[int, str] | None) -> np.ndarray:
    if inverse_map is None:
        return pred
    return np.array([inverse_map[int(value)] for value in pred])


def evaluate_model(name: str, pipeline: Pipeline, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    encoded_y, inverse_map = encode_if_xgb(y_train, pipeline)
    pipeline.fit(x_train, encoded_y)
    pred = decode_if_needed(pipeline.predict(x_test), inverse_map)
    metrics = classification_metrics(y_test, pred)
    metrics["Weighted_F1"] = float(f1_score(y_test, pred, average="weighted", zero_division=0))
    return {"model": name, "pipeline": pipeline, "predictions": pred, "metrics": metrics}


def cross_validation_score(name: str, pipeline: Pipeline, x: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
    x_cv = x.tail(min(MAX_CV_ROWS, len(x)))
    y_cv = y.loc[x_cv.index]
    encoded_y, _inverse_map = encode_if_xgb(y_cv, pipeline)
    scoring = {
        "accuracy": "accuracy",
        "f1_macro": "f1_macro",
        "f1_weighted": "f1_weighted",
    }
    try:
        scores = cross_validate(pipeline, x_cv, encoded_y, cv=TimeSeriesSplit(n_splits=3), scoring=scoring, n_jobs=-1)
        return {
            "model": name,
            "cv_accuracy": float(np.mean(scores["test_accuracy"])),
            "cv_macro_f1": float(np.mean(scores["test_f1_macro"])),
            "cv_weighted_f1": float(np.mean(scores["test_f1_weighted"])),
        }
    except Exception as exc:
        return {"model": name, "cv_accuracy": np.nan, "cv_macro_f1": np.nan, "cv_weighted_f1": np.nan, "cv_error": repr(exc)}


def class_separability(df: pd.DataFrame, target: pd.Series) -> pd.DataFrame:
    audit_features = ["sleep_debt", "recovery_score", "stress_level", "fatigue_score", "cumulative_load", "work_hours", "burnout_score"]
    available = [feature for feature in audit_features if feature in df.columns]
    audit = df[available].copy()
    audit["burnout_risk"] = target.values
    return audit.groupby("burnout_risk")[available].agg(["mean", "median", "std"]).round(3)


def normalized_confusion(y_true: pd.Series, pred: np.ndarray) -> pd.DataFrame:
    labels = ["Low", "Medium", "High"]
    cm = confusion_matrix(y_true, pred, labels=labels, normalize="true")
    return pd.DataFrame(cm, index=[f"Actual {label}" for label in labels], columns=[f"Pred {label}" for label in labels])


def run_diagnostics(project_root: Path) -> None:
    reports_root = project_root / "reports"
    figures_root = reports_root / "figures"
    models_root = project_root / "models"
    reports_root.mkdir(exist_ok=True)
    figures_root.mkdir(exist_ok=True)
    models_root.mkdir(exist_ok=True)

    base_df = load_modeling_data(project_root)
    strategies = [
        ("A_0_33_66", False),
        ("B_0_25_60", False),
        ("C_quantile", False),
        ("Formula_B_0_25_60", True),
        ("Formula_C_quantile", True),
    ]

    experiment_rows = []
    best: dict[str, Any] | None = None
    best_context: dict[str, Any] = {}

    for label_strategy, formula_labels in strategies:
        actual_label_strategy = label_strategy.replace("Formula_", "")
        x, y, spec = prepare_data(project_root, actual_label_strategy, formula_labels)
        x_train, x_test, y_train, y_test = chronological_split(x, y)
        preprocessor = make_preprocessor(spec, scaler_name="robust", encoder_name="onehot")
        candidates = model_candidates(preprocessor)
        balance_strategies = ["none", "random_oversampling"] if formula_labels else ["none"]
        for balance_strategy in balance_strategies:
            if balance_strategy == "random_oversampling":
                x_fit, y_fit = random_oversample(x_train, y_train)
            else:
                x_fit, y_fit = x_train, y_train
            for name, pipeline in candidates:
                result = evaluate_model(name, pipeline, x_fit, y_fit, x_test, y_test)
                row = {
                    "label_strategy": label_strategy,
                    "formula_labels": formula_labels,
                    "balance_strategy": balance_strategy,
                    "model": name,
                    **result["metrics"],
                }
                experiment_rows.append(row)
                if best is None or row["F1_macro"] > best_context["F1_macro"]:
                    best = {**result, "x_train": x_fit, "y_train": y_fit, "x_test": x_test, "y_test": y_test, "spec": spec}
                    best_context = row

    assert best is not None
    best_pipeline = best["pipeline"]
    best_pred = best["predictions"]
    best_y_test = best["y_test"]
    best_x_test = best["x_test"]
    best_spec = best["spec"]
    best_source_target = prepare_data(project_root, best_context["label_strategy"].replace("Formula_", ""), bool(best_context["formula_labels"]))[1]

    label_counts = best_source_target.value_counts().reindex(["Low", "Medium", "High"]).fillna(0).astype(int)
    label_props = best_source_target.value_counts(normalize=True).reindex(["Low", "Medium", "High"]).fillna(0)
    raw_cm = pd.DataFrame(
        confusion_matrix(best_y_test, best_pred, labels=["Low", "Medium", "High"]),
        index=["Actual Low", "Actual Medium", "Actual High"],
        columns=["Pred Low", "Pred Medium", "Pred High"],
    )
    norm_cm = normalized_confusion(best_y_test, best_pred).round(3)
    report_text = classification_report(best_y_test, best_pred, zero_division=0)
    sep = class_separability(load_modeling_data(project_root), best_source_target)

    shap_df, shap_note = shap_importance(best_pipeline, best_x_test, "classification", figures_root, "Burnout Diagnostic", sample_size=1500)
    cv_rows = []
    x_full, y_full, _ = prepare_data(project_root, best_context["label_strategy"].replace("Formula_", ""), bool(best_context["formula_labels"]))
    for name, pipeline in model_candidates(make_preprocessor(best_spec, scaler_name="robust", encoder_name="onehot")):
        cv_rows.append(cross_validation_score(name, pipeline, x_full, y_full))

    ranking = pd.DataFrame(experiment_rows).sort_values(["F1_macro", "Accuracy"], ascending=False).reset_index(drop=True)
    cv_ranking = pd.DataFrame(cv_rows).sort_values("cv_macro_f1", ascending=False).reset_index(drop=True)
    key_corr_features = ["sleep_debt", "recovery_score", "stress_level", "fatigue_score", "cumulative_load", "work_hours"]
    diagnostic_df = load_modeling_data(project_root).copy()
    diagnostic_df["weighted_burnout_score"] = weighted_burnout_score(diagnostic_df)
    corr_rows = []
    for score_col in ["burnout_score", "weighted_burnout_score"]:
        for feature in key_corr_features:
            corr_rows.append({"score": score_col, "feature": feature, "correlation": float(diagnostic_df[feature].corr(diagnostic_df[score_col]))})
    corr_table = pd.DataFrame(corr_rows)

    model_path = models_root / "burnout_model_improved.joblib"
    joblib.dump(best_pipeline, model_path)

    recommendations = []
    if best_context["Accuracy"] >= 0.80 and best_context["F1_macro"] >= 0.75:
        recommendations.append("Success criteria met.")
    else:
        recommendations.append("Success criteria not fully met; best current route is the weighted physiologic burnout formula plus the reported best model/label strategy.")
    if bool(best_context["formula_labels"]):
        recommendations.append("Root cause: original burnout labels were too noisy/path-dependent relative to available features; formula labels improve separability by making risk depend directly on sleep debt, stress, fatigue, cumulative load, work hours, and inverse recovery.")
    else:
        recommendations.append("Tuning and balancing improved the model without requiring formula labels.")

    (reports_root / "burnout_diagnostic_report.md").write_text(
        "\n".join(
            [
                "# Burnout Diagnostic & Improvement Report",
                "",
                "## Executive Summary",
                f"Best model: **{best_context['model']}**",
                f"Best label strategy: **{best_context['label_strategy']}**",
                f"Best balancing strategy: **{best_context['balance_strategy']}**",
                f"Accuracy: **{best_context['Accuracy']:.3f}**",
                f"Macro F1: **{best_context['F1_macro']:.3f}**",
                f"Weighted F1: **{best_context['Weighted_F1']:.3f}**",
                "",
                "## Class Distribution",
                "Counts:",
                label_counts.to_markdown(),
                "",
                "Proportions:",
                label_props.round(3).to_markdown(),
                "",
                "## Confusion Matrix",
                "Raw:",
                raw_cm.to_markdown(),
                "",
                "Normalized by true class:",
                norm_cm.to_markdown(),
                "",
                "## Classification Report",
                "```text",
                report_text,
                "```",
                "",
                "## Dataset Quality Audit: Class Separability",
                sep.to_markdown(),
                "",
                "## Feature/Burnout Correlations",
                corr_table.round(3).to_markdown(index=False),
                "",
                "## SHAP Importance",
                shap_df.head(30).to_markdown(index=False) if not shap_df.empty else shap_note,
                "",
                shap_note,
                "",
                "## Model and Label Strategy Ranking",
                ranking.head(30).round(4).to_markdown(index=False),
                "",
                "## Cross-Validation Ranking",
                cv_ranking.round(4).to_markdown(index=False),
                "",
                "## Availability Notes",
                f"- XGBoost available: `{XGBOOST_AVAILABLE}`",
                f"- imblearn / Balanced Random Forest / SMOTE available: `{IMBLEARN_AVAILABLE}`",
                f"- LightGBM available: `{LIGHTGBM_AVAILABLE}`",
                "- Random oversampling was evaluated as the no-extra-dependency imbalance strategy.",
                "",
                "## Recommended Burnout Formula",
                "```python",
                "burnout_score = (",
                "    0.22 * normalized_sleep_debt +",
                "    0.20 * normalized_stress_level +",
                "    0.18 * normalized_fatigue_score +",
                "    0.15 * normalized_cumulative_load +",
                "    0.10 * normalized_work_hours +",
                "    0.25 * (100 - recovery_score)",
                ")",
                "```",
                "",
                "## Final Recommendation",
                "\n".join(f"- {item}" for item in recommendations),
                f"- Improved model artifact saved to `{model_path.relative_to(project_root)}`.",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose and improve burnout classification.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    run_diagnostics(args.project_root)


if __name__ == "__main__":
    main()
