import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from base_trainer import build_preprocessor, load_training_data, repo_path

# Optional UX layer experiments (not part of core hackathon training path):
# from clothing_ux_policy import clothing_ux_from_proba, clothing_ux_to_payload

DATA_PATH = repo_path("ml", "data", "raw", "hourly_observations.csv")
MODEL_PATH = repo_path("ml", "trained_models", "clothing_model.pkl")
SCHEMA_PATH = repo_path("ml", "trained_models", "clothing_feature_schema.json")
METRICS_PATH = repo_path("ml", "trained_models", "clothing_metrics.json")

TARGET = "clothing_recommendation"
RANDOM_STATE = 42
N_SPLITS = 5

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


def run() -> dict:
    df = load_training_data(DATA_PATH, TARGET, target_kind="classification")
    test_start = int(len(df) * 0.85)
    if test_start <= 0 or test_start >= len(df):
        raise ValueError("Dataset too small for 85/15 temporal holdout split.")
    df_train, df_test = df.iloc[:test_start], df.iloc[test_start:]

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(str)
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
                        n_estimators=700,
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
    cv_accuracy_scores: list[float] = []
    cv_macro_f1_scores: list[float] = []
    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(x_train, y_train), start=1):
        x_fold_train = x_train.iloc[train_idx]
        y_fold_train = y_train.iloc[train_idx]
        x_fold_val = x_train.iloc[val_idx]
        y_fold_val = y_train.iloc[val_idx]

        fold_clf = make_clf()
        fold_clf.fit(x_fold_train, y_fold_train)
        val_pred = fold_clf.predict(x_fold_val)
        fold_accuracy = accuracy_score(y_fold_val, val_pred)
        fold_macro_f1 = f1_score(y_fold_val, val_pred, average="macro", zero_division=0)
        cv_accuracy_scores.append(fold_accuracy)
        cv_macro_f1_scores.append(fold_macro_f1)
        print(
            f"Fold {fold_idx}/{effective_splits} Accuracy: {fold_accuracy:.4f}, "
            f"Macro-F1: {fold_macro_f1:.4f}"
        )

    dev_accuracy = float(pd.Series(cv_accuracy_scores).mean())
    dev_accuracy_std = float(pd.Series(cv_accuracy_scores).std(ddof=0))
    dev_macro_f1 = float(pd.Series(cv_macro_f1_scores).mean())
    dev_macro_f1_std = float(pd.Series(cv_macro_f1_scores).std(ddof=0))

    clf = make_clf()
    clf.fit(x_train, y_train)
    test_pred = clf.predict(x_test)
    test_accuracy = accuracy_score(y_test, test_pred)
    test_macro_f1 = f1_score(y_test, test_pred, average="macro", zero_division=0)

    print(f"Clothing CV Accuracy (mean): {dev_accuracy:.4f} +/- {dev_accuracy_std:.4f}")
    print(f"Clothing Test Accuracy: {test_accuracy:.4f}")
    print(f"Clothing CV Macro-F1 (mean): {dev_macro_f1:.4f} +/- {dev_macro_f1_std:.4f}")
    print(f"Clothing Test Macro-F1: {test_macro_f1:.4f}")
    print("Test classification report:")
    print(classification_report(y_test, test_pred, zero_division=0))

    # ------------------------------------------------------------------
    # UX presentation demo (optional; commented out for hackathon scope)
    #
    # This block does not change training; it only prints example payloads.
    # Uncomment later to experiment with user-facing "top-2 + layering note"
    # behavior based on predict_proba + simple weather guardrails.
    # ------------------------------------------------------------------
    # import numpy as np
    #
    # proba = clf.predict_proba(x_test)
    # classes = list(clf.classes_)
    # top2 = np.partition(proba, -2, axis=1)[:, -2:]
    # top_p = top2[:, 1]
    # margin = top_p - top2[:, 0]
    #
    # temp_c = pd.to_numeric(df_test.get("temperature_c"), errors="coerce").to_numpy()
    # precip_mm = pd.to_numeric(df_test.get("precipitation_mm"), errors="coerce").to_numpy()
    #
    # def weather_dict(i: int) -> dict:
    #     row = df_test.iloc[i]
    #     return {
    #         "temperature_c": row.get("temperature_c"),
    #         "humidity_pct": row.get("humidity_pct"),
    #         "precipitation_mm": row.get("precipitation_mm"),
    #         "precipitation_type": row.get("precipitation_type"),
    #         "weather_condition": row.get("weather_condition"),
    #         "wind_speed_kmh": row.get("wind_speed_kmh"),
    #         "wind_gust_kmh": row.get("wind_gust_kmh"),
    #     }
    #
    # i_high = int(np.argmax(margin))
    # i_low = int(np.argmin(margin))
    #
    # wet_mask = precip_mm > 0.05
    # cold_mask = temp_c <= 12.0
    # cand = np.flatnonzero(wet_mask & cold_mask & np.isfinite(temp_c))
    # i_cw = int(cand[0]) if cand.size else i_low
    #
    # print("\nClothing UX policy examples (test split):")
    # for title, idx in (
    #     ("highest confidence margin", i_high),
    #     ("lowest confidence margin", i_low),
    #     (
    #         "cold + wet example"
    #         if cand.size
    #         else "cold+wet not found; showing lowest margin",
    #         i_cw,
    #     ),
    # ):
    #     ux = clothing_ux_from_proba(
    #         classes=classes,
    #         proba_row=proba[idx],
    #         weather=weather_dict(idx),
    #     )
    #     payload = clothing_ux_to_payload(ux)
    #     ts = df_test.iloc[idx].get("timestamp")
    #     print(f"- {title}: timestamp={ts}")
    #     print(f"  weather={weather_dict(idx)}")
    #     print(
    #         f"  model_top={test_pred[idx]!r} p_top={top_p[idx]:.3f} margin={margin[idx]:.3f}"
    #     )
    #     print(f"  ux_payload={payload}")

    Path(repo_path("ml", "trained_models")).mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    schema = {
        "target": TARGET,
        "features": x_train.columns.tolist(),
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "split_strategy": f"temporal_holdout_85_15_plus_stratified_kfold_{effective_splits}",
        "classes": sorted(y_train.unique().tolist()),
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    metrics = {
        "dev_accuracy": dev_accuracy,
        "cv_accuracy_std": dev_accuracy_std,
        "test_accuracy": test_accuracy,
        "dev_macro_f1": dev_macro_f1,
        "cv_macro_f1_std": dev_macro_f1_std,
        "test_macro_f1": test_macro_f1,
        "rows_train": int(len(df_train)),
        "rows_dev": int(len(df_train) / effective_splits),
        "rows_test": int(len(df_test)),
        "n_classes": int(y_train.nunique()),
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
