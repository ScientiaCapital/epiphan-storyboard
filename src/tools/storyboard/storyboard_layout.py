"""Deterministic storyboard layout builder (Track C).

The diffusion model renders a TEXT-FREE hero illustration only; every word of
copy is composited client-side on a ``<canvas>`` in crisp Söhne from the
``StoryboardLayout`` this module produces. Because text never reaches the image
model, the garble/duplication failure modes are structurally impossible.

``build_layout`` is a *pure* mapping from an already-extracted
``StoryboardUnderstanding`` plus presets — no LLM call, fully unit-testable.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.tools.storyboard.epiphan_presets import (
    get_product,
    get_stage_template,
    get_vertical,
    normalize_product_id,
)
from src.tools.storyboard.gemini_client import StoryboardUnderstanding, _dedupe_and_cap

_EYEBROW_FALLBACK = "Epiphan Storyboard"
_NEUTRAL_ICON = "clipboard-check"

# Ordered keyword → icon rules. First substring match wins, so the more specific
# / higher-signal concepts (money, logistics) sit above the generic ones.
_ICON_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("dollar", ("$", "save", "saving", "cost", "roi", "budget", "revenue", "price")),
    ("truck", ("truck", "on-site", "onsite", "travel", "drive", "rolls")),
    ("cloud", ("cloud", "fleet", "remote", "manage", "edge", "provision")),
    ("lock", ("secure", "security", "lock", "privacy", "compliance", "encrypt")),
    ("encoder", ("record", "encode", "encoder", "stream", "capture", "broadcast")),
    ("network", ("network", "ndi", "srt", "rtmp", "bandwidth")),
    ("lecture-hall", ("lecture", "classroom", "campus", "course", "teaching")),
    ("camera", ("camera", "ptz", "lens", "zoom", "framing")),
    ("display", ("display", "screen", "monitor", "projector", "hdmi")),
    ("calendar", ("schedule", "calendar", "deadline", "hours", "week")),
    ("users", ("team", "staff", "people", "person", "user", "director", "student")),
    ("building", ("building", "facility", "venue", "court", "hospital", "plant")),
]


def _svg(viewbox_paths: str) -> str:
    """Wrap inner SVG markup in a consistent 24×24 stroke icon.

    The ``xmlns`` is required: these SVGs are rendered client-side as standalone
    ``image/svg+xml`` data-URL images on a ``<canvas>``, and an SVG used as an
    image must declare its namespace or the browser refuses to load it.
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round">'
        f"{viewbox_paths}</svg>"
    )


# Curated AV/IT glyph set. Self-contained, tiny, drawn client-side from a
# ``image/svg+xml`` data URL. Keys are the canonical icon names ``resolve_icon``
# returns; ``build_layout`` ships only the subset a given layout actually uses.
ICON_SVGS: dict[str, str] = {
    "dollar": _svg(
        '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
    ),
    "truck": _svg(
        '<rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>'
    ),
    "cloud": _svg('<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>'),
    "lock": _svg(
        '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    ),
    "encoder": _svg(
        '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="7" cy="12" r="2"/><line x1="13" y1="10" x2="19" y2="10"/><line x1="13" y1="14" x2="19" y2="14"/>'
    ),
    "network": _svg(
        '<rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M12 8v4M12 12H5v4M12 12h7v4"/>'
    ),
    "lecture-hall": _svg(
        '<path d="M3 9l9-5 9 5-9 5-9-5z"/><path d="M7 11v5a5 3 0 0 0 10 0v-5"/>'
    ),
    "camera": _svg(
        '<path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>'
    ),
    "display": _svg(
        '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
    ),
    "calendar": _svg(
        '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>'
    ),
    "users": _svg(
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "building": _svg(
        '<rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="6" x2="9" y2="6"/><line x1="15" y1="6" x2="15" y2="6"/><line x1="9" y1="10" x2="9" y2="10"/><line x1="15" y1="10" x2="15" y2="10"/><path d="M10 22v-4h4v4"/>'
    ),
    "clipboard-check": _svg(
        '<path d="M9 2h6a2 2 0 0 1 2 2H7a2 2 0 0 1 2-2z"/><path d="M7 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/><path d="M9 14l2 2 4-4"/>'
    ),
}


class LayoutCard(BaseModel):
    """One content card: a short copy line plus the icon that illustrates it."""

    caption: str = Field(..., description="Deduped, length-capped copy line")
    icon: str = Field(..., description="Key into ICON_SVGS")


class StoryboardLayout(BaseModel):
    """A fixed, brand-owned infographic layout the client renders on canvas."""

    eyebrow: str = Field(..., description="Vertical display name (or fallback)")
    headline: str = Field(..., description="Hero headline")
    cards: list[LayoutCard] = Field(
        default_factory=list, description="2–4 content cards; empty fields collapse"
    )
    stat_value: str = Field(
        default="", description='Stat number, e.g. "$6,600" ("" hides callout)'
    )
    stat_label: str = Field(default="", description="Short context for the stat")
    cta: str = Field(..., description="Persona/stage-appropriate call to action")
    product_name: str | None = Field(
        default=None, description="Lead product display name"
    )
    hero_alt: str = Field(..., description="Alt text for the hero illustration")
    icon_svgs: dict[str, str] = Field(
        default_factory=dict,
        description="Only the used icon keys → inline <svg> markup",
    )


def resolve_icon(caption: str, suggested_icon: str = "") -> str:
    """Pick an icon key for *caption*.

    Keyword scan first (deterministic), then the model's ``suggested_icon`` if it
    names a known glyph, then a neutral default. Pure function.
    """
    text = caption.lower()
    for icon, keywords in _ICON_RULES:
        if any(kw in text for kw in keywords):
            return icon
    if suggested_icon in ICON_SVGS:
        return suggested_icon
    return _NEUTRAL_ICON


_STAT_RE = re.compile(r"\$?\d[\d,]*\.?\d*\s?%?")
_LABEL_STOP = re.compile(r"^[\s\-–—:,.]+")


def _parse_stat(business_value: str) -> tuple[str, str]:
    """Pull the headline number + a short trailing label out of *business_value*.

    Returns ``("", "")`` when there's no number (the client then hides the
    stat callout rather than rendering an empty box).
    """
    match = _STAT_RE.search(business_value)
    if not match:
        return "", ""
    value = match.group(0).strip()
    tail = _LABEL_STOP.sub("", business_value[match.end() :])
    label = " ".join(tail.split()[:3]).strip(" .,")
    return value, label


def _eyebrow_for(vertical: str | None) -> str:
    if not vertical:
        return _EYEBROW_FALLBACK
    try:
        return str(get_vertical(vertical)["name"])
    except (ValueError, KeyError):
        return _EYEBROW_FALLBACK


def _cta_for(stage: str) -> str:
    try:
        return str(get_stage_template(stage)["cta"])
    except (ValueError, KeyError):
        return str(get_stage_template("preview")["cta"])


def _product_name_for(understanding: StoryboardUnderstanding) -> str | None:
    for raw in understanding.recommended_products:
        pid = normalize_product_id(raw) or raw
        try:
            return str(get_product(pid)["name"])
        except (ValueError, KeyError):
            continue
    return None


def build_layout(
    understanding: StoryboardUnderstanding,
    vertical: str | None = None,
    stage: str = "demo",
) -> StoryboardLayout:
    """Map an extracted understanding + presets into a deterministic layout.

    No model call: every field comes from ``understanding`` or the preset SSOT.
    ``business_value`` feeds the stat callout (never a card); the remaining copy
    fields become 2–4 cards (deduped, capped, empties collapsed).
    """
    captions = _dedupe_and_cap(
        [
            understanding.what_it_does,
            understanding.differentiator,
            understanding.pain_point_addressed,
            understanding.who_benefits,
        ]
    )[:4]
    cards = [
        LayoutCard(caption=c, icon=resolve_icon(c, understanding.suggested_icon))
        for c in captions
    ]
    stat_value, stat_label = _parse_stat(understanding.business_value)
    used_icons = {c.icon for c in cards}
    return StoryboardLayout(
        eyebrow=_eyebrow_for(vertical),
        headline=understanding.headline,
        cards=cards,
        stat_value=stat_value,
        stat_label=stat_label,
        cta=_cta_for(stage),
        product_name=_product_name_for(understanding),
        hero_alt=understanding.tagline or understanding.headline,
        icon_svgs={k: ICON_SVGS[k] for k in used_icons},
    )
