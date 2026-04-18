import sys
from pathlib import Path

_here = Path(__file__).parent.resolve()
# backend/ → services, routers, db importları çalışsın
sys.path.insert(0, str(_here))
# proje kökü → rag paketi import edilebilsin
sys.path.insert(0, str(_here.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# RAG routerları (rag/ klasöründen)
from rag.recommend import router as rec_router
from rag.chat import router as chat_router

# Auth router
from routers.auth import router as auth_router

# ML predictor (sağlık kontrolü için)
from services.predictor import predictor

# DB başlat
from db import init_db

app = FastAPI(title="WeatherWise API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()
    print("[WeatherWise] Database initialized.")


app.include_router(rec_router)
app.include_router(chat_router)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_active": predictor.is_loaded,
        "mode": "ml" if predictor.is_loaded else "fallback",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)