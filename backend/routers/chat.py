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


# =========================
# Request Schema
# =========================
class ChatRequest(BaseModel):
    city: str
    question: str


# =========================
# POST /chat
# =========================
@router.post("/")
async def chat(req: ChatRequest):
    # -------------------------
    # 1. Clean & validate input
    # -------------------------
    city = (req.city or "").strip()
    question = (req.question or "").strip()

    if not city:
        raise HTTPException(status_code=400, detail="City is required")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # -------------------------
    # 2. Fetch weather data
    # -------------------------
    weather_data = fetch_current_weather(city)

    # -------------------------
    # 3. Convert to ML features
    # -------------------------
    features = normalize_to_model_features(
        weather_data["raw"],
        weather_data["utc_offset"],
        latitude=weather_data["latitude"],
        longitude=weather_data["longitude"],
    )

    # -------------------------
    # 4. Run ML prediction
    # -------------------------
    prediction = predictor.predict(features)

    # -------------------------
    # 5. Build context for LLM
    # -------------------------
    weather_context = {
        "city": weather_data["location"],
        "country": weather_data["country"],
        "timezone": weather_data["timezone"],
        "temperature_c": features.get("temperature_c"),
        "weather_raw": weather_data["raw"],
    }

    # -------------------------
    # 6. Build prompts
    # -------------------------
    system_prompt = build_chat_system_prompt()
    user_prompt = build_chat_user_prompt(
        question,
        weather_context,
        prediction
    )

    # -------------------------
    # 7. Fallback (VERY IMPORTANT)
    # -------------------------
    umbrella_text = (
        "Take an umbrella."
        if prediction.get("umbrella_needed")
        else "You likely do not need an umbrella."
    )
    score = prediction.get("suitability_score")
    try:
        score_f = float(score)
    except (TypeError, ValueError):
        score_f = None

    if score_f is None:
        suitability_text = "Outdoor conditions are okay overall."
    elif score_f >= 8:
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

    # -------------------------
    # 8. Call LLM safely
    # -------------------------
    llm_output = generate_chat_answer(
        system_prompt,
        user_prompt,
        fallback_text
    )

    # -------------------------
    # 9. Return response
    # -------------------------
    return {
        "city": weather_data["location"],
        "country": weather_data["country"],
        "question": question,
        "answer": llm_output["answer"],
        "llm_mode": llm_output["llm_mode"],
        "prediction_mode": prediction.get("mode", "unknown"),
    }