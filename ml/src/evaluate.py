import json
from pathlib import Path

import pandas as pd

from base_trainer import repo_path

DATA_PATH = repo_path("ml", "data", "raw", "forecast_vs_actual.csv")
JSON_OUT = repo_path("ml", "trained_models", "forecast_quality_metrics.json")
CSV_OUT = repo_path("ml", "trained_models", "forecast_quality_by_lead_time.csv")


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "lead_time_hours",
        "umbrella_correct",
        "condition_correct",
        "clothing_correct",
    ]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in forecast file: {missing}")

    for metric_col in ["umbrella_correct", "condition_correct", "clothing_correct"]:
        df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce")

    grouped = (
        df.dropna(subset=["lead_time_hours", "umbrella_correct", "condition_correct"])
        .groupby("lead_time_hours", as_index=False)
        .agg(
            sample_count=("lead_time_hours", "size"),
            umbrella_correct_rate=("umbrella_correct", "mean"),
            condition_correct_rate=("condition_correct", "mean"),
            clothing_correct_rate=("clothing_correct", "mean"),
        )
        .sort_values("lead_time_hours")
        .reset_index(drop=True)
    )

    # Keep values easy to read in reports.
    rounded = grouped.copy()
    for col in [
        "umbrella_correct_rate",
        "condition_correct_rate",
        "clothing_correct_rate",
    ]:
        rounded[col] = rounded[col].round(6)

    Path(repo_path("ml", "trained_models")).mkdir(parents=True, exist_ok=True)
    rounded.to_csv(CSV_OUT, index=False)

    summary = {
        "source_file": DATA_PATH,
        "rows_total": int(len(df)),
        "lead_time_metrics": rounded.to_dict(orient="records"),
    }
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Forecast quality by lead time:")
    print(rounded.to_string(index=False))
    print(f"Saved CSV -> {CSV_OUT}")
    print(f"Saved JSON -> {JSON_OUT}")


if __name__ == "__main__":
    main()
