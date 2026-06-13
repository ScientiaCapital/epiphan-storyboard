"""Single source of truth for the demo UI dropdowns.

The demo's persona/vertical/style/format vocabulary used to live in three
places — the Pydantic schema in ``router.py``, the ``<option>`` blocks in
``static/demo.html``, and (for personas only) the ``AudiencePersona`` enum
in ``epiphan_presets.py``. The drift between them caused the same bug class
twice in two days (visual_style="blueprint" 2026-05-05 b1d5789, av_integrator
2026-05-08), each surfacing as a silent 422 in production.

This module is now the SSOT. Adding a new option:

1. Add the value to the relevant ``Enum`` in this file (or to ``AudiencePersona``
   in ``epiphan_presets.py`` for personas — that enum is the deeper source for
   personas because prompt-building code already keys off it).
2. Add the matching ``Option(value, label, emoji, group)`` entry to the
   corresponding ``*_OPTIONS`` list below.
3. Add the ``<option value="...">`` element to ``static/demo.html``.
4. Run ``pytest tests/demo/`` — ``test_dropdown_parity.py`` will guard
   the three-way SSOT↔router↔HTML invariant going forward.

All three steps are mechanical and the tests fail loudly until they're done.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.tools.storyboard.epiphan_presets import AudiencePersona

# ---------------------------------------------------------------------------
# Enums consumed by GenerateRequest in router.py
# ---------------------------------------------------------------------------


class Vertical(str, Enum):
    """Target vertical / industry for storyboard generation."""

    HIGHER_ED = "higher_ed"
    CORPORATE = "corporate"
    LIVE_EVENTS = "live_events"
    GOVERNMENT = "government"
    HOUSES_OF_WORSHIP = "houses_of_worship"
    HEALTHCARE = "healthcare"
    INDUSTRIAL = "industrial"
    LEGAL = "legal"
    UX_RESEARCH = "ux_research"
    K12 = "k12"
    BROADCASTING = "broadcasting"


class OutputFormat(str, Enum):
    """Storyboard output aspect ratio."""

    INFOGRAPHIC = "infographic"  # 16:9 horizontal
    STORYBOARD = "storyboard"  # 9:16 vertical


class VisualStyle(str, Enum):
    """Visual style of the generated image."""

    CLEAN = "clean"
    POLISHED = "polished"
    PHOTO_REALISTIC = "photo_realistic"
    MINIMALIST = "minimalist"
    ISOMETRIC = "isometric"
    SKETCH = "sketch"
    DATA_VIZ = "data_viz"
    BOLD = "bold"
    BLUEPRINT = "blueprint"


class ArtistStyle(str, Enum):
    """Optional artist-style overlay. ``NONE`` is a sentinel for 'no overlay'.

    The downstream prompt builder treats ``"none"`` and an empty/None value
    identically (see ``prompts.get_artist_style_instructions`` — unknown keys
    return an empty string). Keeping ``NONE`` as a real enum value lets the
    UI always send a non-empty string.
    """

    NONE = "none"
    SALVADOR_DALI = "salvador_dali"
    MONET = "monet"
    DIEGO_RIVERA = "diego_rivera"
    WARHOL = "warhol"
    VAN_GOGH = "van_gogh"
    PICASSO = "picasso"
    GIGER = "giger"
    FRIDA_KAHLO = "frida_kahlo"
    SIQUEIROS = "siqueiros"


# ---------------------------------------------------------------------------
# UI metadata — labels + emojis + (optional) optgroup
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Option:
    """A single dropdown option with display metadata.

    ``value`` is what the API consumes (must match an enum value).
    ``label`` is the human-readable text shown next to the emoji.
    ``group`` is an ``<optgroup label>`` for clustering (personas only today).
    """

    value: str
    label: str
    emoji: str = ""
    group: str | None = None


PERSONA_OPTIONS: list[Option] = [
    # ATL — Decision Makers
    Option(
        AudiencePersona.AV_DIRECTOR.value, "AV Director", "🎬", "ATL — Decision Makers"
    ),
    Option(
        AudiencePersona.LD_DIRECTOR.value, "L&D Director", "📚", "ATL — Decision Makers"
    ),
    Option(
        AudiencePersona.SIM_CENTER_DIRECTOR.value,
        "Sim Center Dir",
        "🏥",
        "ATL — Decision Makers",
    ),
    Option(
        AudiencePersona.COURT_ADMIN.value, "Court Admin", "⚖️", "ATL — Decision Makers"
    ),
    Option(
        AudiencePersona.CORP_COMMS.value, "Corp Comms", "📢", "ATL — Decision Makers"
    ),
    Option(
        AudiencePersona.EHS_MANAGER.value, "EHS Manager", "🦺", "ATL — Decision Makers"
    ),
    Option(
        AudiencePersona.LAW_FIRM_IT.value, "Law Firm IT", "💼", "ATL — Decision Makers"
    ),
    # ATL — Higher Ed / Edtech
    Option(AudiencePersona.PROVOST.value, "Provost", "🎓", "ATL — Higher Ed / Edtech"),
    Option(
        AudiencePersona.UNIVERSITY_PRESIDENT.value,
        "Univ President",
        "🏛️",
        "ATL — Higher Ed / Edtech",
    ),
    Option(
        AudiencePersona.UNIVERSITY_FINANCE.value,
        "Univ Finance",
        "📊",
        "ATL — Higher Ed / Edtech",
    ),
    Option(
        AudiencePersona.EDTECH_MANAGER.value,
        "Edtech Manager",
        "💻",
        "ATL — Higher Ed / Edtech",
    ),
    # ATL — Live Events
    Option(
        AudiencePersona.VENUE_MANAGER.value, "Venue Manager", "🏟️", "ATL — Live Events"
    ),
    Option(
        AudiencePersona.PRODUCTION_DIRECTOR.value,
        "Production Director",
        "🎥",
        "ATL — Live Events",
    ),
    # BTL — Operators
    Option(
        AudiencePersona.TECHNICAL_DIRECTOR.value,
        "Technical Director",
        "🔧",
        "BTL — Operators",
    ),
    # CHANNEL — Partners
    Option(
        AudiencePersona.DEALER_DAVE.value, "Dealer Dave", "🤝", "CHANNEL — Partners"
    ),
    Option(
        AudiencePersona.SYSTEM_ENGINEER.value,
        "System Engineer",
        "⚙️",
        "CHANNEL — Partners",
    ),
    Option(
        AudiencePersona.AV_INTEGRATOR.value, "AV Integrator", "🔩", "CHANNEL — Partners"
    ),
]


VERTICAL_OPTIONS: list[Option] = [
    Option(Vertical.HIGHER_ED.value, "Higher Ed", "🎓"),
    Option(Vertical.CORPORATE.value, "Corporate", "🏢"),
    Option(Vertical.LIVE_EVENTS.value, "Live Events", "🎤"),
    Option(Vertical.GOVERNMENT.value, "Government", "🏛️"),
    Option(Vertical.HOUSES_OF_WORSHIP.value, "Worship", "⛪"),
    Option(Vertical.HEALTHCARE.value, "Healthcare", "🏥"),
    Option(Vertical.INDUSTRIAL.value, "Industrial", "🏭"),
    Option(Vertical.LEGAL.value, "Legal", "⚖️"),
    Option(Vertical.UX_RESEARCH.value, "UX Research", "🔬"),
    Option(Vertical.K12.value, "K-12", "📚"),
    Option(Vertical.BROADCASTING.value, "Broadcasting", "📺"),
]


OUTPUT_FORMAT_OPTIONS: list[Option] = [
    Option(OutputFormat.INFOGRAPHIC.value, "Infographic", "📋"),
    Option(OutputFormat.STORYBOARD.value, "Storyboard", "📱"),
]


VISUAL_STYLE_OPTIONS: list[Option] = [
    Option(VisualStyle.POLISHED.value, "Polished", "✨"),
    Option(VisualStyle.CLEAN.value, "Clean", "🍎"),
    Option(VisualStyle.PHOTO_REALISTIC.value, "Photo", "📷"),
    Option(VisualStyle.MINIMALIST.value, "Minimal", "🔷"),
    Option(VisualStyle.ISOMETRIC.value, "3D", "🧊"),
    Option(VisualStyle.SKETCH.value, "Sketch", "✏️"),
    Option(VisualStyle.DATA_VIZ.value, "Data", "📊"),
    Option(VisualStyle.BOLD.value, "Bold", "🔶"),
    Option(VisualStyle.BLUEPRINT.value, "Blueprint", "📐"),
]


ARTIST_STYLE_OPTIONS: list[Option] = [
    Option(ArtistStyle.NONE.value, "None", "🎨"),
    Option(ArtistStyle.SALVADOR_DALI.value, "Dali", "🕐"),
    Option(ArtistStyle.MONET.value, "Monet", "🌸"),
    Option(ArtistStyle.DIEGO_RIVERA.value, "Rivera", "🖼️"),
    Option(ArtistStyle.WARHOL.value, "Warhol", "🎯"),
    Option(ArtistStyle.VAN_GOGH.value, "Van Gogh", "🌻"),
    Option(ArtistStyle.PICASSO.value, "Picasso", "🔺"),
    Option(ArtistStyle.GIGER.value, "Giger", "🦾"),
    Option(ArtistStyle.FRIDA_KAHLO.value, "Frida Kahlo", "🌺"),
    Option(ArtistStyle.SIQUEIROS.value, "Siqueiros", "🖌️"),
]


# ---------------------------------------------------------------------------
# Serialisation helpers consumed by ``GET /demo/options``
# ---------------------------------------------------------------------------


def options_payload() -> dict[str, list[dict[str, str | None]]]:
    """Render the SSOT as a JSON-serialisable dict for the ``/demo/options`` endpoint."""

    def _render(options: list[Option]) -> list[dict[str, str | None]]:
        return [
            {
                "value": opt.value,
                "label": opt.label,
                "emoji": opt.emoji,
                "group": opt.group,
            }
            for opt in options
        ]

    return {
        "personas": _render(PERSONA_OPTIONS),
        "verticals": _render(VERTICAL_OPTIONS),
        "output_formats": _render(OUTPUT_FORMAT_OPTIONS),
        "visual_styles": _render(VISUAL_STYLE_OPTIONS),
        "artist_styles": _render(ARTIST_STYLE_OPTIONS),
    }
