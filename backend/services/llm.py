import logging
from typing import Any
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    try:
        llm = ChatOllama(model="PhanarAi", temperature=0.2)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        raise

def generate_recommendation_tip(system_prompt: str, user_prompt: str, fallback_tip: str) -> dict[str, Any]:
    try:
        text = _call_ollama(system_prompt, user_prompt)
        if not text:
            return {"tip_text": fallback_tip, "llm_mode": "fallback_empty"}
        return {"tip_text": text, "llm_mode": "ollama_local"}
    except Exception:
        logger.exception("Ollama recommend call failed; returning fallback tip.")
        return {"tip_text": fallback_tip, "llm_mode": "fallback_error"}

def generate_chat_answer(system_prompt: str, user_prompt: str, fallback_text: str) -> dict[str, Any]:
    try:
        text = _call_ollama(system_prompt, user_prompt)
        if not text:
            return {"answer": fallback_text, "llm_mode": "fallback_empty"}
        return {"answer": text, "llm_mode": "ollama_local"}
    except Exception:
        logger.exception("Ollama chat call failed; returning fallback answer.")
        return {"answer": fallback_text, "llm_mode": "fallback_error"}