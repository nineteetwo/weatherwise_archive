from datetime import datetime, timezone, timedelta

def _get_season(month: int) -> int:
    if month in (12, 1, 2): return 0   # Winter
    if month in (3, 4, 5):  return 1   # Spring
    if month in (6, 7, 8):  return 2   # Summer
    return 3                            # Autumn

def normalize_to_model_features(raw_weather: dict, utc_offset: int = 0) -> dict:
   
    utc_now = datetime.now(timezone.utc)
    city_time = utc_now + timedelta(seconds=utc_offset)

    wind_ms  = float(raw_weather.get("wind_speed_10m", 0.0))
    wind_kmh = round(wind_ms * 3.6, 2)

    vis_m  = float(raw_weather.get("visibility", 10000))
    vis_km = round(vis_m / 1000, 2)

    return {
        "temperature":    float(raw_weather.get("temperature_2m", 20.0)),
        "humidity":       float(raw_weather.get("relative_humidity_2m", 50.0)),
        "wind_speed_kmh": wind_kmh,
        "precipitation":  float(raw_weather.get("precipitation", 0.0)),
        "cloud_cover":    float(raw_weather.get("cloud_cover", 0.0)),
        "pressure":       float(raw_weather.get("pressure_msl", 1013.25)),
        "visibility_km":  vis_km,
        "weather_code":   int(raw_weather.get("weather_code", 0)),
        "hour_of_day":    city_time.hour,        
        "month":          city_time.month,
        "day_of_week":    city_time.weekday(),
        "is_weekend":     1 if city_time.weekday() >= 5 else 0,
        "season":         _get_season(city_time.month)
    }