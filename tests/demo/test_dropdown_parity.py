"""Three-way parity tests for the demo dropdown SSOT.

Background — the schema-drift bug class
========================================
Three places independently know the persona/vertical/style/format vocabulary:

1. ``src/demo/_dropdowns.py``       — the canonical SSOT (lists of Option dicts)
2. ``src/demo/router.py``           — the Pydantic ``GenerateRequest`` schema
3. ``static/demo.html``             — the ``<option>`` elements the UI renders

When any two of these drift, the failure mode is a silent 422 in production
(commit b1d5789 visual_style=blueprint, av_integrator missing 2026-05-08, etc.).
The structural fix is to make ``_dropdowns.py`` the source and have router.py
import its enums; these tests guard the **third** vertex (HTML) and assert
that ``GET /demo/options`` exposes the SSOT correctly.

If you add a new persona / vertical / style:
- Add it to ``src/demo/_dropdowns.py`` only. router.py picks it up via the
  enum import, and ``static/demo.html`` should already match because these
  tests will fail loudly until you sync the ``<option>`` block.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Project root is two levels up from this file (tests/demo/<file>).
_DEMO_HTML = Path(__file__).resolve().parents[2] / "static" / "demo.html"


def _scrape_html_select_options(select_id: str) -> set[str]:
    """Cheap regex scrape of ``<option value="...">`` values inside a ``<select>``.

    Mirrors the helper in ``test_router.py`` so tests stay independent.
    The HTML path is anchored to ``__file__`` so the test behaves the same
    no matter what cwd pytest runs from. A missing ``<select>`` returns
    ``set()`` which the assertion compares against the SSOT to surface a
    clear "drifted" failure rather than a silent file-not-found.
    """
    html = _DEMO_HTML.read_text()
    select_re = re.compile(
        rf'<select\b[^>]*\bid="{re.escape(select_id)}"[^>]*>(.*?)</select>',
        flags=re.DOTALL,
    )
    match = select_re.search(html)
    if not match:
        return set()
    return set(re.findall(r'<option\s+value="([^"]*)"', match.group(1)))


# ---------------------------------------------------------------------------
# 1. SSOT module shape
# ---------------------------------------------------------------------------


def test_ssot_module_exports_all_canonical_lists() -> None:
    """``_dropdowns.py`` must export the five canonical option lists."""
    from src.demo import _dropdowns

    for attr in (
        "PERSONA_OPTIONS",
        "VERTICAL_OPTIONS",
        "OUTPUT_FORMAT_OPTIONS",
        "VISUAL_STYLE_OPTIONS",
        "ARTIST_STYLE_OPTIONS",
    ):
        assert hasattr(_dropdowns, attr), f"_dropdowns.py is missing {attr}"
        options = getattr(_dropdowns, attr)
        assert len(options) > 0, f"{attr} is empty — no options to render"
        for opt in options:
            assert opt.value, f"{attr} has an empty value"
            assert opt.label, f"{attr} option {opt.value!r} has an empty label"


def test_ssot_persona_values_match_audience_persona_enum() -> None:
    """Every PERSONA_OPTIONS value must come from the AudiencePersona enum.

    Prevents drift at the bottom of the stack — if someone adds a persona to
    ``_dropdowns.py`` without adding it to the enum in ``epiphan_presets.py``,
    downstream prompt-building code that looks up by enum will silently miss
    the new persona.
    """
    from src.demo._dropdowns import PERSONA_OPTIONS
    from src.tools.storyboard.epiphan_presets import AudiencePersona

    enum_values = {p.value for p in AudiencePersona}
    ssot_values = {opt.value for opt in PERSONA_OPTIONS}

    assert ssot_values == enum_values, (
        f"PERSONA_OPTIONS and AudiencePersona enum disagree. "
        f"Only in SSOT: {ssot_values - enum_values}. "
        f"Only in enum: {enum_values - ssot_values}."
    )


# ---------------------------------------------------------------------------
# 2. SSOT ↔ HTML parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "select_id,ssot_attr",
    [
        ("audienceSelect", "PERSONA_OPTIONS"),
        ("verticalSelect", "VERTICAL_OPTIONS"),
        ("outputFormatSelect", "OUTPUT_FORMAT_OPTIONS"),
        ("visualStyleSelect", "VISUAL_STYLE_OPTIONS"),
        ("artistStyleSelect", "ARTIST_STYLE_OPTIONS"),
    ],
)
def test_html_dropdown_options_match_ssot(select_id: str, ssot_attr: str) -> None:
    """HTML ``<option value="...">`` set must equal the SSOT values for that select.

    The verticalSelect has an extra ``""`` (empty value) for the auto-detect
    sentinel; we strip empty values before comparing.
    """
    from src.demo import _dropdowns

    html_values = {v for v in _scrape_html_select_options(select_id) if v}
    ssot_values = {opt.value for opt in getattr(_dropdowns, ssot_attr)}

    assert html_values == ssot_values, (
        f"static/demo.html <select id={select_id!r}> drifted from "
        f"src/demo/_dropdowns.{ssot_attr}. "
        f"Only in HTML: {html_values - ssot_values}. "
        f"Only in SSOT: {ssot_values - html_values}."
    )


# ---------------------------------------------------------------------------
# 3. SSOT ↔ Pydantic parity (router.py uses the enums)
# ---------------------------------------------------------------------------


def test_router_audience_field_uses_audience_persona_enum() -> None:
    """``GenerateRequest.audience`` must be typed as the enum (or accept all enum values).

    The point of the SSOT refactor is that router.py imports the enum
    directly rather than duplicating values inline. This test fails loudly
    if anyone replaces the enum with an inline Literal again.
    """
    from src.demo.router import GenerateRequest
    from src.tools.storyboard.epiphan_presets import AudiencePersona

    schema = GenerateRequest.model_json_schema()
    audience_schema = schema["properties"]["audience"]

    # When the field is typed as the enum, Pydantic emits a $ref. We resolve
    # it via the schema's $defs to get the accepted values.
    if "$ref" in audience_schema:
        ref_name = audience_schema["$ref"].rsplit("/", 1)[-1]
        accepted = set(schema["$defs"][ref_name]["enum"])
    elif "enum" in audience_schema:
        accepted = set(audience_schema["enum"])
    else:
        # Inline Literal would surface here as ``"enum": [...]`` so this
        # branch only fires if the schema is something unexpected.
        pytest.fail(
            f"audience field schema has no enum: {audience_schema!r}. "
            "The SSOT refactor expects router.py to import AudiencePersona."
        )

    enum_values = {p.value for p in AudiencePersona}
    assert accepted == enum_values, (
        f"GenerateRequest.audience accepts {accepted - enum_values} that aren't "
        f"in AudiencePersona, or rejects {enum_values - accepted} that should be."
    )


# ---------------------------------------------------------------------------
# 4. GET /demo/options exposes the SSOT
# ---------------------------------------------------------------------------


def test_get_demo_options_returns_canonical_structure(client: TestClient) -> None:
    """``GET /demo/options`` must return the five canonical lists.

    This is the future-proofing piece — once the demo HTML migrates to
    fetch + populate, this endpoint is the contract it consumes.
    """
    response = client.get("/demo/options")
    assert response.status_code == 200, response.text

    data = response.json()
    for key in (
        "personas",
        "verticals",
        "output_formats",
        "visual_styles",
        "artist_styles",
    ):
        assert key in data, f"GET /demo/options is missing {key!r} key"
        assert isinstance(data[key], list), f"{key} is not a list"
        assert len(data[key]) > 0, f"{key} is empty"
        for opt in data[key]:
            assert "value" in opt, f"{key} option missing 'value': {opt!r}"
            assert "label" in opt, f"{key} option missing 'label': {opt!r}"


def test_get_demo_options_persona_values_match_ssot(client: TestClient) -> None:
    """Endpoint personas must equal the SSOT persona values."""
    from src.demo._dropdowns import PERSONA_OPTIONS

    response = client.get("/demo/options")
    payload_values = {p["value"] for p in response.json()["personas"]}
    ssot_values = {opt.value for opt in PERSONA_OPTIONS}

    assert payload_values == ssot_values, (
        f"GET /demo/options returned personas {payload_values - ssot_values} "
        f"or omitted {ssot_values - payload_values}."
    )
