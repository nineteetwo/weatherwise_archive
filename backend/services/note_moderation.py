"""
Optional note sanitization for user-visible condition report text.

Uses whole-word matches only (ASCII letters). Intended for notes that may be
shown in a public feed; can be disabled with CONDITION_REPORT_NOTE_SANITIZE=0.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

# Longer tokens first so alternation prefers multi-word / compound matches.
_BLOCKED_TERMS: tuple[str, ...] = tuple(
    sorted(
        {
            "motherfucker",
            "motherfuckers",
            "bullshit",
            "asshole",
            "assholes",
            "cocksucker",
            "fucking",
            "fucker",
            "fucked",
            "fuck",
            "shit",
            "bitch",
            "bitches",
            "bastard",
            "bastards",
            "pissed",
            "piss",
            "dickhead",
            "dick",
            "cock",
            "whore",
            "slut",
            "sluts",
            "crap",
        },
        key=len,
        reverse=True,
    )
)


def note_sanitization_enabled() -> bool:
    raw = (os.getenv("CONDITION_REPORT_NOTE_SANITIZE") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


@lru_cache
def _profanity_pattern() -> re.Pattern[str]:
    inner = "|".join(re.escape(w) for w in _BLOCKED_TERMS)
    return re.compile(rf"\b(?:{inner})\b", re.IGNORECASE)


def sanitize_public_note(text: str) -> str:
    """Mask blocked whole words; pass-through when sanitization is disabled."""
    if not text or not note_sanitization_enabled():
        return text
    return _profanity_pattern().sub("***", text)


def normalize_optional_note(note: str | None) -> str | None:
    """
    After sanitization, drop notes that are empty or only masking placeholders.
    """
    if note is None:
        return None
    t = note.strip()
    if not t:
        return None
    if not re.search(r"[^\s*]", t):
        return None
    return t
