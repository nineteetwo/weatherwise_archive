from __future__ import annotations

from pathlib import Path

import pandas as pd


def repo_path(*parts: str) -> str:
    """
    Absolute path under the repository root (weatherwise/).

    Scripts live in ml/src/, so parents[2] of this file is the repo root.
    Works regardless of the process current working directory.
    """
    root = Path(__file__).resolve().parents[2]
    return str(root.joinpath(*parts))
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def load_training_data(data_path: str, target: str, target_kind: str) -> pd.DataFrame:
    """
    Load CSV, validate target, parse timestamps, and sort for temporal training.

    target_kind:
      - "classification": keep target as-is (string/int) and drop null targets.
      - "regression": coerce target to numeric and drop null targets.
    """
    df = pd.read_csv(data_path)
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in {data_path}")
    if "timestamp" not in df.columns:
        raise ValueError(f"'timestamp' column not found in {data_path}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if target_kind == "regression":
        df[target] = pd.to_numeric(df[target], errors="coerce")
    elif target_kind != "classification":
        raise ValueError("target_kind must be either 'classification' or 'regression'")

    df = (
        df.dropna(subset=["timestamp", target])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    return df


def temporal_split(
    df: pd.DataFrame, train_ratio: float = 0.70, dev_ratio: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split sorted dataframe into train/dev/test without temporal leakage."""
    n = len(df)
    train_end = int(n * train_ratio)
    dev_end = int(n * (train_ratio + dev_ratio))
    if train_end == 0 or dev_end <= train_end or dev_end >= n:
        raise ValueError("Dataset too small for temporal split.")
    return df.iloc[:train_end], df.iloc[train_end:dev_end], df.iloc[dev_end:]


def build_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    """Create a shared preprocessing pipeline for numeric and categorical features."""
    return ColumnTransformer(
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
