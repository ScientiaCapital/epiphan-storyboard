# Project Context: epiphan-storyboard

**Generated:** 2026-05-07 (end-of-day, merged to main 2026-05-08 morning)
**Branch:** main @ abae0f1 (Phase 1 BDR Workflow merged via fast-forward)
**Tag:** v1.0-bdr-workflow
**Production:** https://epiphan-storyboard.vercel.app (main-aligned deploy, smoke-verified)
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

---

## Phase 1 BDR Discovery Workflow — Shipped & Live

11 commits originally on `feature/bdr-call-brief-and-surveys`, fast-forwarded to `main`, tagged `v1.0-bdr-workflow`, redeployed cleanly from main.

| Layer | Status |
|---|---|
| Problem Statements library (Higher Ed / Legal / Live Events seeded) | ✅ live |
| Transcript Compactor (replaces 32K hard truncation) | ✅ live |
| Prompt builder polish (4 fixes including brand-agnostic Frankenstack) | ✅ live |
| 3 vertical workflow surveys (Higher Ed 18q / Legal 17q / Live Events 40q) | ✅ live |
| Survey API endpoints (GET templates / POST submit) | ✅ live |
| BDR Call Brief generator (deterministic core) | ✅ live |
| Quality gate enhancements (3 new checks) | ✅ live |
| Demo UI BDR Discovery Workflow panel | ✅ live |

## Production smoke (main-aligned deploy)

```
GET  /health                                       → 200
GET  /storyboard/survey/templates/higher_ed        → 200 (18q / 6 sections)
GET  /storyboard/survey/templates/legal            → 200 (17q)
GET  /storyboard/survey/templates/live_events      → 200 (40q)
GET  /storyboard/survey/templates/government       → 404 (Phase 2 hint)
POST /storyboard/survey/submit                     → av_director, ICP 90, 3 statements / 5 questions / 76-word email
GET  /                                             → demo with BDR Discovery section
```

## Working Tree Status

```
clean — main pushed to origin/main
  Local:   main @ abae0f1
  Remote:  origin/main @ abae0f1
  Tag:     v1.0-bdr-workflow → abae0f1 (pushed)
  Branch:  feature/bdr-call-brief-and-surveys preserved (merged, can be deleted by user)
```

## DA observer audit summary

- **0 critical findings**
- **4 warnings** (1 fixed inline, 3 in Backlog)
- **3 risks + 4 smells** all in Backlog as DA-* items
- **Brand-agnosticism on partner platforms** (Panopto/Kaltura/YuJa/Echo360/Canvas/Blackboard/Moodle/Zoom/Teams/WebEx) — verified zero violations

---

## Tomorrow's Sprint Kickoff (2026-05-08)

**Recommended lead task:** **DA-R1 — Wire two-pass narrative+schema Forces extraction into `gemini_client.py`**
- Effort: 2–3 hr / Impact: HIGH
- Why: Phase 1.3 shipped the prompts as infrastructure-ready, but the orchestration call site that runs both passes is the open half. Realizes the Forces-of-Progress quality lift.
- Where: `src/tools/storyboard/gemini_client.py:516–630` (existing refine plumbing as integration point)
- TDD: write a test that asserts a two-pass call path is taken when transcript ≥ ~10K chars or `extraction_confidence < 0.75`
- Skill: `feature-dev`
- Estimate: $4–8

**If wrapping for the sprint or pivoting:**
| Quick wins (under 1 hr) | Effort | Impact |
|---|---|---|
| DA-W2: Tighten `except Exception` in `build_problem_statement_anchor` | 15 min | low |
| DA-W4: 5 edge-case tests for `transcript_compactor` | 30 min | low |
| DA-I2: Skip dup `key_moments` block when ratio==1.0 | 10 min | low |
| `av_integrator` audience Literal audit | 5 min | low |
| `.gitleaksignore` for historical placeholder | 5 min | low |

**Medium-impact (~1 hr each):**
- DA-S1: End-to-end grounding integration test (3 fixtures, one per Phase-1 vertical)
- DA-S4: Capture one anonymized real Clari/Gong transcript per Phase-1 vertical as regression fixture

**Phase 2 work (multi-day):**
- Surveys for Government / Corporate AV / Healthcare / Houses of Worship / K-12 / Channel
- Outbound HubSpot webhook for BDR brief auto-attach
- Survey response persistence (Supabase / Redis)

## Sprint kickoff command

```bash
cd /Users/tmk/Desktop/tk_projects/epiphan-storyboard
git checkout -b feature/two-pass-forces-extraction main
# Open .claude/Backlog.md and read the DA-R1 entry for the spec
```

---

_Auto-updated by /end workflow on rollover to 2026-05-08._
