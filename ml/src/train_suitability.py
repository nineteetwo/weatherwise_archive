import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline

from base_trainer import build_preprocessor, load_training_data, repo_path

DATA_PATH = repo_path("ml", "data", "raw", "hourly_observations.csv")
MODEL_PATH = repo_path("ml", "trained_models", "suitability_model.pkl")
SCHEMA_PATH = repo_path("ml", "trained_models", "suitability_feature_schema.json")
METRICS_PATH = repo_path("ml", "trained_models", "suitability_metrics.json")

TARGET = "outdoor_suitability_score"
RANDOM_STATE = 42
N_SPLITS = 5

# Remove IDs/text and other targets to prevent leakage.
DROP_COLUMNS = [
    "obs_id",
    "timestamp",
    "date",
    "recommendation_headline",
    "recommendation_text",
    "umbrella_needed",
    "clothing_recommendation",
    TARGET,
]


def run() -> dict:
    df = load_training_data(DATA_PATH, TARGET, target_kind="regression")
    test_start = int(len(df) * 0.85)
    if test_start <= 0 or test_start >= len(df):
        raise ValueError("Dataset too small for 85/15 temporal holdout split.")
    df_train, df_test = df.iloc[:test_start], df.iloc[test_start:]

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(float)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_test, y_test = split_xy(df_test)

    cat_cols = x_train.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = [c for c in x_train.columns if c not in cat_cols]

    preprocess = build_preprocessor(num_cols, cat_cols)

    def make_reg() -> Pipeline:
        return Pipeline(
            [
                ("preprocess", preprocess),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=800,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

    kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    cv_mae_scores: list[float] = []
    cv_r2_scores: list[float] = []
    for fold_idx, (train_idx, val_idx) in enumerate(kf.split(x_train), start=1):
        x_fold_train = x_train.iloc[train_idx]
        y_fold_train = y_train.iloc[train_idx]
        x_fold_val = x_train.iloc[val_idx]
        y_fold_val = y_train.iloc[val_idx]

        fold_reg = make_reg()
        fold_reg.fit(x_fold_train, y_fold_train)
        val_pred = fold_reg.predict(x_fold_val)
        fold_mae = mean_absolute_error(y_fold_val, val_pred)
        fold_r2 = r2_score(y_fold_val, val_pred)
        cv_mae_scores.append(fold_mae)
        cv_r2_scores.append(fold_r2)
        print(f"Fold {fold_idx}/{N_SPLITS} MAE: {fold_mae:.4f}, R2: {fold_r2:.4f}")

    dev_mae = float(pd.Series(cv_mae_scores).mean())
    dev_mae_std = float(pd.Series(cv_mae_scores).std(ddof=0))
    dev_r2 = float(pd.Series(cv_r2_scores).mean())
    dev_r2_std = float(pd.Series(cv_r2_scores).std(ddof=0))

    reg = make_reg()
    reg.fit(x_train, y_train)
    test_pred = reg.predict(x_test)
    test_mae = mean_absolute_error(y_test, test_pred)
    test_r2 = r2_score(y_test, test_pred)

    print(f"Suitability CV MAE (mean): {dev_mae:.4f} +/- {dev_mae_std:.4f}")
    print(f"Suitability Test MAE: {test_mae:.4f}")
    print(f"Suitability CV R2 (mean): {dev_r2:.4f} +/- {dev_r2_std:.4f}")
    print(f"Suitability Test R2: {test_r2:.4f}")

    Path(repo_path("ml", "trained_models")).mkdir(parents=True, exist_ok=True)
    joblib.dump(reg, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "split_strategy": "temporal_holdout_85_15_plus_kfold_5",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_mae": dev_mae,
        "cv_mae_std": dev_mae_std,
        "test_mae": test_mae,
        "dev_r2": dev_r2,
        "cv_r2_std": dev_r2_std,
        "test_r2": test_r2,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_train) / N_SPLITS),
        "rows_test": int(len(df_test)),
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
