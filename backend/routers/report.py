import time
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from db import get_user_by_id, insert_condition_report
from services.auth_service import decode_token
from services.weather import fetch_current_weather, resolve_city

router = APIRouter(tags=["report"])

RatingChoice = Literal["colder", "accurate", "warmer"]

_REPORT_LIMIT = 60
_REPORT_WINDOW_SEC = 3600
_report_times: dict[int, list[float]] = defaultdict(list)


def _enforce_report_rate_limit(user_id: int) -> None:
    now = time.monotonic()
    window_start = now - _REPORT_WINDOW_SEC
    times = _report_times[user_id]
    while times and times[0] < window_start:
        times.pop(0)
    if len(times) >= _REPORT_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many reports; try again later.",
        )
    times.append(now)


class ReportBody(BaseModel):
    city: str
    rating: RatingChoice
    note: str | None = Field(default=None, max_length=500)


@router.post("/report")
async def create_report(
    body: ReportBody,
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    city_in = body.city.strip()
    if not city_in:
        raise HTTPException(status_code=400, detail="City name cannot be empty")

    _enforce_report_rate_limit(user_id)

    loc = await resolve_city(city_in)
    weather = fetch_current_weather(city_in, resolved_location=loc)
    cr = weather["current_raw"]

    row = insert_condition_report(
        user_id,
        place_id=loc.get("place_id"),
        canonical_city=loc["name"],
        latitude=float(loc["latitude"]),
        longitude=float(loc["longitude"]),
        rating=body.rating,
        note=body.note,
        temp_c=cr.get("temperature_2m"),
        apparent_temp_c=cr.get("apparent_temperature"),
        weather_code=cr.get("weather_code"),
        precipitation_mm=cr.get("precipitation"),
        relative_humidity=cr.get("relative_humidity_2m"),
        wind_speed_10m=cr.get("wind_speed_10m"),
        snapshot={
            "location": weather["location"],
            "country": weather["country"],
            "current": cr,
        },
    )
    if not row:
        raise HTTPException(status_code=400, detail="Invalid report payload")

    return {
        "success": True,
        "id": row["id"],
        "city": loc["name"],
        "country": loc["country"],
    }
