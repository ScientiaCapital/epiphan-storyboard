"""Tests for demo router endpoints."""

import base64
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
        "video_script_generator",
        "gemini_client",
    }

    assert expected.issubset(example_names), f"Missing examples: {expected - example_names}"


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
            "audience": "c_suite",
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
            "audience": "c_suite",
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
            "audience": "c_suite",
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
            "audience": "c_suite",
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
            "audience": "c_suite",
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
            "audience": "c_suite",
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
                "audience": "c_suite",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["storyboard_png"] == "fake_base64_png"
        assert "understanding" in data
        assert data["input_type"] == "code"
        assert data["stage"] == "preview"
        assert data["audience"] == "c_suite"


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
                "audience": "c_suite",
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
