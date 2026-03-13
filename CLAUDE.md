# Epiphan Storyboard

## Identity
- Epiphan Video storyboard and content generation platform
- Owner: THK Enterprises LLC
- Deployed on Vercel

## Dev Commands
- `uvicorn src.api:app --reload` — Run dev server
- `python -m pytest tests/ -v` — Run tests
- `python -m mypy src/ --ignore-missing-imports` — Type check
- `ruff check src/` — Lint
- `ruff format src/` — Format

## Code Conventions
- Python 3.11+, async/await throughout
- Pydantic v2 for all schemas
- Type hints required on all functions
- FastAPI routers in src/routers/
- Agent logic in src/router/ (classifier + chains)
- Tools in src/tools/ (storyboard, recording, video)

## Key Architecture
- src/api.py — FastAPI app entry point
- src/tools/storyboard/ — Storyboard generation (Gemini Flash)
- src/tools/storyboard/epiphan_presets.py — ICP presets and personas
- src/router/ — Agent router (classification + chain execution)
- src/knowledge/ — Knowledge brain (learning pipeline)
- src/connectors/ — Data connectors (Gong, Fireflies, Close, etc.)
- src/storyboard/ — Storyboard state, schemas, router

## Epiphan Context
- Products: Pearl Mini ($3,750), Pearl Nano ($1,999), Pearl Nexus ($3,299), Pearl-2 ($7,999), EC20 PTZ ($1,899), AV.io 4K ($579.95), AV.io HD+ ($449.95), AV.io SDI+ ($579.95)
- Verticals (10): Higher Ed, Corporate, Live Events, Government, Houses of Worship, Healthcare, Industrial, Legal, UX Research, K-12
- Personas (8 BDR Playbook):
  - ATL Decision Makers (7): AV Director, L&D Director, Sim Center Director, Court Admin, Corp Comms, EHS Manager, Law Firm IT
  - BTL Operators (1): Technical Director
- Default persona: av_director (most common buyer across verticals)

## Rules
- NO OpenAI — use Anthropic, Google Gemini, or OpenRouter only
- All content must reference Epiphan products only
- All storyboard content must use epiphan_presets.py ICP
