# Observer: Architecture Report

**Date:** 2026-05-08
**Session:** leverage-day Fix A (SSOT demo dropdowns)
**Project:** epiphan-storyboard
**Observer Model:** claude-sonnet-4-6

---

## Blockers (stop work immediately)

None.

---

## Risks (address this sprint)

**[WARNING] — src/demo/router.py — OpenAPI schema shape change: inline enum replaced by $ref**

Before this change, `GenerateRequest.audience` emitted `"enum": ["av_director", ...]` inline. After, Pydantic v2 emits `"$ref": "#/$defs/AudiencePersona"` and populates `$defs`. This is not a breaking change for FastAPI or the demo UI itself, but any external consumer that introspects `GenerateRequest.model_json_schema()["properties"]["audience"]["enum"]` directly (e.g., a test or a code-gen script) will KeyError. The parity test `test_router_audience_field_uses_audience_persona_enum` already handles both shapes — it is the correct pattern. Worth noting if `src/api.py` exposes the OpenAPI spec to downstream tooling.

---

## Smells (log to backlog)

**[SMELL] — src/demo/_dropdowns.py:73-91 + src/demo/router.py:153 — Dual-nullability: `ArtistStyle.NONE` sentinel and `artist_style: ArtistStyle | None`**

`GenerateRequest.artist_style` is typed `ArtistStyle | None` and has a Python-level default of `None`. But `ArtistStyle` also defines a `NONE = "none"` member. This creates two different ways to represent "no artist style selected": the Python value `None` (field not sent or sent as `null`) and the string `"none"` (UI sends `ArtistStyle.NONE`). Downstream code at `router.py:431` checks truthiness (`if request.artist_style:`), which means `None` → skip, `"none"` → inject into tool_args (accidental pass-through). The downstream `prompts.get_artist_style_instructions` handles this by `dict.get("none", "")` falling back to empty string — so no user-visible bug — but the design has two code paths for the same intent.

Recommended resolution: Remove `ArtistStyle.NONE` from the enum. Make the UI send `""` or nothing when "None" is selected, and let the Pydantic field coerce that to `None`. The `NONE` sentinel exists to keep the UI dropdown non-empty, but that can be solved with an explicit `<option value="">None</option>` in the HTML plus a `@field_validator` that maps `""` to `None`.

**[SMELL] — src/demo/_dropdowns.py — `options_payload()` is a new endpoint with no contract**

`GET /demo/options` is described as a "future-proofing" endpoint (docstring: "once the demo HTML migrates to fetch + populate"). The HTML does not yet consume it. This is forward-looking scope with no immediate consumer. Not harmful, but worth tracking: if the HTML is never migrated, this endpoint becomes dead weight. Add to backlog: either migrate demo.html to fetch-on-load by end of sprint, or mark the endpoint `deprecated=True` to signal it's aspirational.

**[SMELL] — tests/demo/test_dropdown_parity.py — `test_ssot_persona_values_match_audience_persona_enum` asserts bidirectional equality**

The test asserts `ssot_values == enum_values` (line 100). This means SSOT and `AudiencePersona` enum must be exactly equal — no extras in either direction. This is architecturally correct (no orphan SSOT entries, no missing SSOT entries), but it means adding a new persona to `AudiencePersona` in `epiphan_presets.py` will immediately fail this test until `_dropdowns.py` is also updated. That is the intended behavior per the module docstring. Documenting it here so the next developer adding a persona knows to update both files atomically.

---

## Contract Compliance

| Contract | Status | Notes |
|----------|--------|-------|
| No feature contract file found in .claude/contracts/ | [WARNING] | No formal contract — scope inferred from commit messages and docstrings |
| SSOT -> GenerateRequest parity | PASS | Enum imports enforce at module load time |
| SSOT -> HTML parity | PASS (test-enforced) | `test_html_dropdown_options_match_ssot` parametrized over 5 selects |
| AudiencePersona -> SSOT parity | PASS (test-enforced) | `test_ssot_persona_values_match_audience_persona_enum` |
| artist_style downstream behavior | PASS (by accident) | "none" string falls through dict.get to empty string — see QUALITY.md warning |

---

## Devil's Advocate Challenges

| File | Challenge | Verdict |
|------|-----------|---------|
| `src/demo/_dropdowns.py` | Does this file need to exist? Could the enums live in `epiphan_presets.py` alongside `AudiencePersona`? | JUSTIFIED. `epiphan_presets.py` is a domain model for prompt-building; `_dropdowns.py` is a UI presentation concern. Mixing display metadata (emoji, label, optgroup) into the domain model would be a worse separation violation. |
| `src/demo/_dropdowns.py:ArtistStyle.NONE` | `NONE = "none"` is a sentinel value inside an otherwise substantive enum. This is a code smell (nullability encoded in a domain enum). | VALID CONCERN. See Smells section. The `ArtistStyle | None` field already expresses optionality. `NONE` is redundant and creates dual nullability. |
| `src/demo/router.py` `GET /demo/options` endpoint | This endpoint has no consumer today. Adding it before it is needed is speculative generality. | MILD CONCERN. The endpoint is cheap (pure data, no I/O) and the test covers it. Acceptable as scaffolding if the HTML migration is planned. Flag for backlog. |
| `tests/demo/test_dropdown_parity.py:51` | Relative path `Path("static/demo.html")` — does this always resolve correctly? | VALID CONCERN. Logged in QUALITY.md. Should be anchored to `__file__`. |

---

## Monitoring Runs

| Date | Session | Findings | Status |
|------|---------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | 3 risks / 4 smells | archived to .claude/archive/2026-05-07-OBSERVER-ARCH.md |
| 2026-05-08 | leverage-day Fix A (SSOT demo dropdowns) | 0 blockers / 1 risk / 3 smells | OPEN |
| 2026-05-08 | leverage-day Fix B (grounding integration tests) | 0 blockers / 0 risks / 2 smells | OPEN |

---

## Fix B (2026-05-08) — Architecture

**Date:** 2026-05-08
**Files audited:** `tests/storyboard/test_grounding_integration.py`, `tests/fixtures/transcripts/` (3 files)

### Regression Scenario Analysis

**Refactor scenario A (remove `problem_statement_anchor` parameter from `_build_transcript_prompt`):** CAUGHT. The `test_grounding_chain_injects_anchor` test asserts that `"VERBATIM PAIN LANGUAGE"` appears in the assembled prompt. If the anchor injection call is removed, this header disappears and the test fails. The chain assertion at Step 3 is the correct kill-switch.

**Refactor scenario B (Frankenstack block reintroduces Crestron/Extron/Q-SYS):** CAUGHT. `test_prompt_does_not_name_forbidden_brands` strips the literal transcript from the prompt and checks only builder-added content against `FORBIDDEN_BRAND_TOKENS`. The transcript-strip technique is sound — it isolates the builder's contribution, not the fixture's vocabulary.

**Refactor scenario C (new AudiencePersona member without problem_statements records):** NOT CAUGHT. The test only covers three hard-coded `GROUNDED_COMBOS`. A new persona silently joins the Phase-2 degradation bucket with no CI signal. See QUALITY.md [INFO] for the recommended all-personas enumeration test.

### Fixture Location Convention

Fixtures live at `tests/fixtures/transcripts/`. The existing test tree has no other `fixtures/` directory — this is net-new. The `tests/storyboard/` subdirectory has a `transcripts/` sub-path only implicitly via the path calculation `Path(__file__).resolve().parents[1] / "fixtures" / "transcripts"`. This resolves to `tests/fixtures/transcripts/` when `__file__` is `tests/storyboard/test_grounding_integration.py`, which is correct.

The path anchor pattern matches the Fix A resolution for `test_dropdown_parity.py` — it is the right pattern and will resolve correctly from any pytest invocation directory.

### Test File Location

`tests/storyboard/` is the correct location for this file. It requires no API keys, no network, and no live database — all assertions operate on the output of in-process Python functions. Placing it under `tests/integration/` would be misleading (that directory is gated by API key availability). The storyboard subdirectory already contains `test_api_integration.py` and `test_schemas.py`, so `test_grounding_integration.py` follows the local naming convention.

### Devil's Advocate Challenges (Fix B)

| File | Challenge | Verdict |
|------|-----------|---------|
| `tests/fixtures/transcripts/` | Should fixtures live under `tests/storyboard/fixtures/` to co-locate with the test that uses them? | MILD CONCERN. The `tests/fixtures/` root placement is consistent with a shared-fixtures convention and keeps the storyboard test directory clean. The path anchor in the test is explicit. Acceptable as-is unless a second test module needs its own fixture subdirectory. |
| `test_grounding_chain_graceful_when_no_statements` | This test re-uses the `higher_ed` fixture for a `government` vertical call. Does that misrepresent the test's intent? | VALID CONCERN. The graceful-degradation test is checking prompt-builder behavior, not transcript relevance, so reusing an unrelated fixture is technically correct. But a reader could mistake it for a government-vertical fixture. A one-line comment — `# Fixture content is irrelevant here; we're testing builder behavior for an unseeded vertical` — would prevent confusion. |
| `FORBIDDEN_BRAND_TOKENS = ["Crestron", "Extron", "Q-SYS"]` | Is this list maintained? If a fourth brand is added to the cleanup contract, this constant won't update automatically. | MILD CONCERN. The list is defined once at module level with a clear reference to the cleanup commit. If the BDR brand-safety contract expands, this constant is the single place to update. The risk is forgetting to update it — there is no enforcement mechanism. A comment linking to an authoritative source (e.g., a backlog item or a doc) would reduce drift risk. |
| `test_prompt_carries_persona_signal` | Asserting `persona in prompt` is a loose check. `"av_director"` would pass even if it appeared only in the transcript content itself. | VALID CONCERN. The test does not strip the transcript before checking. If a fixture happened to mention "av_director" verbatim, the test would pass even if the builder omitted the persona signal. The brand-agnosticism tests do strip the transcript — this test does not. Lower severity because persona names are unlikely to appear verbatim in the synthetic transcripts, but the inconsistency is worth noting. |

---

## DA-R1 (2026-05-09) — Architecture

**Session:** leverage-day +1 / DA-R1 two-pass narrative+schema Forces extraction in `gemini_client.py`.
**Goal realized:** Phase-1.3 prompt builders (`build_narrative_extraction_prompt`, `build_schema_mapping_prompt`) are now wired into the production `_understand` orchestration loop with a length+confidence trigger.

### Blockers
None.

### Risks
None — all risks below are documented in the plan and addressed by the design.

### Smells (log to backlog)

**[SMELL] — `_call_text_model` duplicates dispatch logic that lives inline in `_understand`.**

The new `_call_text_model` (lines 758-772) mirrors the text-path dispatch in `_understand` (lines 853-878 — DeepSeek primary, Gemini if Google API key, DeepSeek fallback). I deliberately did NOT refactor `_understand` to use the new helper because the goal of DA-R1 is the orchestration wiring, not a refactor of the entire client. Forward-debt: when somebody touches the text-path routing rules (e.g., adding Qwen as a third text provider), they'll need to update both call sites or refactor first. Worth a backlog item to consolidate after DA-R1 ships and stabilizes — call it `DA-A3`.

### Contract Compliance

| Contract | Status | Notes |
|----------|--------|-------|
| `StoryboardUnderstanding` schema is additive (no required field changes) | ✅ PASS | New fields `forces_of_progress` and `frankenstack` default to `None`. Verified across 16 callsites in `src/` + `tests/`. |
| Two-pass replaces refinement (no double-burn) | ✅ PASS | `_understand` returns directly from `_extract_via_two_pass` when triggered, skipping `_refine_extraction`. |
| Mocking discipline (no live LLM in CI) | ✅ PASS | All 14 new tests use `MagicMock(text=...)` with `side_effect`. Zero new `requires_api_keys` markers. |
| Brand-agnosticism on new fixture | ✅ PASS | 17,074-char fixture contains zero Crestron/Extron/Q-SYS tokens. |
| Mypy delta | ✅ PASS | 46 errors pre, 46 errors post — exact baseline preserved. |
| Ruff lint delta on changed files | ✅ PASS | 0 new warnings; 1 pre-existing B904 at line 313 (not my code). |

### Devil's Advocate Challenges

| File | Challenge | Verdict |
|------|-----------|---------|
| `_extract_via_two_pass` | Why `max(single, two_pass)` for confidence merge? Could pick the two-pass value directly since it had a richer narrative intermediate. | DEFENSIBLE. Max is the safer choice — if the schema-mapping pass returns a low confidence (parse went OK but the LLM signaled low certainty), we don't want to *downgrade* the single-pass result. The single-pass already had its own confidence signal. Max means "two-pass can only improve, never regress." |
| Trigger condition `len(content) >= threshold OR conf < threshold` | The OR short-circuits to two-pass on degenerate input (short transcript, parse error → conf=0.0). 2× LLM cost on a malformed input. | DEFENSIBLE BUT INSTRUMENTABLE. Desirable behavior — we want to retry low-confidence regardless of length. If cost dashboards ever show a spike, add a `min_chars_for_two_pass` floor (e.g., 1000) to gate the conf-based trigger. Not a blocker today. |
| Schema extension via Option B (additive) instead of Option A (rewrite pass-2 prompt) | Option A is "purer" — single source of extraction truth. Option B keeps two flows. | DEFENSIBLE. User picked B explicitly during brainstorming for backwards-compat. Option A would have required prompt-engineering risk (large changes to a tested prompt) and would have made the rollout less safe. B preserves the existing single-pass quality bar and adds richer fields on top. |
| Why does `build_schema_mapping_prompt` exist if we don't rewrite it? | The prompt was shipped in Phase 1.3 and never invoked. DA-R1 is its first caller. | NOT A CONCERN. This is exactly what DA-R1 was scoped to do — wire the unused infrastructure. The prompts had unit tests already (`test_prompt_builders.py:312-349`). The integration call was the missing piece, and that's what this fix delivers. |
| Why isn't `meeting_recap.py` also wired? | `meeting_recap.process_meeting_recap` uses its own prompt builder, not `understand_transcript`. Two-pass benefits would compound there too. | LEGITIMATE FOLLOWUP. Out of scope for DA-R1 (which targets `gemini_client.py` per the backlog). Worth a stretch goal in the plan or a follow-up backlog item — `DA-R1.1` to wire two-pass into `process_meeting_recap`. |

### Monitoring Runs

| Date | Session | Findings | Status |
|------|---------|----------|--------|
| 2026-05-08 | leverage-day Fix B | 0 blockers / 0 risks / 0 critical | OPEN — see Fix B section |
| 2026-05-09 | DA-R1 two-pass extraction | 0 blockers / 0 risks / 1 smell (`DA-A3` follow-up) / 0 critical | **🟢 GREEN — ship** |
