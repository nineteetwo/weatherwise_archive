# WeatherWise

WeatherWise is a full-stack weather advisory and chat application developed for the Yandex Anadolu hackathon. It combines real-time weather data with machine learning predictions and a conversational AI to provide personalized outdoor recommendations.

## Features

- **FastAPI Backend:** Serves the REST API (`/recommend`, `/chat`, `/auth`) and dynamically mounts the static web frontend.
- **Machine Learning Models:** Utilizes pre-trained scikit-learn models to analyze current weather conditions and predict:
  - `umbrella_needed` (Classification)
  - `clothing_recommendation` (Classification)
  - `outdoor_suitability_score` (Regression)
- **Contextual LLM Chat:** The `/chat` endpoint fetches real-time data from the Open-Meteo API, merges it with ML predictions, and uses a local YandexGPT runtime to generate natural, personalized advice.
- **User Authentication:** Integrated SQLite database for user registration and session management.
- **Static Web UI:** A lightweight, dependency-free frontend built with vanilla HTML, CSS (Tailwind), and JavaScript. Includes landing, dashboard, and interactive chat pages.

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, SQLite
- **Machine Learning:** Scikit-learn, Pandas
- **Frontend:** Vanilla HTML, CSS, JS
- **Integrations:** Open-Meteo API, YandexGPT

## Getting Started

1. **Backend & API Setup:**
   Navigate to the backend directory and configure your Python environment.
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate
   # Linux/Mac: source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. **Run the Application:**
   Start the FastAPI server. It will automatically serve the frontend static files.
   ```bash
   uvicorn main:app --reload --port 8000
   ```

3. **Access the App:**
   Open your browser and navigate to `http://127.0.0.1:8000/` to access the WeatherWise platform.
