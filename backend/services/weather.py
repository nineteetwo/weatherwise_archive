import asyncio
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


def _geocode(city_name: str) -> dict:
    try:
        geo_res = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_name, "count": 1, "language": "en"},
            timeout=6,
        ).json()
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Geocoding service unavailable")

    if not geo_res.get("results"):
        raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

    loc = geo_res["results"][0]
    return {
        "place_id": str(loc["id"]) if loc.get("id") is not None else None,
        "name": loc["name"],
        "latitude": float(loc["latitude"]),
        "longitude": float(loc["longitude"]),
        "country": loc.get("country", "") or "",
    }


def _forecast(lat: float, lon: float) -> dict:
    try:
        w_res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": CURRENT_FIELDS,
                "hourly": HOURLY_FIELDS,
                "forecast_hours": 24,
                "timezone": "auto",
            },
            timeout=6,
        ).json()
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Weather service unavailable")

    if "current" not in w_res or "hourly" not in w_res:
        raise HTTPException(status_code=503, detail="Invalid weather response")

    return w_res


async def resolve_city(city_name: str) -> dict:
    city_name = (city_name or "").strip()
    if not city_name:
        raise HTTPException(status_code=400, detail="City name cannot be empty")
    return await asyncio.to_thread(_geocode, city_name)


def fetch_current_weather(
    city_name: str,
    *,
    resolved_location: dict | None = None,
) -> dict:
    city_name = (city_name or "").strip()
    if not resolved_location and not city_name:
        raise HTTPException(status_code=400, detail="City name cannot be empty")

    if resolved_location:
        loc = resolved_location
        lat, lon = float(loc["latitude"]), float(loc["longitude"])
    else:
        loc = _geocode(city_name)
        lat, lon = loc["latitude"], loc["longitude"]

    w_res = _forecast(lat, lon)

    return {
        "current_raw": w_res["current"],
        "hourly_raw": w_res["hourly"],
        "location": loc["name"],
        "country": loc.get("country", ""),
        "utc_offset": w_res.get("utc_offset_seconds", 0),
        "latitude": lat,
        "longitude": lon,
        "timezone": w_res.get("timezone", "UTC"),
    }
