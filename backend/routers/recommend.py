from fastapi import APIRouter, HTTPException
from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor

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
        weather_data["utc_offset"]   #    offset  normalizer
    )
    result = predictor.predict(features)
    effect = _weather_effect(weather_data, result)

    return {
        "city":                    weather_data["location"], 
        "country":                 weather_data["country"],
        "temperature":             features["temperature"],
        "utc_offset":              weather_data["utc_offset"], 
        "timezone":                weather_data["timezone"],
        "umbrella_needed":         result["umbrella_needed"],
        "clothing_recommendation": result["clothing_recommendation"],
        "suitability_score":       result["suitability_score"],
        "go_or_no":               result["go_or_no"],
        "weather_effect":          effect,                     
        "mode":                    result["mode"],
        "hour_local":              features["hour_of_day"]
    }