"""Tests for the product visual specs SSOT (pure data, no live API)."""

from src.tools.storyboard.epiphan_presets import EPIPHAN_PRODUCTS
from src.tools.storyboard.product_visual_specs import (
    PRODUCT_VISUAL_SPECS,
    SPECS_VERSION,
    ProductVisualSpec,
    build_product_visual_block,
    collect_do_not_depict,
    get_visual_spec,
)


class TestSpecsIntegrity:
    def test_keys_are_known_products_or_edge(self):
        for product_id in PRODUCT_VISUAL_SPECS:
            assert product_id in EPIPHAN_PRODUCTS or product_id == "epiphan_edge"

    def test_all_entries_validate(self):
        for spec in PRODUCT_VISUAL_SPECS.values():
            assert isinstance(spec, ProductVisualSpec)
            assert spec.product_id
            assert spec.display_name
            assert spec.visual_description

    def test_specs_version_is_non_empty_str(self):
        assert isinstance(SPECS_VERSION, str)
        assert SPECS_VERSION

    def test_full_catalog_coverage(self):
        for product_id in EPIPHAN_PRODUCTS:
            assert product_id in PRODUCT_VISUAL_SPECS


class TestBuildBlock:
    def test_empty_list_returns_empty(self):
        assert build_product_visual_block([]) == ""

    def test_all_unknown_returns_empty(self):
        assert build_product_visual_block(["totally_unknown"]) == ""

    def test_unknown_ids_skipped_when_mixed(self):
        block = build_product_visual_block(["totally_unknown", "ec20_ptz"])
        assert block
        assert "EC20" in block
        assert "totally_unknown" not in block

    def test_respects_limit(self):
        ids = ["pearl_mini", "pearl_nano", "pearl_nexus", "pearl_2", "ec20_ptz"]
        block = build_product_visual_block(ids, limit=2)
        # Each product renders a "<Name>:" header line; count rendered products.
        rendered = sum(
            1
            for line in block.splitlines()
            if line.endswith(":") and not line.startswith("-")
        )
        # 1 header ("PRODUCTS TO DEPICT...") + at most `limit` product headers.
        assert rendered <= 2 + 1

    def test_ec20_block_content(self):
        block = build_product_visual_block(["ec20_ptz"])
        assert "20x" in block
        assert "PoE" in block
        assert "encoder" in block.lower()

    def test_has_header(self):
        block = build_product_visual_block(["pearl_mini"])
        assert "PRODUCTS TO DEPICT" in block


class TestDoNotDepict:
    def test_ec20_blocks_separate_encoder(self):
        spec = get_visual_spec("ec20_ptz")
        assert spec is not None
        joined = " ".join(spec.do_not_depict).lower()
        assert "encoder" in joined

    def test_pearl_nano_mentions_ndi(self):
        spec = get_visual_spec("pearl_nano")
        assert spec is not None
        joined = " ".join(spec.do_not_depict).lower()
        assert "ndi" in joined

    def test_collect_flattens_non_empty(self):
        flat = collect_do_not_depict(["ec20_ptz", "pearl_nano"])
        assert flat
        assert isinstance(flat, list)

    def test_collect_empty(self):
        assert collect_do_not_depict([]) == []

    def test_collect_skips_unknown(self):
        flat = collect_do_not_depict(["totally_unknown"])
        assert flat == []


class TestGetVisualSpec:
    def test_known(self):
        assert get_visual_spec("pearl_mini") is not None

    def test_unknown_returns_none(self):
        assert get_visual_spec("totally_unknown") is None
