import os
import logging
import requests
from typing import Any

YANDEX_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
logger = logging.getLogger(__name__)

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

def _enabled() -> bool:
    return _env("LLM_PROVIDER", "").lower() == "yandex" and bool(_env("YANDEX_API_KEY")) and bool(_env("YANDEX_FOLDER_ID"))

def _model_uri() -> str:
    folder_id = _env("YANDEX_FOLDER_ID")
    model = _env("YANDEX_MODEL", "yandexgpt-lite/latest")
    return f"gpt://{folder_id}/{model}"

def _call_yandex(system_prompt: str, user_prompt: str) -> str:

    headers = {
        "Authorization": f"Api-Key {_env('YANDEX_API_KEY')}",
        "Content-Type": "application/json",
    }

    payload = {
        "modelUri": _model_uri(),
        "completionOptions": {
            "stream": False,
            "temperature": float(_env("YANDEX_TEMPERATURE", "0.2")),
            "maxTokens": int(_env("YANDEX_MAX_TOKENS", "300")),
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt},
        ],
    }

    timeout = int(_env("YANDEX_TIMEOUT_SECONDS", "12"))
    resp = requests.post(YANDEX_URL, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

 
    alternatives = data.get("result", {}).get("alternatives", [])
    if not alternatives:
        raise ValueError("No alternatives returned from Yandex LLM")
    return alternatives[0].get("message", {}).get("text", "").strip()
def generate_recommendation_tip(system_prompt: str, user_prompt: str, fallback_tip: str) -> dict[str, Any]:
    if not _enabled():
        return {"tip_text": fallback_tip, "llm_mode": "fallback_no_config"}
    try:
        text = _call_yandex(system_prompt, user_prompt)
        if not text:
            return {"tip_text": fallback_tip, "llm_mode": "fallback_empty"}
        return {"tip_text": text, "llm_mode": "yandex"}
    except Exception:
        logger.exception("Yandex recommend call failed; returning fallback tip.")
        return {"tip_text": fallback_tip, "llm_mode": "fallback_error"}
def generate_chat_answer(system_prompt: str, user_prompt: str, fallback_text: str) -> dict[str, Any]:
    if not _enabled():
        return {"answer": fallback_text, "llm_mode": "fallback_no_config"}
    try:
        text = _call_yandex(system_prompt, user_prompt)
        if not text:
            return {"answer": fallback_text, "llm_mode": "fallback_empty"}
        return {"answer": text, "llm_mode": "yandex"}
    except Exception:
        logger.exception("Yandex chat call failed; returning fallback answer.")
        return {"answer": fallback_text, "llm_mode": "fallback_error"}