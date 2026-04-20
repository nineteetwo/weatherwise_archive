import time
from collections import defaultdict, deque

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from db import create_community_report, get_user_by_id, list_community_reports
from services.auth_service import decode_token

router = APIRouter(prefix="/community", tags=["community"])

VALID_FEELS = {"colder", "accurate", "warmer"}
MAX_NOTE_LENGTH = 280
MAX_SUBMITS_PER_WINDOW = 8
RATE_WINDOW_SECONDS = 60
_submit_buckets: dict[str, deque[float]] = defaultdict(deque)


class CommunityReportCreate(BaseModel):
    city: str
    feel: str
    note: str = ""


def _parse_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    if user_id <= 0:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def _enforce_submit_rate_limit(scope_key: str) -> None:
    now = time.time()
    bucket = _submit_buckets[scope_key]
    while bucket and (now - bucket[0]) > RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= MAX_SUBMITS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many reports, please try again soon")
    bucket.append(now)


@router.post("/reports")
async def create_report(req: CommunityReportCreate, authorization: str = Header(None)):
    user_id = _parse_user_id(authorization)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    city = (req.city or "").strip()
    feel = (req.feel or "").strip().lower()
    note = (req.note or "").strip()
    if not city:
        raise HTTPException(status_code=400, detail="City is required")
    if feel not in VALID_FEELS:
        raise HTTPException(status_code=400, detail="Invalid feel value")
    if len(note) > MAX_NOTE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Note is too long (max {MAX_NOTE_LENGTH} chars)")

    _enforce_submit_rate_limit(f"user:{user_id}")

    created = create_community_report(
        user_id=user_id,
        city=city,
        feel_label=feel,
        note_text=note,
    )
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create report")

    return {
        "id": created["id"],
        "city": created["city"],
        "feel": created["feel_label"],
        "note": created["note_text"],
        "created_at": created["created_at"],
        "user_name": created.get("user_name") or user.get("name") or "User",
    }


@router.get("/reports")
async def get_reports(
    city: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    city_value = (city or "").strip()
    if not city_value:
        raise HTTPException(status_code=400, detail="City is required")

    items = list_community_reports(city=city_value, limit=limit, offset=offset)
    return {
        "city": city_value,
        "count": len(items),
        "items": [
            {
                "id": item["id"],
                "city": item["city"],
                "feel": item["feel_label"],
                "note": item["note_text"],
                "created_at": item["created_at"],
                "user_name": item.get("user_name") or "User",
            }
            for item in items
        ],
    }
