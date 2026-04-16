import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from base_trainer import build_preprocessor, load_training_data, repo_path

DATA_PATH = repo_path("ml", "data", "raw", "hourly_observations.csv")
MODEL_PATH = repo_path("ml", "trained_models", "umbrella_model.pkl")
SCHEMA_PATH = repo_path("ml", "trained_models", "umbrella_feature_schema.json")
METRICS_PATH = repo_path("ml", "trained_models", "umbrella_metrics.json")

TARGET = "umbrella_needed"
RANDOM_STATE = 42
N_SPLITS = 5

# These columns are either IDs/text or post-processed targets that should not be features.
DROP_COLUMNS = [
    "obs_id",
    "timestamp",
    "date",
    "recommendation_headline",
    "recommendation_text",
    "clothing_recommendation",
    "outdoor_suitability_score",
    TARGET,
]


def choose_best_threshold(y_true: pd.Series, probas: pd.Series) -> tuple[float, float]:
    best_threshold = 0.50
    best_f1 = -1.0
    for step in range(5, 96):  # 0.05 -> 0.95
        threshold = step / 100
        preds = (probas >= threshold).astype(int)
        score = f1_score(y_true, preds)
        if score > best_f1:
            best_f1 = score
            best_threshold = threshold
    return best_threshold, best_f1


def run() -> dict:
    df = load_training_data(DATA_PATH, TARGET, target_kind="classification")
    test_start = int(len(df) * 0.85)
    if test_start <= 0 or test_start >= len(df):
        raise ValueError("Dataset too small for 85/15 temporal holdout split.")
    df_train, df_test = df.iloc[:test_start], df.iloc[test_start:]

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(int)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_test, y_test = split_xy(df_test)

    cat_cols = x_train.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = [c for c in x_train.columns if c not in cat_cols]

    preprocess = build_preprocessor(num_cols, cat_cols)

    def make_clf() -> Pipeline:
        return Pipeline(
            [
                ("preprocess", preprocess),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=600,
                        max_depth=None,
                        min_samples_leaf=1,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                        class_weight="balanced_subsample",
                    ),
                ),
            ]
        )

    min_class_count = int(y_train.value_counts().min())
    effective_splits = max(2, min(N_SPLITS, min_class_count))
    if effective_splits < N_SPLITS:
        print(
            f"Reducing folds from {N_SPLITS} to {effective_splits} "
            f"due to small class size ({min_class_count})."
        )
    skf = StratifiedKFold(n_splits=effective_splits, shuffle=True, random_state=RANDOM_STATE)
    cv_f1_scores: list[float] = []
    cv_thresholds: list[float] = []
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(x_train, y_train), start=1):
        x_fold_train = x_train.iloc[train_idx]
        y_fold_train = y_train.iloc[train_idx]
        x_fold_val = x_train.iloc[val_idx]
        y_fold_val = y_train.iloc[val_idx]

        fold_clf = make_clf()
        fold_clf.fit(x_fold_train, y_fold_train)
        val_probas = fold_clf.predict_proba(x_fold_val)[:, 1]
        fold_threshold, fold_f1 = choose_best_threshold(y_fold_val, pd.Series(val_probas))
        cv_f1_scores.append(fold_f1)
        cv_thresholds.append(fold_threshold)
        print(
            f"Fold {fold_idx}/{effective_splits} F1: "
            f"{fold_f1:.4f} @ threshold={fold_threshold:.2f}"
        )

    best_dev_f1 = float(pd.Series(cv_f1_scores).mean())
    best_dev_f1_std = float(pd.Series(cv_f1_scores).std(ddof=0))
    best_threshold = float(pd.Series(cv_thresholds).mean())

    clf = make_clf()
    clf.fit(x_train, y_train)

    test_probas = clf.predict_proba(x_test)[:, 1]
    test_preds = (test_probas >= best_threshold).astype(int)
    test_f1 = f1_score(y_test, test_preds)

    print(f"Umbrella CV F1 (mean): {best_dev_f1:.4f} +/- {best_dev_f1_std:.4f}")
    print(f"Umbrella CV threshold (mean): {best_threshold:.2f}")
    print(f"Umbrella Test F1: {test_f1:.4f}")
    print("Test classification report:")
    print(classification_report(y_test, test_preds))

    Path(repo_path("ml", "trained_models")).mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "decision_threshold": best_threshold,
        "split_strategy": f"temporal_holdout_85_15_plus_stratified_kfold_{effective_splits}",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_f1_best": best_dev_f1,
        "cv_f1_std": best_dev_f1_std,
        "test_f1": test_f1,
        "decision_threshold": best_threshold,
        "cv_thresholds": cv_thresholds,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_train) / effective_splits),
        "rows_test": int(len(df_test)),
        "target_positive_rate_train": float(y_train.mean()),
        "target_positive_rate_test": float(y_test.mean()),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved schema -> {SCHEMA_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")

    return metrics


def main() -> None:
    run()


if __name__ == "__main__":
    main()