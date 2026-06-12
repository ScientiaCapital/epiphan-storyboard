# Backlog

## Security / Tooling

- ~~**Add `.gitleaksignore` for historical test fixtures**~~ — **DONE 2026-06-12** during /end security sweep. Fingerprint pinned; `gitleaks detect` now reports "no leaks found".

## Tech Debt / Architecture

- **DA-B1: fonts.py — degrade gracefully instead of 502 on upstream failure** (effort: 15 min, impact: low — ops hygiene) **[NEW 2026-06-12]**
  - `src/brand/fonts.py` raises `HTTPException(502)` when chat.epiphan.com is unreachable. Browser falls back to system fonts fine, but the 5xx pollutes Vercel error metrics and may trigger CDN retries. Consider 200 empty-body with `font/otf` content-type, or a long-cached last-known-good response.
  - Source: 2026-06-12 arch audit (smell).

- **DA-B2: downloadCard() html2canvas may blank the teal gradient header** (effort: needs repro first, impact: medium if real — broken PNG exports) **[NEW 2026-06-12]**
  - `static/demo.html` uses `html2canvas(card, { scale: 2, useCORS: true })`; inline-styled gradient + foreignObject rendering is known-flaky with cross-origin stylesheets (Tailwind CDN). Downloaded PNGs may render the header area white while text sections survive. Manually repro before fixing.
  - Source: 2026-06-12 arch audit (smell).

- **DA-A4: SSOT emoji/label drift in `_dropdowns.py`** (effort: 5 min, impact: cosmetic) **[NEW 2026-06-12 — stretch task today]**
  - demo.html changed diego_rivera 🎺→🖼️, siqueiros ⚡→🖌️, and `Infograph 📐`→`Infographic 📋` without updating `OUTPUT_FORMAT_OPTIONS`/`ARTIST_STYLE_OPTIONS`. Parity test checks values only, so no functional break. Sync the SSOT and consider extending the parity test to labels/emoji.
  - Source: 2026-06-12 arch audit (smells ×2, merged).

- **DA-V1: Integration test documenting the maxDuration ↔ 9K-cap coupling** (effort: 30 min, impact: low until someone raises the cap) **[NEW 2026-06-12]**
  - vercel.json `maxDuration: 300` and the demo 9K input cap jointly prevent /demo/generate timeouts, but nothing tests or documents the coupling. If the cap is raised without revisiting the function limit, timeouts return silently. Blocks on DA-A3 (cap derivation) landing first.
  - Source: 2026-06-12 quality audit (info).

- **DA-Q1: Structured error codes on `AgentSession`** (effort: 1 hr, impact: medium — test reliability) **[NEW 2026-06-12]**
  - `tests/integration/test_full.py:49-80` `_skip_if_llm_unavailable()` string-matches `session.error` for "authentication"/"timeout"/"429" — brittle to provider phrasing changes. Add an error-code enum (AUTH_ERROR, RATE_LIMIT, TIMEOUT, …) populated in `runner.py` where the exception is caught.
  - Source: 2026-06-12 quality audit (info).

- **DA-Q2: `.strip()` sweep on remaining `os.getenv()` callsites** (effort: 10 min, impact: low — known footgun class) **[NEW 2026-06-12]**
  - `src/api.py:109-111` and `src/storyboard/router.py:56-58` pass raw env values to StateManager without `.strip()`, violating the project rule born from the 2026-02-19 trailing-newline incident. Pre-existing, not from the 06-10 session. Bundle with the next touch of either file.
  - Source: 2026-06-12 quality audit (warning).

- **DA-A3: Consolidate text-path dispatch into `_call_text_model`** (effort: 45 min, impact: medium — now 3 copies) **[UPDATED 2026-06-12 — in today's sprint]**
  - **Updated by 2026-06-12 audit**: a THIRD copy of the threshold concept landed in commit `9236f4c` — `src/demo/router.py` hardcodes `DEMO_MAX_TEXT_CHARS = 9000` ("below the two-pass threshold") inside the handler. If `two_pass_threshold_chars` is tuned in config, the demo cap silently diverges. Fix alongside the helper: derive the demo cap from `GeminiConfig.two_pass_threshold_chars` (threshold − margin).
  - DA-R1 added `_call_text_model` (`src/tools/storyboard/gemini_client.py:758-772`) but did not refactor the inline text-path dispatch in `_understand` (lines 853-878). The two now mirror each other. When somebody adds a new text provider (e.g. Qwen-text, Claude-via-OpenRouter), they'll need to update both sites — easy to miss.
  - **Updated by DA-R1.1 audit (2026-05-09)**: a SECOND duplicate of the same trigger condition (`enable_two_pass_extraction AND len(content) >= threshold`) now lives in `meeting_recap.py:182-185`. Same risk class. Roll into a single `_should_two_pass(content, config)` helper when consolidating.
  - Fix: refactor `_understand`'s text branch to call `_call_text_model(prompt)` instead of the inline if/elif AND extract the trigger condition into `_should_two_pass`. Verify all tests still pass; mypy delta zero.
  - Source: Observer audits 2026-05-09 (DA-R1 + DA-R1.1). See `.claude/observers/ARCH.md`.

- **DA-R1.1.a: Decide `two_pass_applied` flag visibility** (effort: 10 min, impact: low — observability hygiene) **[NEW 2026-05-09]**
  - DA-R1.1 added `result["two_pass_applied"]: bool` to the meeting-recap dict but did NOT expose it in `MeetingRecapResponse`. With Pydantic's default `extra="ignore"` the flag is silently dropped at the API boundary. Today it's only visible if developers log the raw dict.
  - Fix: pick one — (a) add `two_pass_applied: bool = False` to `MeetingRecapResponse` for first-class observability; (b) remove the flag from the dict and replace with a `logger.info(...)` line inside `process_meeting_recap`.
  - Source: Observer audit 2026-05-09 (DA-R1.1). See `.claude/observers/QUALITY.md`.

- ~~**DA-R1.1: Wire two-pass into `meeting_recap.process_meeting_recap`**~~ — **DONE 2026-05-09** in commit (see PROJECT_CONTEXT.md "DA-R1.1 ship" section). Bundled with the critical broken-endpoint fix (`extract_content` → `_call_text_model`). New tests: 6 in `tests/tools/storyboard/test_meeting_recap.py`. Follow-ups in `DA-A3` (now covers two duplicates) and `DA-R1.1.a` (above).

- **DA-A1: Resolve `ArtistStyle` dual-nullability** (effort: 30 min, impact: low — design hygiene, not user-visible) **[NEW 2026-05-08]**
  - `src/demo/_dropdowns.py:73-91` defines `ArtistStyle.NONE = "none"` while `GenerateRequest.artist_style: ArtistStyle | None` (router.py:153) also allows `None`. Two representations of "no overlay": Python `None` and string `"none"`. Downstream `prompts.get_artist_style_instructions("none")` falls through `dict.get` to empty string — no user-visible bug, but the design has redundant code paths.
  - Recommended fix: remove `NONE` from the enum, change demo HTML to `<option value="">🎨 None</option>`, add a `@field_validator` on `GenerateRequest.artist_style` that maps `""` to `None`. Single source of truth for "no overlay."
  - Source: Observer audit 2026-05-08 (Fix A SSOT). See `.claude/observers/QUALITY.md` warning, `.claude/observers/ARCH.md` smell.

- **DA-A2: Migrate `static/demo.html` dropdowns to fetch `/demo/options`** (effort: 1 hr, impact: low — eliminates the last drift surface) **[NEW 2026-05-08]**
  - Fix A added the `/demo/options` endpoint as future-proofing. The HTML still ships static `<option>` blocks. Migrating to fetch-on-load + JS-populate would eliminate the third drift surface entirely (HTML can no longer disagree with the SSOT — it consumes it). Trade-off: extra network round-trip on page load.
  - If we don't migrate this sprint, the parity test (`test_html_dropdown_options_match_ssot`) keeps the surface honest. Endpoint is then redundant scaffolding — either migrate or mark `deprecated=True`.
  - Source: Observer audit 2026-05-08 (Fix A SSOT). See `.claude/observers/ARCH.md` smell.

- **DA-W2: Tighten exception handling in `build_problem_statement_anchor`** (effort: 15 min, impact: low) **[NEW 2026-05-07]**
  - `src/tools/storyboard/prompt_builders.py:140` catches bare `except Exception:`. Narrow to `(ValueError, ImportError)` and add `logger.debug(...)` so silent grounding-degradation is observable.
  - Source: DA observer audit, finding W-2.

- **DA-W3 / S-2: Phase 2 — extend `AudiencePersona` enum or annotate stretch mappings** (effort: 30 min, impact: medium for Phase-2 verticals) **[NEW 2026-05-07]**
  - `DOC_PERSONA_ALIASES` in `src/tools/storyboard/problem_statements.py` has 9 stretch mappings (e.g., "Senior Pastor" → `venue_manager`, "IT Director / CIO" → `law_firm_it`). Phase-2 verticals (Government, K-12, Houses of Worship) most affected.
  - Options: (a) extend enum with `it_director`, `pastor`, `volunteer_av_lead`, etc.; (b) add `note_for_reviewer` comment beside each stretch mapping. (a) preferred long-term.
  - Source: DA observer audit, findings W-3 + S-2 (deduplicated).

- **DA-W4: Add 5 edge-case tests for `transcript_compactor`** (effort: 30 min, impact: low until production data hits a gap) **[NEW 2026-05-07]**
  - Cases: CRLF line endings, unicode speakers (`José Ramírez:`, `张伟:`), `target_chars=0`, >1 MB transcript, weird speaker punctuation (`Dr. (Dr.) Smith:`).
  - Source: DA observer audit, finding W-4.

- **DA-I2: Skip `key_moments` block when compaction not needed** (effort: 10 min, impact: low — saves tokens on short calls) **[NEW 2026-05-07]**
  - When `compaction_ratio == 1.0`, `_build_transcript_prompt` injects both `=== KEY MOMENTS ===` and `=== FULL CONTEXT ===` containing duplicate content.
  - Skip the KEY MOMENTS block when `len(full_context) <= key_moments_chars`.
  - Source: DA observer audit, finding I-2.

- **DA-R1: Wire two-pass narrative+schema Forces extraction into `gemini_client.py`** (effort: 2–3 hr, impact: HIGH — full Phase-1.3 Fix #2 realization) **[NEW 2026-05-07]**
  - Phase 1.3 shipped `build_narrative_extraction_prompt` + `build_schema_mapping_prompt` as infrastructure-ready, but the orchestration call site that runs both passes for transcript-heavy meeting-recap requests doesn't exist yet. Single-pass extraction still runs.
  - Action: in `src/tools/storyboard/gemini_client.py`, when transcript ≥ ~10 K chars or `extraction_confidence < 0.75`, route through the narrative→schema two-pass instead of the rigid single-pass. Reuse the existing refine plumbing at `gemini_client.py:516–630`.
  - Source: DA observer audit, finding R-1 + I-3.

- **DA-R2: Make Phase-2 vertical degradation visible** (effort: 30 min, impact: medium UX) **[NEW 2026-05-07]**
  - When a user picks Government / K-12 / etc. (vs Phase-1 verticals) the storyboard pipeline runs but the matcher silently returns `[]`. Output is lower quality without any signal.
  - Action: (a) add UI banner in `static/demo.html` flagging Phase-1 verticals; (b) emit `logger.debug` in `prompt_builders.build_problem_statement_anchor` when the (vertical, persona) combo has zero records.
  - Source: DA observer audit, finding R-2.

- **DA-R3: Embedding-based scoring fallback for `compact_transcript`** (effort: 1 day, impact: low until volume) **[NEW 2026-05-07]**
  - Current keyword-overlap scoring drops semantic-rich content with no surface keywords ("our team kludges around it with a homegrown thing").
  - Action: add an embedding fallback (cheap model) that complements keyword scoring. Defer until Phase-1 production traffic surfaces drops.
  - Source: DA observer audit, finding R-3.

- **DA-S1: End-to-end integration test for survey → grounding → prompt → output** (effort: 1 hr, impact: medium — catches regressions across module boundaries) **[NEW 2026-05-07]**
  - All Phase-1 modules are unit-tested independently but no test exercises the full chain: vertical+persona → problem-statement anchor → prompt builder output → assert verbatim text appears.
  - Action: add `tests/storyboard/test_grounding_integration.py` with 3 fixtures covering each Phase-1 vertical.
  - Source: DA observer audit, smell S-1.

- **DA-S3: Vertical-aware Frankenstack pattern blocks** (effort: 1 hr, impact: low) **[NEW 2026-05-07]**
  - `_FRANKENSTACK_PATTERN_BLOCK` is a single global constant. Higher Ed / Live Events / Courts have different Frankenstacks in the wild.
  - Action: parameterize per-vertical pattern blocks in Phase 2.
  - Source: DA observer audit, smell S-3.

- **DA-S4: Real-world transcript fixtures for compactor + prompt-builder tests** (effort: 1 hr, impact: medium — catches Clari/Gong-specific quirks) **[NEW 2026-05-07]**
  - Existing fixtures use synthetic "Speaker 1: filler" content. Real Clari exports have timestamps, speaker IDs, [INAUDIBLE] tokens, etc.
  - Action: capture one anonymized real transcript per Phase-1 vertical and use as a regression fixture.
  - Source: DA observer audit, smell S-4.

- **Single-source-of-truth for demo dropdowns** (effort: 1–2 hr, impact: medium)
  - `static/demo.html` and `src/demo/router.py` keep parallel `visual_style` / `vertical` / `audience` Literal lists. Adding to one without the other 422s.
  - Options: (a) generate HTML `<option>` from a JSON manifest at `/demo/options`; (b) codegen both from a single Python source. Option (a) preferred.
  - Logged: 2026-05-05

- **Vercel `/static/*` routing is dead** (effort: 30 min, impact: low until it bites)
  - `app.mount("/static", StaticFiles(...))` returns 404 under `@vercel/python`. Demo only works via `@app.get("/")` → `FileResponse("static/demo.html")`. Any future static asset URL will 404.
  - Action: inline CSS/JS into `demo.html`, OR migrate routing to `vercel.ts` with rewrites.
  - Logged: 2026-05-05 (see memory: `vercel-static-mount-broken.md`)

- **`av_integrator` may be missing from `audience` Literal** (effort: 5 min, impact: low)
  - Memory: 17 personas including `av_integrator`. `src/demo/router.py` audience Literal lists ~16. Same regression class as the Blueprint bug.
  - Logged: 2026-05-05

## Quality

- **Pre-existing integration test failures** (effort: unknown, impact: low — flaky)
  - 7 tests in `tests/integration/test_full.py` fail with `session.status == FAILED` instead of `COMPLETED`. They hit live LLM APIs.
  - Action: investigate flaky-by-design vs needs-credentials-in-CI vs genuinely broken.
  - Logged: 2026-05-05

- **Pre-existing mypy errors** (effort: 1 hr, impact: low)
  - 46 mypy errors across 9 files (today's count, down from 58 — Phase-1 work added zero new errors). Predates this session.
  - Logged: 2026-05-05 · Re-confirmed 2026-05-07

## Phase 2 (planned, out-of-scope for Phase 1 Workflow Survey)

- **Workflow Surveys for the remaining 6 verticals** — Government, Corporate AV, Healthcare, Houses of Worship, K-12, Channel/Integrators. Same JTBD job-map structure; mine personas from the BDR playbook. (Effort: 1–2 days)
- **Outbound HubSpot webhook** — attach the BDRCallBrief to the contact record automatically when a brief is generated for a known prospect. (Effort: 4 hr)
- **Survey response persistence** — Supabase / Redis storage so a BDR can come back to a partial survey or share a link with a prospect. (Effort: 1 day)
