from fastapi import APIRouter, HTTPException

from services.llm_compact import weather_effect_label
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.weather import fetch_current_weather

router = APIRouter(prefix="/feed")


@router.get("/")
async def get_feed(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    weather_data = fetch_current_weather(city)
    hourly_raw = weather_data["hourly_raw"]

    items = []
    n = min(24, len(hourly_raw.get("time", [])))

    for i in range(n):
        hour_data = {
            "time": hourly_raw["time"][i],
            "temperature_2m": hourly_raw["temperature_2m"][i],
            "relative_humidity_2m": hourly_raw["relative_humidity_2m"][i],
            "precipitation": hourly_raw["precipitation"][i],
            "wind_speed_10m": hourly_raw["wind_speed_10m"][i],
            "cloud_cover": hourly_raw["cloud_cover"][i],
            "weather_code": hourly_raw["weather_code"][i],
        }
        h_features = normalize_to_model_features(
            hour_data,
            weather_data["utc_offset"],
            latitude=weather_data["latitude"],
            longitude=weather_data["longitude"],
        )
        h_result = predictor.predict(h_features)
        h_effect = weather_effect_label(hour_data)

        items.append(
            {
                "time": hour_data["time"],
                "temperature": round(float(h_features["temperature_c"])),
                "weather_effect": h_effect,
                "umbrella_needed": h_result["umbrella_needed"],
                "clothing_recommendation": h_result["clothing_recommendation"],
                "suitability_score": h_result["suitability_score"],
                "go_or_no": h_result["go_or_no"],
            }
        )

    return {
        "city": weather_data["location"],
        "country": weather_data["country"],
        "items": items,
    }
