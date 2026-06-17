"""
Product Visual Specs — Single Source of Truth for image generation
===================================================================

Authoritative VISUAL + TECHNICAL facts about each Epiphan product, so that
generated images depict the right hardware accurately and make no false
technical claims.

Consumed by the image-generation prompt builder (``build_product_visual_block``)
and the technical-accuracy gate (``collect_do_not_depict``).

Keys are the snake_case product ids from ``epiphan_presets.EPIPHAN_PRODUCTS``,
plus one synthetic id ``epiphan_edge`` for the cloud fleet-management service,
which has no catalog entry.

Seed data is verbatim from the Epiphan Knowledge MCP and Epiphan AI MCP. To
refresh it, run ``scripts/regen_product_visual_specs.py`` inside a Claude Code
session that has those MCPs connected, paste the verified facts here, and bump
``SPECS_VERSION``. Coverage is intentionally partial: AV.io capture cards and
bundles carry conservative stubs derived from epiphan_presets.py — that is fine
and is exercised as a graceful-degrade path by the tests.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from .epiphan_presets import EPIPHAN_PRODUCTS

# Bump whenever the seed data below changes. See module docstring + regen script.
SPECS_VERSION: str = "2026.06.17b"


class ProductVisualSpec(BaseModel):
    """Authoritative visual + technical facts for one product."""

    product_id: str
    display_name: str
    # 1-2 sentences an image model can draw from.
    visual_description: str
    # Short, concrete visual cues.
    key_visual_traits: list[str]
    # True capabilities worth depicting / labeling.
    technical_facts: list[str]
    # False / excluded claims the image must avoid.
    do_not_depict: list[str]


# =============================================
# Verified specs (Epiphan Knowledge + Epiphan AI MCP)
# =============================================

PRODUCT_VISUAL_SPECS: dict[str, ProductVisualSpec] = {
    "pearl_mini": ProductVisualSpec(
        product_id="pearl_mini",
        display_name="Pearl Mini",
        visual_description=(
            "Portable desktop hardware encoder in a metal enclosure, "
            "VESA-mountable, roughly 10.25 by 6.75 by 2.375 inches "
            "(261x172x60 mm). A capacitive front touchscreen dominates the "
            "front face."
        ),
        key_visual_traits=[
            "metal rectangular desktop chassis",
            "capacitive front touchscreen (confidence monitoring + one-touch record/stream)",
            "front status LEDs",
            "front SD card slot",
            "front USB 3.0 port",
            "3.5mm audio out on front",
        ],
        technical_facts=[
            "all-in-one encoder/streamer/switcher/recorder",
            "multi-source capture",
            "CMS integration (Kaltura/Panopto/YuJa)",
            "touchscreen one-touch streaming/recording",
        ],
        do_not_depict=[
            "a rack-only/1RU appliance (it is a desktop unit)",
            "a screen on the rear (the touchscreen is on the front)",
        ],
    ),
    "pearl_nano": ProductVisualSpec(
        product_id="pearl_nano",
        display_name="Pearl Nano",
        visual_description=(
            "Compact slim single-channel hardware encoder with a small front "
            "screen and menu. Much smaller and slimmer than Pearl Mini."
        ),
        key_visual_traits=[
            "compact slim chassis",
            "small front screen menu",
            "connectors: BNC (SDI), HDMI type A, USB-A, RJ-45",
            "XLR + RCA audio inputs",
        ],
        technical_facts=[
            "single-channel single-layout encoder for lecture capture / remote contribution",
            "12G SDI + 4K HDMI inputs (4K add-on)",
            "SRT and RTSP",
            "CMS integration Kaltura/Panopto/YuJa",
            "SRT with AES, RTMPS, 802.1x",
        ],
        do_not_depict=[
            "NDI or NDI|HX support (Pearl Nano does NOT support NDI)",
            "Dante audio (not supported)",
            "multi-channel or live switching (single channel, no switching)",
            "capturing HDCP-encrypted sources",
        ],
    ),
    "pearl_nexus": ProductVisualSpec(
        product_id="pearl_nexus",
        display_name="Pearl Nexus",
        visual_description=(
            "1RU rackmounted multi-channel video appliance in the standard "
            "19-inch rack form factor."
        ),
        key_visual_traits=[
            "1RU rackmount chassis",
            "rack-ear mounting",
            "clean front face",
        ],
        technical_facts=[
            "multi-channel encoder/streamer/live-switcher/recorder, up to three 1080p30 channels",
            "NDI|HX ingest",
            "AC-DC power adapter (FSP060-DHAN3)",
            "optional m.2 2280 SATA SSD (NVMe NOT supported)",
        ],
        do_not_depict=[
            "NDI full / NDI Alpha channel (only NDI|HX ingest, no alpha)",
            "NVMe storage (SATA only)",
            "more than three channels",
        ],
    ),
    "pearl_2": ProductVisualSpec(
        product_id="pearl_2",
        display_name="Pearl-2",
        visual_description=(
            "Larger all-in-one live production appliance, available as a "
            "portable unit or 19-inch Rackmount / Rackmount Twin. The front "
            "face has a touch screen, USB 3.0, 3.5mm audio jack, and power button."
        ),
        key_visual_traits=[
            "touch screen front panel",
            "front USB 3.0 + 3.5mm jack + power button",
            "rich rear I/O: 4x XLR, 4x HDMI 1.4, 12G SDI, RCA, RS-232, HDMI out, USB 3.0, RJ-45",
            "Rackmount Twin = two independent systems",
        ],
        technical_facts=[
            "h.264 encoder/streamer/live-switcher/recorder, up to six 1080p30 channels simultaneous/isolated",
            "rear RJ-45 supports RTSP/SRT/NDI/NDI|HX (Tx/Rx)",
            "4K HDMI/SDI inputs with 4K add-on",
        ],
        do_not_depict=[
            "a tiny/handheld device (it is a larger pro appliance)",
            "4K without the 4K feature add-on",
        ],
    ),
    "pearl_duo": ProductVisualSpec(
        product_id="pearl_duo",
        display_name="Pearl Duo",
        visual_description=(
            "Compact, rack-friendly charcoal metal appliance with 'epiphan "
            "video' + 'PEARL DUO' branding at top-left and a signature "
            "lime-green accent panel with a vent grille on the right. Its "
            "front face has TWO side-by-side touchscreen displays (Channel 1 "
            "and Channel 2 confidence monitoring) plus a large circular "
            "push/jog control knob."
        ),
        key_visual_traits=[
            "charcoal metal rack-friendly chassis with a green right-side accent panel",
            "TWO side-by-side front touchscreens (Channel 1 / Channel 2, dual confidence monitoring)",
            "large circular push/jog knob with a touch indicator",
            "CH1/CH2 Record (red) + Stream (blue) + two Scene buttons, plus a Back button",
            "front headphone jack, volume keys, and USB-C port",
        ],
        technical_facts=[
            "dual-channel encode/record/stream; single-channel 4K; H.264 and H.265",
            "12G-SDI + HDMI with passthrough; pro audio inputs; internal SSD recording",
            "PoE+ network interface; USB-C file transfer",
            "SRT, HLS, RTMP(S), RTSP, NDI|HX",
            "on-device control via the dual front touchscreens (no laptop or browser needed)",
            "Epiphan Edge cloud fleet management + open APIs (Stream Deck, Companion, Skaarhoj, Crestron, Q-SYS, Extron)",
            "optional 1RU shelf holds two Duo units (four channels per rack unit)",
            "pre-launch: ships December 2026",
        ],
        # Gate-matching signal phrases: ONLY the false-attribute words, no
        # product name and no true-Duo vocabulary (two/channels/Edge/etc.) —
        # otherwise legitimate Duo copy collides with the avoid-phrase. The
        # full positive context lives in visual_description / key_visual_traits.
        # Pearl Duo, unlike Pearl Mini/Nano/Nexus, does NOT do lecture capture
        # or CMS/LMS integration.
        do_not_depict=[
            "a single-screen device",
            "lecture capture or CMS/LMS integration",
            "classroom recording or CMS publishing",
            "a broadcast production switcher",
            "a local on-device dashboard",
            "a playback or scrubbing recorder",
        ],
    ),
    "ec20_ptz": ProductVisualSpec(
        product_id="ec20_ptz",
        display_name="EC20 PTZ Camera",
        visual_description=(
            "Pan-tilt-zoom camera for ceiling or wall mount, with a visible "
            "motorized lens/zoom barrel, a white/neutral body, and a tally "
            "indicator."
        ),
        key_visual_traits=[
            "ceiling/wall-mountable PTZ camera",
            "motorized PTZ head with visible zoom lens",
            "single PoE+ cable (802.3at)",
            "LCD shows IP address",
        ],
        technical_facts=[
            "4K-capable PTZ, 20x optical + 16x digital zoom",
            "AI auto-tracking (Presenter + Zone modes)",
            "outputs HDMI 2.0 / SDI / USB-C / NDI|HX2 / SRT/RTMP/RTSP over Ethernet",
            "H.265/H.264/MJPEG",
            "pairs with Pearl encoders",
            "can record direct to CMS/LMS with no separate encoder",
            "Dante audio over IP",
        ],
        do_not_depict=[
            "EC20 needing or using a SEPARATE ENCODER to record to a CMS/LMS "
            "(it records direct — this is the #1 false claim to block)",
            "a fixed (non-PTZ) box camera",
            "needing multiple cables for power+data (single PoE+ cable)",
        ],
    ),
    "epiphan_edge": ProductVisualSpec(
        product_id="epiphan_edge",
        display_name="Epiphan Edge (cloud)",
        visual_description=(
            "Web/cloud fleet-management dashboard UI in a browser. A left "
            "vertical side-navigation panel holds icons (labels on hover). The "
            "main area is a Devices Dashboard: a grid/list of paired Pearl "
            "devices showing online/offline status and health stats along the top."
        ),
        key_visual_traits=[
            "browser dashboard",
            "left side-nav with icons",
            "Devices Dashboard grid",
            "online devices highlighted, offline/unpaired devices grayed out",
            "per-row three-dots menu (Reboot, Unpair, Move to Group, Delete)",
            "per-channel start/stop stream & record buttons",
            "filter by status/model/health",
            "device grouping + batch ops for Premium",
        ],
        technical_facts=[
            "cloud-based remote fleet management & monitoring for Pearl devices",
            "status/health monitoring",
            "remote reboot/stream/record",
            "grouping & batch operations (Premium)",
        ],
        do_not_depict=[
            "a piece of physical hardware/box (Edge is cloud software, not a device)",
            "an on-prem-only appliance",
        ],
    ),
}


def _stub_spec(product_id: str) -> ProductVisualSpec:
    """Build a conservative spec for a catalog product lacking verified data.

    Derives a generic visual description and technical facts from the
    epiphan_presets.py ``form_factor`` and ``key_specs`` fields. ``do_not_depict``
    is intentionally empty — we make no exclusion claims we cannot verify.
    """
    product = cast("dict[str, Any]", EPIPHAN_PRODUCTS[product_id])
    name = str(product["name"])
    form_factor = str(product.get("form_factor", "")).strip()
    key_specs = [str(spec) for spec in product.get("key_specs", [])]

    if form_factor:
        visual = f"{name} — {form_factor} Epiphan video product."
    else:
        visual = f"{name} — Epiphan video product."

    traits = [form_factor] if form_factor else []

    return ProductVisualSpec(
        product_id=product_id,
        display_name=name,
        visual_description=visual,
        key_visual_traits=traits,
        technical_facts=key_specs,
        do_not_depict=[],
    )


# Backfill conservative stubs for any catalog product without a verified spec
# (AV.io capture cards, bundles). Verified entries above are never overwritten.
for _product_id in EPIPHAN_PRODUCTS:
    if _product_id not in PRODUCT_VISUAL_SPECS:
        PRODUCT_VISUAL_SPECS[_product_id] = _stub_spec(_product_id)


def get_visual_spec(product_id: str) -> ProductVisualSpec | None:
    """Return the visual spec for ``product_id``, or ``None`` if unknown."""
    return PRODUCT_VISUAL_SPECS.get(product_id)


def build_product_visual_block(product_ids: list[str], limit: int = 3) -> str:
    """Render a prompt-injectable text block for the given products.

    Returns ``""`` when the list is empty or no ids are known (graceful
    degrade). Unknown ids are skipped silently. Caps output at ``limit``
    products, in the order given.
    """
    specs: list[ProductVisualSpec] = []
    for product_id in product_ids:
        spec = PRODUCT_VISUAL_SPECS.get(product_id)
        if spec is not None:
            specs.append(spec)
        if len(specs) >= limit:
            break

    if not specs:
        return ""

    lines: list[str] = ["PRODUCTS TO DEPICT (visual accuracy):"]
    for spec in specs:
        lines.append("")
        lines.append(f"{spec.display_name}:")
        lines.append(f"- Visual: {spec.visual_description}")
        if spec.key_visual_traits:
            lines.append(f"- Key visual traits: {'; '.join(spec.key_visual_traits)}")
        if spec.technical_facts:
            lines.append(f"- Key technical facts: {'; '.join(spec.technical_facts)}")
        if spec.do_not_depict:
            lines.append(f"- Do NOT depict: {'; '.join(spec.do_not_depict)}")
    return "\n".join(lines)


def collect_do_not_depict(product_ids: list[str]) -> list[str]:
    """Flatten ``do_not_depict`` across the known products (for the gate).

    Unknown ids are skipped. Returns ``[]`` when nothing applies.
    """
    flattened: list[str] = []
    for product_id in product_ids:
        spec = PRODUCT_VISUAL_SPECS.get(product_id)
        if spec is not None:
            flattened.extend(spec.do_not_depict)
    return flattened
