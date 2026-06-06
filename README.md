# WeatherWise

WeatherWise is a machine-learning-powered weather advisory application built for the yaHack hackathon. It provides structured, actionable recommendations (like clothing advice, umbrella necessity, and outdoor suitability scores) and uses a local LLM to generate user-friendly, conversational advice.

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

*(Further setup instructions for backend, frontend, and ML training pipelines to be added.)*
