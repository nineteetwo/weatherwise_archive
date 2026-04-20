import json
import logging
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from db import (
    DEFAULT_EMBED_MODEL,
    get_reports_without_embeddings,
    list_embedded_reports_by_city,
    upsert_report_embedding,
)

logger = logging.getLogger(__name__)

_vectorizer = HashingVectorizer(
    n_features=256,
    norm=None,
    alternate_sign=False,
    lowercase=True,
    ngram_range=(1, 2),
)


def _report_text(feel: str, note: str) -> str:
    feel_text = (feel or "").strip().lower()
    note_text = (note or "").strip()
    if note_text:
        return f"feel:{feel_text} note:{note_text}"
    return f"feel:{feel_text}"


def _embed_text(text: str) -> np.ndarray:
    mat = _vectorizer.transform([text or ""])
    vec = np.asarray(mat.toarray()[0], dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _json_to_vec(vector_json: str) -> np.ndarray | None:
    try:
        payload = json.loads(vector_json)
        vec = np.asarray(payload, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
    except Exception:
        return None


def _vec_to_json(vec: np.ndarray) -> str:
    return json.dumps(vec.astype(float).tolist(), separators=(",", ":"))


def sync_missing_report_embeddings(batch_size: int = 100) -> int:
    pending = get_reports_without_embeddings(limit=batch_size)
    upserted = 0
    for row in pending:
        report_id = int(row["id"])
        text = _report_text(row.get("feel_label", ""), row.get("note_text", ""))
        vec = _embed_text(text)
        upsert_report_embedding(
            report_id=report_id,
            vector_json=_vec_to_json(vec),
            model_name=DEFAULT_EMBED_MODEL,
        )
        upserted += 1
    return upserted


def retrieve_city_reports(
    city: str,
    query: str,
    k: int = 4,
    max_age_days: int = 30,
    min_score: float = 0.1,
) -> list[dict[str, Any]]:
    city_name = (city or "").strip()
    question = (query or "").strip()
    if not city_name or not question:
        return []

    try:
        sync_missing_report_embeddings(batch_size=150)
        rows = list_embedded_reports_by_city(city=city_name, max_age_days=max_age_days, limit=300)
        if not rows:
            return []

        q_vec = _embed_text(question)
        results: list[dict[str, Any]] = []
        for row in rows:
            row_vec = _json_to_vec(row.get("vector_json", ""))
            if row_vec is None or row_vec.shape != q_vec.shape:
                continue
            score = float(np.dot(q_vec, row_vec))
            if score < float(min_score):
                continue
            note_text = (row.get("note_text") or "").strip()
            snippet = note_text if note_text else f"Community marked it as {row.get('feel_label', 'reported')}."
            if len(snippet) > 240:
                snippet = f"{snippet[:237]}..."
            results.append(
                {
                    "id": row["id"],
                    "city": row["city"],
                    "feel": row.get("feel_label") or "",
                    "note": note_text,
                    "snippet": snippet,
                    "created_at": row.get("created_at") or "",
                    "score": round(score, 4),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[: max(1, min(10, int(k or 4)))]
    except Exception:
        logger.exception("City report retrieval failed")
        return []
