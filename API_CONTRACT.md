# API Contract

## Endpoints
- `GET /health`
- `GET /recommend?city=<city_name>`
- `GET /forecast?city=<city_name>` (CP2)
- `POST /report` (CP2)
- `GET /chat/should-i` or chatbot route equivalent (CP2)

## Request Format
- `GET /recommend`
  - query: `city` (required)
  - optional later context: language/persona/profile fields
- `POST /report`
  - body (JSON): city, user feedback/rating, optional activity and area

## Response Format
- `GET /recommend` response includes:
  - location and timestamp context
  - structured model outputs (`umbrella_needed`, `clothing_recommendation`, `outdoor_suitability_score`)
  - concise advice text for UI
- Error responses must always return valid JSON with `error` message.

## Tip Schema
- Tips must be:
  - short
  - non-technical
  - actionable
  - easy to read in one glance
