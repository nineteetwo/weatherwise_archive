import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/clothing_model.pkl"
SCHEMA_PATH = "ml/trained_models/clothing_feature_schema.json"
METRICS_PATH = "ml/trained_models/clothing_metrics.json"

TARGET = "clothing_recommendation"
RANDOM_STATE = 42

# Remove IDs/text and other target-like columns to avoid leakage.
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


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found in {DATA_PATH}")

    # Temporal split for realistic evaluation on future timestamps.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", TARGET]).sort_values("timestamp").reset_index(drop=True)

    n = len(df)
    train_end = int(n * 0.70)
    dev_end = int(n * 0.85)
    if train_end == 0 or dev_end <= train_end or dev_end >= n:
        raise ValueError("Dataset too small for 70/15/15 temporal split.")

    df_train = df.iloc[:train_end]
    df_dev = df.iloc[train_end:dev_end]
    df_test = df.iloc[dev_end:]

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(str)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_dev, y_dev = split_xy(df_dev)
    x_test, y_test = split_xy(df_test)

    cat_cols = x_train.select_dtypes(include=["object", "string"]).columns.tolist()
    num_cols = [c for c in x_train.columns if c not in cat_cols]

    preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), num_cols),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                cat_cols,
            ),
        ]
    )

    clf = Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=700,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                    class_weight="balanced_subsample",
                ),
            ),
        ]
    )

    clf.fit(x_train, y_train)

    dev_pred = clf.predict(x_dev)
    test_pred = clf.predict(x_test)

    dev_accuracy = accuracy_score(y_dev, dev_pred)
    test_accuracy = accuracy_score(y_test, test_pred)
    dev_macro_f1 = f1_score(y_dev, dev_pred, average="macro")
    test_macro_f1 = f1_score(y_test, test_pred, average="macro")

    print(f"Clothing Dev Accuracy: {dev_accuracy:.4f}")
    print(f"Clothing Test Accuracy: {test_accuracy:.4f}")
    print(f"Clothing Dev Macro-F1: {dev_macro_f1:.4f}")
    print(f"Clothing Test Macro-F1: {test_macro_f1:.4f}")
    print("Test classification report:")
    print(classification_report(y_test, test_pred, zero_division=0))

    # Final artifact trained on train+dev.
    x_train_dev = pd.concat([x_train, x_dev], ignore_index=True)
    y_train_dev = pd.concat([y_train, y_dev], ignore_index=True)
    clf.fit(x_train_dev, y_train_dev)

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "split_strategy": "temporal_70_15_15",
        "classes": sorted(y_train.unique().tolist()),
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_accuracy": dev_accuracy,
        "test_accuracy": test_accuracy,
        "dev_macro_f1": dev_macro_f1,
        "test_macro_f1": test_macro_f1,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_dev)),
        "rows_test": int(len(df_test)),
        "n_classes": int(y_train.nunique()),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved schema -> {SCHEMA_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
