# WeatherWise

WeatherWise is a machine-learning-powered weather advisory application built for the Yandex Anadolu hackathon. It provides structured, actionable recommendations (like clothing advice, umbrella necessity, and outdoor suitability scores) and uses a local LLM to generate user-friendly, conversational advice.

## Core Features

- **ML-Based Recommendations:**
  - `umbrella_needed` (Classification)
  - `clothing_recommendation` (Classification)
  - `outdoor_suitability_score` (Regression)
- **Conversational AI Advisor:** Converts structured ML outputs into concise, personalized tips using a local YandexGPT runtime.
- **Live Weather Integration:** Fetches real-time weather data via the Open-Meteo API.
- **Lightweight RAG:** Provides structured retrieval (weather snapshot + model outputs + feed/user signals) to contextually ground the LLM responses.

## Project Structure

- `/frontend`: Minimal web UI and chatbot-based "Should I?" interface.
- `/backend`: Normalizes API payloads, handles inference requests (`GET /recommend`), and orchestrates the ML/LLM pipeline.
- `/ml`: Scikit-learn model training scripts (`train_umbrella.py`, `train_clothing.py`, `train_suitability.py`) and dataset processing.
- `/rag`: Lightweight structured retrieval and prompt construction logic.
- `/docs`: Additional project documentation.

## Documentation

For architectural and process decisions, please refer to [DECISIONS.md](DECISIONS.md).
For API request/response contracts, see [API_CONTRACT.md](API_CONTRACT.md).
Pending tasks and roadmap are tracked in [TODO.md](TODO.md).

## Getting Started

### 1. Backend Setup (API & Frontend Service)
The backend is built with FastAPI and also serves the frontend static files.

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your environment variables
uvicorn main:app --reload --port 8000
```

### 2. Frontend Access
Once the backend is running, the frontend is served automatically. 
Open your browser and navigate to: `http://127.0.0.1:8000/home.html`
*(Note: Do not open HTML files directly via `file://` as they require the API on the same origin).*

### 3. ML Pipeline Setup (Optional)
If you wish to retrain the machine learning models:

```bash
cd ml
pip install -r requirements.txt
python src/train_umbrella.py
python src/train_clothing.py
python src/train_suitability.py
```

## How It Works (Architecture Flow)

1. **User Request:** The user interacts with the minimal web UI or chatbot, asking a weather-related question or checking their dashboard.
2. **Data Aggregation:** The backend fetches real-time weather metrics (temperature, precipitation, wind speed, etc.) from the **Open-Meteo API**.
3. **ML Inference:** The aggregated data is fed into our pre-trained scikit-learn models to generate structured outputs (e.g., `umbrella_needed = True`, `suitability_score = 75`).
4. **Context Construction (RAG):** A lightweight structured context is built combining the weather snapshot, ML outputs, and user signals.
5. **LLM Generation:** The constructed context is processed by a local **YandexGPT** runtime to generate a concise, personalized, and jargon-free advisory response.
6. **Delivery:** The backend serves this final tip back to the user via the frontend.

## Tech Stack

- **Frontend:** Vanilla HTML/CSS/JS (Tailwind CSS)
- **Backend:** FastAPI, Python
- **Machine Learning:** Scikit-learn, Pandas
- **AI/LLM:** Local YandexGPT runtime, Lightweight RAG pattern
- **APIs:** Open-Meteo API

## Roadmap

**Checkpoint 1 (Completed MVP):**
- [x] Train 3 ML models (Umbrella, Clothing, Suitability)
- [x] Expose `GET /recommend` endpoint
- [x] Ship a minimal web UI

**Checkpoint 2:**
- [ ] Implement full LLM layer with YandexGPT
- [ ] Create feed/context loop for continuous improvement
- [ ] Build chatbot-based "Should I?" interaction
- [ ] Deployment hardening


