# epiphan-storyboard

**Branch**: main | **Updated**: 2026-02-19

## Status
Phase 13 sprint in progress. Doc hygiene done, CVE patched, visual audit script written,
exponential backoff implemented. Ready to run visual audit.
- 1482 tests passing, 22 skipped, 0 failures, 0 errors
- Security sweep: 1 gitleaks finding (false positive — test fixture fake key)
- 1 CVE remaining (diskcache serialization — no fix upstream)
- langchain-core CVE-2026-26013 FIXED (upgraded to 1.2.11)

## Done (This Session)
### Phase 13: Sprint — Doc Hygiene, CVE, Visual Audit, Backoff
- [x] P4: Updated PLANNING.md (Phase 11.5 → 12.5, added Phase 12/12.5 to completed phases, updated test counts)
- [x] P2: Upgraded langchain-core 1.2.10 → 1.2.11 (CVE-2026-26013 SSRF fix)
- [x] P1: Created scripts/visual_audit.py (generates 6 storyboards: 3 stages x 2 personas)
- [x] P3a: Replaced linear backoff with exponential + jitter in OpenRouter retry (M-5 resolved)
- [x] Added 4 new tests for exponential backoff (TestOpenRouterRetryBackoff)
- [x] Added audit_output/ to .gitignore

### Previous: Phase 12.5 — Storyboard Module Hardening
- Removed MEP contractor content, replaced teal/green with navy/lime brand colors
- Fixed 3 crash bugs (health_check, audience param, dir() bug)
- Added 45 safety tests across 3 test files

## Deferred (Tier 3)
| Issue | Status |
|-------|--------|
| H-4: Sync Gemini call blocks event loop | Deferred — requires google-genai async investigation |
| H-5/M-9: lru_cache on Redis connection | Deferred — infrastructure change |
| H-2: sanitize_content wrong arg type | Deferred — low impact |
| M-5: Linear retry to exponential | DONE — exponential + jitter implemented |
| M-7: No retry on Gemini image gen | Deferred — 2-3x API cost |
| M-8: Unstable model name | Deferred — Google controls this |
| M-11: Sync Supabase in async function | Deferred — requires async client |

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

## Quick Commands
```bash
python3 -m pytest tests/ -v                    # All tests (1482 passing)
python3 -m pytest tests/tools/storyboard/ -v   # Storyboard tests (255 passing)
python scripts/visual_audit.py                 # Generate 6 audit storyboards
ruff check src/tools/storyboard/               # Lint storyboard module
uvicorn src.api:app --reload --port 8000
```

## Known Tech Debt
- mypy: 209 pre-existing errors across 48 files
- diskcache CVE-2025-69872 (HIGH, no fix version yet — unsafe deserialization)
- ruff: 2 pre-existing warnings in storyboard/ (B904, F841 in storage.py)

## Tech Stack
Python 3.13 | FastAPI | Stripe | Supabase | Redis | DeepSeek V3 | Qwen 2.5 VL | Gemini 3 Pro

## Blockers
**User Action Required**: Create Stripe products in Dashboard
- Basic product ($49/mo) -> Add STRIPE_PRICE_ID_BASIC to .env
- Pro product ($199/mo) -> Add STRIPE_PRICE_ID_PRO to .env

## Next Steps
1. Run `python scripts/visual_audit.py` to generate 6 storyboards — manually inspect PNGs
2. Evaluate H-4 (async Gemini calls) if time permits
3. Consider Phase 13 feature work after visual audit passes
