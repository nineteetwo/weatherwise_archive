"""
main.py
-------
Tüm eğitim ve analiz adımlarını sırayla çalıştırır, ardından
konsola özet bir metrik tablosu basar.

Kullanım:
    python main.py
"""

import sys
import traceback

# ---------------------------------------------------------------------------
# Modüller buradan import edilir — her biri bir run() fonksiyonu döndürür.
# ---------------------------------------------------------------------------
import train_umbrella
import train_suitability
import train_clothing
import analyze_forecast


# ---------------------------------------------------------------------------
# Yardımcı: adım çalıştır, hata varsa yakala ama devam et
# ---------------------------------------------------------------------------
def _run_step(name: str, module) -> dict | None:
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  ▶  {name}")
    print(sep)
    try:
        result = module.run()
        print(f"  ✔  {name} tamamlandı.\n")
        return result
    except Exception:
        print(f"\n  ✘  {name} sırasında hata oluştu:")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Özet tablosu yazdıran yardımcı
# ---------------------------------------------------------------------------
def _print_summary(results: dict[str, dict | None]) -> None:
    banner = "═" * 60
    print(f"\n{banner}")
    print("  📊  ÖZET METRİKLER")
    print(banner)

    # --- Şemsiye ---
    m = results.get("Şemsiye Modeli")
    if m:
        print("\n  🌂  Şemsiye (umbrella_needed) — İkili Sınıflandırma")
        print(f"      Dev  F1       : {m['dev_f1_best']:.4f}")
        print(f"      Test F1       : {m['test_f1']:.4f}")
        print(f"      Karar Eşiği   : {m['decision_threshold']:.2f}")
        print(f"      Eğitim / Dev / Test satır sayısı: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Suitability ---
    m = results.get("Suitability Modeli")
    if m:
        print("\n  🌤   Dışarıda Uygunluk (outdoor_suitability_score) — Regresyon")
        print(f"      Dev  MAE      : {m['dev_mae']:.4f}")
        print(f"      Test MAE      : {m['test_mae']:.4f}")
        print(f"      Dev  R²       : {m['dev_r2']:.4f}")
        print(f"      Test R²       : {m['test_r2']:.4f}")
        print(f"      Eğitim / Dev / Test satır sayısı: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Clothing ---
    m = results.get("Giysi Modeli")
    if m:
        print("\n  👗  Giysi Önerisi (clothing_recommendation) — Çok Sınıflı")
        print(f"      Dev  Accuracy : {m['dev_accuracy']:.4f}")
        print(f"      Test Accuracy : {m['test_accuracy']:.4f}")
        print(f"      Dev  Macro-F1 : {m['dev_macro_f1']:.4f}")
        print(f"      Test Macro-F1 : {m['test_macro_f1']:.4f}")
        print(f"      Sınıf sayısı  : {m['n_classes']}")
        print(f"      Eğitim / Dev / Test satır sayısı: "
              f"{m['rows_train']} / {m['rows_dev']} / {m['rows_test']}")

    # --- Forecast ---
    m = results.get("Tahmin Analizi")
    if m:
        print("\n  📡  Tahmin Kalitesi (forecast_vs_actual)")
        print(f"      Genel Şemsiye Doğruluğu  : {m['overall_umbrella_accuracy']:.4f}")
        print(f"      Genel Condition Doğruluğu: {m['overall_condition_accuracy']:.4f}")
        print(f"      Toplam satır              : {m['total_rows']}")
        if "lead_time_breakdown" in m and m["lead_time_breakdown"]:
            print("      Lead Time Dökümü:")
            for row in m["lead_time_breakdown"]:
                print(
                    f"        {row['lead_time_hours']:>4} saat  →  "
                    f"Şemsiye={row['umbrella_correct']:.3f}  "
                    f"Condition={row['condition_correct']:.3f}"
                )

    print(f"\n{banner}\n")


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------
def main() -> None:
    results: dict[str, dict | None] = {}

    results["Şemsiye Modeli"] = _run_step("Şemsiye Modeli", train_umbrella)
    results["Suitability Modeli"] = _run_step("Suitability Modeli", train_suitability)
    results["Giysi Modeli"] = _run_step("Giysi Modeli", train_clothing)
    results["Tahmin Analizi"] = _run_step("Tahmin Analizi", analyze_forecast)

    _print_summary(results)

    # Herhangi bir adım başarısız olduysa çıkış kodunu 1 yap (CI/CD uyumlu)
    failed = [k for k, v in results.items() if v is None]
    if failed:
        print(f"  ⚠️  Başarısız adımlar: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
