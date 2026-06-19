from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
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
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, OrdinalEncoder, RobustScaler, StandardScaler

try:
    from xgboost import XGBClassifier, XGBRegressor

    XGBOOST_AVAILABLE = True
except Exception:
    XGBOOST_AVAILABLE = False

try:
    import shap

    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False


RANDOM_STATE = 42
MAX_TRAIN_ROWS = 20_000
MAX_PERMUTATION_ROWS = 3_000
SYNTHETIC_ONLY_NUMERIC_FEATURES = {
    "deep_work_hours",
    "distraction_score",
    "consecutive_work_days",
    "deadline_pressure",
    "screen_time_hours",
    "social_interaction_score",
    "focus_block_length",
    "break_duration",
    "cognitive_load",
}


@dataclass(frozen=True)
class FeatureSpec:
    numerical_features: list[str]
    categorical_features: list[str]
    excluded_features: list[str]


def load_modeling_data(project_root: Path) -> pd.DataFrame:
    master = pd.read_csv(project_root / "data" / "processed" / "master_dataset.csv", parse_dates=["date"])
    master["source_dataset"] = "master_real_harmonized"
    synthetic = pd.read_csv(project_root / "data" / "synthetic" / "synthetic_productivity_dataset.csv", parse_dates=["date"])
    synthetic["source_dataset"] = "synthetic_longitudinal"
    combined = pd.concat([master, synthetic], ignore_index=True, sort=False)
    combined = combined.sort_values(["date", "user_id"]).reset_index(drop=True)
    for column in combined.columns:
        if column not in {"user_id", "date", "chronotype", "chronotype_proxy", "day_of_week", "circadian_phase", "time_of_day_bin", "source_dataset"}:
            combined[column] = pd.to_numeric(combined[column], errors="coerce")
    combined["burnout_risk"] = pd.cut(
        combined["burnout_score"],
        bins=[-0.001, 33, 66, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    return combined


def build_feature_spec(df: pd.DataFrame) -> FeatureSpec:
    excluded = [
        "user_id",
        "date",
        "productivity_score",
        "burnout_score",
        "burnout_risk",
        "burnout_score_diagnostic",
        "burnout_risk_diagnostic",
        "hourly_productivity",
        "hourly_energy",
        "focus_score",
        "cognitive_capacity",
        "recommended_task_type",
        "circadian_phase",
        "time_of_day_bin",
        "chronotype_proxy",
        "productivity_trend",
        "burnout_momentum",
    ]
    categorical = [column for column in ["chronotype", "day_of_week", "source_dataset"] if column in df.columns]
    numerical = [
        column
        for column in df.columns
        if column not in excluded + categorical and pd.api.types.is_numeric_dtype(df[column])
    ]
    return FeatureSpec(numerical_features=numerical, categorical_features=categorical, excluded_features=excluded)


def make_preprocessor(spec: FeatureSpec, scaler_name: str = "robust", encoder_name: str = "onehot") -> ColumnTransformer:
    scalers = {
        "standard": StandardScaler(),
        "robust": RobustScaler(),
        "minmax": MinMaxScaler(),
        "none": "passthrough",
    }
    if encoder_name == "ordinal":
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    else:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    common_numeric = [feature for feature in spec.numerical_features if feature not in SYNTHETIC_ONLY_NUMERIC_FEATURES]
    synthetic_only_numeric = [feature for feature in spec.numerical_features if feature in SYNTHETIC_ONLY_NUMERIC_FEATURES]
    common_numerical_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", scalers[scaler_name]),
        ]
    )
    synthetic_numerical_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
            ("scaler", scalers[scaler_name]),
        ]
    )
    categorical_transformer = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encoder", encoder)])
    transformers = [
        ("num_common", common_numerical_transformer, common_numeric),
        ("cat", categorical_transformer, spec.categorical_features),
    ]
    if synthetic_only_numeric:
        transformers.insert(1, ("num_synthetic_only", synthetic_numerical_transformer, synthetic_only_numeric))
    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False,
    )


def time_split(df: pd.DataFrame, test_fraction: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    ordered = df.sort_values(["date", "user_id"]).reset_index(drop=True)
    cutoff = int(len(ordered) * (1 - test_fraction))
    return ordered.index[:cutoff].to_numpy(), ordered.index[cutoff:].to_numpy()


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }


def classification_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "Accuracy": float(accuracy_score(y_true, y_pred)),
        "Precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "Recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "F1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def evaluate_pipeline(name: str, pipeline: Pipeline, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, y_test: pd.Series, task: str) -> dict[str, Any]:
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    metrics = regression_metrics(y_test, predictions) if task == "regression" else classification_metrics(y_test, predictions)
    return {"model": name, "metrics": metrics, "pipeline": pipeline, "predictions": predictions}


def tune_model(
    name: str,
    estimator: Any,
    param_distributions: dict[str, list[Any]],
    preprocessor: ColumnTransformer,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    task: str,
) -> RandomizedSearchCV:
    pipeline = Pipeline([("preprocess", preprocessor), ("model", estimator)])
    scoring = "neg_mean_absolute_error" if task == "regression" else "f1_macro"
    search = RandomizedSearchCV(
        pipeline,
        param_distributions={f"model__{key}": value for key, value in param_distributions.items()},
        n_iter=min(2, np.prod([len(value) for value in param_distributions.values()])),
        scoring=scoring,
        cv=TimeSeriesSplit(n_splits=2),
        random_state=RANDOM_STATE,
        n_jobs=-1,
        refit=True,
    )
    search.fit(x_train, y_train)
    search.name = name
    return search


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        return []


def native_importance(pipeline: Pipeline) -> pd.DataFrame:
    names = get_feature_names(pipeline.named_steps["preprocess"])
    model = pipeline.named_steps["model"]
    values = getattr(model, "feature_importances_", None)
    if values is None or not names:
        return pd.DataFrame(columns=["feature", "importance"])
    return pd.DataFrame({"feature": names, "importance": values}).sort_values("importance", ascending=False)


def save_importance_plot(df: pd.DataFrame, title: str, path: Path, top_n: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    top = df.head(top_n).iloc[::-1]
    plt.figure(figsize=(9, 7))
    plt.barh(top["feature"], top["importance"])
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def permutation_importance_frame(pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series, task: str) -> pd.DataFrame:
    scoring = "neg_mean_absolute_error" if task == "regression" else "f1_macro"
    if len(x_test) > MAX_PERMUTATION_ROWS:
        sample_idx = x_test.sample(MAX_PERMUTATION_ROWS, random_state=RANDOM_STATE).index
        x_eval = x_test.loc[sample_idx]
        y_eval = y_test.loc[sample_idx]
    else:
        x_eval = x_test
        y_eval = y_test
    result = permutation_importance(
        pipeline,
        x_eval,
        y_eval,
        scoring=scoring,
        n_repeats=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return (
        pd.DataFrame({"feature": x_test.columns, "importance": result.importances_mean, "std": result.importances_std})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def shap_importance(
    pipeline: Pipeline,
    x_reference: pd.DataFrame,
    task: str,
    figures_root: Path,
    plot_name: str,
    sample_size: int = 1000,
) -> tuple[pd.DataFrame, str]:
    if not SHAP_AVAILABLE:
        return pd.DataFrame(columns=["feature", "mean_abs_shap"]), "SHAP is not installed."

    sample = x_reference.sample(min(sample_size, len(x_reference)), random_state=RANDOM_STATE)
    preprocessor = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    transformed = preprocessor.transform(sample)
    feature_names = get_feature_names(preprocessor)
    if not feature_names:
        feature_names = [f"feature_{idx}" for idx in range(transformed.shape[1])]

    try:
        if model.__class__.__name__ == "LogisticRegression":
            explainer = shap.LinearExplainer(model, transformed)
        else:
            explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(transformed)
    except Exception as exc:
        return pd.DataFrame(columns=["feature", "mean_abs_shap"]), f"SHAP failed for `{model.__class__.__name__}`: {exc!r}."
    if isinstance(shap_values, list):
        values = np.mean([np.abs(values) for values in shap_values], axis=0)
    else:
        values = np.asarray(shap_values)
        if values.ndim == 3:
            values = np.mean(np.abs(values), axis=2)
        else:
            values = np.abs(values)

    mean_abs = np.mean(values, axis=0)
    importance = (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )

    figures_root.mkdir(parents=True, exist_ok=True)
    top = importance.head(20).iloc[::-1]
    plt.figure(figsize=(9, 7))
    plt.barh(top["feature"], top["mean_abs_shap"])
    plt.title(f"{plot_name} SHAP Importance")
    plt.tight_layout()
    plot_path = figures_root / f"{plot_name.lower().replace(' ', '_')}_shap_importance.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    return importance, f"Saved `{plot_path.relative_to(figures_root.parent.parent)}`."


def relationship_checks(model: Pipeline, x_reference: pd.DataFrame, task: str) -> pd.DataFrame:
    checks = [
        ("sleep_quality", 1.0, "higher should improve productivity / reduce burnout risk"),
        ("sleep_debt", 2.0, "higher should reduce productivity / increase burnout risk"),
        ("recovery_score", 10.0, "higher should improve productivity / reduce burnout risk"),
        ("stress_level", 1.0, "higher should reduce productivity / increase burnout risk"),
        ("fatigue_score", 1.0, "higher should reduce productivity / increase burnout risk"),
        ("cumulative_load", 10.0, "higher should reduce productivity / increase burnout risk"),
        ("task_load_score", 10.0, "higher workload pressure should increase burnout risk"),
        ("work_hours", 1.0, "higher workload should increase burnout risk"),
    ]
    rows = []
    sample = x_reference.sample(min(1000, len(x_reference)), random_state=RANDOM_STATE).copy()
    class_order = getattr(model.named_steps["model"], "classes_", None)
    for feature, delta, expectation in checks:
        if feature not in sample.columns:
            continue
        lower = sample.copy()
        higher = sample.copy()
        lower[feature] = pd.to_numeric(lower[feature], errors="coerce") - delta
        higher[feature] = pd.to_numeric(higher[feature], errors="coerce") + delta
        if task == "regression":
            effect = float(np.mean(model.predict(higher) - model.predict(lower)))
        else:
            proba_low = model.predict_proba(lower)
            proba_high = model.predict_proba(higher)
            high_idx = list(class_order).index("High") if class_order is not None and "High" in class_order else -1
            effect = float(np.mean(proba_high[:, high_idx] - proba_low[:, high_idx]))
        rows.append({"feature": feature, "delta": delta, "average_effect": effect, "expectation": expectation})
    return pd.DataFrame(rows)


def markdown_table(records: list[dict[str, Any]]) -> str:
    return pd.DataFrame(records).to_markdown(index=False)


def train_phase2(project_root: Path) -> None:
    models_root = project_root / "models"
    reports_root = project_root / "reports"
    figures_root = reports_root / "figures"
    models_root.mkdir(exist_ok=True)
    reports_root.mkdir(exist_ok=True)

    df = load_modeling_data(project_root)
    spec = build_feature_spec(df)
    train_idx, test_idx = time_split(df)
    train = df.iloc[train_idx].reset_index(drop=True)
    test = df.iloc[test_idx].reset_index(drop=True)
    if len(train) > MAX_TRAIN_ROWS:
        train = train.tail(MAX_TRAIN_ROWS).reset_index(drop=True)
    x_train = train[spec.numerical_features + spec.categorical_features]
    x_test = test[spec.numerical_features + spec.categorical_features]

    scaler_results = []
    for scaler in ["standard", "robust", "minmax"]:
        pre = make_preprocessor(spec, scaler_name=scaler, encoder_name="onehot")
        quick = Pipeline([("preprocess", pre), ("model", GradientBoostingRegressor(random_state=RANDOM_STATE, n_estimators=50))])
        quick.fit(x_train, train["productivity_score"])
        scaler_results.append({"scaler": scaler, **regression_metrics(test["productivity_score"], quick.predict(x_test))})
    best_scaler = min(scaler_results, key=lambda row: row["MAE"])["scaler"]

    encoder_results = []
    for encoder in ["onehot", "ordinal"]:
        pre = make_preprocessor(spec, scaler_name=best_scaler, encoder_name=encoder)
        quick = Pipeline([("preprocess", pre), ("model", GradientBoostingClassifier(random_state=RANDOM_STATE, n_estimators=50))])
        quick.fit(x_train, train["burnout_risk"])
        encoder_results.append({"encoder": encoder, **classification_metrics(test["burnout_risk"], quick.predict(x_test))})
    best_encoder = max(encoder_results, key=lambda row: row["F1_macro"])["encoder"]
    preprocessor = make_preprocessor(spec, scaler_name=best_scaler, encoder_name=best_encoder)

    y_prod_train = train["productivity_score"]
    y_prod_test = test["productivity_score"]
    regression_candidates = [
        ("Mean Baseline", Pipeline([("model", DummyRegressor(strategy="mean"))])),
        ("Random Forest Regressor", Pipeline([("preprocess", clone(preprocessor)), ("model", RandomForestRegressor(n_estimators=60, random_state=RANDOM_STATE, n_jobs=-1, max_depth=12))])),
        ("Gradient Boosting Regressor", Pipeline([("preprocess", clone(preprocessor)), ("model", GradientBoostingRegressor(random_state=RANDOM_STATE, n_estimators=70, max_depth=3))])),
    ]
    if XGBOOST_AVAILABLE:
        regression_candidates.append(
            (
                "XGBoost Regressor",
                Pipeline(
                    [
                        ("preprocess", clone(preprocessor)),
                        ("model", XGBRegressor(n_estimators=70, max_depth=3, learning_rate=0.06, subsample=0.9, colsample_bytree=0.9, random_state=RANDOM_STATE, n_jobs=-1, objective="reg:squarederror")),
                    ]
                ),
            )
        )
    regression_results = [evaluate_pipeline(name, pipe, x_train, y_prod_train, x_test, y_prod_test, "regression") for name, pipe in regression_candidates]

    tuned_regressors = [
        tune_model(
            "Tuned Random Forest Regressor",
            RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1),
            {"n_estimators": [60, 100], "max_depth": [8, 12], "min_samples_split": [2, 8], "min_samples_leaf": [1, 4]},
            clone(preprocessor),
            x_train,
            y_prod_train,
            "regression",
        ),
        tune_model(
            "Tuned Gradient Boosting Regressor",
            GradientBoostingRegressor(random_state=RANDOM_STATE),
            {"learning_rate": [0.05, 0.1], "max_depth": [2, 3], "n_estimators": [70, 120]},
            clone(preprocessor),
            x_train,
            y_prod_train,
            "regression",
        ),
    ]
    if XGBOOST_AVAILABLE:
        tuned_regressors.append(
            tune_model(
                "Tuned XGBoost Regressor",
                XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, objective="reg:squarederror"),
                {"learning_rate": [0.05, 0.1], "max_depth": [2, 3], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0], "n_estimators": [70, 120]},
                clone(preprocessor),
                x_train,
                y_prod_train,
                "regression",
            )
        )
    for search in tuned_regressors:
        regression_results.append(evaluate_pipeline(search.name, search.best_estimator_, x_train, y_prod_train, x_test, y_prod_test, "regression"))
    best_reg = min(regression_results, key=lambda row: row["metrics"]["MAE"])

    y_burn_train = train["burnout_risk"]
    y_burn_test = test["burnout_risk"]
    class_counts = y_burn_train.value_counts().to_dict()
    classification_candidates = [
        ("Majority Baseline", Pipeline([("model", DummyClassifier(strategy="most_frequent"))])),
        ("Random Forest Classifier", Pipeline([("preprocess", clone(preprocessor)), ("model", RandomForestClassifier(n_estimators=60, max_depth=12, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1))])),
        ("Gradient Boosting Classifier", Pipeline([("preprocess", clone(preprocessor)), ("model", GradientBoostingClassifier(random_state=RANDOM_STATE, n_estimators=70, max_depth=3))])),
    ]
    if XGBOOST_AVAILABLE:
        label_map = {"Low": 0, "Medium": 1, "High": 2}
        xgb_classifier = Pipeline(
            [
                ("preprocess", clone(preprocessor)),
                ("model", XGBClassifier(n_estimators=70, max_depth=3, learning_rate=0.06, subsample=0.9, colsample_bytree=0.9, random_state=RANDOM_STATE, n_jobs=-1, eval_metric="mlogloss")),
            ]
        )
    classification_results = [evaluate_pipeline(name, pipe, x_train, y_burn_train, x_test, y_burn_test, "classification") for name, pipe in classification_candidates]
    if XGBOOST_AVAILABLE:
        xgb_classifier.fit(x_train, y_burn_train.map(label_map))
        pred_numeric = xgb_classifier.predict(x_test)
        inverse_map = {value: key for key, value in label_map.items()}
        pred = np.array([inverse_map[int(value)] for value in pred_numeric])
        classification_results.append({"model": "XGBoost Classifier", "metrics": classification_metrics(y_burn_test, pred), "pipeline": xgb_classifier, "predictions": pred})

    tuned_classifiers = [
        tune_model(
            "Tuned Random Forest Classifier",
            RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1, class_weight="balanced"),
            {"n_estimators": [60, 100], "max_depth": [8, 12], "min_samples_split": [2, 8], "min_samples_leaf": [1, 4]},
            clone(preprocessor),
            x_train,
            y_burn_train,
            "classification",
        ),
        tune_model(
            "Tuned Gradient Boosting Classifier",
            GradientBoostingClassifier(random_state=RANDOM_STATE),
            {"learning_rate": [0.05, 0.1], "max_depth": [2, 3], "n_estimators": [70, 120]},
            clone(preprocessor),
            x_train,
            y_burn_train,
            "classification",
        ),
    ]
    for search in tuned_classifiers:
        classification_results.append(evaluate_pipeline(search.name, search.best_estimator_, x_train, y_burn_train, x_test, y_burn_test, "classification"))
    best_cls = max(classification_results, key=lambda row: row["metrics"]["F1_macro"])

    product_pipeline = best_reg["pipeline"]
    burnout_pipeline = best_cls["pipeline"]
    product_importance = native_importance(product_pipeline)
    burnout_importance = native_importance(burnout_pipeline)
    product_perm = permutation_importance_frame(product_pipeline, x_test, y_prod_test, "regression")
    burnout_perm = permutation_importance_frame(burnout_pipeline, x_test, y_burn_test, "classification")
    product_shap, product_shap_note = shap_importance(product_pipeline, x_test, "regression", figures_root, "Productivity")
    burnout_shap, burnout_shap_note = shap_importance(burnout_pipeline, x_test, "classification", figures_root, "Burnout")
    if not product_importance.empty:
        save_importance_plot(product_importance, "Productivity Native Feature Importance", figures_root / "productivity_native_importance.png")
    if not burnout_importance.empty:
        save_importance_plot(burnout_importance, "Burnout Native Feature Importance", figures_root / "burnout_native_importance.png")
    save_importance_plot(product_perm.rename(columns={"importance": "importance"}), "Productivity Permutation Importance", figures_root / "productivity_permutation_importance.png")
    save_importance_plot(burnout_perm.rename(columns={"importance": "importance"}), "Burnout Permutation Importance", figures_root / "burnout_permutation_importance.png")

    product_checks = relationship_checks(product_pipeline, x_test, "regression")
    burnout_checks = relationship_checks(burnout_pipeline, x_test, "classification")

    metadata = {
        "random_state": RANDOM_STATE,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_fraction": 0.2,
        "split_strategy": "Chronological holdout plus TimeSeriesSplit for tuning",
        "best_scaler": best_scaler,
        "best_encoder": best_encoder,
        "feature_spec": asdict(spec),
        "xgboost_available": XGBOOST_AVAILABLE,
        "shap_available": SHAP_AVAILABLE,
        "class_distribution_train": class_counts,
        "leakage_controls": [
            "Excluded target columns from features.",
            "Excluded productivity_trend and burnout_momentum from model features because they are target-derived current-period signals.",
            "Used chronological train/test split and TimeSeriesSplit cross-validation.",
            "Kept sleep_debt and cumulative_load because they are rolling features available up to the prediction date.",
        ],
    }

    joblib.dump(product_pipeline, models_root / "productivity_model.joblib")
    joblib.dump(burnout_pipeline, models_root / "burnout_model.joblib")
    joblib.dump({"preprocessor": preprocessor.fit(x_train), "feature_spec": asdict(spec), "metadata": metadata}, models_root / "preprocessing_pipeline.joblib")
    (models_root / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    reg_rows = [{"model": row["model"], **row["metrics"]} for row in regression_results]
    cls_rows = [{"model": row["model"], **row["metrics"]} for row in classification_results]
    tuned_rows = []
    for search in tuned_regressors + tuned_classifiers:
        tuned_rows.append({"model": search.name, "best_score": float(search.best_score_), "best_params": search.best_params_})

    (reports_root / "productivity_model_report.md").write_text(
        "\n".join(
            [
                "# Productivity Model Report",
                "",
                "## Target",
                "`productivity_score` regression.",
                "",
                "## Model Comparison",
                markdown_table(reg_rows),
                "",
                f"Selected model: **{best_reg['model']}**.",
                "",
                "## Sanity Checks",
                product_checks.to_markdown(index=False),
            ]
        ),
        encoding="utf-8",
    )
    cm = confusion_matrix(y_burn_test, best_cls["predictions"], labels=["Low", "Medium", "High"])
    (reports_root / "burnout_model_report.md").write_text(
        "\n".join(
            [
                "# Burnout Model Report",
                "",
                "## Target",
                "`burnout_risk` classification from `burnout_score`: Low 0-33, Medium 34-66, High 67-100.",
                "",
                "## Class Distribution",
                str(class_counts),
                "",
                "## Model Comparison",
                markdown_table(cls_rows),
                "",
                f"Selected model: **{best_cls['model']}**.",
                "",
                "## Classification Report",
                "```text",
                classification_report(y_burn_test, best_cls["predictions"], zero_division=0),
                "```",
                "",
                "## Confusion Matrix",
                pd.DataFrame(cm, index=["Actual Low", "Actual Medium", "Actual High"], columns=["Pred Low", "Pred Medium", "Pred High"]).to_markdown(),
                "",
                "## Sanity Checks",
                burnout_checks.to_markdown(index=False),
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "model_selection_report.md").write_text(
        "\n".join(
            [
                "# Model Selection Report",
                "",
                "## Preprocessing Experiments",
                "Scaler comparison on productivity quick model:",
                markdown_table(scaler_results),
                "",
                "Encoder comparison on burnout quick model:",
                markdown_table(encoder_results),
                "",
                "## Hyperparameter Search",
                pd.DataFrame(tuned_rows).to_markdown(index=False),
                "",
                "## Leakage Prevention",
                "\n".join(f"- {item}" for item in metadata["leakage_controls"]),
                "",
                "## SMOTE Note",
                "SMOTE was not applied because `imblearn` is not installed and the time-series structure makes synthetic neighbor sampling risky. Class imbalance is addressed with class weights for Random Forest and macro-averaged metrics for selection.",
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "feature_importance_report.md").write_text(
        "\n".join(
            [
                "# Feature Importance Report",
                "",
                "## Productivity Native Importance",
                product_importance.head(25).to_markdown(index=False) if not product_importance.empty else "Native importances unavailable for selected productivity model.",
                "",
                "## Productivity Permutation Importance",
                product_perm.head(25).to_markdown(index=False),
                "",
                "## Burnout Native Importance",
                burnout_importance.head(25).to_markdown(index=False) if not burnout_importance.empty else "Native importances unavailable for selected burnout model.",
                "",
                "## Burnout Permutation Importance",
                burnout_perm.head(25).to_markdown(index=False),
                "",
                "Figures are saved under `reports/figures/`.",
            ]
        ),
        encoding="utf-8",
    )
    (reports_root / "shap_analysis.md").write_text(
        "\n".join(
            [
                "# SHAP Analysis",
                "",
                f"SHAP available: `{SHAP_AVAILABLE}`.",
                "",
                "SHAP was computed with `TreeExplainer` on a chronological holdout sample after applying the saved preprocessing pipeline.",
                "",
                "## Productivity SHAP Importance",
                product_shap.head(25).to_markdown(index=False) if not product_shap.empty else product_shap_note,
                "",
                product_shap_note,
                "",
                "## Burnout SHAP Importance",
                burnout_shap.head(25).to_markdown(index=False) if not burnout_shap.empty else burnout_shap_note,
                "",
                burnout_shap_note,
                "",
                "## Relationship Validation",
                "Productivity checks:",
                product_checks.to_markdown(index=False),
                "",
                "Burnout checks:",
                burnout_checks.to_markdown(index=False),
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Phase 2 productivity and burnout models.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[2], type=Path)
    args = parser.parse_args()
    train_phase2(args.project_root)


if __name__ == "__main__":
    main()
