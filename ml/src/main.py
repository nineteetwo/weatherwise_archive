"""
main.py
-------
Tüm eğitim ve analiz adımlarını sırayla çalıştırır, ardından
konsola özet bir metrik tablosu basar.

Kullanım:
    python main.py
    python main.py --force-retrain
"""

import json
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Modüller buradan import edilir — her biri bir run() fonksiyonu döndürür.
# ---------------------------------------------------------------------------
import train_umbrella
import train_suitability
import train_clothing
import analyze_forecast

from base_trainer import repo_path


def _max_mtime(paths: list[str]) -> float | None:
    mtimes: list[float] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            return None
        mtimes.append(path.stat().st_mtime)
    return max(mtimes) if mtimes else None


def _artifacts_fresher_than(artifact_paths: list[str], dependency_paths: list[str]) -> bool:
    """
    True if every artifact exists and is >= newest dependency mtime.

    This avoids skipping training when CSVs or training code changed after the
    last artifact write.
    """
    if not artifact_paths or not dependency_paths:
        return False
    deps_max = _max_mtime(dependency_paths)
    if deps_max is None:
        return False
    for p in artifact_paths:
        ap = Path(p)
        if not ap.is_file():
            return False
        if ap.stat().st_mtime + 1e-6 < deps_max:
            return False
    return True


# ---------------------------------------------------------------------------
# Yardımcı: adım çalıştır, hata varsa yakala ama devam et
# ---------------------------------------------------------------------------
def _run_step(
    name: str,
    module,
    *,
    artifact_paths: list[str] | None = None,
    metrics_path: str | None = None,
    dependency_paths: list[str] | None = None,
    force_retrain: bool = False,
) -> dict | None:
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"  -> {name}")
    print(sep)
    try:
        if (
            not force_retrain
            and artifact_paths
            and metrics_path
            and dependency_paths
            and _artifacts_fresher_than(artifact_paths, dependency_paths)
        ):
            with open(metrics_path, encoding="utf-8") as f:
                cached = json.load(f)
            print(
                "  SKIP: artifacts are up to date vs inputs/code, using metrics from:\n"
                f"       {metrics_path}\n"
            )
            return cached

        result = module.run()
        print(f"  OK: {name} completed.\n")
        return result
    except Exception:
        print(f"\n  ERROR: {name} failed:")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Özet tablosu yazdıran yardımcı
# ---------------------------------------------------------------------------
def _print_summary(results: dict[str, dict | None]) -> None:
    banner = "=" * 60
    print(f"\n{banner}")
    print("  METRICS SUMMARY")
    print(banner)

    # --- Umbrella ---
    m = results.get("Umbrella Model")
    if m:
        print("\n  Umbrella (umbrella_needed) - Binary Classification")
        print(f"      Dev  F1       : {m['dev_f1_best']:.4f}")
        print(f"      Test F1       : {m['test_f1']:.4f}")
        print(f"      Threshold     : {m['decision_threshold']:.2f}")
        print(f"      Train / Dev / Test rows: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Suitability ---
    m = results.get("Suitability Model")
    if m:
        print("\n  Outdoor Suitability (outdoor_suitability_score) - Regression")
        print(f"      Dev  MAE      : {m['dev_mae']:.4f}")
        print(f"      Test MAE      : {m['test_mae']:.4f}")
        print(f"      Dev  R2       : {m['dev_r2']:.4f}")
        print(f"      Test R2       : {m['test_r2']:.4f}")
        print(f"      Train / Dev / Test rows: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Clothing ---
    m = results.get("Clothing Model")
    if m:
        print("\n  Clothing Recommendation (clothing_recommendation) - Multi-class")
        print(f"      Dev  Accuracy : {m['dev_accuracy']:.4f}")
        print(f"      Test Accuracy : {m['test_accuracy']:.4f}")
        print(f"      Dev  Macro-F1 : {m['dev_macro_f1']:.4f}")
        print(f"      Test Macro-F1 : {m['test_macro_f1']:.4f}")
        print(f"      Class count   : {m['n_classes']}")
        print(f"      Train / Dev / Test rows: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Forecast ---
    m = results.get("Forecast Analysis")
    if m:
        print("\n  Forecast Quality (forecast_vs_actual)")
        print(f"      Overall umbrella accuracy : {m['overall_umbrella_accuracy']:.4f}")
        print(f"      Overall condition accuracy: {m['overall_condition_accuracy']:.4f}")
        print(f"      Total rows                : {m['total_rows']}")
        if "lead_time_breakdown" in m and m["lead_time_breakdown"]:
            print("      Lead time breakdown:")
            for row in m["lead_time_breakdown"]:
                print(
                    f"        {row['lead_time_hours']:>4} hours -> "
                    f"Umbrella={row['umbrella_correct']:.3f}  "
                    f"Condition={row['condition_correct']:.3f}"
                )

    print(f"\n{banner}\n")


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------
def main() -> None:
    force_retrain = "--force-retrain" in sys.argv

    results: dict[str, dict | None] = {}

    base_trainer_py = repo_path("ml", "src", "base_trainer.py")

    results["Umbrella Model"] = _run_step(
        "Umbrella Model",
        train_umbrella,
        artifact_paths=[
            repo_path("ml", "trained_models", "umbrella_model.pkl"),
            repo_path("ml", "trained_models", "umbrella_feature_schema.json"),
            repo_path("ml", "trained_models", "umbrella_metrics.json"),
        ],
        metrics_path=repo_path("ml", "trained_models", "umbrella_metrics.json"),
        dependency_paths=[
            repo_path("ml", "data", "raw", "hourly_observations.csv"),
            repo_path("ml", "src", "train_umbrella.py"),
            base_trainer_py,
        ],
        force_retrain=force_retrain,
    )
    results["Suitability Model"] = _run_step(
        "Suitability Model",
        train_suitability,
        artifact_paths=[
            repo_path("ml", "trained_models", "suitability_model.pkl"),
            repo_path("ml", "trained_models", "suitability_feature_schema.json"),
            repo_path("ml", "trained_models", "suitability_metrics.json"),
        ],
        metrics_path=repo_path("ml", "trained_models", "suitability_metrics.json"),
        dependency_paths=[
            repo_path("ml", "data", "raw", "hourly_observations.csv"),
            repo_path("ml", "src", "train_suitability.py"),
            base_trainer_py,
        ],
        force_retrain=force_retrain,
    )
    results["Clothing Model"] = _run_step(
        "Clothing Model",
        train_clothing,
        artifact_paths=[
            repo_path("ml", "trained_models", "clothing_model.pkl"),
            repo_path("ml", "trained_models", "clothing_feature_schema.json"),
            repo_path("ml", "trained_models", "clothing_metrics.json"),
        ],
        metrics_path=repo_path("ml", "trained_models", "clothing_metrics.json"),
        dependency_paths=[
            repo_path("ml", "data", "raw", "hourly_observations.csv"),
            repo_path("ml", "src", "train_clothing.py"),
            base_trainer_py,
        ],
        force_retrain=force_retrain,
    )
    results["Forecast Analysis"] = _run_step(
        "Forecast Analysis",
        analyze_forecast,
        artifact_paths=[repo_path("ml", "trained_models", "forecast_metrics.json")],
        metrics_path=repo_path("ml", "trained_models", "forecast_metrics.json"),
        dependency_paths=[
            repo_path("ml", "data", "raw", "forecast_vs_actual.csv"),
            repo_path("ml", "src", "analyze_forecast.py"),
            base_trainer_py,
        ],
        force_retrain=force_retrain,
    )

    _print_summary(results)

    # Herhangi bir adım başarısız olduysa çıkış kodunu 1 yap (CI/CD uyumlu)
    failed = [k for k, v in results.items() if v is None]
    if failed:
        print(f"  Failed steps: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
