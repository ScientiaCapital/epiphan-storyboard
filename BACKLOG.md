# BACKLOG.md - Project Task Board

**Project**: Conductor-AI - Multi-Model AI Agent Platform with SDK
**Last Updated**: 2025-12-24
**Sprint**: Current

---

## Quick Stats

| Status | Count |
|--------|-------|
| Blocked | 1 |
| In Progress | 0 |
| Ready | 1 |
| Done (this sprint) | 14 |

**Total Tests**: 941+

---

## Board View

### Blocked

#### 1. [HIGH] Create Stripe Price IDs
- **ID**: TASK-028
- **Assignee**: User
- **Labels**: `billing`, `config`, `user-action`
- **Dependencies**: Stripe Dashboard access

**Description**: Create subscription products in Stripe Dashboard and add price IDs to .env.

**Steps**:
1. Go to https://dashboard.stripe.com/products
2. Create "Basic" product - $49/month recurring
3. Create "Pro" product - $199/month recurring
4. Copy price IDs (start with `price_`)
5. Add to `.env`:
   ```
   STRIPE_PRICE_ID_BASIC=price_xxx
   STRIPE_PRICE_ID_PRO=price_xxx
   ```

**Acceptance Criteria**:
- [ ] Basic product created in Stripe
- [ ] Pro product created in Stripe
- [ ] Price IDs added to .env
- [ ] POST /billing/checkout returns checkout URL

---

### Ready (Prioritized)

#### 1. [HIGH] Phase 12: Auto Demo Video Pipeline
- **ID**: TASK-029
- **Assignee**: Claude
- **Labels**: `feature`, `demo`, `pipeline`
- **Dependencies**: None

**Description**: Build auto demo video pipeline returning individual assets.

**Key Deliverables**:
- `src/demo_pipeline/` module
- Scene extraction from recordings
- Individual storyboard + video clip per scene
- `POST /demos/generate`, `GET /demos/jobs/{id}` endpoints

---

### Backlog (Future)

#### Data Ingestion
| ID | Title | Priority | Labels |
|----|-------|----------|--------|
| TASK-030 | Ingest Loom transcripts | Medium | `data`, `ingestion` |
| TASK-031 | Ingest Close CRM calls | Medium | `data`, `ingestion` |
| TASK-032 | Ingest Miro roadmaps | Low | `data`, `ingestion` |

#### Advanced Features
| ID | Title | Priority | Labels |
|----|-------|----------|--------|
| TASK-002 | Streaming Responses (SSE) | Medium | `feature` |
| TASK-003 | Multi-Agent Collaboration | Medium | `feature` |
| TASK-004 | Memory System | Low | `feature` |

---

### Done (This Sprint)

| ID | Title | Completed | By |
|----|-------|-----------|-----|
| TASK-027 | Phase 11: Billing Infrastructure (73 tests) | 2025-12-24 | Claude |
| TASK-026 | Agent Router (41 tests, 6 chains) | 2025-12-24 | Claude |
| TASK-025 | Phase 9.0 Screen Recording Module (100 tests) | 2025-12-09 | Claude |
| TASK-024 | Phase 8.0 Mixed Input Parity (79 tests) | 2025-12-04 | Claude |
| TASK-023 | Model Catalog Gemini 2.5 via OpenRouter | 2025-12-21 | Claude |
| TASK-000 | Context Engineering Setup | 2025-11-30 | Claude |
| TASK-012 | SDK Foundation (59 tests) | 2025-11-27 | Team |
| TASK-013 | Audit/Observability Layer | 2025-11-28 | Team |
| TASK-014 | dealer-scraper-mvp Plugin | 2025-11-28 | Team |
| TASK-015 | sales-agent Plugin | 2025-11-28 | Team |
| TASK-016 | Model Catalog | 2025-11-29 | Team |
| TASK-017 | Video Tools Module (186 tests) | 2025-12-02 | Claude |
| TASK-018 | Storyboard Tools (168 tests) | 2025-12-02 | Claude |
| TASK-019 | Storyboard Pipeline API (61 tests) | 2025-12-02 | Claude |

---

## Sprint Metrics

### Quality
- **Tests Passing**: 941+ total
- **Type Errors**: 0 (billing module)
- **Lint Issues**: 0 (billing module)
- **NO OpenAI**: Using DeepSeek, Qwen, Claude, Gemini
- **Secrets**: 0 hardcoded (all in .env)

---

## Related Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project overview and rules |
| `PLANNING.md` | Architecture decisions |
| `TASK.md` | Quick task reference |
| `sql/006_billing.sql` | Billing migration |
| `.env.example` | Environment template |

---

## Critical Rules

- **NO OpenAI** - Use Anthropic Claude, Google Gemini, or Chinese LLMs
- **API keys in .env only** - Never hardcode
- **All code changes require tests** - 941+ tests passing
- **Run tests before marking tasks done**

---

*This file is the source of truth for sprint tasks. Keep it updated!*
