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
    """
    Takes the full weather_data from the API, extracts the 24h hourly_raw data,
    normalizes features, and runs them through the scikit-learn models.
    Returns a list of 24 hourly predictions.
    """
    hourly_forecast = []
    hourly_raw = weather_data.get("hourly_raw", {})
    
    if not hourly_raw or "time" not in hourly_raw:
        return []

    limit = min(24, len(hourly_raw["time"]))
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
            hour_data,
            weather_data["utc_offset"],
            latitude=weather_data["latitude"],
            longitude=weather_data["longitude"],
        )
        h_result = predictor.predict(h_features)
        h_effect = _weather_effect(hour_data)

        hourly_forecast.append({
            "time":                    hour_data["time"],
            "temperature":             h_features["temperature_c"],
            "weather_effect":          h_effect,
            "umbrella_needed":         h_result["umbrella_needed"],
            "clothing_recommendation": h_result["clothing_recommendation"],
            "suitability_score":       h_result["suitability_score"],
            "go_or_no":                h_result["go_or_no"],
        })
        
    return hourly_forecast
