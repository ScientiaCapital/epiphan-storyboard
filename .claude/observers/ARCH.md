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
