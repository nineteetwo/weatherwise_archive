import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException

from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.llm import generate_recommendation_tip
from services.prompt_template import (
    build_recommend_system_prompt,
    build_recommend_user_prompt,
)

# استيراد الأدوات اللي عملناها
from .utils import process_24h_forecast, _weather_effect

router = APIRouter(prefix="/recommend")

# ننشئ الـ executor بره عشان نستخدمه في كل الطلبات
executor = ThreadPoolExecutor(max_workers=4)

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


@router.get("/")
async def get_recommendation(city: str):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="City parameter is required")

    print(f"\n--- Bismillah! Profiling Request for: {city} ---")
    t_total_start = time.time()

    # 1. جلب البيانات (خطوة أولية لا بد منها)
    t_weather_start = time.time()
    weather_data = await fetch_current_weather(city)
    t_weather_end = round(time.time() - t_weather_start, 2)

    # 2. ML Predict (Current)
    t_ml_current_start = time.time()
    current_raw = weather_data["current_raw"]
    features = normalize_to_model_features(
        current_raw,
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )
    result = predictor.predict(features)
    t_ml_current_end = round(time.time() - t_ml_current_start, 2)

    # 3. تجهيز بيانات الـ LLM
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

    # 4. 🔥 قياس التوازي (LLM و 24h Loop)
    loop = asyncio.get_event_loop()
    
    # سنستخدم هذه المتغيرات لقياس الوقت داخل المهام
    t_llm_start = time.time()
    t_loop_start = time.time()

    # دالة وسيطة لقياس وقت الـ LLM
    async def timed_llm():
        res = await generate_recommendation_tip(system_prompt, user_prompt, fallback_tip)
        return res, round(time.time() - t_llm_start, 2)

    
    def timed_loop():
        res = process_24h_forecast(weather_data)
        return res, round(time.time() - t_loop_start, 2)

    
    llm_task = timed_llm()
    forecast_task = loop.run_in_executor(executor, timed_loop)

    
    (llm_output, llm_time), (hourly_forecast, loop_time) = await asyncio.gather(llm_task, forecast_task)

    
    t_total_end = round(time.time() - t_total_start, 2)
    
    print(f"📊 [PROFILING REPORT]")
    print(f"   - Weather API:    {t_weather_end}s")
    print(f"   - ML Current:     {t_ml_current_end}s")
    print(f"   - Ollama AI:      {llm_time}s")
    print(f"   - 24h Forecast:   {loop_time}s")
    print(f"🚀 [TOTAL DURATION]: {t_total_end}s")
    print("------------------------------------------\n")

    result["tip_text"] = llm_output["tip_text"]
    result["llm_mode"] = llm_output["llm_mode"]

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
        "weather_effect":          _weather_effect(current_raw),
        "mode":                    result["mode"],
        "hour_local":              features["hour_of_day"],
        "tip_text":                result["tip_text"],
        "llm_mode":                result["llm_mode"],
        "forecast_24h":            hourly_forecast,
    }