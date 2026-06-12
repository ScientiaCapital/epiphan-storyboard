# Observer: Architecture Report

**Date:** 2026-06-12 (audit of the un-closed 2026-06-10 session, `HEAD~5..HEAD` = c5a4cb1 → 177b539)
**Project:** epiphan-storyboard
**Observer Model:** sonnet (read-only Explore agent)

---

## Blockers (stop work immediately)

_No blockers._

---

## Risks (address this sprint)

- [RISK] — `src/demo/router.py` — third copy of the two-pass threshold concept: hardcoded `DEMO_MAX_TEXT_CHARS = 9000` in the handler vs canonical `GeminiConfig.two_pass_threshold_chars = 10_000` — if config is tuned, the demo cap silently diverges.
  - **Disposition:** fix-now → sprint Task 3 (DA-A3 expanded to ×3 copies).
- [RISK] — `vercel.json` — `maxDuration: 300` is plan-gated (silently capped at 60s on lower plans); the timeout fix from 23386f0 may be a no-op, masked by the 9K cap independently keeping generations short. `memory: 1769` is non-standard and rounds up to the 2048 MB tier (cost implication).
  - **Disposition:** verify-now → sprint Task 5.
- [RISK] — `src/brand/fonts.py:78` — `_cache` check has no `asyncio.Lock`; concurrent cold-start requests duplicate upstream fetches to chat.epiphan.com (harmless result, wasteful; 4×N requests possible on cold worker).
  - **Disposition:** fix-now → sprint Task 2.

---

## Smells (log to backlog)

- [SMELL] — demo.html vs `_dropdowns.py` SSOT — artist-option emoji drift (diego_rivera 🎺→🖼️, siqueiros ⚡→🖌️) and `Infograph 📐` → `Infographic 📋` label drift. Parity test checks values only, so it passes; cosmetic SSOT-workflow violation.
  - **Disposition:** sprint Task 6 (stretch) or Backlog DA-A4.
- [SMELL] — commit `c5a4cb1` scope-mixing — transcript-compactor wiring into `meeting_recap.py` and Gemini 120s HTTP timeout landed inside a "brand re-skin" commit; behavior changes for all meeting-recap callers undersold by the message.
  - **Disposition:** discard (historical, not actionable); noted for commit hygiene.
- [SMELL] — `src/brand/fonts.py` returns 502 on upstream failure — pollutes Vercel 5xx metrics; browser falls back fine, but a 200 empty-body or cached fallback would be cleaner ops.
  - **Disposition:** logged to Backlog (DA-B1).
- [SMELL] — `static/demo.html` `downloadCard()` — html2canvas with `useCORS: true` may silently blank the teal gradient header in downloaded PNGs (foreignObject + cross-origin stylesheet limitation).
  - **Disposition:** logged to Backlog (DA-B2 — needs manual repro before fixing).

No new TODO/FIXME/HACK markers; no missing serverless deps; `httpx` already in requirements; html2canvas loaded with SRI hash.

---

## Monitoring Runs

| Date | Session | Findings | Status |
|------|---------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | 3 risks / 4 smells | archived to `.claude/archive/2026-05-07-OBSERVER-ARCH.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 0 blockers / 1 risk / 8 smells (cumulative across 4 audits) — all logged to Backlog (DA-A1, DA-A2, DA-A3, DA-R1.1.a) | archived to `.claude/archive/2026-05-08-OBSERVER-ARCH.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 demo/deploy session (skipped /end) | 0 blockers / 3 risks / 5 smells — all dispositioned above | active |
