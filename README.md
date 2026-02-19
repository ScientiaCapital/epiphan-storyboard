# Epiphan Storyboard

**AI-powered storyboard generator for Epiphan Video sales and marketing**

Owner: THK Enterprises LLC

---

Transforms code, transcripts, and screenshots into executive-ready visual storyboards using NANO BANANA (Gemini Flash Image Preview). Built for Epiphan Video BDRs, AV integrators, and sales teams who need polished one-page visuals — fast.

## What It Does

- Ingests code files, roadmap screenshots, or call transcripts
- Extracts business value and sanitizes technical IP
- Generates beautiful one-page PNG storyboards tailored to AV industry personas
- Supports three BDR cadence stages: Preview, Demo, Shipped
- Personas: AV Integrator, IT Director, CTO, Reseller, BDR

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.13 |
| API Framework | FastAPI |
| Image Generation | Gemini Flash (Image Preview) — NANO BANANA |
| Vision/LLM | Gemini 2.0 Flash + Qwen 2.5 VL 72B via OpenRouter |
| Database | Supabase (Postgres + Storage) |
| Cache | Redis |
| Billing | Stripe |
| Deployment | Vercel |

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Fill in GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, REDIS_URL

# Run dev server
uvicorn src.api:app --reload

# Run tests
python -m pytest tests/ -v

# Type check
python -m mypy src/ --ignore-missing-imports

# Lint / Format
ruff check src/
ruff format src/
```

## API Endpoints

### Storyboard Generation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/storyboard/code` | Generate storyboard from code file |
| `POST` | `/storyboard/roadmap` | Generate teaser from roadmap screenshot |
| `POST` | `/storyboard/unified` | Unified endpoint (code or image input) |

### Agent Orchestration

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agents/run` | Start agent execution |
| `GET` | `/agents/{session_id}` | Poll session status |
| `POST` | `/agents/{session_id}/cancel` | Cancel running session |
| `POST` | `/agents/route` | Auto-classify and route task to chain |
| `GET` | `/agents/route/{job_id}` | Poll router job status |
| `GET` | `/agents/route/chains` | List available chains |

### Billing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/billing/checkout` | Create Stripe Checkout session |
| `GET` | `/billing/subscription` | Get subscription status |
| `POST` | `/billing/portal` | Create Customer Portal session |
| `POST` | `/billing/webhooks/stripe` | Handle Stripe webhooks |

### Utilities

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tools` | List available tools |
| `GET` | `/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/storyboard/code \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "def calculate_roi(): ...",
    "file_name": "calculator.py",
    "icp_preset": "epiphan_av",
    "stage": "preview",
    "audience": "it_director"
  }'
```

## Architecture

```
src/
├── api.py                          # FastAPI app entry point
├── agents/                         # Agent runner + schemas
├── billing/                        # Stripe billing integration
├── connectors/                     # Data connectors (Gong, Fireflies, Close)
├── demo/                           # Demo router
├── knowledge/                      # Knowledge brain (learning pipeline)
│   ├── base.py                     # Base classes
│   ├── cache.py                    # In-memory knowledge cache
│   ├── close_crm.py                # Close CRM connector
│   └── service.py                  # Knowledge service
├── router/                         # Agent classifier + chain execution
│   ├── chains.py                   # Chain definitions
│   └── classifier.py               # Intent classifier
├── routers/                        # FastAPI routers
│   └── connectors.py               # Connector endpoints
├── storyboard/                     # Storyboard API layer
│   ├── router.py                   # Storyboard endpoints
│   └── schemas.py                  # Request/response models
└── tools/
    ├── base.py                     # BaseTool + ToolResult
    ├── registry.py                 # Tool registry
    └── storyboard/                 # Core storyboard pipeline
        ├── epiphan_presets.py      # ICP presets and personas
        ├── gemini_client.py        # Gemini vision + image gen client
        ├── code_to_storyboard.py   # Code -> storyboard tool
        ├── roadmap_to_storyboard.py # Screenshot -> teaser tool
        ├── unified_storyboard.py   # Unified tool
        └── storage.py              # Supabase storage
```

## Environment Variables

```bash
# Supabase (required for persistence)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Redis (required for job state)
REDIS_URL=redis://localhost:6379

# LLM Providers (NO OpenAI)
ANTHROPIC_API_KEY=sk-ant-...        # Claude models
GOOGLE_API_KEY=AIza...              # Gemini Flash (image generation)
OPENROUTER_API_KEY=sk-or-...        # Qwen/DeepSeek vision via OpenRouter

# Stripe Billing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_BASIC=price_...
STRIPE_PRICE_ID_PRO=price_...

# Data Ingestion (optional)
CLOSE_API_KEY=...                   # Close CRM calls/notes
LOOM_API_KEY=...                    # Video analytics

# App Config
APP_ENV=development
API_URL=http://localhost:8000
```

## Epiphan Ecosystem

This tool is part of the Epiphan Video sales and marketing automation stack:

- **epiphan-storyboard** (this repo) — AI storyboard generator
- **epiphan-sales-agent** — Outbound sales automation
- **epiphan-linkedin-engine** — LinkedIn content and outreach engine

Repository: [https://github.com/ScientiaCapital/epiphan-storyboard](https://github.com/ScientiaCapital/epiphan-storyboard)

## Epiphan Products Covered

- **Pearl Mini** — All-in-one video encoder, recorder, and streamer
- **Pearl Nano** — Ultra-compact live production system
- **Pearl Nexus** — Cloud-managed video gateway
- **Epiphan Connect (EC20 PTZ)** — PoE-powered PTZ camera
- **Webcaster X2** — Simple live streaming encoder

## License

MIT — Copyright (c) 2025 THK Enterprises LLC
