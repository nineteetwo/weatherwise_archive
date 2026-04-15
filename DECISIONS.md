# WeatherWise Decisions

## Locked Product Scope
- Checkpoint 1 focus: train 3 ML models, expose `GET /recommend`, and ship a minimal web UI.
- Checkpoint 2 focus: LLM layer, feed/context loop, chatbot-based "Should I?", and deployment hardening.
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
- Primary LLM direction: local YandexGPT runtime (team decision).
- LLM role: convert structured outputs into concise, user-friendly advice.
- RAG role: lightweight structured retrieval (weather snapshot + model outputs + feed/user signals), not vector-DB RAG for MVP.
- Keep fallback generation path when LLM is unavailable (rule-based response path required).

## Weather Provider Decision
- External weather API is required for live inference.
- Provider locked for current implementation path: Open-Meteo (kanban and backend plan alignment).
- If provider changes later, backend normalizer must preserve model feature schema and units.

## Integration Rules
- Backend must normalize API payloads into model feature schema order before inference.
- If required API fields are missing, return safe defaults/fallback and never crash.
- Preserve short, plain-language responses (no technical jargon in user-facing tips).

## Source of Truth
- Architecture/process decisions: `DECISIONS.md` (this file).
- API request/response contracts: `API_CONTRACT.md`.
- Execution/task ownership and sequencing: GitHub Project cards with `depends on` and `unlocks`.
