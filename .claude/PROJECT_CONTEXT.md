# Project Context: epiphan-storyboard

**Generated:** 2026-05-08 (Fri, end-of-day — locked via /end workflow)
**Branch:** main @ 89d021d (clean — pushed, working tree empty, feature branch cleaned)
**Tags:** v1.3-meeting-recap-unblock · v1.2-two-pass-extraction · v1.1-leverage-day · v1.0-bdr-workflow (all pushed to origin)
**Production:** https://epiphan-storyboard.vercel.app — 4 releases live + smoke-verified, including the now-unbroken `POST /storyboard/meeting-recap`
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

> 📌 **Tomorrow:** `DA-R1.1.a + DA-A3` paired sprint via `feature-dev` workflow (Builder + Observer, lightweight) | Est: 40 min, ~$5 | Top unresolved: `_should_two_pass(content, config)` helper (consolidates trigger duplication across 2 callsites). See `.claude/TASK.md` and `Backlog.md` for the full ranked list. If energy is high, stack `DA-S3` (Vertical-aware Frankenstack blocks, +1 hr).

> 🛈 **Date-label note:** internal section headers below say "2026-05-09" — these are writer-error labels added during the late session today (2026-05-08). Git log + archive filenames + tags carry the correct date. All today's work shipped on **2026-05-08**.

---

## 2026-05-09 (later) — DA-R1.1 Meeting-Recap Unblock + Two-Pass Wire

DA-R1.1 from yesterday's backlog turned out to be more than a feature wire — it surfaced and fixed THREE pre-existing production bugs that had been silently 500-ing the `/storyboard/meeting-recap` endpoint. The endpoint had **zero test coverage** before today, which is why the bugs never tripped CI.

### Bugs fixed (in order of discovery)

1. **`extract_content` AttributeError (commit `2e27162`):** `meeting_recap.py:180` was calling a method that does NOT exist on `GeminiStoryboardClient`. Every meeting-recap call was raising AttributeError immediately. Fix: route through `_call_text_model` (the helper DA-R1 added yesterday).

2. **`_parse_json_response` fragile against LLM preamble (commit `ac4a7ac`):** DeepSeek frequently emits `"Here's the structured meeting recap in JSON format:\n\n```json\n{...}\n```"` — preamble before the code fence. The previous parser only stripped a leading triple-backtick, so the function fell into a degraded-response branch. Fix: locate the JSON object by braces (`{...}`) and run through `_repair_json` for robust cleanup.

3. **`summary` returned as JSON array (commit `ac4a7ac`):** Prompt asks for "3-5 bullet executive summary" — DeepSeek interprets as a list. `MeetingRecapResponse.summary: str` rejects with Pydantic ValidationError. Fix: defensive coercion in `process_meeting_recap` joins the list to a multiline string with `•` prefixes.

### Feature wired (the original goal)

**Two-pass narrative+schema augmentation** for long transcripts (≥ 10K chars). After the single-pass parse, runs `build_narrative_extraction_prompt` → `build_schema_mapping_prompt` (the DA-R1 prompt builders) and OVERLAYS the richer `forces_of_progress` and `frankenstack_description` onto the meeting-recap dict. The other 15 keys (job_statement, challenger_reframe, follow_up_email, etc.) come from single-pass and stay untouched. On any failure → graceful degrade to single-pass result with `two_pass_applied=False`.

### Files

| Change | Detail |
|---|---|
| `src/tools/storyboard/meeting_recap.py` (+108/-11) | Fixed 3 bugs above + wired two-pass augmentation |
| `tests/tools/storyboard/test_meeting_recap.py` (new) | 8 tests — net new coverage for `process_meeting_recap` (was 0) |
| `.claude/Backlog.md` | Closed DA-R1.1; new DA-R1.1.a (`two_pass_applied` flag visibility) and DA-A3 expanded |

### Test / lint / mypy delta

| Metric | Before | After | Delta |
|---|---|---|---|
| pytest (excl. live integration) | 1,540 | 1,548 | +8 |
| Mypy errors (`meeting_recap.py`) | 55 | 54 | **−1** (bug fix silenced a pre-existing error) |
| Ruff lint | clean | clean | — |
| Test coverage for `process_meeting_recap` | 0 | 8 mocked + 1 live-LLM round-trip verified | new |

### Live verification — the regression-proof

```bash
curl -X POST https://epiphan-storyboard.vercel.app/storyboard/meeting-recap \
  -H "Content-Type: application/json" \
  -d '{"transcript":"...realistic AV-pain transcript...","audience":"av_director","vertical":"higher_ed"}'
# Was: 500 "Internal Server Error" (silently for weeks)
# Now: 200, 3951 bytes, 27.7s
#   summary: 343-char multiline string with bulleted points
#   forces_of_progress.push: rich pain language from DeepSeek
#   frankenstack_description: correctly names the PC layer (not Canvas/Panopto)
```

### Observer findings

🟢 **GREEN gate** — 0 blockers. Two info-level findings logged as backlog `DA-R1.1.a` (`two_pass_applied` flag visibility) and `DA-A3` (expanded — now covers two trigger-condition duplicates). Audit at `.claude/observers/QUALITY.md` and `ARCH.md` under `## DA-R1.1 (2026-05-09)`.

### New backlog items

- `DA-R1.1.a` — Decide `two_pass_applied` flag visibility (10 min, low). Either expose in `MeetingRecapResponse` or remove from dict and replace with `logger.info`.
- `DA-A3` (expanded) — Consolidate text-path dispatch + two-pass trigger condition. Two callsites now duplicate the trigger logic (`_understand` and `process_meeting_recap`). Roll into a `_should_two_pass(content, config)` helper.

### Tomorrow's lead candidates

The `meeting-recap` endpoint is now actually usable in production. Natural follow-ups:

1. **`DA-R1.1.a`** (10 min) — pick visibility for `two_pass_applied`. Cheap.
2. **`DA-A3`** (30 min) — consolidate the two trigger-condition duplicates into `_should_two_pass`.
3. **`DA-S3`** (1 hr) — Vertical-aware Frankenstack pattern blocks (Higher Ed vs Live Events have different Frankenstacks).
4. **Tighten the meeting-recap prompt** — the `summary` list-vs-string coercion is a band-aid. Updating the prompt to say `"summary": "single multiline string with bullets separated by \\n"` reduces the chance of needing the coercion at all.

```bash
# DA-R1.1.a quick fix
git checkout -b chore/two-pass-applied-visibility main
```

---

## 2026-05-09 (earlier) — DA-R1 Two-Pass Forces Extraction Ship

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
