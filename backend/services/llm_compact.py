"""Small LLM payloads — avoids dumping full Open-Meteo + feature dicts (slow prefill on Ollama)."""


def weather_effect_label(data_slice: dict) -> str:
    code = data_slice.get("weather_code", 0)
    precip = data_slice.get("precipitation", 0)
    temp = data_slice.get("temperature_2m", 20)
    if code in range(95, 100):
        return "thunder"
    if code in range(71, 78):
        return "snow"
    if precip > 2:
        return "heavy-rain"
    if precip > 0:
        return "rain"
    if temp < 0:
        return "snow"
    if data_slice.get("cloud_cover", 0) > 70:
        return "clouds"
    return "clear"


def compact_weather_for_llm(weather_data: dict, current_raw: dict, features: dict) -> dict:
    return {
        "location": weather_data["location"],
        "country": weather_data.get("country", ""),
        "timezone": weather_data.get("timezone", ""),
        "summary": {
            "temperature_c": round(float(features.get("temperature_c", 0)), 1),
            "feels_like_c": round(float(features.get("feels_like_c", 0)), 1),
            "precipitation_mm": round(float(features.get("precipitation_mm", 0)), 2),
            "wind_speed_kmh": round(float(features.get("wind_speed_kmh", 0)), 1),
            "humidity_pct": round(float(features.get("humidity_pct", 0)), 0),
            "cloud_cover_pct": round(float(features.get("cloud_cover_pct", 0)), 0),
            "weather_condition": features.get("weather_condition", ""),
            "precipitation_type": features.get("precipitation_type", ""),
            "hour_local": int(features.get("hour_of_day", 0)),
            "season": int(features.get("season", 0)),
            "weather_effect": weather_effect_label(current_raw),
            "uv_index": round(float(features.get("uv_index", 0)), 1),
        },
    }


def compact_prediction_for_llm(result: dict) -> dict:
    return {
        "umbrella_needed": result.get("umbrella_needed"),
        "clothing_recommendation": result.get("clothing_recommendation"),
        "suitability_score": result.get("suitability_score"),
        "go_or_no": result.get("go_or_no"),
    }
