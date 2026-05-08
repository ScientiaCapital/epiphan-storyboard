# Project Context: epiphan-storyboard

**Generated:** 2026-05-08 (end-of-day, leverage-day wrap)
**Branch:** main @ 08e7344 (Fix A + Fix B shipped sequentially)
**Tag:** v1.1-leverage-day (this session) · v1.0-bdr-workflow (previous Phase 1 merge)
**Production:** https://epiphan-storyboard.vercel.app (main-aligned deploy, Fix A live + smoke-verified)
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

---

## 2026-05-08 — Leverage Day Wrap

Sprint shape (locked via `superpowers:brainstorming` + `agent-teams` + `dispatching-parallel-agents`):

| Decision | Choice |
|---|---|
| Theme | Pay down debt |
| Lens | Highest leverage — kill classes of debt, not papercuts |
| Execution | Native Teams API analog — Lead (Opus) Builder + spawned `observer-full` (Sonnet, read-only) per fix |
| Done bar | Each fix → tests green → observer signoff → push → (Fix A) `vercel --prod --force` + `curl /health` |

### Fix A — SSOT for demo dropdowns (commit `cc17762`)

**Class killed:** UI ↔ Pydantic schema drift (bit us 2026-05-05 b1d5789 + 2026-05-08 av_integrator).

| Change | Detail |
|---|---|
| `src/demo/_dropdowns.py` (new) | Canonical `Vertical` / `OutputFormat` / `VisualStyle` / `ArtistStyle` enums + `Option`-tagged metadata lists + `options_payload()` |
| `src/demo/router.py` | `GenerateRequest` imports the enums + `AudiencePersona` + `StoryboardStage` from presets. `ConfigDict(use_enum_values=True)` keeps runtime fields as plain str |
| `GET /demo/options` (new endpoint) | Future-proofs for fetch-on-load HTML migration (DA-A2 backlog) |
| `tests/demo/test_dropdown_parity.py` (new) | 10 tests: SSOT module shape, SSOT↔AudiencePersona, SSOT↔HTML option values (parametrized over 5 selects), Pydantic schema accepts SSOT, `/demo/options` shape. HTML path anchored to `__file__`. |

**Live verification:** `/health` 200 · `/demo/options` returns 17 personas · 422 error message lists `av_integrator` (the regression-proof) · `blueprint` visual style accepts.

### Fix B — End-to-end grounding integration test (commit `08e7344`)

**Class killed:** Cross-module regression (vertical → persona → problem-statement → prompt — never tested as a chain).

| Change | Detail |
|---|---|
| `tests/storyboard/test_grounding_integration.py` (new) | 30 parametrized tests: anchor injection, graceful Phase-2 degradation, brand-agnosticism (Crestron/Extron/Q-SYS guard), persona signal, **per-persona coverage gate** (every `AudiencePersona` either has statements or is in declared `PHASE_2_PERSONAS_NO_STATEMENTS_YET`), fixture sanity |
| `tests/fixtures/transcripts/` (new) | 3 synthetic multi-speaker transcripts: higher_ed lecture-capture, legal court-recording, live_events venue. ~28/22/19 min calls. Realistic AV-pain language with `[INAUDIBLE]` tokens. No PII. |

**Why the per-persona coverage gate matters:** when someone adds a new persona to `AudiencePersona` and forgets to seed `problem_statements`, the prompt builder silently degrades for that persona with no CI signal. Now the test fails until they either seed statements OR explicitly declare the deferral in the `PHASE_2_PERSONAS_NO_STATEMENTS_YET` allowlist. Closes Backlog DA-S1 + DA-S4.

### Test / lint / mypy delta

| Metric | Before | After | Delta |
|---|---|---|---|
| pytest (excl. live integration) | 1,483 passed | 1,523 passed | +40 |
| Mypy errors (`src/`) | baseline | baseline | 0 new |
| Ruff lint | clean | clean | — |
| Ruff format | clean | clean | — |
| New TODO/FIXME/HACK markers | — | 0 | clean |

### Observer findings (auto-archived after EOD)

- Fix A: 0 blockers, 2 warnings (path-anchor fixed pre-commit; `ArtistStyle.NONE` dual-nullability deferred as `DA-A1` since pre-existing not regression).
- Fix B: 0 blockers, 2 info (coverage gap closed by per-persona gate; persona-signal assertion tightened to strip transcript first).

Latest reports in `.claude/observers/QUALITY.md` and `.claude/observers/ARCH.md`.

### New backlog items added today

- `DA-A1` — Resolve `ArtistStyle` dual-nullability (30 min, low)
- `DA-A2` — Migrate `static/demo.html` to fetch `/demo/options` (1 hr, low)

### Tomorrow's lead task

**DA-R1 — Wire two-pass narrative+schema Forces extraction** in `src/tools/storyboard/gemini_client.py:516–630` (2–3 hr, HIGH impact). The integration test from Fix B will exercise the new code path naturally — write the routing logic, the existing `test_grounding_chain_injects_anchor` parametrized cases pick it up.

```bash
cd /Users/tmk/Desktop/tk_projects/epiphan-storyboard
git checkout -b feature/two-pass-forces-extraction main
# Read .claude/Backlog.md DA-R1 for the full spec
```

---

## Phase 1 BDR Discovery Workflow — Shipped & Live (2026-05-07)

_Original Phase 1 wrap below — preserved for reference. The current state is in "2026-05-08 Leverage Day Wrap" above._

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
  Local:   main @ 08e7344
  Remote:  origin/main @ 08e7344
  Tags:    v1.0-bdr-workflow → abae0f1 (Phase 1 wrap)
           v1.1-leverage-day → 08e7344 (this session — pending push below)
  Branch:  feature/bdr-call-brief-and-surveys preserved from Phase 1 (merged, can be deleted)
```

## DA observer audit summary (cumulative)

- **0 critical findings** across both sessions (Phase 1 + leverage-day)
- **6 warnings** all addressed inline or logged to backlog
- **4 risks + 6 smells** all in Backlog as DA-* items
- **Brand-agnosticism on partner platforms** (Panopto/Kaltura/YuJa/Echo360/Canvas/Blackboard/Moodle/Zoom/Teams/WebEx) — now CI-enforced via `test_prompt_does_not_name_forbidden_brands` (Fix B)

---

_Auto-updated by /end workflow on rollover to 2026-05-09._
