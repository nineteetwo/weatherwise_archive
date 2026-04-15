import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/umbrella_model.pkl"
SCHEMA_PATH = "ml/trained_models/umbrella_feature_schema.json"
METRICS_PATH = "ml/trained_models/umbrella_metrics.json"

TARGET = "umbrella_needed"
RANDOM_STATE = 42

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


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found in {DATA_PATH}")

    # Temporal split is more realistic than random split for production-like weather inference.
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
        y = frame[TARGET].astype(int)
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

    clf.fit(x_train, y_train)

    dev_probas = clf.predict_proba(x_dev)[:, 1]
    best_threshold, best_dev_f1 = choose_best_threshold(y_dev, pd.Series(dev_probas))

    test_probas = clf.predict_proba(x_test)[:, 1]
    test_preds = (test_probas >= best_threshold).astype(int)
    test_f1 = f1_score(y_test, test_preds)

    print(f"Umbrella Dev F1 (best): {best_dev_f1:.4f} @ threshold={best_threshold:.2f}")
    print(f"Umbrella Test F1: {test_f1:.4f}")
    print("Test classification report:")
    print(classification_report(y_test, test_preds))

    # Refit on train+dev with tuned threshold for final artifact.
    x_train_dev = pd.concat([x_train, x_dev], ignore_index=True)
    y_train_dev = pd.concat([y_train, y_dev], ignore_index=True)
    clf.fit(x_train_dev, y_train_dev)
    joblib.dump(clf, MODEL_PATH)

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "decision_threshold": best_threshold,
        "split_strategy": "temporal_70_15_15",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_f1_best": best_dev_f1,
        "test_f1": test_f1,
        "decision_threshold": best_threshold,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_dev)),
        "rows_test": int(len(df_test)),
        "target_positive_rate_train": float(y_train.mean()),
        "target_positive_rate_dev": float(y_dev.mean()),
        "target_positive_rate_test": float(y_test.mean()),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved schema -> {SCHEMA_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")


if __name__ == "__main__":
    main()