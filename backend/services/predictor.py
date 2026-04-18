import json
import traceback
from pathlib import Path

import joblib
import pandas as pd


class WeatherPredictor:
    def __init__(self):
        self.is_loaded = False
        self.models = {}
        self.schemas = {}
        self.umbrella_threshold = 0.5
        self.model_base = self._resolve_model_base()
        self._load_models()

    def _resolve_model_base(self) -> Path:
        here = Path(__file__).resolve()
        repo_root = here.parents[2]
        candidates = [
            repo_root / "ml" / "trained_models",
            repo_root / "backend" / "models" / "artifacts",
            here.parent,
        ]
        for p in candidates:
            if (p / "clothing_model.pkl").exists():
                return p
        return candidates[0]

    def _load_json_if_exists(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_models(self):
        base = self.model_base
        paths = {
            "clothing": "clothing_model.pkl",
            "umbrella": "umbrella_model.pkl",
            "suitability": "suitability_model.pkl",
        }
        try:
            for key, fname in paths.items():
                full = base / fname
                if not full.exists():
                    print(f"[Predictor] Missing: {full} -> fallback mode")
                    return
                self.models[key] = joblib.load(full)
                schema_path = base / f"{key}_feature_schema.json"
                self.schemas[key] = self._load_json_if_exists(schema_path)

            umbrella_metrics = self._load_json_if_exists(base / "umbrella_metrics.json")
            self.umbrella_threshold = float(umbrella_metrics.get("decision_threshold", 0.5))
            self.is_loaded = True
            print(f"[Predictor] All models loaded from: {base}")
        except Exception:
            traceback.print_exc()
            self.is_loaded = False

    def _build_frame(self, f: dict, model_key: str) -> pd.DataFrame:
        schema = self.schemas.get(model_key, {})
        features = schema.get("features")
        if features:
            row = {k: f.get(k) for k in features}
            return pd.DataFrame([row], columns=features)
        return pd.DataFrame([f])

    def predict(self, f: dict) -> dict:
        if not self.is_loaded:
            return self._fallback(f)

        try:
            clothing_x = self._build_frame(f, "clothing")
            umbrella_x = self._build_frame(f, "umbrella")
            suitability_x = self._build_frame(f, "suitability")

            c_pred = self.models["clothing"].predict(clothing_x)[0]
            umbrella_model = self.models["umbrella"]
            if hasattr(umbrella_model, "predict_proba"):
                p = float(umbrella_model.predict_proba(umbrella_x)[:, 1][0])
                u_need = p >= self.umbrella_threshold
            else:
                u_need = bool(umbrella_model.predict(umbrella_x)[0])
            s_score = float(self.models["suitability"].predict(suitability_x)[0])

            return {
                "umbrella_needed": u_need,
                "clothing_recommendation": str(c_pred),
                "suitability_score": round(s_score, 2),
                "go_or_no": s_score >= 6.0,
                "mode": "ml",
            }
        except Exception:
            traceback.print_exc()
            return self._fallback(f)

    def _fallback(self, f: dict) -> dict:
        temp = float(f.get("temperature_c", 20))
        precip = float(f.get("precipitation_mm", 0))
        wind = float(f.get("wind_speed_kmh", 0))
        score = 8.0
        if precip > 2:
            score -= 3
        elif precip > 0:
            score -= 1
        if wind > 50:
            score -= 2
        if temp < 0 or temp > 40:
            score -= 1
        score = max(1.0, min(10.0, score))

        if temp < 5:
            clothing = "warm_jacket_layers"
        elif temp < 15:
            clothing = "light_jacket_or_sweater"
        elif temp < 25:
            clothing = "long_sleeves_light_layer"
        else:
            clothing = "t_shirt_comfortable"

        return {
            "umbrella_needed": precip > 0.1,
            "clothing_recommendation": clothing,
            "suitability_score": round(score, 2),
            "go_or_no": score >= 6.0,
            "mode": "fallback",
        }


predictor = WeatherPredictor()
