# Project Context: epiphan-storyboard

**Generated:** 2026-05-09 (end-of-day, DA-R1 ship)
**Branch:** main @ d1d62a6 (DA-R1 two-pass extraction shipped + tagged)
**Tags:** v1.2-two-pass-extraction (this session) · v1.1-leverage-day (2026-05-08) · v1.0-bdr-workflow (2026-05-07)
**Production:** https://epiphan-storyboard.vercel.app (main-aligned deploy, all three releases live + smoke-verified)
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

---

## 2026-05-09 — DA-R1 Two-Pass Forces Extraction Ship

Realizes Phase 1.3's quality lift. Single architectural fix, ~3 hr execution end-to-end.

| Decision | Choice |
|---|---|
| Theme | Realize Phase 1.3 quality lift (DA-R1 from backlog) |
| Lens | Single high-leverage point fix |
| Execution | Same skill stack — `brainstorming` + `agent-teams` (Builder+Observer) + `dispatching-parallel-agents` + `workflow-orchestrator` gate |
| Schema reconciliation | Locked Option B (additive `forces_of_progress` + `frankenstack` on existing `StoryboardUnderstanding`) |
| Done bar | TDD red→green → observer signoff → push → `vercel --prod --force` → live verify |

### What shipped (commit `d1d62a6`)

| Change | Detail |
|---|---|
| `src/tools/storyboard/gemini_client.py` (+189) | New `ForcesOfProgress` Pydantic model · `StoryboardUnderstanding` extended additively (16 callsites verified backwards-compat) · `GeminiConfig.enable_two_pass_extraction` (default `True`) + `two_pass_threshold_chars` (default `10_000`) · new `_extract_via_two_pass()` method · new `_call_text_model()` helper · trigger wired in `_understand` (replaces `_refine_extraction` when fired) |
| `tests/tools/storyboard/test_gemini_client.py` (+454) | 14 new tests across 4 classes — all mock LLM, zero live API · TDD red→green throughout |
| `tests/storyboard/test_grounding_integration.py` (+43) | 3 new tests pulling the long fixture into the parametrized suite + threshold sanity check |
| `tests/fixtures/transcripts/higher_ed_strategy_review_long_synthetic.txt` (new, 17,074 chars) | Synthetic 47-min strategic AV-portfolio review · multi-speaker · zero forbidden brands |

### Trigger logic
For transcripts: if `len(content) ≥ 10K` OR `extraction_confidence < 0.75` → run two-pass (narrative → schema-mapping) instead of free-form `_refine_extraction`. Two-pass `extraction_confidence` becomes `max(single_pass, two_pass)`. On any failure (LLM error, parse error), graceful degrade to single-pass result with logged warning.

### Test / lint / mypy delta

| Metric | Before | After | Delta |
|---|---|---|---|
| pytest (excl. live integration) | 1,523 | 1,540 | +17 |
| Mypy errors (`gemini_client.py`) | 46 | 46 | 0 |
| Ruff lint | clean | clean | — |
| New TODO/FIXME/HACK markers | — | 0 | clean |

### Observer findings

🟢 **GREEN gate** — 0 blockers, 0 critical, 0 warnings, 1 architecture smell (logged as `DA-A3`). Audit appended to `.claude/observers/QUALITY.md` and `ARCH.md` under `## DA-R1 (2026-05-09)`.

### New backlog items added today

- `DA-A3` — Consolidate text-path dispatch into `_call_text_model` (refactor `_understand`'s inline text branch to call the new helper). 30 min, low.
- `DA-R1.1` — Wire two-pass into `meeting_recap.process_meeting_recap` (currently has its own prompt path that skips the two-pass benefit). 1 hr, medium.

### Live verification (post-deploy)

- ✅ `GET /health` → `{"status":"healthy"}`
- ✅ `POST /demo/generate` schema validation enforces enum (`av_integrator` accepted, `foobar` rejects with 422)
- ✅ `GET /demo/options` returns canonical 17 personas / 11 verticals / 2 formats / 9 styles / 10 artists

### Tomorrow's lead candidates

The DA-R1 fix unlocks a few natural follow-ups in priority order:

1. **`DA-R1.1`** — Wire two-pass into the meeting-recap pipeline (1 hr). Direct quality lift for the BDR meeting-recap flow.
2. **`DA-A3`** — Consolidate text-path dispatch (30 min). Cheap maintenance, removes the dual-callsite hazard.
3. **`DA-S3`** — Vertical-aware Frankenstack pattern blocks (1 hr). Higher-Ed and Live-Events have different Frankenstacks; the current global block dilutes signal.

```bash
git checkout -b feature/two-pass-meeting-recap main
# Read .claude/Backlog.md DA-R1.1 for the spec
```

---

## 2026-05-08 — Leverage Day Wrap

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
