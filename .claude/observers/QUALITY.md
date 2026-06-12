# Observer: Code Quality Report

**Date:** 2026-06-12 (audit of the un-closed 2026-06-10 session, `HEAD~5..HEAD` = c5a4cb1 → 177b539)
**Project:** epiphan-storyboard
**Observer Model:** haiku (read-only Explore agent)

---

## Critical (must fix before merge)

- [CRITICAL] — `src/brand/fonts.py:84-88` — broad `except Exception` masks the difference between upstream auth failures (401/403) and network errors; everything logs as "Font upstream unavailable" — catch `httpx.HTTPStatusError` separately and log status details before raising 502.
  - **Disposition:** fix-now → sprint Task 2 (2026-06-12). Devil's advocate note: error IS logged and surfaced as 502, nothing silently swallowed — severity arguably WARNING; fixed because it's cheap, not an emergency.

---

## Warnings (fix or log to backlog)

- [WARNING] — `src/api.py:109-111`, `src/storyboard/router.py:56-58` — `os.getenv()` values not `.strip()`ed (violates known-footgun project rule; pre-existing, not introduced this session).
  - **Disposition:** logged to Backlog (bundle with next api.py touch).
- [WARNING] — `src/brand/fonts.py` — new module with zero test coverage (no `tests/brand/`).
  - **Disposition:** fix-now → sprint Task 2.
- [WARNING] — `src/demo/router.py` — magic number 9000 (text cap) defined inline; third copy of the two-pass-threshold concept.
  - **Disposition:** fix-now → sprint Task 3 (merged into DA-A3).

---

## Info (nice to have)

- [INFO] — `vercel.json` maxDuration ↔ 9K demo cap coupling has no integration test documenting it.
  - **Disposition:** logged to Backlog (DA-V1).
- [INFO] — `tests/integration/test_full.py:49-80` — LLM-availability skip helper string-matches error text; brittle to provider phrasing changes. Suggest structured error-code enum on `AgentSession`.
  - **Disposition:** logged to Backlog (DA-Q1).

## Positives (verified, no action)

- `src/agents/runner.py:468-481` error capture is solid (logger.exception + session.error).
- Type hints complete on all new functions; no unused imports; no OpenAI usage.
- Meeting-recap prompt now explicitly demands "Single STRING (not an array)" for summary.
- New `_check_frankenstack_grounding()` quality-gate check prevents ungrounded recaps.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned | 24 (full HEAD~5..HEAD diff) |
| Critical findings | 1 |
| Warnings | 3 |
| Info items | 2 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1–1.3 | 6 | 7 (0C/4W/3I) | archived to `.claude/archive/2026-05-07-OBSERVER-QUALITY.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 4 sequential audits across the day | 14 cumulative | 12 cumulative (0C/2W/10I) — all dispositioned, none silently dropped | archived to `.claude/archive/2026-05-08-OBSERVER-QUALITY.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 demo/deploy session (skipped /end) | /begin Phase 2 | 24 | 6 (1C/3W/2I) — all dispositioned above | active |
