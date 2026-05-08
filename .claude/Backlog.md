# Backlog

## Security / Tooling

- **Add `.gitleaksignore` for historical test fixtures** (effort: 5 min, impact: low)
  - Gitleaks flags `tests/api/test_connectors.py:499` (commit `fe25349`, 2026-02-19) for `"fireflies_api_key_123"` — a placeholder test string. The file has since been deleted from HEAD but remains in history.
  - Action: add a `.gitleaksignore` entry pinning that finding so future security gates pass cleanly without manual triage.
  - Logged: 2026-05-05 · Re-confirmed 2026-05-07 (still the only leak finding)

## Tech Debt / Architecture

- **DA-A3: Consolidate text-path dispatch into `_call_text_model`** (effort: 30 min, impact: low — code dedup) **[NEW 2026-05-09]**
  - DA-R1 added `_call_text_model` (`src/tools/storyboard/gemini_client.py:758-772`) but did not refactor the inline text-path dispatch in `_understand` (lines 853-878). The two now mirror each other. When somebody adds a new text provider (e.g. Qwen-text, Claude-via-OpenRouter), they'll need to update both sites — easy to miss.
  - Fix: refactor `_understand`'s text branch to call `_call_text_model(prompt)` instead of the inline if/elif. Verify all 1540 tests still pass; mypy delta zero.
  - Source: Observer audit 2026-05-09 (DA-R1). See `.claude/observers/ARCH.md` smell.

- **DA-R1.1: Wire two-pass into `meeting_recap.process_meeting_recap`** (effort: 1 hr, impact: medium for meeting-recap-only callers) **[NEW 2026-05-09]**
  - DA-R1 wired two-pass into `_understand`/`understand_transcript` in `gemini_client.py`. The meeting-recap pipeline at `src/tools/storyboard/meeting_recap.py:158-180` uses its own `build_meeting_recap_prompt` and does NOT route through `understand_transcript`. Long meeting-recap transcripts therefore don't benefit from the two-pass quality lift.
  - Fix: Either (a) refactor `process_meeting_recap` to invoke `understand_transcript` with the long-transcript path, OR (b) replicate the trigger+two-pass logic inside `process_meeting_recap`. Option (a) consolidates code paths; option (b) preserves the dedicated meeting-recap prompt.
  - Source: Observer audit 2026-05-09 (DA-R1). See `.claude/observers/ARCH.md` Devil's Advocate row.

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
