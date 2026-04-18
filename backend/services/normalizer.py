from datetime import datetime, timezone, timedelta

def _get_season(month: int) -> int:
    if month in (12, 1, 2): return 0
    if month in (3, 4, 5):  return 1
    if month in (6, 7, 8):  return 2
    return 3

def _weather_condition_from_code(code: int) -> str:
    if code in (0, 1):
        return "clear"
    if code in (2, 3):
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "thunderstorm"
    return "unknown"

def _precip_type(code: int, precip_mm: float) -> str:
    if precip_mm <= 0:
        return "none"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    return "rain"

def normalize_to_model_features(
    raw_weather: dict,
    utc_offset: int = 0,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> dict:
   
    utc_now = datetime.now(timezone.utc)
    city_time = utc_now + timedelta(seconds=utc_offset)

    wind_ms = float(raw_weather.get("wind_speed_10m", 0.0))
    wind_kmh = round(wind_ms * 3.6, 2)
    gust_ms = float(raw_weather.get("wind_gusts_10m", 0.0))
    gust_kmh = round(gust_ms * 3.6, 2)

    vis_m = float(raw_weather.get("visibility", 10000))
    vis_km = round(vis_m / 1000, 2)
    precip_mm = float(raw_weather.get("precipitation", 0.0))
    code = int(raw_weather.get("weather_code", 0))
    weather_condition = _weather_condition_from_code(code)
    precip_type = _precip_type(code, precip_mm)
    is_thunderstorm = 1 if code in (95, 96, 99) else 0

    return {
        # Categorical columns from model schema.
        "station_id": "live_api",
        "station_name": "open_meteo",
        "climate_zone": "unknown",
        "season": _get_season(city_time.month),
        "precipitation_type": precip_type,
        "weather_condition": weather_condition,
        "road_surface": "unknown",
        # Numeric columns from model schema.
        "latitude": float(latitude),
        "longitude": float(longitude),
        "elevation_m": float(raw_weather.get("elevation_m", 0.0)),
        "hour_of_day": city_time.hour,
        "month": city_time.month,
        "day_of_week": city_time.weekday(),
        "is_weekend": 1 if city_time.weekday() >= 5 else 0,
        "temperature_c": float(raw_weather.get("temperature_2m", 20.0)),
        "feels_like_c": float(raw_weather.get("apparent_temperature", raw_weather.get("temperature_2m", 20.0))),
        "dew_point_c": float(raw_weather.get("dew_point_2m", raw_weather.get("temperature_2m", 20.0) - 2.0)),
        "humidity_pct": float(raw_weather.get("relative_humidity_2m", 50.0)),
        "pressure_hpa": float(raw_weather.get("pressure_msl", 1013.25)),
        "wind_speed_kmh": wind_kmh,
        "wind_direction_deg": float(raw_weather.get("wind_direction_10m", 0.0)),
        "wind_gust_kmh": gust_kmh,
        "precipitation_mm": precip_mm,
        "cloud_cover_pct": float(raw_weather.get("cloud_cover", 0.0)),
        "visibility_km": vis_km,
        "uv_index": float(raw_weather.get("uv_index", 0.0)),
        "is_thunderstorm": is_thunderstorm,
    }