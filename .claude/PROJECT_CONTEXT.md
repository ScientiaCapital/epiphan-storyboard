# epiphan-storyboard

**Branch**: main | **Updated**: 2026-02-19

## Status
Phase 11.0 complete. Stripe billing infrastructure implemented with:
- Full Stripe SDK integration (checkout, portal, subscriptions, webhooks)
- 4-tier pricing system (Free/Basic/Pro/Enterprise) with quota enforcement
- Billing middleware for protecting storyboard and router endpoints
- 73 billing tests + 41 router tests = 114 tests passing
- mypy clean, ruff clean

## Today's Accomplishments
### Phase 11: Monetization Infrastructure
1. **Billing Module** - `src/billing/` with Stripe SDK wrapper
2. **SubscriptionService** - Webhook handlers, tier management
3. **Billing Middleware** - `require_billing()`, `require_tier()`, `require_quota()`
4. **API Endpoints** - POST /billing/checkout, GET /subscription, POST /portal, webhooks
5. **Database Migration** - sql/006_billing.sql
6. **Endpoint Protection** - Storyboard + Router hooked to billing/quotas

### Phase 10: Agent Router (Previous Session)
- 3-stage task classification (pattern -> keyword -> LLM fallback)
- 6 pre-built chains (storyboard, video, scrape, code_run, knowledge, sql)
- FastAPI endpoints for auto-classify and route
- Redis + Supabase hybrid state management

## API Keys Status
| Key | Status |
|-----|--------|
| SUPABASE_* | Set |
| ANTHROPIC_API_KEY | Set |
| GOOGLE_API_KEY | Set |
| OPENROUTER_API_KEY | Set |
| STRIPE_SECRET_KEY | Set (test mode) |
| CARTESIA_API_KEY | Missing |
| BROWSERBASE_* | Missing |
| RUNWAY_API_KEY | Missing |
| CLOSE_API_KEY | Missing |

## OpenRouter Model IDs (2025)
```
google/gemini-2.5-flash              # Main workhorse
google/gemini-2.5-flash-image-preview # NANO BANANA (storyboards)
google/gemini-2.0-flash-exp:free     # FREE tier
deepseek/deepseek-chat-v3            # Best value flagship
deepseek/deepseek-r1                 # Deep reasoning
qwen/qwen-2.5-coder-32b-instruct     # Best coder
```

## Quick Commands
```bash
python3 -m pytest tests/billing/ -v  # Billing tests (73 passing)
python3 -m pytest tests/router/ -v   # Router tests (41 passing)
python3 -m pytest tests/ -v          # All tests
python3 -m mypy src/billing/ --ignore-missing-imports
uvicorn src.api:app --reload --port 8000
```

## API Endpoints
### Billing
- `POST /billing/checkout` - Create Stripe Checkout session
- `GET /billing/subscription` - Get subscription status
- `POST /billing/portal` - Create Customer Portal session
- `POST /billing/webhooks/stripe` - Handle Stripe events
- `GET /billing/health` - Billing health check

### Router
- `POST /agents/route` - Auto-classify and route task (402/429 protected)
- `GET /agents/route/{job_id}` - Poll job status
- `GET /agents/route/chains` - List available chains

## Pricing Tiers
| Tier | Price | Hourly | Daily | Monthly |
|------|-------|--------|-------|---------|
| Free | $0 | 1K tokens | 10K | 100K |
| Basic | $49/mo | 5K | 50K | 500K |
| Pro | $199/mo | 50K | 500K | 5M |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited |

## Tech Stack
Python 3.13 | FastAPI | Stripe | Supabase | Redis | DeepSeek V3 | Qwen 2.5 | Gemini 2.0

## Blockers
**User Action Required**: Create Stripe products in Dashboard
- Basic product ($49/mo) -> Add `STRIPE_PRICE_ID_BASIC` to .env
- Pro product ($199/mo) -> Add `STRIPE_PRICE_ID_PRO` to .env

## Tomorrow Start
Phase 12: Auto Demo Video Pipeline - Scene extraction and individual assets
