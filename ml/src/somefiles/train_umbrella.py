"""
train_umbrella.py
-----------------
Şemsiye gerekliliği (umbrella_needed) ikili sınıflandırma modeli.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline

# Ortak fonksiyonları içeri aktar
from base_trainer import load_and_prep_data, temporal_split, build_preprocessor

DATA_PATH = "ml/data/raw/hourly_observations.csv"
MODEL_PATH = "ml/trained_models/umbrella_model.pkl"
SCHEMA_PATH = "ml/trained_models/umbrella_feature_schema.json"
METRICS_PATH = "ml/trained_models/umbrella_metrics.json"

TARGET = "umbrella_needed"
RANDOM_STATE = 42

# timestamp artık extract_time_features tarafından işlenecek, burada droplayabiliriz.
# hour, month, dayofweek özellikleri otomatik olarak X'e dahil olacaktır.
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

# NOT: Hiperparametreler (n_estimators=600 vb.) sabit bırakılmıştır.
# Zaman serisi temporal split kullanıldığı için standart CrossValidation (CV) yapılamaz.
# İleri seviyede TimeSeriesSplit ile arama yapılabilir ancak mevcut RF ayarları güçlü bir baseline sunar.


def _choose_best_threshold(y_true: pd.Series, probas: pd.Series) -> tuple[float, float]:
    """Dev seti üzerinde F1'i maksimize eden karar eşiğini bulur."""
    best_thr, best_f1 = 0.50, -1.0
    for step in range(5, 96):
        thr = step / 100
        preds = (probas >= thr).astype(int)
        score = f1_score(y_true, preds, zero_division=0)
        if score > best_f1:
            best_f1, best_thr = score, thr
    return best_thr, best_f1


def run() -> dict:
    """Modeli eğitir, kaydeder ve metrik sözlüğü döner."""
    # 1. Veri Yükleme ve Temizleme (Artık base_trainer'da)
    df = load_and_prep_data(DATA_PATH, TARGET)

    # 2. Temporal Split
    df_train, df_dev, df_test = temporal_split(df)

    def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        x = frame.drop(columns=[c for c in DROP_COLUMNS if c in frame.columns])
        y = frame[TARGET].astype(int)
        return x, y

    x_train, y_train = split_xy(df_train)
    x_dev, y_dev = split_xy(df_dev)
    x_test, y_test = split_xy(df_test)

    # 3. Feature Engineering (Otomatik algılama)
    cat_cols: list[str] = x_train.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()
    num_cols: list[str] = [c for c in x_train.columns if c not in cat_cols]

    print(f"  [Umbrella] Sayısal özellikler ({len(num_cols)}): {num_cols}")
    print(f"  [Umbrella] Kategorik özellikler ({len(cat_cols)}): {cat_cols}")

    # 4. Pipeline Kurulumu
    preprocessor = build_preprocessor(num_cols, cat_cols)
    clf = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestClassifier(
            n_estimators=600,
            max_depth=None,
            min_samples_leaf=1,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])

    clf.fit(x_train, y_train)

    # 5. Eşik (Threshold) Ayarı ve Test Değerlendirmesi
    dev_probas = pd.Series(clf.predict_proba(x_dev)[:, 1])
    best_thr, best_dev_f1 = _choose_best_threshold(y_dev, dev_probas)

    test_probas = clf.predict_proba(x_test)[:, 1]
    test_preds = (test_probas >= best_thr).astype(int)
    test_f1 = f1_score(y_test, test_preds, zero_division=0)

    print(f"  [Umbrella] Dev F1 (en iyi): {best_dev_f1:.4f}  (eşik={best_thr:.2f})")
    print(f"  [Umbrella] Test F1: {test_f1:.4f}")
    print(classification_report(y_test, test_preds, zero_division=0))

    # 6. Son Artifact: Train + Dev üzerinde yeniden eğitim
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
        "decision_threshold": best_thr,
        "split_strategy": "temporal_70_15_15",
    }
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    metrics = {
        "dev_f1_best": best_dev_f1,
        "test_f1": test_f1,
        "decision_threshold": best_thr,
        "rows_train": len(df_train),
        "rows_dev": len(df_dev),
        "rows_test": len(df_test),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"  [Umbrella] Model → {MODEL_PATH}")
    return metrics


if __name__ == "__main__":
    run()