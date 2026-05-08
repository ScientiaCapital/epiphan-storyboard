# Project Context: epiphan-storyboard

**Generated:** 2026-05-07 (end-of-day)
**Branch:** feature/bdr-call-brief-and-surveys @ b003112 (pushed to origin)
**Production:** https://epiphan-storyboard.vercel.app (deployed today, smoke-verified)
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

---

## Today's Work (2026-05-07) — Phase 1 BDR Discovery Workflow ✅

Shipped 11 commits on `feature/bdr-call-brief-and-surveys`, 5,630 LOC, 1,446 tests passing, deployed to production.

| Commit | What |
|---|---|
| `4e5752c` | feat: Problem Statements library (Phase 1.1) — verbatim BDR pain library, ~30 statements seeded across Higher Ed / Legal / Live Events × all key personas, 32-doc-role → 17-enum alias table |
| `d58a675` | feat: Transcript Compactor (Phase 1.2) — replaces 32K hard truncation with extractive summarization |
| `bcb53d3` | feat: Prompt Builder polish (Phase 1.3) — 4 fixes: compactor wired, two-pass narrative+schema prompts, verbatim grounding anchor, brand-agnostic Frankenstack patterns |
| `06ef8e6` | fix: dropped Crestron/Extron/Q-SYS brand names from Frankenstack (DA-W1) + DA audit reports |
| `40f688f` | feat: Vertical Workflow Surveys (Phase 1.4) — Higher Ed 18q / Legal 17q / Live Events 40q |
| `5795d9f` | feat: BDR Call Brief generator (Phase 1.6) — persona-keyed templates, NSTTD email, NBA decision matrix |
| `23593dd` | feat: Survey API endpoints (Phase 1.5) — GET /storyboard/survey/templates/{vertical}, POST /storyboard/survey/submit |
| `6d4444d` | feat: 3 quality-gate checks for the BDR brief (Phase 1.7) — resonance, calibrated form, brief completeness |
| `271c2df` | feat: BDR Discovery Workflow UI panel (Phase 1.8) — vertical/mode toggle, dynamic survey form, brief result card |
| `f497086` | fix: contraction-aware calibrated-question filter (post-smoke polish) |
| `b003112` | chore: end-of-day backlog + observer archive |

**DA observer audit:** 0 criticals, 4 warnings (1 fixed inline, 3 in backlog), 3 risks + 4 smells (all in backlog as DA-* items). Brand-agnosticism on partner platforms (Panopto/Kaltura/YuJa/Echo360/Canvas/Blackboard/Moodle/Zoom/Teams/WebEx) verified clean — zero violations.

## Working Tree Status

```
clean — feature branch pushed to origin
worktree: epiphan-storyboard @ b003112 [feature/bdr-call-brief-and-surveys]
```

## Production Verification (smoke)

```
GET  /health                                       → 200 {"status":"healthy"}
GET  /storyboard/survey/templates/higher_ed        → 200 (18 questions / 6 sections)
GET  /storyboard/survey/templates/legal            → 200 (17 questions)
GET  /storyboard/survey/templates/live_events      → 200 (40 questions)
GET  /storyboard/survey/templates/government       → 404 (Phase 2 hint message)
POST /storyboard/survey/submit (transcript-only)   → av_director, ICP 90, 5 calibrated qs, 76-word email
GET  /                                             → demo page renders with BDR Discovery section
```

---

## Tomorrow

**Recommended next:** **DA-R1 — Wire two-pass narrative+schema Forces extraction into `gemini_client.py`** (effort: 2–3 hr, impact: HIGH). The prompts are infrastructure-ready from Phase 1.3; the missing piece is the orchestration call site that runs both passes when transcript size or low extraction confidence warrants. This realizes the Forces-of-Progress quality lift documented in the original `tidy-beaming-pebble.md` plan.

**Skill:** `feature-dev` for the orchestration design; standard TDD with the existing refine-pass plumbing at `src/tools/storyboard/gemini_client.py:516–630` as the integration point.

**Estimated cost:** $4–8 for the orchestration work + tests.

**Top unresolved observer/backlog flag:** **DA-R1** (above) — this is the open half of Phase 1.3's Fix #2. Until it's wired the new prompts are dormant infrastructure. Second-priority is **DA-S1** (1 hr): an end-to-end integration test that asserts the full grounding chain (vertical+persona → problem-statement anchor → prompt builder → verbatim text in output) — guards against module-boundary regressions when DA-R1 lands.

**Alternative path:** if continuing the BDR thread isn't the priority tomorrow, **merge `feature/bdr-call-brief-and-surveys` to `main` via PR**. The branch is fully shipped and production-deployed; merging is just bookkeeping. URL to open the PR: https://github.com/ScientiaCapital/epiphan-storyboard/pull/new/feature/bdr-call-brief-and-surveys

---

_Auto-updated by /end workflow._
