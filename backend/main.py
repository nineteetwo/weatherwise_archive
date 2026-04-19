import sys
from pathlib import Path

_here = Path(__file__).parent.resolve()
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_here.parent))

from dotenv import load_dotenv

load_dotenv(_here / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from rag.chat import router as chat_router
from rag.feed import router as feed_router
from rag.recommend import router as rec_router
from routers.auth import router as auth_router
from routers.report import router as report_router
from services.predictor import predictor
from db import init_db

app = FastAPI(title="WeatherWise API", version="2.0.0")

_WEB_DIR = _here.parent / "frontend" / "web"

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


app.include_router(rec_router)
app.include_router(chat_router)
app.include_router(feed_router)
app.include_router(auth_router)
app.include_router(report_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_active": predictor.is_loaded,
        "mode": "ml" if predictor.is_loaded else "fallback",
    }


@app.get("/")
async def root():
    return RedirectResponse(url="/landing.html", status_code=302)


if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
else:
    alt_path = _here.parent / "frontend"
    if alt_path.is_dir():
        app.mount("/", StaticFiles(directory=str(alt_path), html=True), name="web")
    else:
        print(f"⚠️ Warning: Frontend directory not found at {_WEB_DIR}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
