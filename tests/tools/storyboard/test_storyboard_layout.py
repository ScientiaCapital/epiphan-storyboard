"""Tests for the deterministic storyboard layout builder (Track C).

``build_layout`` is a pure, model-free mapping from an already-extracted
``StoryboardUnderstanding`` plus presets into a fixed infographic layout. The
client composites this on a ``<canvas>`` in crisp Söhne, so text never touches
the diffusion model — garble/duplication become structurally impossible.

These tests pin the mapping, the dedup/collapse behavior, stat parsing, product
display-name resolution, the icon-resolution fallback chain, and that every
icon a layout references ships a well-formed ``<svg>``.
"""

import re

from src.tools.storyboard.gemini_client import StoryboardUnderstanding
from src.tools.storyboard.storyboard_layout import (
    ICON_SVGS,
    LayoutCard,
    StoryboardLayout,
    build_layout,
    resolve_icon,
)


def _understanding(**overrides) -> StoryboardUnderstanding:
    base = {
        "headline": "Stop walking SD cards between classrooms",
        "tagline": "One box from capture to cloud",
        "what_it_does": "Pearl Nexus records and streams every room without an operator.",
        "business_value": "Saves $6,600 per room vs traditional AV",
        "who_benefits": "AV Directors and their Media Services team",
        "differentiator": "Only Pearl pairs capture with fleet management via Epiphan Edge",
        "pain_point_addressed": "Manual SD card collection after every lecture",
        "suggested_icon": "camera",
        "recommended_products": ["pearl_nexus", "ec20_ptz"],
    }
    base.update(overrides)
    return StoryboardUnderstanding(**base)


# --------------------------------------------------------------------------- #
# build_layout — field mapping
# --------------------------------------------------------------------------- #


def test_build_layout_maps_headline_verbatim() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert isinstance(layout, StoryboardLayout)
    assert layout.headline == "Stop walking SD cards between classrooms"


def test_eyebrow_is_vertical_display_name() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert layout.eyebrow == "Higher Education"


def test_eyebrow_falls_back_when_vertical_missing() -> None:
    assert build_layout(_understanding(), vertical=None).eyebrow == "Epiphan Storyboard"


def test_eyebrow_falls_back_on_unknown_vertical() -> None:
    layout = build_layout(_understanding(), vertical="atlantis")
    assert layout.eyebrow == "Epiphan Storyboard"


def test_hero_alt_prefers_tagline() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert layout.hero_alt == "One box from capture to cloud"


def test_hero_alt_falls_back_to_headline_when_no_tagline() -> None:
    layout = build_layout(_understanding(tagline=""), vertical="higher_ed")
    assert layout.hero_alt == "Stop walking SD cards between classrooms"


# --------------------------------------------------------------------------- #
# build_layout — cards
# --------------------------------------------------------------------------- #


def test_cards_built_from_copy_fields() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert 2 <= len(layout.cards) <= 4
    assert all(isinstance(c, LayoutCard) for c in layout.cards)
    captions = " ".join(c.caption for c in layout.cards).lower()
    assert "records and streams" in captions
    assert "fleet management" in captions


def test_business_value_is_not_a_card() -> None:
    # business_value feeds the stat callout, never a card.
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert not any("$6,600" in c.caption for c in layout.cards)


def test_empty_copy_fields_collapse_cards() -> None:
    layout = build_layout(
        _understanding(differentiator="", pain_point_addressed=""),
        vertical="higher_ed",
    )
    # what_it_does + who_benefits remain → 2 cards, no blanks.
    assert all(c.caption.strip() for c in layout.cards)
    assert len(layout.cards) == 2


def test_duplicate_copy_lines_are_deduped() -> None:
    dupe = "Fewer truck rolls. Managed remotely."
    layout = build_layout(
        _understanding(differentiator=dupe, pain_point_addressed=dupe),
        vertical="higher_ed",
    )
    matches = [c for c in layout.cards if "truck rolls" in c.caption.lower()]
    assert len(matches) == 1


def test_cards_capped_at_four() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert len(layout.cards) <= 4


# --------------------------------------------------------------------------- #
# build_layout — stat callout
# --------------------------------------------------------------------------- #


def test_stat_value_parsed_from_business_value() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert layout.stat_value == "$6,600"
    assert "room" in layout.stat_label.lower()


def test_stat_parses_percentage() -> None:
    layout = build_layout(
        _understanding(business_value="Cuts setup time by 40% per event"),
        vertical="live_events",
    )
    assert layout.stat_value == "40%"


def test_stat_hidden_when_no_number() -> None:
    layout = build_layout(
        _understanding(business_value="Unable to determine - extraction failed"),
        vertical="higher_ed",
    )
    assert layout.stat_value == ""
    assert layout.stat_label == ""


# --------------------------------------------------------------------------- #
# build_layout — product + cta
# --------------------------------------------------------------------------- #


def test_product_name_resolved_to_display_name() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    assert layout.product_name == "Pearl Nexus"


def test_product_name_none_when_no_products() -> None:
    layout = build_layout(_understanding(recommended_products=[]), vertical="higher_ed")
    assert layout.product_name is None


def test_cta_from_stage_template() -> None:
    assert build_layout(_understanding(), vertical="higher_ed", stage="demo").cta == (
        "Let's talk about your operation."
    )
    assert build_layout(
        _understanding(), vertical="higher_ed", stage="preview"
    ).cta == ("See how it works for your team.")


# --------------------------------------------------------------------------- #
# resolve_icon
# --------------------------------------------------------------------------- #


def test_resolve_icon_matches_keyword() -> None:
    assert resolve_icon("Saves $6,600 per room", "camera") == "dollar"
    assert resolve_icon("Cloud-managed fleet via Epiphan Edge", "camera") == "cloud"
    assert resolve_icon("No more SD card truck rolls", "camera") == "truck"


def test_resolve_icon_falls_back_to_suggested() -> None:
    # No keyword in the caption → use the model's suggested_icon if it's known.
    assert resolve_icon("A pleasant generic sentence", "encoder") == "encoder"


def test_resolve_icon_neutral_default_when_all_unknown() -> None:
    assert resolve_icon("A pleasant generic sentence", "not-a-real-icon") == (
        "clipboard-check"
    )


def test_every_resolved_icon_exists_in_registry() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    for card in layout.cards:
        assert card.icon in ICON_SVGS


# --------------------------------------------------------------------------- #
# icon_svgs payload
# --------------------------------------------------------------------------- #


def test_layout_ships_only_used_icon_svgs() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    used = {c.icon for c in layout.cards}
    assert set(layout.icon_svgs) == used


def test_icon_svgs_are_well_formed() -> None:
    layout = build_layout(_understanding(), vertical="higher_ed")
    for svg in layout.icon_svgs.values():
        assert svg.lstrip().startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "viewBox" in svg


def test_registry_entries_all_well_formed() -> None:
    assert ICON_SVGS  # non-empty
    for key, svg in ICON_SVGS.items():
        assert re.match(r"^[a-z0-9-]+$", key), key
        assert svg.lstrip().startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
