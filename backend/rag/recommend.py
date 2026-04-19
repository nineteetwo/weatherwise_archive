import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from services.llm import generate_recommendation_tip
from services.llm_compact import (
    compact_prediction_for_llm,
    compact_weather_for_llm,
    weather_effect_label,
)
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.prompt_template import (
    build_recommend_system_prompt,
    build_recommend_user_prompt,
)
from services.rag_retriever import retrieve_similar_conditions
from services.weather import fetch_current_weather

from .utils import process_24h_forecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommend")

executor = ThreadPoolExecutor(max_workers=4)


def _rule_based_tip(city: str, result: dict, features: dict) -> str:
    temp = features.get("temperature_c", 20)
    precip = features.get("precipitation_mm", 0)
    score = result.get("suitability_score", 7)
    go = result.get("go_or_no", True)
    cloth = result.get("clothing_recommendation", "")

    if not go:
        return f"Today in {city} isn't great for going out. Consider staying in!"
    if precip > 0:
        return f"Don't forget your umbrella in {city}! Wear a {cloth} and stay dry."
    if temp > 35:
        return f"It's very hot in {city}! Stay hydrated and wear light clothes."
    if temp < 5:
        return f"Bundle up in {city} — it's cold! A {cloth} is a must."
    return f"Nice day in {city}! Suitability score is {score}/10 — enjoy your time outside."


@router.get("/")
async def get_recommendation(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    print(f"\n--- Profiling request for: {city} ---")
    t_total_start = time.time()

    t_weather_start = time.time()
    weather_data = fetch_current_weather(city)
    t_weather_end = round(time.time() - t_weather_start, 2)

    current_raw = weather_data["current_raw"]
    features = normalize_to_model_features(
        current_raw,
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )

    t_ml_current_start = time.time()
    result = predictor.predict(features)
    t_ml_current_end = round(time.time() - t_ml_current_start, 2)

    historical_context = None
    try:
        historical_context = retrieve_similar_conditions(features)
    except Exception:
        logger.exception("RAG retrieve_similar_conditions failed; continuing without RAG")
        historical_context = None

    system_prompt = build_recommend_system_prompt()
    user_prompt = build_recommend_user_prompt(
        compact_weather_for_llm(weather_data, current_raw, features),
        compact_prediction_for_llm(result),
        historical_context,
    )
    fallback_tip = _rule_based_tip(weather_data["location"], result, features)

    async def timed_llm():
        t_llm_start = time.time()
        res = await generate_recommendation_tip(system_prompt, user_prompt, fallback_tip)
        return res, round(time.time() - t_llm_start, 2)

    def timed_loop():
        t_loop_start = time.time()
        res = process_24h_forecast(weather_data)
        return res, round(time.time() - t_loop_start, 2)

    loop = asyncio.get_event_loop()
    llm_task = timed_llm()
    forecast_task = loop.run_in_executor(executor, timed_loop)
    (llm_output, llm_time), (hourly_forecast, loop_time) = await asyncio.gather(llm_task, forecast_task)

    t_total_end = round(time.time() - t_total_start, 2)
    print("📊 [PROFILING]")
    print(f"   - Weather API:  {t_weather_end}s")
    print(f"   - ML current:   {t_ml_current_end}s")
    print(f"   - Ollama LLM:   {llm_time}s")
    print(f"   - 24h forecast: {loop_time}s")
    print(f"🚀 TOTAL: {t_total_end}s\n")

    result["tip_text"] = llm_output["tip_text"]
    result["llm_mode"] = llm_output["llm_mode"]

    current_effect = weather_effect_label(current_raw)

    return {
        "city": weather_data["location"],
        "country": weather_data["country"],
        "temperature": features["temperature_c"],
        "utc_offset": weather_data["utc_offset"],
        "timezone": weather_data["timezone"],
        "umbrella_needed": result["umbrella_needed"],
        "clothing_recommendation": result["clothing_recommendation"],
        "suitability_score": result["suitability_score"],
        "go_or_no": result["go_or_no"],
        "weather_effect": current_effect,
        "mode": result["mode"],
        "hour_local": features["hour_of_day"],
        "tip_text": result["tip_text"],
        "llm_mode": result["llm_mode"],
        "rag_mode": "dataset" if historical_context else "none",
        "forecast_24h": hourly_forecast,
    }
