"""
clothing_ux_policy.py
---------------------
Presentation-layer helpers for clothing recommendations.

The sklearn model still predicts a single best class, but the UX layer can:
- surface a second close alternative when confidence is low / ambiguous
- add a short, non-technical layering note when conditions suggest layering helps

This module is intentionally dependency-free (stdlib only) so backend code can
import it without pulling ML training utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


def _fmt_label(label: str) -> str:
    return label.replace("_", " ").strip()


def _lower(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip().lower()


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _is_wet(weather: dict[str, Any] | None) -> bool:
    if not weather:
        return False
    precip = _to_float(weather.get("precipitation_mm"))
    if precip is not None and precip > 0.05:
        return True
    ptype = _lower(weather.get("precipitation_type"))
    if ptype and ptype not in {"none", "dry"}:
        return True
    cond = _lower(weather.get("weather_condition"))
    return any(k in cond for k in ("rain", "drizzle", "storm", "thunder", "snow", "sleet"))


def _is_cold(temp_c: float | None, threshold_c: float = 12.0) -> bool:
    return temp_c is not None and temp_c <= threshold_c


def _warmth_bucket(label: str) -> str:
    lab = label.lower()
    if any(
        k in lab
        for k in (
            "winter",
            "heavy",
            "warm_jacket",
            "coat",
            "gloves",
            "scarf",
            "layers",
        )
    ):
        return "warm"
    if any(k in lab for k in ("jacket", "sweater", "long_sleeves")):
        return "mid"
    return "light"


@dataclass(frozen=True)
class ClothingUxResult:
    primary: str
    secondary: str | None
    primary_probability: float
    secondary_probability: float | None
    margin: float | None
    show_secondary: bool
    layering_note: str | None
    flags: tuple[str, ...]


def clothing_ux_from_proba(
    *,
    classes: Iterable[str],
    proba_row: Iterable[float],
    weather: dict[str, Any] | None = None,
    tau: float = 0.62,
    margin: float = 0.12,
    cold_threshold_c: float = 12.0,
) -> ClothingUxResult:
    """
    Build UX-friendly clothing output from a single row of predict_proba output.

    Args:
        classes: clf.classes_ ordering must match proba_row ordering.
        proba_row: iterable of probabilities for each class (sums ~ 1).
        weather: optional dict with keys like temperature_c, precipitation_mm,
            precipitation_type, weather_condition (as in hourly_observations.csv).
        tau: if top probability < tau, show secondary suggestion.
        margin: if top - second < margin, show secondary suggestion.
        cold_threshold_c: used with wetness to recommend layering guidance.
    """
    cls_list = [str(c) for c in classes]
    probs = [float(p) for p in proba_row]
    if len(cls_list) != len(probs):
        raise ValueError("classes and proba_row must have the same length")

    ranked = sorted(zip(cls_list, probs), key=lambda t: t[1], reverse=True)
    top_lab, top_p = ranked[0]
    second_lab, second_p = ranked[1] if len(ranked) > 1 else (None, None)

    m = None
    if second_lab is not None:
        m = top_p - second_p

    temp_c = _to_float(weather.get("temperature_c")) if weather else None
    wet = _is_wet(weather)
    cold = _is_cold(temp_c, threshold_c=cold_threshold_c)

    flags: list[str] = []
    if top_p < tau:
        flags.append("low_top_probability")
    if m is not None and m < margin:
        flags.append("small_top_second_margin")
    if cold and wet:
        flags.append("cold_and_wet")

    show_secondary = False
    if second_lab is not None and second_p is not None:
        if top_p < tau or (m is not None and m < margin):
            show_secondary = True

        # If it's cold+wet and the model's top pick is a very light outfit, show a
        # warmer alternative if one exists among the top few ranked classes.
        if cold and wet and _warmth_bucket(top_lab) == "light":
            for lab, p in ranked[1:6]:
                if p >= 0.12 and _warmth_bucket(lab) in {"mid", "warm"}:
                    second_lab, second_p = lab, p
                    show_secondary = True
                    flags.append("cold_wet_light_top_override_second")
                    break

    layering_note = None
    if show_secondary or (cold and wet):
        layering_note = (
            "If you run warm or cold easily, bring a layer you can add or remove."
        )

    return ClothingUxResult(
        primary=top_lab,
        secondary=second_lab if show_secondary else None,
        primary_probability=top_p,
        secondary_probability=second_p if show_secondary else None,
        margin=m,
        show_secondary=bool(show_secondary),
        layering_note=layering_note,
        flags=tuple(flags),
    )


def clothing_ux_to_payload(ux: ClothingUxResult) -> dict[str, Any]:
    """JSON-serializable dict suitable for API responses."""
    return {
        "clothing_primary": ux.primary,
        "clothing_primary_display": _fmt_label(ux.primary),
        "clothing_secondary": ux.secondary,
        "clothing_secondary_display": _fmt_label(ux.secondary) if ux.secondary else None,
        "clothing_primary_probability": ux.primary_probability,
        "clothing_secondary_probability": ux.secondary_probability,
        "clothing_probability_margin": ux.margin,
        "clothing_show_secondary": ux.show_secondary,
        "clothing_layering_note": ux.layering_note,
        "clothing_ux_flags": list(ux.flags),
    }
