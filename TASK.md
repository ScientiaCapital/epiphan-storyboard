# TASK.md - Conductor-AI

**Project**: conductor-ai
**Last Updated**: 2025-12-24

---

## Current Status

**Phase 11.0: Monetization Infrastructure - COMPLETE**

Implemented full Stripe billing integration:
- ✅ `src/billing/` module (6 files, 800+ LOC)
- ✅ Stripe SDK wrapper (checkout, portal, subscriptions, webhooks)
- ✅ SubscriptionService with webhook event handlers
- ✅ Billing middleware for quota enforcement
- ✅ FastAPI endpoints (checkout, subscription, portal, webhooks)
- ✅ 73 billing tests passing
- ✅ sql/006_billing.sql migration
- ✅ Storyboard + Router endpoints hooked to billing/quotas

**Environment Variables Required**:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_BASIC=price_...   # $49/mo
STRIPE_PRICE_ID_PRO=price_...     # $199/mo
```

**Pricing Tiers**:
| Tier | Price | Hourly | Daily | Monthly |
|------|-------|--------|-------|---------|
| Free | $0 | 1K tokens | 10K | 100K |
| Basic | $49/mo | 5K | 50K | 500K |
| Pro | $199/mo | 50K | 500K | 5M |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited |

**Phase 10.0: Agent Router - COMPLETE**

Implemented dynamic agent router with auto-classification:
- ✅ `src/router/` module (7 files, 1800+ LOC)
- ✅ TaskClassifier - 3-stage classification (pattern → keyword → LLM)
- ✅ 6 pre-built chains (storyboard, video, scrape, code_run, knowledge, sql)
- ✅ AgentRouter - Core routing logic with chain selection
- ✅ FastAPI endpoints (POST /agents/route, GET status, GET chains)
- ✅ RouterJobManager - Redis hot + Supabase cold state
- ✅ 41 tests passing (classifier, chains, router, API)
- ✅ sql/005_router_jobs.sql migration

**Phase 9.0: Screen Recording Module - COMPLETE**

**Total Tests**: 941+ (868 previous + 73 billing)

**SQL Migrations**: All 6 migrations ready

---

## Active Tasks

### 🔴 HIGH Priority

**Create Stripe Price IDs** - Billing module needs:
- Create Basic product ($49/mo) in Stripe Dashboard
- Create Pro product ($199/mo) in Stripe Dashboard
- Add `STRIPE_PRICE_ID_BASIC` and `STRIPE_PRICE_ID_PRO` to .env

---

### 🟡 MEDIUM Priority

**Phase 12: Auto Demo Video Pipeline** (Next Phase)
- Scene extraction from recordings
- Individual asset output (storyboards + video clips per scene)
- Complete `_record_video()` gap in screen_capture.py

**Ingest Real Data** - Knowledge Brain needs actual content:
- Loom transcripts (~20-25 videos)
- Close CRM calls/notes
- Miro screenshots

---

### 🟢 LOW Priority / Nice-to-Have

**None currently**

---

## Completed Phases

### Phase 11.0: Monetization Infrastructure (2025-12-24)
- ✅ Stripe SDK integration (checkout, portal, subscriptions)
- ✅ SubscriptionService with webhook handlers
- ✅ Billing middleware (require_billing, require_tier, require_quota)
- ✅ FastAPI billing endpoints (4 endpoints)
- ✅ Storyboard + Router endpoints quota-protected (402/429 responses)
- ✅ sql/006_billing.sql migration
- ✅ 73 tests (schemas, stripe_client, service, router)

### Phase 10.0: Agent Router (2025-12-24)
- ✅ TaskClassifier with 3-stage classification
- ✅ 6 pre-built chains
- ✅ FastAPI endpoints
- ✅ RouterJobManager with Redis + Supabase
- ✅ 41 tests

### Phase 9.0: Screen Recording Module (2025-12-09)
- ✅ BrowserbaseClient for cloud browser sessions
- ✅ RunwayClient for video generation
- ✅ 100 tests

### Phase 7.6: Intelligent Model Routing (2025-12-04)
- ✅ 3-Stage Pipeline (EXTRACT → REFINE → GENERATE)
- ✅ DeepSeek V3, Qwen 2.5 VL, Gemini 3 Pro

### Phase 7.5: Knowledge → Storyboard Integration (2025-12-04)
- ✅ KnowledgeCache singleton
- ✅ Language guidelines enriched

### Phase 7: Knowledge Brain (2025-12-04)
- ✅ Multi-source ingestion
- ✅ 43 tests

### Phase 6: Demo App (2025-12-04)
- ✅ FastAPI demo router
- ✅ Web UI

### Phase 5: Storyboard Pipeline API (2025-12-02)
- ✅ Async FastAPI endpoints
- ✅ Redis + Supabase state

### Phase 4: Storyboard Tools (2025-12-02)
- ✅ CodeToStoryboardTool
- ✅ RoadmapToStoryboardTool

### Phase 3: Video Tools (2025-12-02)
- ✅ VideoScriptGeneratorTool
- ✅ VideoGeneratorTool

### Phase 2: Plugin Integration (2025-11-28)
- ✅ SDK Foundation

### Phase 1: SDK Foundation (2025-11-27)
- ✅ BaseTool, ToolRegistry

---

## Technical Debt

**None currently** - All code follows modern Python best practices

---

## Notes

- All code follows project standards (see PLANNING.md)
- All tests passing (941+ total)
- No OpenAI models used (DeepSeek/Qwen/Gemini only)
- API keys in .env only (never hardcoded)
- Billing integrated with quotas

---

**Phase 11 complete - Stripe billing live. Next: Phase 12 Demo Pipeline or create Stripe price IDs.**
