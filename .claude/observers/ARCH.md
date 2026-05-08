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
