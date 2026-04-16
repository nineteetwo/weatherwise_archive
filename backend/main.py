from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.recommend import router as rec_router
from services.predictor import predictor

app = FastAPI(title="WeatherWise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_credentials=False,  
    allow_headers=["*"],
)

app.include_router(rec_router)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models_active": predictor.is_loaded,
        "mode": "ml" if predictor.is_loaded else "fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)