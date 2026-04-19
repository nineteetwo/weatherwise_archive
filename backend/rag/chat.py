from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.llm import generate_chat_answer
from services.llm_compact import compact_prediction_for_llm, compact_weather_for_llm
from services.normalizer import normalize_to_model_features
from services.predictor import predictor
from services.prompt_template import (
    build_chat_system_prompt,
    build_chat_user_prompt,
)
from services.weather import fetch_current_weather

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

    weather_data = fetch_current_weather(city)

    features = normalize_to_model_features(
        weather_data["current_raw"],
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )

    prediction = predictor.predict(features)

    weather_context = compact_weather_for_llm(
        weather_data, weather_data["current_raw"], features
    )

    system_prompt = build_chat_system_prompt()
    user_prompt = build_chat_user_prompt(
        question,
        weather_context,
        compact_prediction_for_llm(prediction),
    )

    umbrella_text = (
        "Take an umbrella." if prediction.get("umbrella_needed") else "You likely do not need an umbrella."
    )
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

    llm_output = await generate_chat_answer(system_prompt, user_prompt, fallback_text)

    return {
        "city": weather_data["location"],
        "country": weather_data["country"],
        "question": question,
        "answer": llm_output["answer"],
        "llm_mode": llm_output["llm_mode"],
        "prediction_mode": prediction.get("mode", "unknown"),
    }
