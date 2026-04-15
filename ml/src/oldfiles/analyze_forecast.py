import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = "ml/data/raw/forecast_vs_actual.csv"
METRICS_PATH = "ml/trained_models/forecast_metrics.json"
PLOT_PATH = "ml/trained_models/forecast_quality.png"


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    required_cols = {"lead_time_hours", "umbrella_correct", "condition_correct"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {DATA_PATH}: {missing}")

    # Lead time bazında ortalama doğruluk
    quality = (
        df.groupby("lead_time_hours")[["umbrella_correct", "condition_correct"]]
        .mean()
        .reset_index()
    )

    print("Lead Time (Saat) Bazında Tahmin Doğruluğu:")
    print(quality.to_string(index=False))

    # --- Grafik ---
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        quality["lead_time_hours"],
        quality["umbrella_correct"],
        marker="o",
        linestyle="-",
        color="steelblue",
        linewidth=2,
        label="Şemsiye Tahmin Doğruluğu",
    )
    ax.plot(
        quality["lead_time_hours"],
        quality["condition_correct"],
        marker="s",
        linestyle="--",
        color="tomato",
        linewidth=2,
        label="Hava Durumu (Condition) Doğruluğu",
    )

    ax.set_title("Lead Time'a Göre Tahmin Kalitesi", fontsize=14)
    ax.set_xlabel("Tahmin Süresi (Lead Time - Saat)", fontsize=12)
    ax.set_ylabel("Doğruluk Oranı", fontsize=12)
    ax.set_xticks(quality["lead_time_hours"])
    ax.set_ylim(0, 1.1)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.4)
    fig.tight_layout()

    Path("ml/trained_models").mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_PATH, dpi=150)
    plt.show()
    print(f"Grafik kaydedildi -> {PLOT_PATH}")

    # --- Metrikler ---
    metrics = {
        "overall_umbrella_accuracy": float(df["umbrella_correct"].mean()),
        "overall_condition_accuracy": float(df["condition_correct"].mean()),
        "lead_time_breakdown": quality.to_dict(orient="records"),
        "total_rows": int(len(df)),
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"Metrikler kaydedildi -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
