from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from services.auth_service import hash_password, verify_password, create_access_token, decode_token
from db import create_user, get_user_by_email, get_user_by_id, update_user_country_city

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Request Modelleri ───────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    str
    password: str
    country:  str = ""
    city:     str = ""


class LoginRequest(BaseModel):
    email:    str
    password: str


class UpdateProfileRequest(BaseModel):
    country: str = ""
    city:    str = ""


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/register", summary="Yeni kullanıcı kaydı")
async def register(req: RegisterRequest):
    name  = req.name.strip()
    email = req.email.strip().lower()

    if not name or not email or not req.password:
        raise HTTPException(status_code=400, detail="All fields are required")

    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(req.password)
    user   = create_user(name, email, hashed, req.country, req.city)

    if not user:
        raise HTTPException(status_code=500, detail="Registration failed")

    token = create_access_token({"sub": str(user["id"]), "name": user["name"]})
    return {
        "token":   token,
        "name":    user["name"],
        "email":   user["email"],
        "country": user["country"],
        "city":    user["city"],
    }


@router.post("/login", summary="Kullanıcı girişi")
async def login(req: LoginRequest):
    email = req.email.strip().lower()
    user  = get_user_by_email(email)

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user["id"]), "name": user["name"]})
    return {
        "token":   token,
        "name":    user["name"],
        "email":   user["email"],
        "country": user["country"],
        "city":    user["city"],
    }


@router.patch("/profile", summary="Update signed-in user country and city")
async def update_profile(req: UpdateProfileRequest, authorization: str = Header(None)):
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

    country = (req.country or "").strip()
    city = (req.city or "").strip()
    if not city:
        raise HTTPException(status_code=400, detail="City is required")

    updated = update_user_country_city(user_id, country, city)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")

    return {
        "id": updated["id"],
        "name": updated["name"],
        "email": updated["email"],
        "country": updated["country"],
        "city": updated["city"],
    }


@router.get("/me", summary="Giriş yapan kullanıcı bilgisi")
async def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token   = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    user    = get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id":      user["id"],
        "name":    user["name"],
        "email":   user["email"],
        "country": user["country"],
        "city":    user["city"],
    }
