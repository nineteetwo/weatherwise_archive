"""
base_trainer.py
---------------
Tüm eğitim scriptleri tarafından paylaşılan ortak fonksiyonlar.
DRY (Don't Repeat Yourself) prensibi gereği ayrıştırılmıştır.
"""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def extract_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Zaman damgasından saat, ay ve gün özelliklerini çıkarır.
    Hava durumu verilerinde 'saat' ve 'mevsim' model için en önemli sinyallerden biridir.
    """
    df["hour"] = df["timestamp"].dt.hour
    df["month"] = df["timestamp"].dt.month
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    return df


def load_and_prep_data(data_path: str, target: str) -> pd.DataFrame:
    """Veriyi yükler, zaman damgasını parse eder, eksikleri siler ve sıralar."""
    df = pd.read_csv(data_path)
    if target not in df.columns:
        raise ValueError(f"Hedef sütun '{target}' bulunamadı: {data_path}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    # Hedef değişkenin tipini kontrol et (regresyon için float, sınıflandırma için int/str olacak)
    if df[target].dtype == "object":
        df = df.dropna(subset=["timestamp", target])
    else:
        df[target] = pd.to_numeric(df[target], errors="coerce")
        df = df.dropna(subset=["timestamp", target])

    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Zaman özelliklerini çıkar (timestamp droplamadan hemen önce)
    df = extract_time_features(df)
    
    return df


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Zaman damgasına göre 70 / 15 / 15 bölme. Data leakage'ı önler."""
    n = len(df)
    train_end = int(n * 0.70)
    dev_end = int(n * 0.85)
    if train_end == 0 or dev_end <= train_end or dev_end >= n:
        raise ValueError("Veri seti 70/15/15 temporal bölme için çok küçük.")
    return df.iloc[:train_end], df.iloc[train_end:dev_end], df.iloc[dev_end:]


def build_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    """Sayısal + kategorik sütunlar için ayrı pipeline döner."""
    num_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        # NOT: sparse_output=False KULLANILMAK ZORUNDADIR.
        # Sebebi: Scikit-learn'in RandomForest algoritması sparse (seyrek) matrisleri 
        # girdi olarak kabul etmez. Hafıza tüketimi yüksek olsa da RF için bu zorunludur.
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    
    return ColumnTransformer(
        transformers=[
            ("num", num_pipe, num_cols),
            ("cat", cat_pipe, cat_cols),
        ],
        remainder="drop",
    )