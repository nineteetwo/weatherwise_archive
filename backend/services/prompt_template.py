import json
from typing import Any


_SYSTEM_PROMPT = (
    "You are a helpful, conversational Weather and Wardrobe AI assistant.\n\n"
    "Behavior rules:\n"
    "- Convert structured weather and model outputs into natural, practical advice.\n"
    "- Never mention technical ML terms (classification, regression, F1, MAE, "
    "accuracy, model names, schema names).\n"
    "- Never mention backend payload format or that structured data was attached.\n"
    "- If umbrella is needed, remind the user to take one; otherwise reassure them.\n"
    "- Translate suitability score into plain language mood (great/okay/not ideal).\n"
    "- Suggest clothing naturally as friendly outfit guidance.\n"
    "- Keep tone warm, concise, and user-facing.\n"
    "- Respond in the same language as the user.\n"
    "- Allowed languages only: English, Turkish, Russian; do not mix languages.\n"
    "- If forecast confidence is lower for longer lead time, add a gentle uncertainty note.\n"
)


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(obj)


def build_recommend_system_prompt() -> str:
    return _SYSTEM_PROMPT

def build_recommend_user_prompt(weather: dict[str, Any], prediction: dict[str, Any]) -> str:
    forecast_24h = weather.get("forecast_24h", [])
    
    return (
        "Create a comprehensive daily recommendation for the user based on the 24-hour ML forecast.\n\n"
        "Current Weather Context:\n"
        f"{_pretty(weather)}\n\n"
        "Current Prediction Context:\n"
        f"{_pretty(prediction)}\n\n"
        "24-Hour Forecast Context:\n"
        f"{_pretty(forecast_24h)}\n\n"
        "Output requirements:\n"
        "1. Tell the user exactly what clothing they should wear today.\n"
        "2. Clearly state if they need to bring an umbrella and why.\n"
        "3. Provide a friendly hour-by-hour (or period-by-period) summary of how the weather will change throughout the day.\n"
        "- non-technical\n"
        "- warm and conversational"
    )

def build_chat_system_prompt() -> str:
    return _SYSTEM_PROMPT

def build_chat_user_prompt(
    question: str,
    weather: dict[str, Any],
    prediction: dict[str, Any],
) -> str:
    forecast_24h = weather.get("forecast_24h", [])
    
    return (
        "Answer the user's question using the provided context.\n\n"
        f"User question:\n{question}\n\n"
        "Current Weather Context:\n"
        f"{_pretty(weather)}\n\n"
        "Current Prediction Context:\n"
        f"{_pretty(prediction)}\n\n"
        "24-Hour Forecast Context:\n"
        f"{_pretty(forecast_24h)}\n\n"
        "Output requirements:\n"
        "- concise conversational answer\n"
        "- practical and specific\n"
        "- no technical jargon"
    )