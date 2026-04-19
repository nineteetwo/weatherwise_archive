from services.normalizer import normalize_to_model_features
from services.predictor import predictor

def _weather_effect(data_slice: dict) -> str:
    code   = data_slice.get("weather_code", 0)
    precip = data_slice.get("precipitation", 0)
    temp   = data_slice.get("temperature_2m", 20)
    if code in range(95, 100): return "thunder"
    if code in range(71, 78):  return "snow"
    if precip > 2:             return "heavy-rain"
    if precip > 0:             return "rain"
    if temp < 0:               return "snow"
    if data_slice.get("cloud_cover", 0) > 70: return "clouds"
    return "clear"

def process_24h_forecast(weather_data: dict) -> list[dict]:
    hourly_raw = weather_data.get("hourly_raw", {})
    if not hourly_raw or "time" not in hourly_raw:
        return []

    limit = min(24, len(hourly_raw["time"]))
    
    # 1. تجهيز كل البيانات في قوائم
    all_hour_data = []
    all_features  = []
    
    for i in range(limit):
        hour_data = {
            "time":                 hourly_raw["time"][i],
            "temperature_2m":       hourly_raw["temperature_2m"][i],
            "relative_humidity_2m": hourly_raw["relative_humidity_2m"][i],
            "precipitation":        hourly_raw["precipitation"][i],
            "wind_speed_10m":       hourly_raw["wind_speed_10m"][i],
            "cloud_cover":          hourly_raw["cloud_cover"][i],
            "weather_code":         hourly_raw["weather_code"][i],
        }
        h_features = normalize_to_model_features(
            hour_data, weather_data["utc_offset"],
            latitude=weather_data["latitude"],
            longitude=weather_data["longitude"],
        )
        all_hour_data.append(hour_data)
        all_features.append(h_features)
    
    # 2. استدعاء واحد للموديل لكل الساعات دفعة واحدة
    all_results = predictor.predict_batch(all_features)
    

    return [
        {
            "time":                    all_hour_data[i]["time"],
            "temperature":             all_features[i]["temperature_c"],
            "weather_effect":          _weather_effect(all_hour_data[i]),
            "umbrella_needed":         all_results[i]["umbrella_needed"],
            "clothing_recommendation": all_results[i]["clothing_recommendation"],
            "suitability_score":       all_results[i]["suitability_score"],
            "go_or_no":                all_results[i]["go_or_no"],
        }
        for i in range(limit)
    ]