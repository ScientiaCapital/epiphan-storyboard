# epiphan-storyboard

**Branch**: main | **Updated**: 2026-02-19

## Status
Phase 11.5 complete. Test suite fully repaired after fork + God-class decomposition:
- 1341 tests passing, 22 skipped, 0 failures, 0 errors (was 1264 pass / 95 broken)
- 6 root causes diagnosed and fixed across 7 test files (zero source code changes)
- Security sweep: 0 secrets, 0 hardcoded credentials, 0 env issues
- Ready for Phase 12 feature work

## Today's Accomplishments
### Phase 11.5: Test Suite Repair
1. **RC-1/RC-2** - Patched supabase `create_client` in 4 StateManager fixtures (79 tests)
2. **RC-3** - Rewrote 3 language guidelines tests for extracted `build_language_guidelines()`
3. **RC-4** - Isolated `GOOGLE_API_KEY` env in `test_raises_without_api_key`
4. **RC-5** - Skipped 10 plugin integration tests referencing missing sibling projects
5. **RC-6** - Replaced hardcoded year 2025 with `datetime.now().year`
6. **Env pollution** - Fixed OpenRouter skip condition to check `sk-or-` prefix

### Phase 11: Monetization Infrastructure (Previous Session)
- Full Stripe SDK integration (checkout, portal, subscriptions, webhooks)
- 4-tier pricing system (Free/Basic/Pro/Enterprise) with quota enforcement
- Billing middleware for protecting storyboard and router endpoints

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

## Known Tech Debt
- mypy: 209 pre-existing errors across 48 files
- ruff: 400 pre-existing lint issues (342 auto-fixable)
- ruff format: 72 files need formatting
- diskcache CVE-2025-69872 (HIGH, pending fix version)
- cryptography 46.0.3 → 46.0.5 needed (MEDIUM CVE)

## Tomorrow Start
Phase 12: Auto Demo Video Pipeline - Scene extraction and individual assets
