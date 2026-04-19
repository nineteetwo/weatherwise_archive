import asyncio
import logging
import os
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def _ollama_base_url() -> str:
    return (
        os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
    ).rstrip("/")


def _ollama_model() -> str:
    return (os.getenv("OLLAMA_MODEL") or "PhanarAi").strip() or "PhanarAi"


def _make_ollama() -> ChatOllama:
    return ChatOllama(
        base_url=_ollama_base_url(),
        model=_ollama_model(),
        temperature=0.2,
        num_predict=220,
    )


async def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    try:
        llm = _make_ollama()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: llm.invoke(messages))
        return response.content
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        raise


async def generate_recommendation_tip(
    system_prompt: str, user_prompt: str, fallback_tip: str
) -> dict[str, Any]:
    try:
        text = await _call_ollama(system_prompt, user_prompt)
        if not text:
            return {"tip_text": fallback_tip, "llm_mode": "fallback_empty"}
        return {"tip_text": text, "llm_mode": "ollama_local"}
    except Exception:
        logger.exception("Ollama recommend failed")
        return {"tip_text": fallback_tip, "llm_mode": "fallback_error"}


async def generate_chat_answer(
    system_prompt: str, user_prompt: str, fallback_text: str
) -> dict[str, Any]:
    try:
        text = await _call_ollama(system_prompt, user_prompt)
        if not text:
            return {"answer": fallback_text, "llm_mode": "fallback_empty"}
        return {"answer": text, "llm_mode": "ollama_local"}
    except Exception:
        logger.exception("Ollama chat failed")
        return {"answer": fallback_text, "llm_mode": "fallback_error"}
