# epiphan-storyboard

**Branch**: main | **Updated**: 2026-02-19

## Status
Phase 16 sprint complete. Smoke test E2E validated (4 scenarios, 4 PNGs, BDR email). Retry-After
cap applied to all 4 connectors. Ruff lint clean. Auto-trigger storyboard on sync implemented.
Image generation rerouted through OpenRouter (Nano Banana / gemini-2.5-flash-image).
- 1930 tests collected, 1913 passing, 21 skipped, 0 failures
- Security sweep: 1 gitleaks finding (false positive — test fixture fake key)
- 1 CVE remaining (diskcache serialization — no fix upstream)

## Done (This Session)
### Phase 16: Smoke Test Validation, Retry-After Cap, Auto-Trigger
- [x] P0: Added `output/` to `.gitignore`
- [x] P1: Ran smoke test E2E — 4 scenarios matched, 4 PNGs generated, BDR email drafted (~51s)
- [x] P2: Rerouted image generation through OpenRouter (Nano Banana) — no Google API key needed
- [x] P3: Capped Retry-After at 60s in 4 connector clients (HubSpot, Clari, Gong, Fireflies)
- [x] P4: Fixed 2 ruff lint issues in `src/agents/runner.py` (B904 `from e`, B007 `_step_num`)
- [x] P5: Auto-trigger storyboard generation on HubSpot/Clari connector sync
- [x] P6: Added 12 new tests (4 retry-cap + 7 auto-storyboard + 1 gemini health check)
- [x] P7: Updated PROJECT_CONTEXT.md and PLANNING.md

### Key Changes
- `src/tools/storyboard/gemini_client.py` — dual-path: direct Google API or OpenRouter for images
- `src/routers/connectors.py` — `_auto_generate_storyboards()` non-blocking post-sync hook
- 4 connector clients — `min(int(retry_after), 60)` security fix

## Video Generation Research
OpenRouter does NOT support video output. Best alternatives:
- **fal.ai** — broadest model library (Kling, MiniMax, Wan 2.1, LTX)
- **Veo 3.1 via Gemini API** — $0.40/sec, direct Google API key required
- **Runway API** — includes Veo access, professional video tooling
- **Replicate** — serverless GPU, pay-per-second

## Deferred (Tier 3)
| Issue | Status |
|-------|--------|
| H-4: Sync Gemini call blocks event loop | Deferred — requires google-genai async investigation |
| H-5/M-9: lru_cache on Redis connection | Deferred — infrastructure change |
| H-2: sanitize_content wrong arg type | Deferred — low impact |
| M-7: No retry on Gemini image gen | Deferred — 2-3x API cost |
| M-8: Unstable model name | Deferred — Google controls this |
| M-11: Sync Supabase in async function | Deferred — requires async client |

## API Keys Status
| Key | Status |
|-----|--------|
| SUPABASE_* | Set |
| ANTHROPIC_API_KEY | Set |
| GOOGLE_API_KEY | Placeholder (not needed — using OpenRouter) |
| OPENROUTER_API_KEY | Set (real key from epiphan-lead-harvester) |
| STRIPE_SECRET_KEY | Set (test mode) |
| CARTESIA_API_KEY | Missing |
| BROWSERBASE_* | Missing |
| RUNWAY_API_KEY | Missing |
| CLOSE_API_KEY | Missing |
| HUBSPOT_PRIVATE_APP_TOKEN | Missing (blocks live HubSpot data) |
| CLARI_API_KEY / CLARI_API_PASSWORD | Missing (blocks live Clari data) |

## Quick Commands
```bash
python3 -m pytest tests/ -v                    # All tests (1930 collected)
python3 -m pytest tests/tools/storyboard/ -v   # Storyboard tests
python scripts/smoke_test_transcript.py        # E2E pipeline validation
ruff check src/                                # Lint (0 issues)
uvicorn src.api:app --reload --port 8000
```

## Known Tech Debt
- mypy: 209 pre-existing errors across 48 files
- diskcache CVE-2025-69872 (HIGH, no fix version yet — unsafe deserialization)
- Gemini 2.0 Flash models deprecated March 2026 — migrate to 2.5 Flash

## Tech Stack
Python 3.13 | FastAPI | Stripe | Supabase | Redis | DeepSeek V3 | Qwen 2.5 VL | Gemini 2.5 Flash Image (via OpenRouter)

## Blockers
- **HUBSPOT_PRIVATE_APP_TOKEN** not in `.env` — blocks live HubSpot connector test
- **CLARI_API_KEY + CLARI_API_PASSWORD** not in `.env` — blocks live Clari connector test

## Next Steps
1. Wire real HubSpot/Clari data (requires API tokens from user)
2. Evaluate video generation integration (fal.ai or Veo 3.1)
3. Phase 17: Persist auto-storyboard results to Supabase
