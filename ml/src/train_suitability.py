import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/suitability_model.pkl"
SCHEMA_PATH = "ml/trained_models/suitability_feature_schema.json"
METRICS_PATH = "ml/trained_models/suitability_metrics.json"

TARGET = "outdoor_suitability_score"
RANDOM_STATE = 42

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


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found in {DATA_PATH}")

    # Temporal split is closer to real usage than random splitting.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", TARGET]).sort_values("timestamp").reset_index(drop=True)
    df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
    df = df.dropna(subset=[TARGET]).reset_index(drop=True)

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
        y = frame[TARGET].astype(float)
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

    reg = Pipeline(
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

    reg.fit(x_train, y_train)

    dev_pred = reg.predict(x_dev)
    test_pred = reg.predict(x_test)

    dev_mae = mean_absolute_error(y_dev, dev_pred)
    test_mae = mean_absolute_error(y_test, test_pred)
    dev_r2 = r2_score(y_dev, dev_pred)
    test_r2 = r2_score(y_test, test_pred)

    print(f"Suitability Dev MAE: {dev_mae:.4f}")
    print(f"Suitability Test MAE: {test_mae:.4f}")
    print(f"Suitability Dev R2: {dev_r2:.4f}")
    print(f"Suitability Test R2: {test_r2:.4f}")

    # Final artifact on train+dev for serving.
    x_train_dev = pd.concat([x_train, x_dev], ignore_index=True)
    y_train_dev = pd.concat([y_train, y_dev], ignore_index=True)
    reg.fit(x_train_dev, y_train_dev)

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    joblib.dump(reg, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "split_strategy": "temporal_70_15_15",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_mae": dev_mae,
        "test_mae": test_mae,
        "dev_r2": dev_r2,
        "test_r2": test_r2,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_dev)),
        "rows_test": int(len(df_test)),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved schema -> {SCHEMA_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
