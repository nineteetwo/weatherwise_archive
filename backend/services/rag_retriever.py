"""
Lightweight RAG (Retrieval-Augmented Generation) for WeatherWise.

RAG means: given a user query, retrieve relevant context from a
knowledge base, then pass that context to the LLM to ground its output.

Here we use pandas filtering instead of a vector database because:
- Our dataset is structured and tabular (not unstructured text)
- Filtering by season + temperature + condition is more precise than embeddings
- No additional dependencies or infrastructure needed
- Fast enough for real-time inference

The retrieved context is injected into the LLM prompt so tips are
grounded in real historical patterns, not just LLM intuition.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_df: pd.DataFrame | None = None
_LOAD_ERROR: str | None = None

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CSV_CANDIDATES = (
    _REPO_ROOT / "ml" / "data" / "raw" / "hourly_observations.csv",
    _REPO_ROOT / "ml" / "data" / "hourly_observations.csv",
)


def _load_hourly_frame() -> None:
    global _df, _LOAD_ERROR
    if _df is not None or _LOAD_ERROR is not None:
        return
    for path in _CSV_CANDIDATES:
        if not path.exists():
            continue
        try:
            _df = pd.read_csv(path)
            logger.info("RAG retriever loaded historical dataset from %s", path)
            return
        except Exception as e:
            logger.warning("RAG retriever could not read %s: %s", path, e)
    _LOAD_ERROR = "no_csv"
    logger.warning(
        "RAG retriever: could not load hourly observations from %s or %s — RAG disabled",
        _CSV_CANDIDATES[0],
        _CSV_CANDIDATES[1],
    )
    _df = None


_load_hourly_frame()


def _umbrella_as_int(series: pd.Series) -> pd.Series:
    s = series
    if s.dtype == bool:
        return s.astype(int)
    return (pd.to_numeric(s, errors="coerce").fillna(0).astype(int)).clip(0, 1)


def retrieve_similar_conditions(current_features: dict, top_n: int = 3) -> str | None:
    """
    Given current normalized weather features, find similar historical rows
    and return a short context string for the LLM, or None if unavailable.

    top_n is reserved for future use (e.g. limiting exemplars); aggregation
    uses all rows that pass the filter chain.
    """
    _ = top_n
    try:
        if _df is None or _df.empty:
            return None

        required = (
            "season",
            "temperature_c",
            "weather_condition",
            "wind_speed_kmh",
            "outdoor_suitability_score",
            "clothing_recommendation",
            "umbrella_needed",
        )
        missing = [c for c in required if c not in _df.columns]
        if missing:
            logger.warning("RAG retriever: dataset missing columns %s", missing)
            return None

        season = int(current_features.get("season", 0))
        temp = float(current_features.get("temperature_c", 0.0))
        weather_condition = current_features.get("weather_condition", "")
        wind = float(current_features.get("wind_speed_kmh", 0.0))

        base = _df
        season_s = pd.to_numeric(base["season"], errors="coerce").fillna(-999).astype(int)
        temp_s = pd.to_numeric(base["temperature_c"], errors="coerce")
        wind_s = pd.to_numeric(base["wind_speed_kmh"], errors="coerce")

        m0 = season_s == season
        subset = base.loc[m0]
        if len(subset) < 5:
            return None

        # Progressive filters: apply next filter only if it still leaves >= 5 rows.
        m = m0
        m_temp = m & (temp_s.sub(temp).abs() <= 3)
        if m_temp.sum() >= 5:
            m = m_temp
            subset = base.loc[m]

        m_cond = m & (base["weather_condition"] == weather_condition)
        if m_cond.sum() >= 5:
            m = m_cond
            subset = base.loc[m]

        m_wind = m & (wind_s.sub(wind).abs() <= 10)
        if m_wind.sum() >= 5:
            m = m_wind
            subset = base.loc[m]

        if len(subset) < 5:
            return None

        avg_suitability = round(float(subset["outdoor_suitability_score"].mean()), 1)
        common_clothing = str(subset["clothing_recommendation"].value_counts().idxmax())
        common_clothing = common_clothing.replace("_", " ")

        u = _umbrella_as_int(subset["umbrella_needed"])
        umbrella_pct = int(round(100.0 * float(u.mean())))

        common_condition = str(subset["weather_condition"].value_counts().idxmax())

        temp_label = int(round(temp))

        return (
            f"Historical context: On similar days this season ({common_condition}, ~{temp_label}°C):\n"
            f"- Average comfort score was {avg_suitability}/10\n"
            f"- Most common clothing was {common_clothing}\n"
            f"- Umbrella was needed {umbrella_pct}% of the time"
        )
    except Exception:
        logger.exception("RAG retriever: retrieve_similar_conditions failed")
        return None
