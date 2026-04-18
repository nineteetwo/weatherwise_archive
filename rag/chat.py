from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from services.weather import fetch_current_weather
from services.normalizer import normalize_to_model_features
from services.predictor import predictor

from services.llm import generate_chat_answer
from services.prompt_template import (
    build_chat_system_prompt,
    build_chat_user_prompt,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    city: str
    question: str


@router.post("/")
async def chat(req: ChatRequest):
    city = (req.city or "").strip()
    question = (req.question or "").strip()

    if not city:
        raise HTTPException(status_code=400, detail="City is required")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # 1. Hava verisi
    weather_data = fetch_current_weather(city)

    # 2. ML feature normalize (BUG FIX: "current_raw" kullan, "raw" değil)
    features = normalize_to_model_features(
        weather_data["current_raw"],
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )

    # 3. ML tahmini
    prediction = predictor.predict(features)

    # 4. LLM context
    weather_context = {
        "city":          weather_data["location"],
        "country":       weather_data["country"],
        "timezone":      weather_data["timezone"],
        "temperature_c": features.get("temperature_c"),
        "weather_raw":   weather_data["current_raw"],
    }

    # 5. Prompt
    system_prompt = build_chat_system_prompt()
    user_prompt   = build_chat_user_prompt(question, weather_context, prediction)

    # 6. Fallback metin
    umbrella_text = "Take an umbrella." if prediction.get("umbrella_needed") else "You likely do not need an umbrella."
    score_f = float(prediction.get("suitability_score", 7) or 7)
    if score_f >= 8:
        suitability_text = "It looks like a great time to be outside."
    elif score_f >= 6:
        suitability_text = "Outdoor conditions look fairly good."
    elif score_f >= 4:
        suitability_text = "Outdoor conditions are mixed, so plan accordingly."
    else:
        suitability_text = "Outdoor conditions are not ideal right now."

    clothing_text = prediction.get("clothing_recommendation", "comfortable layers")
    fallback_text = (
        f"In {weather_data['location']}, I'd suggest {clothing_text}. "
        f"{umbrella_text} {suitability_text}"
    )

    # 7. LLM
    llm_output = generate_chat_answer(system_prompt, user_prompt, fallback_text)

    return {
        "city":            weather_data["location"],
        "country":         weather_data["country"],
        "question":        question,
        "answer":          llm_output["answer"],
        "llm_mode":        llm_output["llm_mode"],
        "prediction_mode": prediction.get("mode", "unknown"),
    }