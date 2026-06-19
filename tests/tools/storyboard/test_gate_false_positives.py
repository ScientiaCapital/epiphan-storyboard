"""Regression tests for the two quality-gate false-positives that fired on
otherwise-correct higher-ed output:

    Unknown product ID 'pearl-nexus' — not in EPIPHAN_PRODUCTS catalog
    Unknown product ID 'ec20-ptz'   — not in EPIPHAN_PRODUCTS catalog
    Personal names in output: ['Media Services'] — must use roles only

Root causes:
* product ids arrived kebab-case from the LLM while the catalog keys on
  snake_case, and there was no normalization layer; and
* the personal-name detector flagged any two Title-Case words unless one was a
  job-role word, so org-units / verticals ("Media Services", "Live Events",
  "Higher Ed") tripped it.

Both products are real and current (verified against the live Epiphan catalog:
Pearl Nexus ESP1948/$3,999; EC20 PTZ ESP1899/$1,899, catalog slug ``ec20``).
"""

import pytest

from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_PRODUCTS,
    normalize_product_id,
)
from src.tools.storyboard.quality_gate import QualityReport, run_quality_gate


def _understanding(**overrides) -> dict:
    base = {
        "headline": "Stop walking SD cards between classrooms",
        "tagline": "One box from capture to cloud",
        "what_it_does": "Pearl Nexus records and streams every room without an operator.",
        "business_value": "Saves $6,600 per room vs traditional",
        "who_benefits": "AV Directors and their Media Services team",
        "differentiator": "Only Pearl pairs capture with fleet management via Epiphan Edge",
        "pain_point_addressed": "Manual SD card collection after every lecture",
        "recommended_products": ["pearl_nexus", "ec20_ptz"],
    }
    base.update(overrides)
    return base


def _brand_issues(report: QualityReport) -> list:
    return [i for i in report.issues if i.category == "brand"]


class TestNormalizeProductId:
    def test_kebab_maps_to_snake(self):
        assert normalize_product_id("pearl-nexus") == "pearl_nexus"
        assert normalize_product_id("ec20-ptz") == "ec20_ptz"

    def test_ec20_bare_slug_aliases_to_ptz(self):
        # Live catalog slug for the camera is literally "ec20".
        assert normalize_product_id("ec20") == "ec20_ptz"

    def test_spaces_and_case_and_whitespace(self):
        assert normalize_product_id("  Pearl Nexus  ") == "pearl_nexus"
        assert normalize_product_id("PEARL-2") == "pearl_2"

    def test_already_canonical_is_idempotent(self):
        for pid in EPIPHAN_PRODUCTS:
            assert normalize_product_id(pid) == pid

    def test_synthetic_cloud_id_passes(self):
        assert normalize_product_id("epiphan-edge") == "epiphan_edge"

    def test_unknown_returns_none(self):
        assert normalize_product_id("totally-made-up") is None
        assert normalize_product_id("") is None


class TestProductReferenceGate:
    def test_kebab_ids_no_longer_flagged(self):
        report = run_quality_gate(
            _understanding(recommended_products=["pearl-nexus", "ec20-ptz"]),
            audience="av_director",
        )
        msgs = [i.message for i in _brand_issues(report)]
        assert not any("Unknown product ID" in m for m in msgs), msgs

    def test_genuinely_unknown_id_still_flagged(self):
        report = run_quality_gate(
            _understanding(recommended_products=["acme-9000"]),
            audience="av_director",
        )
        assert any(
            "Unknown product ID" in i.message for i in _brand_issues(report)
        )


class TestPersonalNameGate:
    @pytest.mark.parametrize(
        "phrase",
        ["Media Services", "Live Events", "Higher Ed", "Creative Services"],
    )
    def test_org_units_and_verticals_pass(self, phrase):
        report = run_quality_gate(
            _understanding(who_benefits=phrase),
            audience="av_director",
        )
        assert not any(
            "Personal names" in i.message for i in _brand_issues(report)
        ), phrase

    def test_real_person_name_still_flagged(self):
        report = run_quality_gate(
            _understanding(who_benefits="Contact John Smith for scheduling"),
            audience="av_director",
        )
        assert any(
            "Personal names" in i.message for i in _brand_issues(report)
        )
