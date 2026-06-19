# Design: Deterministic text layer for storyboard art (Track C)

**Date:** 2026-06-19
**Status:** Approved design — implementation pending (separate session)
**Predecessor:** Tracks A+B shipped in commit `0b1000e` (gate false-positives +
prompt-level image polish). This design is the architectural fix for the
remaining exec-facing problem: garbled/duplicated text baked into diffusion
images (e.g. "222 ar a perfect fit", duplicate "Fewer truck rolls" label).

## Context

The storyboard "art" is a single diffusion-model PNG with all text baked in.
Diffusion models cannot reliably spell or de-duplicate text, so exec-facing
output garbles. Tracks A+B reduced the symptom (lower temperature, dedup, drop
debug text) but cannot eliminate it — a diffusion model rendering text is
fundamentally lossy. Track C removes text from the model's job entirely.

## Decisions (locked)

1. **Deliverable:** a downloadable PNG file.
2. **Render site:** client-side, in the demo SPA, via `<canvas>` →
   `canvas.toBlob('image/png')`. No server-side rasterization (headless
   Chromium is impractical on the `@vercel/python` serverless deploy).
3. **Layout:** one fixed, brand-owned template with known regions. The model
   never decides placement.
4. **Visuals:** diffusion produces ONE text-free hero illustration for the
   hero zone; small card icons come from a curated SVG set; all text is canvas
   Söhne in fixed slots.

Scope guards (YAGNI): PNG only (PDF deferred); single template; no server-side
render; no new extraction pass.

## Architecture & data flow

```
POST /demo/generate
  ├─ Stage 1 UNDERSTAND   (unchanged → StoryboardUnderstanding)
  ├─ Quality gate          (unchanged — clean after A+B)
  ├─ Stage 2 GENERATE      (CHANGED): diffusion → TEXT-FREE hero image only
  └─ Response (CHANGED):   { hero_png_b64: str, layout: StoryboardLayout }

demo.html:
  1. await document.fonts.ready            # Söhne via existing /brand/fonts.css proxy
  2. draw on <canvas 1600x900> (export @2x → 3200x1800):
        background (brand tokens) → header band (headline) →
        content cards (caption + SVG icon) → stat callout →
        hero zone (paint hero_png_b64) → footer (CTA + logo SVG)
  3. canvas.toBlob('image/png') → download
```

The backend stops being the renderer: it returns structured data + one
illustration. **Text never touches the diffusion model**, so the garble/dup
failure modes become structurally impossible.

## Template regions (fractions of a 1600×900 canvas)

```
┌─────────────────────────────────────────────────────┐
│ HEADER BAND (0,0 → 1.0,0.18)  navy #1D2B51            │
│   headline (Söhne ~54px white) · eyebrow = vertical   │
├──────────────────────────┬──────────────────────────┤
│ CARDS COLUMN              │ HERO ZONE                 │
│ (0,0.18 → 0.55,0.82)      │ (0.55,0.18 → 1.0,0.82)    │
│  card: icon + caption ×2–4│  diffusion hero_png       │
├──────────────────────────┴──────────────────────────┤
│ STAT CALLOUT (lime #8CBE3F) · FOOTER: CTA + logo SVG  │
│ (0,0.82 → 1.0,1.0)                                    │
└─────────────────────────────────────────────────────┘
```

Colors / spacing / radii / typography from the Epiphan Brand MCP
`get_brand_asset_kit` → `tokens`; logo from `assets.logos`; Söhne from
`assets.fontsCss` (already proxied same-origin at `/brand/fonts.css`). Cache
the kit (static) rather than calling per generation.

## Response schema

```python
class LayoutCard(BaseModel):
    caption: str        # deduped/capped copy line (reuse _dedupe_and_cap)
    icon: str           # key into the curated SVG set

class StoryboardLayout(BaseModel):
    eyebrow: str            # vertical display name
    headline: str
    cards: list[LayoutCard] # 2–4; empty fields collapse + re-flow
    stat_value: str         # e.g. "$6,600/room"
    stat_label: str
    cta: str                # persona-appropriate
    product_name: str | None  # canonical id → display name
    hero_alt: str
```

`build_layout(understanding, persona, vertical) -> StoryboardLayout` is a pure
mapping from existing extraction + presets — no model call. Field mapping:
headline → header; what_it_does / differentiator / pain_point_addressed →
cards; business_value → stat; CTA from persona presets.

## Per-card icons

`understanding.suggested_icon` is a single value; cards need one each. Add a
deterministic `resolve_icon(caption, suggested_icon) -> str`: scan the caption
for keywords against a curated AV/IT SVG set (~20–30 glyphs: camera, encoder,
cloud, display, lecture-hall, truck, dollar, lock, network, calendar, …), fall
back to `suggested_icon`, then a neutral default. SVGs live in
`src/tools/storyboard/icons/` (or an inline dict) and are drawn on canvas via
`Path2D`. Pure function, fully unit-testable, zero model dependency.

## Hero image (the one diffusion call)

Rewrite the generation prompt to demand a **text-free editorial illustration**
sized to the hero zone aspect: "a clean, modern scene depicting {vertical}
{scene}; NO text, NO words, NO labels, NO UI chrome; navy/lime palette; flat
editorial vector style." Keep existing reference-image conditioning and the
palette instruction; temperature stays at the Track-B `_TEXT_FIDELITY_TEMPERATURE`
(0.4). On failure/timeout, the hero zone degrades to a brand gradient — the
infographic still renders fully.

## Error handling (degrade, never block)

- Hero gen fails → brand-gradient hero zone; log reason (AgentSession.error
  pattern). Infographic still renders.
- Empty copy field → card collapses, remaining cards re-flow (2–4 supported).
- Missing stat/CTA → hide stat callout; persona-default CTA.
- Fonts not ready → `await document.fonts.ready` gates first draw; if Söhne
  still absent, fall back to system sans + surface a soft warning (never ship
  wrong fonts silently).
- Icon keyword miss → neutral default glyph.

## Testing & verification

- **Backend (deterministic, the bulk):**
  - `build_layout(...)` field mapping, card collapse, stat fallback, product
    display-name resolution.
  - `resolve_icon(...)` keyword + fallback chain.
  - Hero-prompt builder asserts the "no text/words/labels" instruction.
  - Endpoint response-contract test (`{hero_png_b64, layout}` shape).
- **Frontend canvas:** `webapp-testing` skill + Playwright MCP — one golden-path
  E2E: generate, wait for canvas, screenshot, assert download blob is a valid
  PNG of expected dimensions. No pixel-diffing.
- **Manual exec check:** higher-ed AV-director storyboard → crisp Söhne text,
  correct spelling, no duplicates, on-brand palette, downloadable PNG.

## Files (anticipated)

- `src/tools/storyboard/gemini_client.py` — text-free hero prompt; generation
  returns hero bytes (not a composited infographic).
- `src/tools/storyboard/storyboard_layout.py` (new) — `StoryboardLayout`,
  `LayoutCard`, `build_layout`, `resolve_icon`.
- `src/tools/storyboard/icons/` (new) — curated SVG glyph set.
- `src/demo/router.py` (or storyboard router) — response now returns
  `{hero_png_b64, layout}`.
- `static/demo.html` — canvas renderer + PNG download; `await
  document.fonts.ready`.
- Tests: `tests/tools/storyboard/test_storyboard_layout.py` (+ Playwright E2E).

## Out of scope / future

- PDF export (canvas→PNG is native; add jsPDF only if execs ask).
- Multiple template variants (stat-led / story-led / comparison).
- Server-side rendering for automated email attachments (would need a
  browser-free SVG→PNG path, e.g. resvg, validated on Vercel).
- Tech-accuracy note carried forward: Pearl Nexus Dante is licensed but not
  functional until ~fall 2026 — do not claim Dante works today.
