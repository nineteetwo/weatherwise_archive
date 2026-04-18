from fastapi import APIRouter, HTTPException
from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.llm import generate_recommendation_tip
from services.prompt_template import (
    build_recommend_system_prompt,
    build_recommend_user_prompt,
)

router = APIRouter(prefix="/recommend")


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


@router.get("/")
async def get_recommendation(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    # 1. جلب البيانات
    weather_data = fetch_current_weather(city)

    # 2. normalize الحالي
    current_raw = weather_data["current_raw"]
    features = normalize_to_model_features(
        current_raw,
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )

    # 3. predict الحالي
    result = predictor.predict(features)

    # 4. LLM tip
    system_prompt = build_recommend_system_prompt()
    prompt_weather_context = {
        "location":             weather_data["location"],
        "country":              weather_data["country"],
        "timezone":             weather_data["timezone"],
        "raw":                  current_raw,
        "normalized_features":  features,
    }
    user_prompt  = build_recommend_user_prompt(prompt_weather_context, result)
    fallback_tip = _rule_based_tip(weather_data["location"], result, features)
    llm_output   = generate_recommendation_tip(system_prompt, user_prompt, fallback_tip)

    result["tip_text"] = llm_output["tip_text"]
    result["llm_mode"] = llm_output["llm_mode"]

    current_effect = _weather_effect(current_raw)

    # 5. الـ 24h loop
    hourly_forecast = []
    hourly_raw = weather_data["hourly_raw"]

    for i in range(min(24, len(hourly_raw["time"]))):
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

    # 6. Response
    return {
        "city":                    weather_data["location"],
        "country":                 weather_data["country"],
        "temperature":             features["temperature_c"],
        "utc_offset":              weather_data["utc_offset"],
        "timezone":                weather_data["timezone"],
        "umbrella_needed":         result["umbrella_needed"],
        "clothing_recommendation": result["clothing_recommendation"],
        "suitability_score":       result["suitability_score"],
        "go_or_no":                result["go_or_no"],
        "weather_effect":          current_effect,
        "mode":                    result["mode"],
        "hour_local":              features["hour_of_day"],
        "tip_text":                result["tip_text"],
        "llm_mode":                result["llm_mode"],
        "forecast_24h":            hourly_forecast,
    }


def _rule_based_tip(city: str, result: dict, features: dict) -> str:
    temp   = features.get("temperature_c", 20)
    precip = features.get("precipitation_mm", 0)
    score  = result.get("suitability_score", 7)
    go     = result.get("go_or_no", True)
    cloth  = result.get("clothing_recommendation", "")

    if not go:
        return f"Today in {city} isn't great for going out. Consider staying in!"
    if precip > 0:
        return f"Don't forget your umbrella in {city}! Wear a {cloth} and stay dry."
    if temp > 35:
        return f"It's very hot in {city}! Stay hydrated and wear light clothes."
    if temp < 5:
        return f"Bundle up in {city} — it's cold! A {cloth} is a must."
    return f"Nice day in {city}! Suitability score is {score}/10 — enjoy your time outside."