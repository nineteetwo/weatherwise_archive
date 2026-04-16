import joblib, os, traceback

CLOTHING_MAP = {
    0: "Heavy Winter Wear",
    1: "Light Sweater",
    2: "Summer T-shirt",
    3: "Raincoat"
}

FEATURE_ORDER = [
    "temperature", "humidity", "wind_speed_kmh", "precipitation",
    "cloud_cover", "pressure", "hour_of_day", "month",
    "day_of_week", "is_weekend", "season"
]

class WeatherPredictor:
    def __init__(self):
        self.is_loaded = False
        self.models = {}
        self._load_models()

    def _load_models(self):
        base = os.path.dirname(__file__)
        paths = {
            "clothing":   "clothing_model.pkl",
            "umbrella":   "umbrella_model.pkl",
            "suitability":"suitability_model.pkl"
        }
        try:
            for key, fname in paths.items():
                full = os.path.join(base, fname)
                if not os.path.exists(full):
                    print(f"[Predictor] Missing: {full} → fallback mode")
                    return
                self.models[key] = joblib.load(full)
            self.is_loaded = True
            print("[Predictor] ✅ All models loaded")
        except Exception:
            traceback.print_exc()
            self.is_loaded = False

    def _build_vector(self, f: dict) -> list:
        return [[f.get(k, 0) for k in FEATURE_ORDER]]

    def predict(self, f: dict) -> dict:
        if not self.is_loaded:
            return self._fallback(f)

        try:
            vec = self._build_vector(f)
            c_idx   = int(self.models["clothing"].predict(vec)[0])
            u_need  = bool(self.models["umbrella"].predict(vec)[0])
            s_score = float(self.models["suitability"].predict(vec)[0])

            return {
                "umbrella_needed":         u_need,
                "clothing_recommendation": CLOTHING_MAP.get(c_idx, "Normal Wear"),
                "suitability_score":       round(s_score, 2),
                "go_or_no":               s_score >= 6.0,
                "mode":                   "ml"
            }
        except Exception:
            traceback.print_exc()
            return self._fallback(f)

    def _fallback(self, f: dict) -> dict:
        temp  = f.get("temperature", 20)
        precip = f.get("precipitation", 0)
        wind  = f.get("wind_speed_kmh", 0)
        score = 8.0
        if precip > 2:   score -= 3
        elif precip > 0: score -= 1
        if wind > 50:    score -= 2
        if temp < 0 or temp > 40: score -= 1
        score = max(1.0, min(10.0, score))

        if temp < 5:   clothing = "Heavy Winter Wear"
        elif temp < 15: clothing = "Light Sweater"
        elif temp < 25: clothing = "Summer T-shirt"
        else:           clothing = "Light Summer Wear"

        return {
            "umbrella_needed":         precip > 0.1,
            "clothing_recommendation": clothing,
            "suitability_score":       round(score, 2),
            "go_or_no":               score >= 6.0,
            "mode":                   "fallback"
        }

predictor = WeatherPredictor()