from __future__ import annotations

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


def build_recommend_user_prompt(
    weather: dict[str, Any],
    prediction: dict[str, Any],
    historical_context: str | None = None,
    community_context: str | None = None,
) -> str:
    parts = [
        "Create one short recommendation tip for the user.\n\n"
        "Weather context:\n"
        f"{_pretty(weather)}\n\n"
        "Prediction context:\n"
        f"{_pretty(prediction)}\n\n",
    ]
    if historical_context:
        parts.append(f"{historical_context}\n\n")
    if community_context:
        parts.append(
            "Recent local peer feedback (only shown when enough reports; use lightly, "
            "do not contradict obvious weather):\n"
            f"{community_context}\n\n"
        )
    parts.append(
        "Output requirements:\n"
        "- 2-4 short sentences\n"
        "- non-technical\n"
        "- actionable\n"
        "- no bullet points"
    )
    return "".join(parts)


def build_chat_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_chat_user_prompt(
    question: str,
    weather: dict[str, Any],
    prediction: dict[str, Any],
    historical_context: str | None = None,
) -> str:
    parts = [
        "Answer the user's question using the provided context.\n\n"
        f"User question:\n{question}\n\n"
        "Weather context:\n"
        f"{_pretty(weather)}\n\n"
        "Prediction context:\n"
        f"{_pretty(prediction)}\n\n",
    ]
    if historical_context:
        parts.append(f"{historical_context}\n\n")
    parts.append(
        "Output requirements:\n"
        "- concise conversational answer\n"
        "- practical and specific\n"
        "- no technical jargon"
    )
    return "".join(parts)