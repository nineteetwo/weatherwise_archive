import logging
import asyncio
import os
from typing import Any
from groq import Groq

logger = logging.getLogger(__name__)

_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    response = _groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


async def generate_recommendation_tip(
    system_prompt: str, user_prompt: str, fallback_tip: str
) -> dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, lambda: _call_groq(system_prompt, user_prompt)
        )
        if not text:
            return {"tip_text": fallback_tip, "llm_mode": "fallback_empty"}
        return {"tip_text": text, "llm_mode": "groq"}
    except Exception:
        logger.exception("Groq recommend failed")
        return {"tip_text": fallback_tip, "llm_mode": "fallback_error"}


async def generate_chat_answer(
    system_prompt: str, user_prompt: str, fallback_text: str
) -> dict[str, Any]:
    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, lambda: _call_groq(system_prompt, user_prompt)
        )
        if not text:
            return {"answer": fallback_text, "llm_mode": "fallback_empty"}
        return {"answer": text, "llm_mode": "groq"}
    except Exception:
        logger.exception("Groq chat failed")
        return {"answer": fallback_text, "llm_mode": "fallback_error"}