# Observer: Code Quality Report

**Date:** 2026-05-08
**Session:** leverage-day Fix A (SSOT demo dropdowns)
**Project:** epiphan-storyboard
**Observer Model:** claude-sonnet-4-6

---

## Critical (must fix before merge)

None.

---

## Warnings (fix or log to backlog)

**[WARNING] — src/demo/router.py:431 — ArtistStyle.NONE passes truthy string "none" to tool layer**

With `use_enum_values=True`, `ArtistStyle.NONE` becomes the plain string `"none"` at runtime. The guard on line 431 (`if request.artist_style:`) evaluates `"none"` as truthy, so it is injected into `tool_args` and forwarded to `unified_storyboard.run()`. Downstream, `prompts.get_artist_style_instructions("none")` does `artists.get("none", "")` — since `"none"` is not a dict key, it returns `""` and is harmless. But the intent (no overlay) leaks an unnecessary key into `tool_args` every time the user selects "None" in the UI.

Suggested fix: Either (a) normalize at the router boundary — `if request.artist_style and request.artist_style != "none":` — or (b) keep `artist_style: ArtistStyle | None = None` in `GenerateRequest` and treat `NONE` as a UI-only sentinel that maps to Python `None` in a validator (`@field_validator`). Option (b) is cleaner and removes the dual-nullability ambiguity (`None` vs `"none"`).

---

**[WARNING] — tests/demo/test_dropdown_parity.py:51 — HTML path is relative, not anchored**

`Path("static/demo.html").read_text()` uses a relative path. If pytest is invoked from a directory other than the project root, the test silently returns `set()` (see the helper's fallback), and the assertion `html_values == ssot_values` becomes `set() == ssot_values`, which fails loudly — but with a confusing error message rather than a clear "file not found." Better to anchor: `Path(__file__).parents[2] / "static" / "demo.html"`.

---

## Info (nice to have)

**[INFO] — src/demo/_dropdowns.py — optgroup labels are not tested**

The `Option.group` field (e.g., "ATL — Decision Makers", "CHANNEL — Partners") is display metadata that lives only in `_dropdowns.py` and is replicated as `<optgroup label="...">` in `static/demo.html`. The parity tests guard `<option value>` but not `<optgroup label>`. If an optgroup label changes in the HTML, no test fails. Low risk (labels are cosmetic), but worth noting as an untested surface.

**[INFO] — No new TODO/FIXME/HACK/XXX/TEMP markers introduced**

Zero tech-debt markers found in the three changed files (`src/demo/router.py`, `src/demo/_dropdowns.py`, `tests/demo/test_dropdown_parity.py`). The existing `# NEW ARTIST STYLE` and `# MX/LATAM ARTIST STYLES` comments in `src/tools/storyboard/prompts.py` pre-date this change.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned | 5 (router.py, _dropdowns.py, test_dropdown_parity.py, prompts.py, unified_storyboard.py) |
| Critical findings | 0 |
| Warnings | 2 |
| Info items | 2 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1-1.3 | 6 | 7 (0C/4W/3I) | archived to .claude/archive/2026-05-07-OBSERVER-QUALITY.md |
| 2026-05-08 | leverage-day Fix A (SSOT demo dropdowns) | Read-only audit of GenerateRequest SSOT refactor | 5 | 4 (0C/2W/2I) | OPEN |
| 2026-05-08 | leverage-day Fix B (grounding integration tests) | Read-only audit of test_grounding_integration.py + 3 fixtures | 5 | 2 (0C/0W/2I) | OPEN |

---

## Fix B (2026-05-08) — Quality

**Date:** 2026-05-08
**Files audited:** `tests/storyboard/test_grounding_integration.py`, `tests/fixtures/transcripts/higher_ed_lecture_capture_synthetic.txt`, `tests/fixtures/transcripts/legal_court_recording_synthetic.txt`, `tests/fixtures/transcripts/live_events_venue_synthetic.txt`

### Test Run Results

All 13 tests pass in 0.02s. Full suite (excluding integration): 1506 passed. Ruff: all checks passed.

### Findings

**[INFO] — tests/storyboard/test_grounding_integration.py — Coverage gap: new AudiencePersona members without problem_statements records are not caught**

`test_grounding_chain_injects_anchor` only covers the three hard-coded `GROUNDED_COMBOS`. If a developer adds a new persona to `AudiencePersona` without seeding `problem_statements`, this file catches nothing — the persona simply joins the Phase-2 silent-degradation bucket without warning. There is no test that iterates all `AudiencePersona` members and asserts each either (a) has at least one problem statement or (b) is explicitly enumerated in an allowed Phase-2 set.

Suggested fix: Add a `test_all_personas_either_grounded_or_phase2_declared()` test that calls `get_problem_statements(vertical, persona)` for every `AudiencePersona` and fails if any new member is in neither a grounded set nor a declared Phase-2 allowlist. This converts a silent-degradation risk into a loud CI failure at persona-addition time.

**[INFO] — tests/fixtures/transcripts/ — Fixtures are 4.2–4.5 KB (brief but structurally valid)**

The three fixtures clock in at 4,218–4,461 bytes (roughly 40 lines each), representing 19–28 minute calls. This passes the `>1500 char` sanity assertion with headroom but is shorter than a real Gong transcript of that stated length (which would typically be 15,000–25,000 chars). For the current test purpose — asserting prompt structure, not LLM extraction quality — the size is adequate. If `match_statements_to_transcript` scoring is ever exercised in a test, the fixtures may need to be more verbose to produce meaningful signal-match counts.

No TODO/FIXME/HACK/XXX/TEMP markers introduced. No new dependencies added. No silent failures or empty catch blocks in the new test file.

### Fix B Quality Metrics

| Metric | Value |
|--------|-------|
| Tests added | 13 |
| Tests passing | 13 |
| Tests failing | 0 |
| Ruff warnings | 0 |
| New tech-debt markers | 0 |
| New dependencies | 0 |
| Coverage gaps flagged | 1 (all-personas enumeration) |

---

## DA-R1 (2026-05-09) — Quality

**Session:** leverage-day +1 / DA-R1 two-pass narrative+schema Forces extraction
**Files changed:** `src/tools/storyboard/gemini_client.py` (+189/-27), `tests/tools/storyboard/test_gemini_client.py` (+454), `tests/storyboard/test_grounding_integration.py` (+43), `tests/fixtures/transcripts/higher_ed_strategy_review_long_synthetic.txt` (new, 17,074 chars).
**Builder verification before audit:** 1540 pytest pass (+17 net new), mypy 46 (baseline preserved, zero new errors), ruff clean on changed files.

### Critical (must fix before merge)
None.

### Warnings (fix or log to backlog)
None.

### Info (nice to have)

**[INFO] — `_extract_via_two_pass` catches `Exception` broadly** (`gemini_client.py:711-715`)

The method wraps narrative+schema+parse in a single try/except that catches `Exception` and returns `single_pass_result` unchanged with a `logger.warning`. This is appropriate graceful degradation — the existing `_refine_extraction` (lines 626-630) uses an identical pattern with the same intent (preserve the known-good single-pass output rather than fail the whole understand call). The warning IS logged with the exception type and message, so debugging is not blind. Not a silent-failure regression.

**[INFO] — Cost-trigger sanity** (`gemini_client.py:_understand`)

Two-pass fires for transcripts when `len(content) >= 10_000` OR `extraction_confidence < 0.75`. The OR has a footgun: a malformed JSON in single-pass produces `extraction_confidence == 0.0` which trips the trigger even on a 200-character transcript. This is desirable (we want to retry low-confidence extractions) but doubles the cost on degenerate input. Acceptable in production; worth instrumenting if it ever shows up in cost dashboards.

**[INFO] — Test mocking discipline** — 54 mock invocations across the new tests; zero `real_api` / `live_api` / `requires_api_keys` markers introduced. The new test class `TestUnderstandRoutesToTwoPass` parametrizes via `MagicMock(text=...).side_effect = [responses]` to inject sequential LLM responses (single-pass + narrative + schema). Pattern matches the existing `TestUnderstandCodeMocked` class. CI-cheap and deterministic.

**[INFO] — Long fixture brand-agnosticism** — `higher_ed_strategy_review_long_synthetic.txt` (17,074 chars) contains zero Crestron/Extron/Q-SYS tokens. Frankenstack-style language ("classroom-PC layer", "software encoder", "[INAUDIBLE]") matches the convention from yesterday's three shorter fixtures. Multi-speaker structure (CIO, AV Director, VP, Faculty Senate, BDR) makes the long-context two-pass actually exercise narrative extraction across viewpoints rather than a single-voice monologue.

### Code Quality Metrics

| Metric | Value |
|--------|-------|
| Tests added | 17 (14 in test_gemini_client.py, 3 in test_grounding_integration.py) |
| Tests passing | 17/17 |
| Tests failing | 0 |
| Mypy delta | 0 (46 baseline preserved) |
| Ruff warnings introduced | 0 |
| New tech-debt markers | 0 |
| New dependencies | 0 |
| Coverage gaps flagged | 0 |
| StoryboardUnderstanding callsites verified backwards-compat | 16 (all in src/ + tests/, all pass) |

**Gate:** 🟢 GREEN — ship to prod.
