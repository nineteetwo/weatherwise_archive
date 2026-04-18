import requests
from fastapi import HTTPException

CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,"
    "wind_speed_10m,cloud_cover,pressure_msl,"
    "weather_code,visibility,wind_direction_10m"
)

HOURLY_FIELDS = (
    "temperature_2m,relative_humidity_2m,precipitation,"
    "wind_speed_10m,cloud_cover,weather_code"
)

def fetch_current_weather(city_name: str) -> dict:
    city_name = city_name.strip()
    if not city_name:
        raise HTTPException(status_code=400, detail="City name cannot be empty")

    # Step 1: Geocoding
    try:
        geo_res = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_name, "count": 1, "language": "en"},
            timeout=6
        ).json()
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Geocoding service unavailable")

    if not geo_res.get("results"):
        raise HTTPException(status_code=404, detail=f"City '{city_name}' not found")

    loc = geo_res["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]

    # Step 2: Weather Fetch (Now with 24h Hourly Data)
    try:
        w_res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": CURRENT_FIELDS,
                "hourly": HOURLY_FIELDS,
                "forecast_hours": 24,
                "timezone": "auto"
            },
            timeout=6
        ).json()
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Weather service unavailable")

    if "current" not in w_res or "hourly" not in w_res:
        raise HTTPException(status_code=503, detail="Invalid weather response")

    # --- [Output Testing] ---
    print(f"\n✅ SUCCESS: Fetched 24-hour forecast for {loc['name']}")
    times = w_res["hourly"]["time"]
    temps = w_res["hourly"]["temperature_2m"]
    
    print("--- Preview of the next 4 hours ---")
    for i in range(4):
        print(f"Time: {times[i]} | Temp: {temps[i]}°C")
    print("-----------------------------------\n")
    # -------------------------

    return {
        "current_raw": w_res["current"],
        "hourly_raw": w_res["hourly"],
        "location": loc["name"],        
        "country": loc.get("country", ""),
        "utc_offset": w_res.get("utc_offset_seconds", 0),
        "latitude": lat,
        "longitude": lon,
        "timezone": w_res.get("timezone", "UTC")
    }