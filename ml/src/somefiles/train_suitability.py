"""
train_suitability.py
--------------------
Dışarıda bulunma uygunluğu (outdoor_suitability_score) regresyon modeli.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline

from base_trainer import load_and_prep_data, temporal_split, build_preprocessor

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/suitability_model.pkl"
SCHEMA_PATH = "ml/trained_models/suitability_feature_schema.json"
METRICS_PATH = "ml/trained_models/suitability_metrics.json"

TARGET = "outdoor_suitability_score"
RANDOM_STATE = 42

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
    df = load_and_prep_data(DATA_PATH, TARGET)
    df_train, df_dev, df_test = temporal_split(df)

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(float)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_dev, y_dev = split_xy(df_dev)
    x_test, y_test = split_xy(df_test)

    cat_cols: list[str] = x_train.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    num_cols: list[str] = [c for c in x_train.columns if c not in cat_cols]

    print(f"  [Suitability] Sayısal özellikler ({len(num_cols)}): {num_cols}")
    print(f"  [Suitability] Kategorik özellikler ({len(cat_cols)}): {cat_cols}")

    preprocessor = build_preprocessor(num_cols, cat_cols)
    reg = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=800,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])

    reg.fit(x_train, y_train)

    dev_pred = reg.predict(x_dev)
    test_pred = reg.predict(x_test)

    dev_mae = mean_absolute_error(y_dev, dev_pred)
    test_mae = mean_absolute_error(y_test, test_pred)
    dev_r2 = r2_score(y_dev, dev_pred)
    test_r2 = r2_score(y_test, test_pred)

    print(f"  [Suitability] Dev  MAE={dev_mae:.4f}  R²={dev_r2:.4f}")
    print(f"  [Suitability] Test MAE={test_mae:.4f}  R²={test_r2:.4f}")

    x_td = pd.concat([x_train, x_dev], ignore_index=True)
    y_td = pd.concat([y_train, y_dev], ignore_index=True)
    reg.fit(x_td, y_td)

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    joblib.dump(reg, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "numeric_features": num_cols,
        "categorical_features": cat_cols,
        "split_strategy": "temporal_70_15_15",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    metrics = {
        "dev_mae": dev_mae,
        "test_mae": test_mae,
        "dev_r2": dev_r2,
        "test_r2": test_r2,
        "rows_train": len(df_train),
        "rows_dev": len(df_dev),
        "rows_test": len(df_test),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"  [Suitability] Model → {MODEL_PATH}")
    return metrics


if __name__ == "__main__":
    run()