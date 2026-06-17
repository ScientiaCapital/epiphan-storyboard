# Observer: Architecture Report

**Date:** 2026-06-17
**Project:** epiphan-storyboard
**Observer Model:** claude-sonnet-4-6

---

## Blockers (stop work immediately)

_No blockers._

---

## Risks (address this sprint)

_No risks identified yet from prior sessions._

---

## Smells (log to backlog)

_No smells from prior sessions._

---

## product-grounded-image-gen 2026-06-17

### Scope / Agent Drift (Pattern 1)

No feature contract found in `.claude/contracts/` for this branch. All 9 modified/created files are within the expected module boundaries (src/tools/storyboard/, src/demo/, scripts/, tests/). No scope violation detected.

[WARNING] — No feature contract defined for branch feature/product-grounded-image-gen. Recommend creating a contract for features touching the quality gate, as the gate is production-critical and drift is hard to detect without a stated contract.

---

### Scope Creep (Pattern 4)

No new API endpoints added. No new files in unexpected directories. `scripts/regen_product_visual_specs.py` is explicitly NOT imported at runtime (confirmed by diff); it lives in scripts/, which is the correct location for non-runtime helpers.

No scope creep detected.

---

### Contract Drift (Pattern 7)

No feature contract exists to diff against. However, checking internal SSOT consistency:

**[RISK] — quality_gate.py — Double-extraction on competitor+tech violation not possible, but tech gate re-runs `find_tech_accuracy_violations` on a stale `understanding.model_dump()` after the competitor reframe fires.**

Specifically: when competitor reframe fires (lines 594-615), `understanding` is re-extracted and `report` is updated. Then line 622 calls `find_tech_accuracy_violations(understanding.model_dump())` on the NEW post-reframe understanding — correct. The budget guard `not reframe_applied` prevents a second LLM call. No double-extract risk. However, if both violations coexist in the original extraction and only the competitor gate fires, the tech-accuracy issues are visible in the final `report` (which was re-run after the competitor reframe at line 612-614) but the tech reframe is silently skipped with no log entry noting the skip. The remaining tech issues surface in the quality payload — this is correct per the comment — but there is no explicit WARNING log that says "tech reframe skipped because competitor reframe already ran". A future reader debugging a false product claim that shipped will have no trace of the skip.

Suggested fix: add `logger.warning("tech_accuracy reframe skipped — competitor reframe already consumed the budget; %s issues will surface in report", len(tech_hits))` in the `if tech_hits and not reframe_applied` else path.

**[RISK] — gemini_client.py:1342 / product_visual_specs.py — Hardcoded `mime_type="image/png"` for all reference image Parts on the genai SDK path.**

User-uploaded reference photos arrive as decoded bytes after base64 decode from demo/router.py. The original image format is lost by the time the bytes reach `generate_storyboard`. If a user uploads a JPEG and it happens to come through as a data URL without `image/jpeg` in the prefix (or the demo router strips the prefix on split(",")[1]), the bytes are sent to Gemini with `mime_type="image/png"` — a lie. Most Gemini multimodal endpoints are tolerant of this for common formats, but JPEG/WEBP inputs misidentified as PNG can silently produce degraded or refused responses rather than a hard error. The OpenRouter path uses the same hardcoded `data:image/png;base64,...` data URL (line 484).

Suggested fix: sniff the magic bytes (b'\xff\xd8' = JPEG, b'\x89PNG' = PNG, b'RIFF' = WEBP) and set the correct MIME type. Three lines of code. Alternatively, document that the demo UI must normalize to PNG before sending (not currently enforced).

---

### Devil's Advocate Challenges

| # | File | Challenge | Verdict |
|---|------|-----------|---------|
| DA-PG-1 | `product_visual_specs.py` | Does this module need to exist, or could `epiphan_presets.py` carry the visual+exclusion data? | Justified. `epiphan_presets.py` is already 2500+ lines; it carries pricing/persona/vertical data for runtime use. Mixing image-model prompt facts and do_not_depict exclusion lists into it would make both harder to audit. Separate SSOT is correct. |
| DA-PG-2 | `_asserts_phrase` negation guard (quality_gate.py) | "any negation clears the whole field" — is this too broad? A field containing "no encoder, no NDI support, needs switching" would be cleared by the "no encoder" negation even though "needs switching" is a false claim for Pearl Nano. | Real limitation, low practical risk today (fields are short, claims are narrow). The comment documents the bias explicitly. Accept as known conservative tradeoff; annotate with a test case when a multi-claim field is encountered in practice. |
| DA-PG-3 | `scripts/regen_product_visual_specs.py` | Not imported at runtime — should it be in a separate `scripts/` repo or a Makefile target instead of living in the repo tree? | Fine in repo. It is a human-run MCP helper, explicitly documented as such. No runtime path touches it. Convention is fine for this project size. |
| DA-PG-4 | `unified_storyboard.py:677-681` reference_images slicing | `[:3]` applied at the unified_storyboard layer but also applied again inside `generate_storyboard` and `_generate_image_via_openrouter`. Triple cap is harmless but is redundant logic in three places. | Low priority. The demo/router ceiling (DEMO_MAX_IMAGE_B64_CHARS) + the [:3] slice in unified_storyboard are the real guards; the inner caps are belt-and-suspenders. Log to backlog, not a blocker. |

---

## Monitoring Runs

| Date | Session | Findings | Status |
|------|---------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | 3 risks / 4 smells | archived to `.claude/archive/2026-05-07-OBSERVER-ARCH.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 0 blockers / 1 risk / 8 smells (cumulative across 4 audits) — all logged to Backlog (DA-A1, DA-A2, DA-A3, DA-R1.1.a) | archived to `.claude/archive/2026-05-08-OBSERVER-ARCH.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 session + debt-paydown sprint | 0 blockers / 3 risks / 5 smells — 2 risks fixed same day, 1 cleared as non-issue (vercel verified Pro/300s); smells fixed (DA-A4) or backlogged (DA-B1, DA-B2) | archived to `.claude/archive/2026-06-12-OBSERVER-ARCH.md` |
| 2026-06-17 | feature/product-grounded-image-gen | 0 blockers / 2 risks / 0 smells / 4 DA challenges | OPEN |

---

## pearl-duo 2026-06-17

### Scope / Agent Drift (Pattern 1)

No feature contract defined for feature/pearl-duo.

[WARNING] — No feature contract in `.claude/contracts/`. Files changed: epiphan_presets.py, product_visual_specs.py, quality_gate.py, scripts/regen_product_visual_specs.py, CLAUDE.md, plus 2 test files and 2 observer files. All within expected module boundaries. No files modified outside the product catalog + quality gate + tests scope. No drift detected.

Commit e01e431 (cherry-pick of image-gen observer fixes) applied cleanly: it touches unified_storyboard.py, gemini_client.py, and test_unified_storyboard.py/test_image_to_image.py. All four are within the storyboard tooling boundary. No cross-concern modification visible. Sanity check passes.

---

### Scope Creep (Pattern 4)

No new API endpoints added. No new routers or route registrations. Pearl Duo is added to the data layer only (catalog dict + visual specs dict). All five new recommended_products entries are pure data; no new runtime code paths introduced.

No scope creep detected.

---

### Contract Drift (Pattern 7)

No feature contract to diff against. Internal SSOT consistency check:

**Vertical wiring validation:**

Four verticals updated — live_events, corporate, government, houses_of_worship. The fifth vertical in pearl_duo's own `"verticals"` list is `"healthcare"`, but healthcare's `recommended_products` list was NOT modified (it remains `["pearl_2", "pearl_mini", "avio_4k", "ec20_ptz"]`). This is a minor inconsistency: pearl_duo lists healthcare as a target vertical in its own dict, but healthcare does not list pearl_duo as a recommended product. This is an in-data discrepancy, not a code bug — the gate reads from `EPIPHAN_VERTICALS[v]["recommended_products"]`, not from `EPIPHAN_PRODUCTS[p]["verticals"]`.

[WARNING] — `epiphan_presets.py:203-209` — Pearl Duo's own `"verticals"` list includes `"healthcare"`, but the healthcare vertical's `recommended_products` was not updated to include `"pearl_duo"`. This is a bidirectional mapping that is now out of sync. The gate and prompt builder both read from `EPIPHAN_VERTICALS`, so healthcare storyboards will not recommend Pearl Duo despite the Duo's own metadata claiming healthcare as a target. Decide: either add `"pearl_duo"` to healthcare's recommended_products (requires a product justification, since healthcare favors Pearl-2/Mini for sim-lab multi-angle capture that Duo does not support), or remove `"healthcare"` from Duo's `"verticals"` key.

**_check_product_references gate acceptance:**

`_check_product_references` (quality_gate.py:569-583) validates that each `recommended_products` id is in `EPIPHAN_PRODUCTS` or `_NON_CATALOG_PRODUCT_IDS`. `pearl_duo` is now in `EPIPHAN_PRODUCTS`. Gate accepts it. Confirmed clean.

**Catalog consumer compatibility — "availability" extra key:**

Two catalog consumers read product dicts directly:

- `scene_extractor.py:282` — reads `product_data.get("price", "")` as str, passed as `product_price` into an f-string template. The `"TBA — ships December 2026"` string is valid str content. The `"availability"` key is simply ignored (`.get()` with a specific key). No breakage.
- `meeting_recap.py:159` — iterates `EPIPHAN_PRODUCTS.items()` and calls `.get("price", "")`. Same pattern. The extra `"availability"` key is not accessed; it is silently ignored. No breakage.
- `prompts.py:743` — accesses `EPIPHAN_PRODUCTS[pid]["name"]` only. No breakage.
- `transcript_to_scenarios.py:83` — accesses `EPIPHAN_PRODUCTS[p]["name"]` only. No breakage.
- `product_visual_specs.py:271-272` (`_stub_spec`) — accesses `product["name"]`, `.get("form_factor")`, `.get("key_specs")`. Pearl Duo has all three. The `"availability"` key is ignored. No breakage.

The `"availability"` key is additive and safe. No consumer assumes a fixed schema; all use `.get()` with defaults or specific key lookups. Zero risk of breakage.

**Pre-launch copy risk:**

The `"price"` field value `"TBA — ships December 2026"` is injected directly into LLM prompts by both scene_extractor.py:85 (`"- Product: {product_name} ({product_price})"`) and meeting_recap.py:165 (`f"- {pid}: {name} ({price}) — {tagline}"`). The model will see the TBA/December annotation inline with the product name, which should suppress invented pricing and "available now" claims. The `"availability"` key and the `technical_facts` entry "pre-launch: ships December 2026" in product_visual_specs.py provide two additional anchors. Coverage is adequate for the risk.

[INFO] — No Epiphan product page URL exists yet for Pearl Duo (it is pre-launch). `SALES_COLLATERAL["product_pages"]` does not include `"pearl_duo"`. The collateral-link check in `quality_gate._check_links` only validates non-epiphan.com URLs, so this does not trip the gate. However, any generated CTA or collateral block that tries to auto-insert a product URL for pearl_duo from `SALES_COLLATERAL` will find no entry and silently omit it. No action needed before merge — the product has no public URL to link to. Add the URL to `SALES_COLLATERAL["product_pages"]` when the product page goes live.

---

### Devil's Advocate Challenges

| # | File | Challenge | Verdict |
|---|------|-----------|---------|
| DA-PD-1 | `epiphan_presets.py:181-210` | Does Pearl Duo need its own catalog entry now, or should it be staged behind a feature flag until launch? | Justified as-is. The entry is data-only; it affects storyboard copy quality (prompts get the TBA price, the no-CMS caveat, the dual-screen hardware description). A feature flag would add code complexity with minimal benefit since the data is not surfaced to end users outside internal storyboard generation. The pre-launch signal is embedded in the data itself. |
| DA-PD-2 | `epiphan_presets.py:200` — "Camera + presentation capture" in pearl_duo's `best_for` | The word "capture" appears in a best_for entry. "capture" is now a stopword. Is this a self-defeating description given the do_not_depict phrase "lecture capture or CMS/LMS integration"? | The `best_for` list is injected into LLM prompts (scene_extractor.py:283 `", ".join(product_data.get("best_for", []))`), not evaluated by the gate's stopword logic. The gate evaluates `understanding` output fields (headline, tagline, etc.), not input context. No collision. The phrasing "camera + presentation capture" is accurate (ISO + program recording of camera and presentation sources) and correctly distinct from "lecture capture" (CMS-integrated automated recording). Justified. |
| DA-PD-3 | `product_visual_specs.py:193-199` — "a local on-device dashboard" in do_not_depict | This phrase's signal words after stopword filtering: "local" (7 chars, not stopworded), "dashboard" (9 chars, not stopworded). "local" is very common in legitimate AV copy ("local recording", "local SSD", "local control"). Does this create false positives on clean Duo copy? | Moderate risk. "local" alone is not distinctive. But the gate requires BOTH "local" AND "dashboard" to overlap — AND both must appear in the same hero field AND not be negated. "dashboard" is rare in Duo hero copy (the correct framing is "touchscreen" not "dashboard"). Practical risk is low. Accept, but note in a backlog item: if "local" triggers unexpected false positives in production, split into a more specific phrase like "browser-based dashboard" or "web dashboard". |
| DA-PD-4 | Forward-negation window `_NEGATION_WINDOW_FWD: int = 2` (new constant in quality_gate.py) | Does adding a forward window create new false negatives — cases where a real violation is cleared because an unrelated "free" or "not" appears after the signal word? | The forward window is 2 tokens. In practice, "encoder-free" and "NDI-free" compound adjectives are the intended targets. Extending the window to 2 (rather than 1) means "encoder runs free" would also clear — a contrived example. The window size of 2 is a reasonable tradeoff. The prior-session [WARNING] about forward negation is now fixed by this change. |

---

## Monitoring Runs

| Date | Session | Findings | Status |
|------|---------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | 3 risks / 4 smells | archived to `.claude/archive/2026-05-07-OBSERVER-ARCH.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 0 blockers / 1 risk / 8 smells (cumulative across 4 audits) — all logged to Backlog (DA-A1, DA-A2, DA-A3, DA-R1.1.a) | archived to `.claude/archive/2026-05-08-OBSERVER-ARCH.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 session + debt-paydown sprint | 0 blockers / 3 risks / 5 smells — 2 risks fixed same day, 1 cleared as non-issue (vercel verified Pro/300s); smells fixed (DA-A4) or backlogged (DA-B1, DA-B2) | archived to `.claude/archive/2026-06-12-OBSERVER-ARCH.md` |
| 2026-06-17 | feature/product-grounded-image-gen | 0 blockers / 2 risks / 0 smells / 4 DA challenges | OPEN |
| 2026-06-17 | feature/pearl-duo | Pearl Duo catalog addition merge gate | 0 blockers / 1 risk / 0 smells / 4 DA challenges | OPEN |
