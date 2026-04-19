# WeatherWise Decisions

## Locked Product Scope
- **Checkpoints (historical delivery framing):**
  - **Checkpoint 1** (delivered, e.g. April 16): train three ML models, expose `GET /recommend`, ship a minimal web UI.
  - **Checkpoint 2** (in progress / next): LLM integration, feed/context loop, chatbot-style “Should I?”, deployment hardening; some pieces exist in code but are not all wired end-to-end yet.
- Do not expand into optional mobile/iOS scope unless core web MVP is stable.

## ML Pipeline Decisions
- Keep scikit-learn based predictors as the structured decision core:
  - `umbrella_needed` (classification, F1)
  - `clothing_recommendation` (classification, accuracy + macro-F1)
  - `outdoor_suitability_score` (regression, MAE)
- Keep temporal split (`70/15/15`) for all model training scripts.
- Training scripts are standardized in:
  - `ml/src/train_umbrella.py`
  - `ml/src/train_clothing.py`
  - `ml/src/train_suitability.py`
- Shared trainer utilities live in `ml/src/base_trainer.py`.

## LLM and RAG Decisions
- **LLM runtime:** local **Ollama** instance with model **`PhanarAi`** (LangChain `ChatOllama` in `backend/services/llm.py`). YandexGPT was discussed earlier but is **not** wired into this codebase.
- **LLM role:** convert structured outputs into concise, user-friendly advice.
- **RAG (implemented):** `backend/services/rag_retriever.py` loads historical tabular data (CSV under `ml/data/…`) and uses **pandas filtering** (season, temperature band, condition, wind) to build a short context string for the LLM — **not** a vector-database embedding pipeline; still “structured retrieval,” but it is live code, not a future placeholder.
- Keep fallback generation path when LLM is unavailable (rule-based response path required).

## Weather Provider Decision
- External weather API is required for live inference.
- Provider locked for current implementation path: Open-Meteo (kanban and backend plan alignment).
- If provider changes later, backend normalizer must preserve model feature schema and units.

## Auth and Identity
- **Storage:** SQLite (`backend/users.db` via `backend/db.py`).
- **Passwords:** PBKDF2-HMAC-SHA256 (stdlib `hashlib`), no bcrypt dependency.
- **Sessions API:** JWT access tokens (`python-jose`), **7-day** expiry, HS256 (`backend/services/auth_service.py`, `backend/routers/auth.py`).

## Frontend Stack
- **Vanilla** HTML, CSS, and JavaScript — no React or SPA framework; static assets served from `frontend/web/` (often same FastAPI host as the API).

## Branding
- Repository and API name remain **WeatherWise**; **user-facing UI** uses the **PhanarAi** brand (titles, landing, home).

## Community Reports
- **Planned behavior:** signed-in users submit feedback via **`POST /report`** (colder / accurate / warmer vs model advice), with optional notes and rate limiting in `backend/routers/report.py`.
- **Status:** contract and router code exist; endpoint is **not yet mounted** in `backend/main.py` and needs DB support aligned with that router before production use.

## Deployment
- **Target:** hackathon-provided VM (not AWS-first); tune env secrets (`SECRET_KEY`, Ollama host, etc.) for that environment.

## Integration Rules
- Backend must normalize API payloads into model feature schema order before inference.
- If required API fields are missing, return safe defaults/fallback and never crash.
- Preserve short, plain-language responses (no technical jargon in user-facing tips).

## Source of Truth
- Architecture/process decisions: `DECISIONS.md` (this file).
- API request/response contracts: `API_CONTRACT.md`.
- Execution/task ownership and sequencing: GitHub Project cards with `depends on` and `unlocks`.
