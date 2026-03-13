# Coding Rules — epiphan-storyboard

## Stack
Python 3.13+, FastAPI, Pydantic v2, async/await

## Rules
- No OpenAI — use Anthropic Claude or Google Gemini only
- API keys in .env only, never hardcode
- Type hints required on all functions; use `-> ReturnType`
- Pydantic v2 for all request/response schemas
- FastAPI routers in src/routers/; one router per domain
- async/await throughout — no blocking I/O
- All storyboard content must reference Epiphan products via epiphan_presets.py
- ruff for linting and formatting; mypy for type checking
