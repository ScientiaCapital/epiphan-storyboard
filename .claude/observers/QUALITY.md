# Observer: Code Quality Report

**Date:** 2026-06-17
**Project:** epiphan-storyboard
**Observer Model:** claude-sonnet-4-6

---

## Critical (must fix before merge)

_No findings yet from prior sessions._

---

## Warnings (fix or log to backlog)

_No findings from prior sessions._

---

## Info (nice to have)

_No findings from prior sessions._

---

## product-grounded-image-gen 2026-06-17

### Tech Debt Accumulation (Pattern 2)

Zero TODO/FIXME/HACK/XXX/TEMP markers introduced across all 9 changed files. The only `# noqa`-class annotation is the existing `type: ignore` baseline (mypy count unchanged at 372). Clean.

---

### Test Gaps (Pattern 3)

Three new test files, 517 lines. Coverage against stated scope:

| Component | Tested? | Notes |
|-----------|---------|-------|
| `StoryboardUnderstanding.recommended_products` field | Yes | `test_image_to_image.py::TestRecommendedProductsField` |
| `build_product_visual_block` prompt injection | Yes | `TestContentSectionGrounding` — checks presence and EC20 "20x" trait |
| genai SDK image-to-image (Parts path) | Yes | `TestGenaiPathImageToImage` — asserts `contents` is list, counts `IMG_PART` |
| genai SDK text-only degrade | Yes | `TestGenaiPathImageToImage::test_no_reference_images_keeps_text_only` |
| OpenRouter image-to-image (multimodal messages) | Yes | `TestOpenRouterPathImageToImage` |
| OpenRouter text-only degrade | Yes | Same class |
| `find_tech_accuracy_violations` — false claim flagged | Yes | `test_quality_gate_tech_accuracy.py` |
| Negation guard (true claim not flagged) | Yes | `TestFindTechAccuracyViolations::test_true_encoder_claim_not_flagged` |
| `epiphan_edge` exemption in `_check_product_references` | Yes | `TestEpiphanEdgeExemption` |
| `collect_do_not_depict` / `build_product_visual_block` / `get_visual_spec` | Yes | `test_product_visual_specs.py` |
| All catalog products have stub coverage | Yes | `TestSpecsIntegrity::test_full_catalog_coverage` |

[WARNING] — `unified_storyboard.py:622-648` — The tech-accuracy corrective retry path (the actual `await extract(corrective_instruction=corrective)` call and subsequent `run_quality_gate`) has no unit test. `test_quality_gate_tech_accuracy.py` tests the gate in isolation; `test_image_to_image.py` tests the generation layer. But nothing tests that `UnifiedStoryboardTool.run()` wires up the retry: specifically that `find_tech_accuracy_violations` triggers `extract` exactly once more, and that `tech_accuracy_reframe_applied=True` appears in the returned quality dict. The competitor-as-hero retry has the same gap (pre-existing). This is a WARNING, not a blocker — the gate itself is well-tested — but a regression here would be silent.

Suggested fix: add one `@pytest.mark.asyncio` test in `test_image_to_image.py` that mocks `extract` to return a bad-then-clean pair of understandings and asserts `tech_accuracy_reframe_applied` is True in the result dict.

[INFO] — `test_image_to_image.py` — The genai SDK path test (`TestGenaiPathImageToImage`) patches `_client` and `_ensure_client` but does not exercise the exception branch at `gemini_client.py:1368` (`except Exception: logger.error ... raise`). Acceptable for a merge gate; log to backlog for completeness.

---

### Import Bloat (Pattern 5)

`gemini_client.py:1130` — `build_product_visual_block` is imported inside `_build_generation_content_section` (function-level lazy import) rather than at module top. This is a deliberate pattern already used by connectors (per MEMORY.md) to avoid circular imports on serverless. The import is not unused. No bloat.

No new dependencies added to `pyproject.toml` or `requirements*.txt`. Clean.

---

### Silent Failures (Pattern 6)

`unified_storyboard.py:663` — The quality gate is wrapped in `except Exception: logger.exception(...)` — intentional, documented, pre-existing. Not introduced by this diff.

`gemini_client.py:1368` — `except Exception as e: logger.error(...); raise` — re-raises correctly. No swallowed error.

`demo/router.py:396-404` — Oversized images are dropped with a `logger.warning` and the request continues. This is an explicit silent degrade: the caller never learns which image was dropped (no response field). Acceptable for a serverless size ceiling, but the demo UI will render a storyboard with no conditioning and no error. Consider echoing the drop count in the quality payload so the UI can surface it.

[INFO] — `demo/router.py:396-404` — Dropped oversized images are not surfaced to the caller. If all 3 images are oversized, `is_image` remains True but `reference_images` will be `None` inside `generate_storyboard`. The gate and generation degrade gracefully (confirmed by code path), but the user sees a text-to-image result with no indication why. Low priority — log to backlog.

---

### Negation Guard False-Positive/False-Negative Analysis (requested)

**False-negative risk (gate misses a real violation):** The "any negated shared signal clears the whole field" policy means a field like "EC20 needs an encoder — unlike competitors that go direct" would be cleared by the negation on "direct" if "direct" were a shared signal word. However, "direct" IS in `_TECH_STOPWORDS` (`directly` is listed; "direct" resolves to a 6-char token not in stopwords but not in the EC20 do_not_depict phrases either). Actual EC20 do_not_depict signals are "encoder", "separate", "cable", "cables". Of these, "separate" is in stopwords ("separate" is NOT listed — checked). So the real risk phrase is "EC20 needing or using a SEPARATE ENCODER". Content words surviving stopword filter: {"separate", "encoder", "needing", "using"} — but "using" and "needing" are stopworded. Net signals: {"separate", "encoder"}. A field saying "EC20 records direct — no separate encoder" has both signal words but "separate" is preceded by "no" within 3 tokens → clears. Correct behavior.

**False-positive risk (gate fires on clean copy):** A field saying "Pearl Nano encodes without NDI overhead" contains "ndi" — shared with the Pearl Nano do_not_depict phrase "NDI or NDI|HX support". But "without" is a `_NEGATION_TOKEN` and precedes "ndi" by 1 token → clears. Correct.

A field saying "NDI-free encoding with Pearl Nano" — "ndi" is in the phrase, "free" is a `_NEGATION_TOKEN`. "free" is at idx N, "ndi" is at idx N-1... wait: "free" follows "ndi" here ("NDI-free"), not precedes it. The negation window looks BACK from the signal word ("ndi"), so it sees nothing. The hyphenated form "NDI-free" is tokenized by `r"[A-Za-z][A-Za-z0-9]+"` as ["NDI", "free"] — "free" is token after "ndi", not before. This would produce a false positive: "NDI-free" copy flagged as asserting NDI support.

[WARNING] — `quality_gate.py:_raw_tokens` — The negation window only looks backward. A common English pattern "NDI-free" or "encoder-free" tokenizes to [signal_word, "free"]. "free" in _NEGATION_TOKENS is never seen in the window before the signal word. These compound adjectives will be false-positive flagged.

Impact: clean copy like "NDI-free single-channel encoder" for Pearl Nano would trigger the gate, causing a corrective reframe retry that adds latency and may introduce its own copy defects. Not a correctness crisis (the storyboard still ships after the retry), but a real usability defect.

Suggested fix: also check a forward window of 1-2 tokens after the signal word for negation tokens, or add "NDI-free", "encoder-free" as explicit safe-patterns. The cleanest mechanical fix: extend `_asserts_phrase` to also scan `field_tokens[idx+1:idx+2]` for negation tokens.

---

## Code Quality Metrics

| Metric | Value |
|--------|-------|
| Files scanned | 9 (7 src, 1 script, 1 test bundle) |
| Critical findings | 0 |
| Warnings | 3 |
| Info items | 2 |
| Tech debt markers introduced | 0 |
| New dependencies | 0 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1–1.3 | 6 | 7 (0C/4W/3I) | archived to `.claude/archive/2026-05-07-OBSERVER-QUALITY.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 4 sequential audits across the day | 14 cumulative | 12 cumulative (0C/2W/10I) — all dispositioned, none silently dropped | archived to `.claude/archive/2026-05-08-OBSERVER-QUALITY.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 session + debt-paydown sprint | /begin Phase 2 audit → all 6 findings resolved or backlogged same day (CRITICAL fixed in 3187555) | 24 | 6 (1C/3W/2I) | archived to `.claude/archive/2026-06-12-OBSERVER-QUALITY.md` |
| 2026-06-17 | feature/product-grounded-image-gen | merge gate review: product visual specs SSOT, image-to-image wiring, tech-accuracy gate | 9 | 5 (0C/3W/2I) | OPEN |

---

## pearl-duo 2026-06-17

### Tech Debt Accumulation (Pattern 2)

Zero TODO/FIXME/HACK/XXX/TEMP markers introduced across all changed files (confirmed by diff inspection of epiphan_presets.py, product_visual_specs.py, quality_gate.py, both test files). The source comments in epiphan_presets.py:176-180 are deliberate spec-citation notes, not debt markers. Clean.

---

### Test Gaps (Pattern 3)

New test coverage for Pearl Duo additions:

| Component | Tested? | Notes |
|-----------|---------|-------|
| `pearl_duo` in EPIPHAN_PRODUCTS catalog | Yes | `TestPearlDuo::test_in_catalog_and_ssot` |
| `availability` key value | Yes | `TestPearlDuo::test_availability_captured` |
| Visual block contains dual-screen signal words | Yes | `TestPearlDuo::test_visual_block_shows_dual_screens` |
| `do_not_depict` blocks lecture capture and switcher | Yes | `TestPearlDuo::test_do_not_depict_blocks_lecture_capture_and_switcher` |
| Tech gate flags lecture-capture copy | Yes | `TestPearlDuoTechAccuracy::test_lecture_capture_claim_flagged` |
| Tech gate flags broadcast-switcher copy | Yes | `TestPearlDuoTechAccuracy::test_broadcast_switcher_claim_flagged` |
| Clean dual-channel copy passes gate | Yes | `TestPearlDuoTechAccuracy::test_clean_dual_channel_copy_passes` |

[WARNING] — `tests/tools/storyboard/test_quality_gate_tech_accuracy.py` — No test covers the "single-screen device" or "local on-device dashboard" or "playback or scrubbing recorder" do_not_depict phrases for Pearl Duo. Only lecture-capture and broadcast-switcher are exercised. If those three phrases have signal-word collisions with legitimate Duo copy (e.g. "local" in "local SSD recording" for the dashboard phrase, or "device" in standard copy for "a local on-device dashboard"), the gate behavior is unverified. Low risk given the phrases are multi-word and distinctive, but the test surface is incomplete.

Suggested fix: add two cases to `TestPearlDuoTechAccuracy` — one asserting "a local on-device dashboard" phrase fires on dashboard copy, one asserting "playback or scrubbing recorder" fires on scrubbing copy.

[INFO] — No test asserts that `pearl_duo` appears in the recommended_products lists of the four modified verticals (live_events, corporate, government, houses_of_worship). The vertical wiring is structural data with no runtime guard other than `_check_product_references`; the gate test for that check (`TestEpiphanEdgeExemption`) does not include a pearl_duo recommendation flow. Acceptable — the product id is now in EPIPHAN_PRODUCTS so the gate would pass — but explicit coverage would be cleaner.

---

### Import Bloat (Pattern 5)

No new imports or dependencies. `product_visual_specs.py` already imports from `epiphan_presets.py`; the Pearl Duo entry follows the exact same pattern as existing entries. Clean.

---

### Silent Failures (Pattern 6)

`product_visual_specs.py:295-297` — The stub backfill loop calls `_stub_spec(product_id)` which accesses `EPIPHAN_PRODUCTS[product_id]["name"]` (line 272) with a hard key lookup, not `.get()`. If a catalog entry ever omits the `"name"` key it raises `KeyError` at import time. Pearl Duo has a `"name"` key, so this is not introduced by this diff — it is pre-existing and pearl_duo does not worsen it.

No new silent failure patterns introduced. Clean.

---

### "capture" / "captures" Stopword Addition — Collateral Damage Check

The diff adds `camera cameras ptz zoom pan tilt motorized lens capture captures` to `_TECH_STOPWORDS` in `quality_gate.py`.

Checked every `do_not_depict` entry across all products in `product_visual_specs.py` for phrases whose signal depends on "capture" or "captures" surviving the stopword filter:

| Product | do_not_depict phrase | "capture" token present? | Signal surviving after stopword removal |
|---------|---------------------|-------------------------|----------------------------------------|
| pearl_mini | "a rack-only/1RU appliance..." | No | Unaffected |
| pearl_mini | "a screen on the rear..." | No | Unaffected |
| pearl_nano | "NDI or NDI|HX support..." | No | Unaffected |
| pearl_nano | "Dante audio (not supported)" | No | Unaffected |
| pearl_nano | "multi-channel or live switching..." | No | Unaffected |
| pearl_nano | "capturing HDCP-encrypted sources" | YES — "capturing" | "capturing" is tokenized as "capturing" (10 chars, not in stopwords — stopwords list "capture captures" not "capturing") |
| pearl_nexus | (3 phrases) | No | Unaffected |
| pearl_2 | (2 phrases) | No | Unaffected |
| pearl_duo | "lecture capture or CMS/LMS integration" | YES — "capture" | "capture" is now a stopword. Signal words remaining: "lecture", "cms", "lms", "integration" — but "cms" and "lms" are ALSO stopwords. Net surviving signals: {"lecture", "integration"}. Gate still fires on "lecture" alone. See [WARNING] below. |
| ec20_ptz | (3 phrases) | No | Unaffected |

[WARNING] — `quality_gate.py` / `product_visual_specs.py:195` — The Pearl Duo do_not_depict phrase "lecture capture or CMS/LMS integration" loses "capture", "cms", and "lms" to stopwords. The remaining distinctive signals are "lecture" and "integration". "lecture" is strong and distinctive; it will fire the gate on "lecture" copy. "integration" is present in many legitimate Duo copy contexts (e.g. "Epiphan Edge integration", "API integration"). This means the gate now relies entirely on "lecture" as the signal for this Duo false-claim phrase. If generated copy uses the concept without the word "lecture" — for example "classroom recording" or "CMS publishing workflow" — the gate will not catch it.

This is not a regression introduced by adding "capture" to stopwords — the phrase was always fragile without "capture" (since "cms" and "lms" were already stopworded in the original list). But the stopword addition does confirm that "lecture" is the sole load-bearing signal, and that is worth documenting.

Mitigation: either split into two separate do_not_depict phrases ("lecture capture" and "CMS/LMS integration"), or add a dedicated second phrase "CMS or LMS publishing" using a non-stopworded signal word. Alternatively, accept the current behavior and note in a comment that "lecture" is the sole firing signal.

[INFO] — Pearl Nano do_not_depict phrase "capturing HDCP-encrypted sources" — the word "capturing" (gerund, 10 chars) survives the stopword filter because the stopwords list contains "capture" and "captures" but not "capturing". The gate behavior for this phrase is unchanged. However, if "capturing" is ever added to stopwords, the phrase degrades to {"hdcp", "encrypted"} which remains distinctive. No action needed.

---

## Code Quality Metrics (cumulative after pearl-duo session)

| Metric | Value |
|--------|-------|
| Files scanned (this session) | 5 (src) + 2 (tests) = 7 |
| Critical findings | 0 |
| Warnings | 2 (new this session) |
| Info items | 2 (new this session) |
| Tech debt markers introduced | 0 |
| New dependencies | 0 |

---

## Monitoring Runs

| Date | Session | Task | Files Checked | Findings | Status |
|------|---------|------|--------------|----------|--------|
| 2026-05-07 | feature/bdr-call-brief-and-surveys | DA audit Phase 1.1–1.3 | 6 | 7 (0C/4W/3I) | archived to `.claude/archive/2026-05-07-OBSERVER-QUALITY.md` |
| 2026-05-08 | leverage-day Fix A + Fix B + DA-R1 + DA-R1.1 + DA-R1.1.b | 4 sequential audits across the day | 14 cumulative | 12 cumulative (0C/2W/10I) — all dispositioned, none silently dropped | archived to `.claude/archive/2026-05-08-OBSERVER-QUALITY.md` |
| 2026-06-12 | catch-up audit of 2026-06-10 session + debt-paydown sprint | /begin Phase 2 audit → all 6 findings resolved or backlogged same day (CRITICAL fixed in 3187555) | 24 | 6 (1C/3W/2I) | archived to `.claude/archive/2026-06-12-OBSERVER-QUALITY.md` |
| 2026-06-17 | feature/product-grounded-image-gen | merge gate review: product visual specs SSOT, image-to-image wiring, tech-accuracy gate | 9 | 5 (0C/3W/2I) | OPEN |
| 2026-06-17 | feature/pearl-duo | Pearl Duo catalog addition merge gate | 7 | 4 (0C/2W/2I) | OPEN |
