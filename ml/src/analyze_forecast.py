"""
analyze_forecast.py
-------------------
Tahmin doğruluğunu lead time'a göre analiz eder, grafik ve metrik JSON kaydeder.
"""

import json
from pathlib import Path

import pandas as pd

from base_trainer import repo_path

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

DATA_PATH = repo_path("ml", "data", "raw", "forecast_vs_actual.csv")
METRICS_PATH = repo_path("ml", "trained_models", "forecast_metrics.json")
PLOT_PATH = repo_path("ml", "trained_models", "forecast_quality.png")


def run() -> dict:
    df = pd.read_csv(DATA_PATH)

    required = {"lead_time_hours", "umbrella_correct", "condition_correct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {DATA_PATH}: {missing}")

    quality = (
        df.groupby("lead_time_hours")[["umbrella_correct", "condition_correct"]]
        .mean()
        .reset_index()
    )

    print("  [Forecast] Lead Time Accuracy:")
    print(quality.to_string(index=False))

    Path(repo_path("ml", "trained_models")).mkdir(parents=True, exist_ok=True)
    if plt is None:
        print("  [Forecast] matplotlib is not installed, skipping plot.")
    else:
        # Plot
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(
            quality["lead_time_hours"],
            quality["umbrella_correct"],
            marker="o",
            color="steelblue",
            linewidth=2,
            label="Umbrella Accuracy",
        )
        ax.plot(
            quality["lead_time_hours"],
            quality["condition_correct"],
            marker="s",
            linestyle="--",
            color="tomato",
            linewidth=2,
            label="Condition Accuracy",
        )
        ax.set_title("Forecast Quality by Lead Time", fontsize=14)
        ax.set_xlabel("Lead Time (Hours)", fontsize=12)
        ax.set_ylabel("Accuracy", fontsize=12)
        ax.set_xticks(quality["lead_time_hours"])
        ax.set_ylim(0, 1.1)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.4)
        fig.tight_layout()

        fig.savefig(PLOT_PATH, dpi=150)
        plt.close(fig)
        print(f"  [Forecast] Plot -> {PLOT_PATH}")

    metrics = {
        "overall_umbrella_accuracy": float(df["umbrella_correct"].mean()),
        "overall_condition_accuracy": float(df["condition_correct"].mean()),
        "lead_time_breakdown": quality.to_dict(orient="records"),
        "total_rows": int(len(df)),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  [Forecast] Metrics -> {METRICS_PATH}")

    return metrics


if __name__ == "__main__":
    run()
