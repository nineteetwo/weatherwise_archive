from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from routers.recommend import router as rec_router
from services.predictor import predictor
from routers.chat import router as chat_router

app = FastAPI(title="WeatherWise API")

_WEB_DIR = Path(__file__).resolve().parent.parent / "frontend" / "web"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rec_router)
app.include_router(chat_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_active": predictor.is_loaded,
        "mode": "ml" if predictor.is_loaded else "fallback"
    }


@app.get("/")
async def root():
    return RedirectResponse(url="/landing.html", status_code=302)


if _WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)