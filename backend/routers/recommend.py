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

def _weather_effect(data: dict, res: dict) -> str:
    code = data["raw"].get("weather_code", 0)
    precip = data["raw"].get("precipitation", 0)
    temp   = data["raw"].get("temperature_2m", 20)
    if code in range(95, 100): return "thunder"
    if code in range(71, 78):  return "snow"
    if precip > 2:             return "heavy-rain"
    if precip > 0:             return "rain"
    if temp < 0:               return "snow"
    if data["raw"].get("cloud_cover", 0) > 70: return "clouds"
    return "clear"

@router.get("/")
async def get_recommendation(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    weather_data = fetch_current_weather(city)
    features     = normalize_to_model_features(
        weather_data["raw"],
        weather_data["utc_offset"],   # local time enrichment
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )
    result = predictor.predict(features)

    system_prompt = build_recommend_system_prompt()
    prompt_weather_context = {
        "location": weather_data["location"],
        "country": weather_data["country"],
        "timezone": weather_data["timezone"],
        "raw": weather_data["raw"],
        "normalized_features": features,
    }
    user_prompt = build_recommend_user_prompt(prompt_weather_context, result)

    fallback_tip = "Carry an umbrella if rain is expected."

    llm_output = generate_recommendation_tip(system_prompt, user_prompt, fallback_tip)

    result["tip_text"] = llm_output["tip_text"]
    result["llm_mode"] = llm_output["llm_mode"]

    effect = _weather_effect(weather_data, result)

    return {
        "city":                    weather_data["location"], 
        "country":                 weather_data["country"],
        "temperature":             features["temperature_c"],
        "utc_offset":              weather_data["utc_offset"], 
        "timezone":                weather_data["timezone"],
        "umbrella_needed":         result["umbrella_needed"],
        "clothing_recommendation": result["clothing_recommendation"],
        "suitability_score":       result["suitability_score"],
        "go_or_no":               result["go_or_no"],
        "weather_effect":          effect,                     
        "mode":                    result["mode"],
        "hour_local":              features["hour_of_day"],
        "tip_text":                result["tip_text"],
        "llm_mode":                result["llm_mode"],
    }