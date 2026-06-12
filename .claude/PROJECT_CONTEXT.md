# Project Context: epiphan-storyboard

**Updated:** 2026-06-12 (end of day — locked via /end workflow)
**Branch:** main @ 6dc3a32 (clean, pushed; stale feature branch deleted)
**Tags:** v1.3-meeting-recap-unblock · v1.2-two-pass-extraction · v1.1-leverage-day · v1.0-bdr-workflow (all pushed to origin)
**Production:** https://epiphan-storyboard.vercel.app — debt-paydown sprint live + smoke-verified (deployed 2026-06-12)
**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, Vercel serverless

> 📌 **Tomorrow:** `DA-R2 + DA-A2` (~1.5 hr, ~$5) — DA-R2 is the only medium-impact open item (Phase-2 verticals silently degrade with no UI/log signal); DA-A2 migrates demo dropdowns to fetch `/demo/options`, killing the last drift surface. Stack DA-A1 if energy is high. TDD → observer signoff → single deploy + smoke. | **Observer notes:** 0 blockers; top unresolved flags are DA-B2 (html2canvas may blank card-header gradient in PNG downloads — needs 15-min manual repro) and the **budget config question** ($87.43 day vs $15 cap, $453.66 MTD vs $100/mo — decide whether caps are stale or spend needs reining in).

---

## 2026-06-12 (EOD) — Debt-paydown sprint: all 6 tasks shipped + security gate fully clean

8 commits (`a1df5d0` → `6dc3a32`), all pushed and deployed. Tests 1,548 → **1,574** (+26). Mypy **−1** (373→372). Gitleaks: **"no leaks found"** for the first time (historical placeholder pinned in `.gitleaksignore`).

| Shipped | Commit |
|---|---|
| Retroactive observer audit of the un-closed 06-10 session (1C/3W/2I + 0B/3R/5S, all dispositioned) | `a1df5d0` |
| fonts.py hardening: status-vs-network 502 granularity + per-key asyncio.Lock + 8 tests (was zero coverage) — cleared the CRITICAL | `3187555` |
| DA-A3 ×3: `should_run_two_pass()` SSOT, demo cap derived from config (was hardcoded 9000), `_understand` text dispatch collapsed into `_call_text_model` | `8d74e24` |
| DA-R1.1.a: `two_pass_applied` first-class on `MeetingRecapResponse` | `92ff4c8` |
| DA-A4: SSOT emoji/label sync (🖼️ 🖌️ 📋) | `6544dd7` |
| Vercel truth: verified via API — plan=Pro, `timeout: 300` IS applied (audit's plan-gating RISK was wrong), memory 1769 rounds to 2048 → config now says 2048 | `7137314` |
| EOD lockdown: observer archive, doc sync, `.gitleaksignore`, stale branch deleted | `429a167`, `6dc3a32` |

**Key facts for future sessions:** memory file `vercel-pro-function-limits.md` records the verified Pro-plan limits and the applied-config API check (`/v11/deployments/{id}/builds`); installed Vercel CLI 50.4.11 lacks `vercel api` — upgrade recommended. Two-pass threshold logic now lives ONLY in `should_run_two_pass` (gemini_client.py) — never restate the trigger.

---

## 2026-06-12 — /begin catch-up: retroactive audit of the 2026-06-10 session

The 2026-06-10 session (5 commits, `c5a4cb1` → `177b539`) shipped a demo brand re-skin, the brand storyboard card with overlay text, /demo/generate timeout mitigations (vercel `maxDuration: 300`, live progress UI, 9K input cap), the Söhne font same-origin proxy (`src/brand/fonts.py`), and wired transcript compaction into `meeting_recap.py` — but **skipped /end**: no observer audit, stale docs, and a miscounted metrics entry.

Today's /begin ran the audit retroactively over `HEAD~5..HEAD`:

| Report | Result |
|---|---|
| Quality (haiku) | 1 CRITICAL (`fonts.py` broad except masks auth-vs-network) · 3 WARNINGS (`os.getenv` strip rule, fonts.py zero tests, inline 9000 magic number) · 2 INFO |
| Architecture (sonnet) | 0 BLOCKERS · 3 RISKS (third copy of two-pass threshold in demo router; vercel maxDuration plan-gating + memory 1769→2048 rounding; fonts.py cache race) · 5 SMELLS |

All findings dispositioned in `.claude/observers/QUALITY.md` / `ARCH.md` — fix-now items became today's sprint tasks 2/3/5/6; the rest logged to Backlog (DA-V1, DA-Q1, DA-B1, DA-B2, DA-A4).

**Devil's advocate notes:** the fonts.py CRITICAL is arguably WARNING-grade (error is logged + 502 returned, nothing swallowed). The vercel `maxDuration: 300` may be a silent no-op depending on plan — the timeout "fix" may only appear fixed because the 9K cap independently keeps generations short; verify before trusting. Budget tracker shows $57.87 today / $424 MTD vs $15-day/$100-mo caps — config likely stale, flagged for Tim.

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
