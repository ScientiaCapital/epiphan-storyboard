"""Tests for demo router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.tools.base import ToolResult


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ============================================================================
# GET /demo/examples Tests
# ============================================================================


def test_list_examples_success(client):
    """Test GET /demo/examples returns list of examples."""
    response = client.get("/demo/examples")

    assert response.status_code == 200
    data = response.json()

    assert "examples" in data
    assert isinstance(data["examples"], list)
    assert len(data["examples"]) > 0

    # Check first example has required fields
    example = data["examples"][0]
    assert "name" in example
    assert "path" in example
    assert "description" in example


def test_list_examples_structure(client):
    """Test example objects have correct structure."""
    response = client.get("/demo/examples")
    data = response.json()

    for example in data["examples"]:
        assert isinstance(example["name"], str)
        assert isinstance(example["path"], str)
        assert isinstance(example["description"], str)
        assert example["name"]  # Not empty
        assert example["path"]  # Not empty
        assert example["description"]  # Not empty


def test_list_examples_contains_expected(client):
    """Test list contains expected examples."""
    response = client.get("/demo/examples")
    data = response.json()

    example_names = {ex["name"] for ex in data["examples"]}

    # Check for key examples
    expected = {
        "unified_storyboard",
        "gemini_client",
        "epiphan_presets",
    }

    assert expected.issubset(example_names), (
        f"Missing examples: {expected - example_names}"
    )


# ============================================================================
# GET /demo/examples/{name} Tests
# ============================================================================


def test_get_example_code_success(client):
    """Test GET /demo/examples/{name} returns code."""
    response = client.get("/demo/examples/unified_storyboard")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert data["name"] == "unified_storyboard"
    assert "path" in data
    assert "description" in data
    assert "code" in data
    assert "line_count" in data

    # Check code content
    assert len(data["code"]) > 0
    assert data["line_count"] > 0
    assert isinstance(data["line_count"], int)


def test_get_example_code_content_valid(client):
    """Test returned code is valid Python."""
    response = client.get("/demo/examples/unified_storyboard")
    data = response.json()

    # Should be valid Python file (contains imports, classes, etc.)
    code = data["code"]
    assert "import" in code or "from" in code
    assert "class" in code or "def" in code


def test_get_example_code_line_count_accurate(client):
    """Test line_count matches actual code lines."""
    response = client.get("/demo/examples/unified_storyboard")
    data = response.json()

    actual_lines = len(data["code"].splitlines())
    assert data["line_count"] == actual_lines


def test_get_example_code_not_found(client):
    """Test GET /demo/examples/nonexistent returns 404."""
    response = client.get("/demo/examples/nonexistent_example")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_example_code_all_examples_readable(client):
    """Test all listed examples are readable."""
    # Get list of examples
    list_response = client.get("/demo/examples")
    examples = list_response.json()["examples"]

    # Try to read each one
    for example in examples:
        response = client.get(f"/demo/examples/{example['name']}")
        assert response.status_code == 200, f"Failed to read {example['name']}"


# ============================================================================
# POST /demo/generate Tests
# ============================================================================


def test_generate_rejects_empty_code(client):
    """Test POST /demo/generate rejects empty code input."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "code",
            "code": "",
            "stage": "preview",
            "audience": "av_director",
        },
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    assert "empty" in response.json()["detail"].lower()


def test_generate_rejects_empty_image(client):
    """Test POST /demo/generate rejects empty image input."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "image",
            "image_base64": "",
            "stage": "preview",
            "audience": "av_director",
        },
    )

    assert response.status_code == 400
    assert "detail" in response.json()


def test_generate_rejects_whitespace_only(client):
    """Test POST /demo/generate rejects whitespace-only input."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "code",
            "code": "   \n\t  ",
            "stage": "preview",
            "audience": "av_director",
        },
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_generate_requires_image_when_type_image(client):
    """Test POST /demo/generate requires image_base64 when input_type='image'."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "image",
            "code": "def foo(): pass",  # Wrong field
            "stage": "preview",
            "audience": "av_director",
        },
    )

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_generate_requires_code_when_type_code(client):
    """Test POST /demo/generate requires code when input_type='code'."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "code",
            "image_base64": "fake_base64",  # Wrong field
            "stage": "preview",
            "audience": "av_director",
        },
    )

    assert response.status_code == 400
    assert "code" in response.json()["detail"]


def test_generate_validates_input_type(client):
    """Test POST /demo/generate validates input_type enum."""
    response = client.post(
        "/demo/generate",
        json={
            "input_type": "invalid_type",
            "code": "def foo(): pass",
            "stage": "preview",
            "audience": "av_director",
        },
    )

    # Should fail validation (422)
    assert response.status_code == 422


def test_generate_with_code_mocked(client):
    """Test POST /demo/generate with code input (mocked tool)."""
    mock_result = ToolResult(
        tool_name="unified_storyboard",
        success=True,
        result={
            "storyboard_png": "fake_base64_png",
            "understanding": {
                "headline": "Test Feature",
                "what_it_does": "Does testing",
                "business_value": "Saves time",
                "who_benefits": "Developers",
                "differentiator": "Fast",
                "pain_point_addressed": "Slow tests",
                "suggested_icon": "test",
            },
            "input_type": "code",
        },
        execution_time_ms=1000,
    )

    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = mock_result
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def calculate_roi(): return 100",
                "stage": "preview",
                "audience": "av_director",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["storyboard_png"] == "fake_base64_png"
        assert "understanding" in data
        assert data["input_type"] == "code"
        assert data["stage"] == "preview"
        assert data["audience"] == "av_director"


def test_generate_handles_tool_failure(client):
    """Test POST /demo/generate handles tool failure gracefully."""
    mock_result = ToolResult(
        tool_name="unified_storyboard",
        success=False,
        result={},
        error="API key missing",
        execution_time_ms=100,
    )

    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = mock_result
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "stage": "preview",
                "audience": "av_director",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["error"] == "API key missing"
        assert data["storyboard_png"] is None


def test_generate_passes_open_browser_false(client):
    """Test POST /demo/generate sets open_browser=False."""
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = ToolResult(
            tool_name="unified_storyboard",
            success=True,
            result={
                "storyboard_png": "fake",
                "understanding": {},
                "input_type": "code",
            },
            execution_time_ms=100,
        )
        MockTool.return_value = mock_instance

        client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
            },
        )

        # Verify open_browser=False was passed
        call_args = mock_instance.run.call_args
        assert call_args is not None
        assert call_args[0][0]["open_browser"] is False


# ============================================================================
# Schema Regression Tests (commit 9930fad — Broadcasting + Blueprint + artists)
# ============================================================================


def _mock_tool_success():
    """Build a successful ToolResult fixture for /demo/generate mocks."""
    return ToolResult(
        tool_name="unified_storyboard",
        success=True,
        result={
            "storyboard_png": "fake_base64_png",
            "understanding": {},
            "input_type": "code",
        },
        execution_time_ms=100,
    )


def test_generate_accepts_blueprint_visual_style(client):
    """Regression for 9930fad: visual_style='blueprint' must not 422.

    The frontend dropdown in static/demo.html offers 'blueprint' but the
    Pydantic Literal in src/demo/router.py was not updated, producing a
    422 Unprocessable Entity that the demo UI rendered as
    'Generation failed: [object Object]'.
    """
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = _mock_tool_success()
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "stage": "demo",
                "audience": "av_director",
                "vertical": "higher_ed",
                "output_format": "storyboard",
                "visual_style": "blueprint",
                "artist_style": "frida_kahlo",
            },
        )

        assert response.status_code != 422, (
            f"Pydantic rejected payload — schema out of sync with demo.html. "
            f"Body: {response.text}"
        )
        assert response.status_code == 200
        assert response.json()["visual_style"] == "blueprint"


def test_generate_accepts_broadcasting_vertical(client):
    """Regression for 9930fad: vertical='broadcasting' must not 422."""
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = _mock_tool_success()
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "audience": "av_director",
                "vertical": "broadcasting",
            },
        )

        assert response.status_code != 422, (
            f"Pydantic rejected vertical='broadcasting'. Body: {response.text}"
        )
        assert response.status_code == 200


def test_generate_accepts_new_artist_styles(client):
    """Regression for 9930fad: frida_kahlo + siqueiros artists pass validation.

    artist_style is typed `str | None` so this should already pass — the test
    locks the contract in case someone tightens the type later.
    """
    for artist in ("frida_kahlo", "siqueiros"):
        with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = _mock_tool_success()
            MockTool.return_value = mock_instance

            response = client.post(
                "/demo/generate",
                json={
                    "input_type": "code",
                    "code": "def foo(): pass",
                    "audience": "av_director",
                    "artist_style": artist,
                },
            )

            assert response.status_code != 422, (
                f"Pydantic rejected artist_style={artist!r}. Body: {response.text}"
            )
            assert response.status_code == 200


# ============================================================================
# Source-of-truth regression — HTML dropdown options must match Literal types
# ============================================================================
#
# The Blueprint regression (b1d5789), Broadcasting regression (b1d5789), and
# av_integrator regression (today) are all the same bug class: the HTML
# `<option value="...">` list and the Pydantic Literal in src/demo/router.py
# drift out of sync. The fix is documented in Backlog as a future SSOT
# refactor, but until that lands these scrape-based tests catch any new
# drift fail-loud at CI.


def _scrape_html_select_options(select_id: str) -> set[str]:
    """Return the set of `<option value="...">` values for the given <select>.

    Cheap regex scrape — keeps the test free of an HTML-parser dependency.
    Returns the empty set if the select isn't found, which would itself be
    a regression worth flagging.
    """
    import re
    from pathlib import Path

    html = Path("static/demo.html").read_text()
    # Find the select block — match from the opening tag (with id) to its
    # closing </select>. Allow attributes between id and the >.
    select_re = re.compile(
        rf'<select\b[^>]*\bid="{re.escape(select_id)}"[^>]*>(.*?)</select>',
        flags=re.DOTALL,
    )
    m = select_re.search(html)
    if not m:
        return set()
    block = m.group(1)
    return set(re.findall(r'<option\s+value="([^"]+)"', block))


@pytest.mark.parametrize(
    "html_value",
    sorted(_scrape_html_select_options("audienceSelect")),
)
def test_audience_dropdown_values_in_pydantic_literal(client, html_value):
    """Every value in the audienceSelect <select> must validate via the
    GenerateRequest schema. Catches drift like commit b1d5789 (visual_style)
    and the av_integrator gap surfaced 2026-05-08.
    """
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = _mock_tool_success()
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "audience": html_value,
            },
        )

        assert response.status_code != 422, (
            f"Pydantic rejected audience={html_value!r} from the demo "
            f"dropdown. The HTML and the Literal in src/demo/router.py "
            f"have drifted. Body: {response.text}"
        )


@pytest.mark.parametrize(
    "html_value",
    sorted(_scrape_html_select_options("verticalSelect")),
)
def test_vertical_dropdown_values_in_pydantic_literal(client, html_value):
    """Every value in the verticalSelect <select> must validate via
    GenerateRequest. Catches the same drift class for verticals."""
    if html_value == "auto":
        # The demo wires "auto" to None on the client side. Skip — the
        # Pydantic Literal correctly rejects "auto" as a sentinel.
        return
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = _mock_tool_success()
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "audience": "av_director",
                "vertical": html_value,
            },
        )

        assert response.status_code != 422, (
            f"Pydantic rejected vertical={html_value!r} from the demo "
            f"dropdown. The HTML and the Literal in src/demo/router.py "
            f"have drifted. Body: {response.text}"
        )


@pytest.mark.parametrize(
    "html_value",
    sorted(_scrape_html_select_options("visualStyleSelect")),
)
def test_visual_style_dropdown_values_in_pydantic_literal(client, html_value):
    """Every value in the visualStyleSelect <select> must validate."""
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = _mock_tool_success()
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "audience": "av_director",
                "visual_style": html_value,
            },
        )

        assert response.status_code != 422, (
            f"Pydantic rejected visual_style={html_value!r} from the demo "
            f"dropdown. The HTML and the Literal in src/demo/router.py "
            f"have drifted. Body: {response.text}"
        )


# ============================================================================
# Integration Tests (require files to exist)
# ============================================================================


def test_integration_read_real_file(client):
    """Integration test: Read a real example file."""
    response = client.get("/demo/examples/gemini_client")

    # Should succeed if file exists
    if response.status_code == 200:
        data = response.json()
        assert len(data["code"]) > 100  # Real file should be substantial
        assert "Gemini" in data["code"] or "gemini" in data["code"]


def test_generate_passes_quality_through(client):
    """The quality gate report from the tool must reach the API response."""
    mock_result = ToolResult(
        tool_name="unified_storyboard",
        success=True,
        result={
            "storyboard_png": "fake_base64_png",
            "understanding": {"headline": "Test"},
            "input_type": "code",
            "quality": {
                "passed": False,
                "score": 85.0,
                "reframe_applied": True,
                "issues": [
                    {
                        "category": "brand",
                        "severity": "critical",
                        "message": "Competitor 'sony' positioned as hero in headline",
                    }
                ],
            },
        },
        execution_time_ms=1000,
    )

    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = mock_result
        MockTool.return_value = mock_instance

        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "stage": "preview",
                "audience": "av_director",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["quality"]["passed"] is False
    assert data["quality"]["reframe_applied"] is True
    assert data["quality"]["issues"][0]["category"] == "brand"


def test_generate_forwards_layout_and_hero(client):
    """Track C: /demo/generate forwards `layout` and `hero_png_b64` to the client."""
    result = ToolResult(
        tool_name="unified_storyboard",
        success=True,
        result={
            "storyboard_png": "fake_base64_png",
            "hero_png_b64": "hero_base64_png",
            "layout": {
                "eyebrow": "Higher Education",
                "headline": "Walk SD cards no more",
                "cards": [{"caption": "Records every room", "icon": "encoder"}],
                "stat_value": "$6,600",
                "stat_label": "per room",
                "cta": "Let's talk about your operation.",
                "product_name": "Pearl Nexus",
                "hero_alt": "One box from capture to cloud",
                "icon_svgs": {"encoder": '<svg viewBox="0 0 24 24"></svg>'},
            },
            "understanding": {},
            "input_type": "code",
        },
        execution_time_ms=100,
    )
    with patch("src.demo.router.UnifiedStoryboardTool") as MockTool:
        mock_instance = AsyncMock()
        mock_instance.run.return_value = result
        MockTool.return_value = mock_instance
        response = client.post(
            "/demo/generate",
            json={
                "input_type": "code",
                "code": "def foo(): pass",
                "stage": "demo",
                "audience": "av_director",
                "vertical": "higher_ed",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["hero_png_b64"] == "hero_base64_png"
    assert body["layout"]["headline"] == "Walk SD cards no more"
    assert body["layout"]["cards"][0]["icon"] == "encoder"
