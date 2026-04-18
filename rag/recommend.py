from fastapi import APIRouter, HTTPException
from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.llm import generate_recommendation_tip
from services.prompt_template import (
    build_recommend_system_prompt,
    build_recommend_user_prompt,
)
from rag.utils import process_24h_forecast, _weather_effect

router = APIRouter(prefix="/recommend")

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

    # 4. 24h Loop
    hourly_forecast = process_24h_forecast(weather_data)

    # 5. LLM tip
    system_prompt = build_recommend_system_prompt()
    prompt_weather_context = {
        "location":             weather_data["location"],
        "country":              weather_data["country"],
        "timezone":             weather_data["timezone"],
        "raw":                  current_raw,
        "normalized_features":  features,
        "forecast_24h":         hourly_forecast,
    }
    user_prompt  = build_recommend_user_prompt(prompt_weather_context, result)
    fallback_tip = _rule_based_tip(weather_data["location"], result, features)
    llm_output   = generate_recommendation_tip(system_prompt, user_prompt, fallback_tip)

    result["tip_text"] = llm_output["tip_text"]
    result["llm_mode"] = llm_output["llm_mode"]

    current_effect = _weather_effect(current_raw)

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