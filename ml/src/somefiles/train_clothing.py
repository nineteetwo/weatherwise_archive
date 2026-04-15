"""
train_clothing.py
-----------------
Giysi önerisi (clothing_recommendation) çok sınıflı sınıflandırma modeli.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline

from base_trainer import load_and_prep_data, temporal_split, build_preprocessor

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/clothing_model.pkl"
SCHEMA_PATH = "ml/trained_models/clothing_feature_schema.json"
METRICS_PATH = "ml/trained_models/clothing_metrics.json"

TARGET = "clothing_recommendation"
RANDOM_STATE = 42

DROP_COLUMNS = [
    "obs_id",
    "timestamp",
    "date",
    "recommendation_headline",
    "recommendation_text",
    "umbrella_needed",
    "outdoor_suitability_score",
    TARGET,
]


def run() -> dict:
    df = load_and_prep_data(DATA_PATH, TARGET)
    df_train, df_dev, df_test = temporal_split(df)

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(str)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_dev, y_dev = split_xy(df_dev)
    x_test, y_test = split_xy(df_test)

    cat_cols: list[str] = x_train.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    num_cols: list[str] = [c for c in x_train.columns if c not in cat_cols]

    print(f"  [Clothing] Sayısal özellikler ({len(num_cols)}): {num_cols}")
    print(f"  [Clothing] Kategorik özellikler ({len(cat_cols)}): {cat_cols}")

    preprocessor = build_preprocessor(num_cols, cat_cols)
    clf = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestClassifier(
            n_estimators=700,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])

    clf.fit(x_train, y_train)

    dev_pred = clf.predict(x_dev)
    test_pred = clf.predict(x_test)

    dev_acc = accuracy_score(y_dev, dev_pred)
    test_acc = accuracy_score(y_test, test_pred)
    dev_macro_f1 = f1_score(y_dev, dev_pred, average="macro", zero_division=0)
    test_macro_f1 = f1_score(y_test, test_pred, average="macro", zero_division=0)

    print(f"  [Clothing] Dev  Accuracy={dev_acc:.4f}  Macro-F1={dev_macro_f1:.4f}")
    print(f"  [Clothing] Test Accuracy={test_acc:.4f}  Macro-F1={test_macro_f1:.4f}")
    print(classification_report(y_test, test_pred, zero_division=0))

    x_td = pd.concat([x_train, x_dev], ignore_index=True)
    y_td = pd.concat([y_train, y_dev], ignore_index=True)
    clf.fit(x_td, y_td)

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "numeric_features": num_cols,
        "categorical_features": cat_cols,
        "split_strategy": "temporal_70_15_15",
        "classes": sorted(y_train.unique().tolist()),
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    metrics = {
        "dev_accuracy": dev_acc,
        "test_accuracy": test_acc,
        "dev_macro_f1": dev_macro_f1,
        "test_macro_f1": test_macro_f1,
        "rows_train": len(df_train),
        "rows_dev": len(df_dev),
        "rows_test": len(df_test),
        "n_classes": int(y_train.nunique()),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"  [Clothing] Model → {MODEL_PATH}")
    return metrics


if __name__ == "__main__":
    run()