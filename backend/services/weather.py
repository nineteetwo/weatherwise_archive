import time
import requests
from fastapi import HTTPException

CURRENT_FIELDS = (
    "temperature_2m,apparent_temperature,dew_point_2m,"
    "relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m,"
    "cloud_cover,pressure_msl,weather_code,visibility,wind_direction_10m,uv_index"
)

HOURLY_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,"
    "wind_speed_10m,cloud_cover,weather_code"
)

_session = requests.Session()
_session.headers.update({"Accept-Encoding": "gzip"})


def _get_with_retry(url: str, params: dict, timeout: int = 8, retries: int = 3) -> dict:
    last_err = None
    for attempt in range(retries):
        try:
            res = _session.get(url, params=params, timeout=timeout)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))
    raise last_err


def fetch_current_weather(city_name: str) -> dict:
    city_name = city_name.strip()
    if not city_name:
        raise HTTPException(status_code=400, detail="City name cannot be empty")

    try:
        geo_res = _get_with_retry(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_name, "count": 1, "language": "en"},
        )
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Geocoding service unavailable")

    if not geo_res.get("results"):
        raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

    loc = geo_res["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]

    try:
        w_res = _get_with_retry(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": CURRENT_FIELDS,
                "hourly": HOURLY_FIELDS,
                "forecast_hours": 24,
                "timezone": "auto",
            },
        )
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Weather service unavailable")

    if "current" not in w_res or "hourly" not in w_res:
        raise HTTPException(status_code=503, detail="Invalid weather response")

    return {
        "current_raw": w_res["current"],
        "hourly_raw":  w_res["hourly"],
        "location":    loc["name"],
        "country":     loc.get("country", ""),
        "utc_offset":  w_res.get("utc_offset_seconds", 0),
        "latitude":    lat,
        "longitude":   lon,
        "timezone":    w_res.get("timezone", "UTC"),
    }