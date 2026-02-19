# Plan: Persona Resonance Polish

**Branch**: `feature/persona-resonance-gtm`
**Goal**: Polish persona matching, visual styles, and value framing for better GTM output

---

## Summary

Improve the existing storyboard system with:
1. Stronger persona voices (distinct vocabulary/hooks)
2. Persona-specific visual treatments
3. Amplified COI/ROI/EASE value framing
4. New artist styles for Nano Banana

---

## Changes

### 1. Polish Persona Voices

**File**: `src/tools/storyboard/coperniq_presets.py`

Make each persona sound distinctly different:

| Persona | Current | Polish |
|---------|---------|--------|
| **field_crew** | Simple language | Blue-collar idioms, tool metaphors, "get it done" energy |
| **c_suite** | Executive tone | Board-room brevity, metrics-first, strategic framing |
| **business_owner** | Pain-focused | Founder anxiety, cash flow stress, "my baby" ownership |
| **btl_champion** | Practical | Internal advocate language, "sell it up", risk mitigation |
| **top_tier_vc** | Investment | Pattern matching, moat obsession, 10x thinking |

Add to each persona preset:
- `voice_tone`: Specific tone descriptor
- `vocabulary`: 5-10 key phrases that resonate
- `forbidden_phrases`: Words that turn this persona off

### 2. Persona-Specific Visual Styles

**File**: `src/tools/storyboard/coperniq_presets.py`

Map each persona to a default visual treatment:

| Persona | Visual Style | Why |
|---------|-------------|-----|
| **field_crew** | Hand-drawn sketch | Approachable, whiteboard feel, not corporate |
| **c_suite** | Data visualization | Numbers-forward, McKinsey aesthetic |
| **business_owner** | Isometric/3D icons | Modern SaaS feel, Stripe/Linear quality |
| **btl_champion** | Clean infographic | Shareable internally, professional |
| **top_tier_vc** | Bold/Geometric | Stand out in pitch deck, memorable |

Add `default_visual_style` to each persona in `ICP_PERSONAS`.

### 3. Strengthen Value Framing

**File**: `src/tools/storyboard/gemini_client.py`

Amplify COI/ROI/EASE in `_get_value_angle_instruction()`:

```python
# Current: Generic instruction
# Polish: Persona-specific value amplification

if audience == "business_owner":
    return """VALUE ANGLE: COI (Cost of Inaction)

    AMPLIFY THE FEAR:
    - What are they LOSING every day they don't act?
    - What's slipping through the cracks?
    - How much is manual work costing them?
    - Paint the picture of continued pain

    FORBIDDEN: Don't talk about gains. Focus on what they're hemorrhaging."""
```

### 4. New Artist Styles

**File**: `src/tools/storyboard/gemini_client.py`

Add to `_get_artist_style_instructions()`:

| Style | Description |
|-------|-------------|
| **isometric** | Clean 3D isometric icons, Stripe/Linear aesthetic, soft shadows, modern SaaS |
| **sketch** | Hand-drawn whiteboard style, napkin sketch feel, imperfect lines, marker aesthetic |
| **data_viz** | Chart-heavy, numbers prominent, McKinsey/BCG consulting deck style |
| **giger** | H.R. Giger biomechanical, dark intricate patterns, organic-meets-machine (bold choice) |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/tools/storyboard/coperniq_presets.py` | Add voice_tone, vocabulary, forbidden_phrases, default_visual_style per persona |
| `src/tools/storyboard/gemini_client.py` | Amplify value angle instructions, add 4 new artist styles |

---

## Testing

1. Generate storyboard for each persona
2. Verify distinct voice/vocabulary
3. Verify visual style matches persona
4. Verify value framing is strong (COI=fear, ROI=gains, EASE=simplicity)
5. Test each new artist style

---

## Risk: Low

- Modifying prompts only (no architecture changes)
- Session-based (no persistence needed)
- Easy to iterate on wording
