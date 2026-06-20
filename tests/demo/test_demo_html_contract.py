"""Guard tests for the Track C demo frontend contract (static/demo.html).

The canvas renderer can't be exercised by pytest (it's browser JS — that path is
verified live via Playwright), but these cheap, deterministic checks lock the
wiring so a future edit can't silently revert Track C: the single canvas asset,
the toBlob download, consumption of the {layout, hero_png_b64} response, and the
removal of the old garbled-image / html2canvas path.
"""

from pathlib import Path

import pytest

_HTML = Path(__file__).resolve().parents[2] / "static" / "demo.html"


@pytest.fixture(scope="module")
def html() -> str:
    return _HTML.read_text(encoding="utf-8")


def test_canvas_element_present(html: str) -> None:
    assert 'id="storyboardCanvas"' in html


def test_renderer_and_toblob_download_wired(html: str) -> None:
    assert "function renderStoryboard" in html
    assert "canvas.toBlob" in html  # lossless export, replaces html2canvas


def test_consumes_track_c_response_contract(html: str) -> None:
    # The renderer must read the structured layout + the text-free hero.
    assert "result.layout" in html
    assert "hero_png_b64" in html


def test_share_and_copy_affordances_present(html: str) -> None:
    assert "function copyImage" in html
    assert "function copyShareLink" in html
    assert 'id="shareLinkBtn"' in html


def test_old_garbled_image_path_removed(html: str) -> None:
    # Regression guard: the dual-output toggle, the garbled AI <img>, and the
    # flaky html2canvas rasterizer must stay gone.
    assert "html2canvas(" not in html
    assert 'id="storyboardCard"' not in html
    assert 'id="resultImg"' not in html
    assert "toggleAiVisual" not in html


def test_internal_qa_not_customer_facing(html: str) -> None:
    # The quality-gate report is internal QA — it must not render in the demo
    # (it still runs server-side to drive the reframe retry).
    assert "renderQuality" not in html
    assert 'id="qualitySection"' not in html
    assert "review before sending" not in html


def test_no_hardware_name_in_canvas_footer(html: str) -> None:
    # By request: the footer names no product/hardware.
    assert "layout.product_name" not in html
