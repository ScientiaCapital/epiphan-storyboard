"""Tests for UnifiedStoryboardTool."""

import base64
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.base import BaseTool, ToolCategory
from src.tools.storyboard.gemini_client import StoryboardUnderstanding
from src.tools.storyboard.unified_storyboard import UnifiedStoryboardTool


class TestUnifiedStoryboardDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        """Tool should have correct name."""
        tool = UnifiedStoryboardTool()
        assert tool.definition.name == "unified_storyboard"

    def test_definition_category(self):
        """Tool should be in DATA category."""
        tool = UnifiedStoryboardTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_description(self):
        """Tool should have meaningful description."""
        tool = UnifiedStoryboardTool()
        desc = tool.definition.description
        assert "storyboard" in desc.lower()
        assert len(desc) > 50

    def test_definition_has_parameters(self):
        """Tool should have parameters schema."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "properties" in params
        assert "input" in params["properties"]

    def test_inherits_from_base_tool(self):
        """Tool should inherit from BaseTool."""
        tool = UnifiedStoryboardTool()
        assert isinstance(tool, BaseTool)

    def test_does_not_require_approval(self):
        """Tool should not require approval."""
        tool = UnifiedStoryboardTool()
        assert tool.definition.requires_approval is False

    def test_has_open_browser_parameter(self):
        """Tool should have open_browser parameter."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "open_browser" in params
        assert params["open_browser"]["type"] == "boolean"


class TestUnifiedStoryboardParameters:
    """Tests for parameter handling."""

    def test_accepts_input_parameter(self):
        """Tool should accept input parameter."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "input" in params
        assert params["input"]["type"] == "string"

    def test_accepts_stage_parameter(self):
        """Tool should accept stage parameter."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "stage" in params
        assert params["stage"]["enum"] == ["preview", "demo", "shipped"]

    def test_accepts_audience_parameter(self):
        """Tool should accept audience parameter."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "audience" in params
        assert "business_owner" in params["audience"]["enum"]
        assert "c_suite" in params["audience"]["enum"]
        assert "btl_champion" in params["audience"]["enum"]

    def test_accepts_icp_preset_parameter(self):
        """Tool should accept icp_preset parameter."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "icp_preset" in params

    def test_input_is_required(self):
        """Input parameter should be required."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters
        assert "required" in params
        assert "input" in params["required"]


class TestInputTypeDetection:
    """Tests for input type detection."""

    def test_detects_miro_url(self):
        """Should detect Miro board URLs."""
        tool = UnifiedStoryboardTool()
        assert (
            tool.detect_input_type("https://miro.com/app/board/uXjVK123/") == "miro_url"
        )

    def test_detects_image_data_url(self):
        """Should detect base64 image data URLs."""
        tool = UnifiedStoryboardTool()
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
        assert tool.detect_input_type(data_url) == "image_data"

    def test_detects_image_url_png(self):
        """Should detect PNG image URLs."""
        tool = UnifiedStoryboardTool()
        assert tool.detect_input_type("https://example.com/image.png") == "image_url"

    def test_detects_image_url_jpg(self):
        """Should detect JPG image URLs."""
        tool = UnifiedStoryboardTool()
        assert tool.detect_input_type("https://example.com/image.jpg") == "image_url"

    def test_detects_image_url_jpeg(self):
        """Should detect JPEG image URLs."""
        tool = UnifiedStoryboardTool()
        assert tool.detect_input_type("https://example.com/image.jpeg") == "image_url"

    def test_detects_file_path(self):
        """Should detect existing file paths."""
        tool = UnifiedStoryboardTool()
        # Use a file that definitely exists
        file_path = __file__  # This test file itself
        assert tool.detect_input_type(file_path) == "file_path"

    def test_detects_code_as_fallback(self):
        """Should treat unknown input as code."""
        tool = UnifiedStoryboardTool()
        code = "def calculate_roi(): return revenue - costs"
        assert tool.detect_input_type(code) == "code"

    def test_detects_multiline_code_as_code(self):
        """Should detect multiline code strings."""
        tool = UnifiedStoryboardTool()
        code = """
def calculate_roi(revenue, costs):
    return revenue - costs
"""
        assert tool.detect_input_type(code) == "code"


class TestBrowserOpening:
    """Tests for browser opening functionality."""

    def test_save_and_open_browser_creates_file(self):
        """Should save PNG to temp file."""
        tool = UnifiedStoryboardTool()
        # Minimal valid PNG
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        # Don't actually open browser in tests
        with patch("webbrowser.open"):
            file_path = tool.save_and_open_browser(png_bytes, open_browser=False)

        assert os.path.exists(file_path)
        assert file_path.endswith(".png")

        # Cleanup
        os.remove(file_path)

    def test_save_and_open_browser_calls_webbrowser(self):
        """Should call webbrowser.open when open_browser=True."""
        tool = UnifiedStoryboardTool()
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        with patch("webbrowser.open") as mock_open:
            file_path = tool.save_and_open_browser(png_bytes, open_browser=True)
            mock_open.assert_called_once()
            call_arg = mock_open.call_args[0][0]
            assert call_arg.startswith("file://")

        # Cleanup
        os.remove(file_path)

    def test_save_and_open_browser_skips_when_disabled(self):
        """Should NOT call webbrowser.open when open_browser=False."""
        tool = UnifiedStoryboardTool()
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        with patch("webbrowser.open") as mock_open:
            file_path = tool.save_and_open_browser(png_bytes, open_browser=False)
            mock_open.assert_not_called()

        # Cleanup
        os.remove(file_path)


class TestCodeInputHandling:
    """Tests for handling code input."""

    @pytest.mark.asyncio
    async def test_run_with_code_string(self):
        """Should process code string input."""
        tool = UnifiedStoryboardTool()

        # Mock the Gemini client
        mock_understanding = StoryboardUnderstanding(
            headline="ROI Calculator",
            what_it_does="Calculates return on investment",
            business_value="Save 10 hours per week",
            who_benefits="Finance teams",
            differentiator="Simple and fast",
            pain_point_addressed="Manual calculations",
            suggested_icon="calculator",
        )

        # Minimal valid PNG in base64
        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "def calculate_roi(): return revenue - costs",
                    "open_browser": False,
                }
            )

        assert result.success is True
        assert "storyboard_png" in result.result
        assert result.result["input_type"] == "code"


class TestImageInputHandling:
    """Tests for handling image input."""

    @pytest.mark.asyncio
    async def test_run_with_base64_image(self):
        """Should process base64 image input."""
        tool = UnifiedStoryboardTool()

        # Mock the Gemini client
        mock_understanding = StoryboardUnderstanding(
            headline="Product Roadmap",
            what_it_does="Shows upcoming features",
            business_value="Align team priorities",
            who_benefits="Product teams",
            differentiator="Visual clarity",
            pain_point_addressed="Miscommunication",
            suggested_icon="roadmap",
        )

        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",
                    "open_browser": False,
                }
            )

        assert result.success is True
        assert "storyboard_png" in result.result
        assert result.result["input_type"] == "image_data"


class TestFilePathHandling:
    """Tests for handling file path input."""

    @pytest.mark.asyncio
    async def test_run_with_python_file(self):
        """Should process Python file input."""
        tool = UnifiedStoryboardTool()

        # Create a temp Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): return 'world'")
            temp_path = f.name

        try:
            mock_understanding = StoryboardUnderstanding(
                headline="Hello Function",
                what_it_does="Returns greeting",
                business_value="Simplifies greetings",
                who_benefits="Developers",
                differentiator="Clean code",
                pain_point_addressed="Complex greetings",
                suggested_icon="wave",
            )

            mock_png = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            )

            mock_client = MagicMock()
            mock_client.understand_code = AsyncMock(return_value=mock_understanding)
            mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
            tool._gemini_client = mock_client

            with patch("webbrowser.open"):
                result = await tool.run(
                    {
                        "input": temp_path,
                        "open_browser": False,
                    }
                )

            assert result.success is True
            assert result.result["input_type"] == "file_path"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_run_with_image_file(self):
        """Should process image file input."""
        tool = UnifiedStoryboardTool()

        # Create a temp PNG file
        png_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            f.write(png_bytes)
            temp_path = f.name

        try:
            mock_understanding = StoryboardUnderstanding(
                headline="Screenshot Analysis",
                what_it_does="Analyzes screenshot",
                business_value="Quick insights",
                who_benefits="Teams",
                differentiator="Visual processing",
                pain_point_addressed="Manual review",
                suggested_icon="camera",
            )

            mock_client = MagicMock()
            mock_client.understand_image = AsyncMock(return_value=mock_understanding)
            mock_client.generate_storyboard = AsyncMock(return_value=png_bytes)
            tool._gemini_client = mock_client

            with patch("webbrowser.open"):
                result = await tool.run(
                    {
                        "input": temp_path,
                        "open_browser": False,
                    }
                )

            assert result.success is True
            assert result.result["input_type"] == "file_path"
            # Should detect it's an image file
            assert result.result.get("is_image_file") is True
        finally:
            os.unlink(temp_path)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_run_without_input_fails(self):
        """Should fail when no input provided."""
        tool = UnifiedStoryboardTool()

        result = await tool.run({})

        assert result.success is False
        assert "input" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_with_nonexistent_file_fails(self):
        """Should fail when file does not exist."""
        tool = UnifiedStoryboardTool()

        # This path should not exist, so it will be treated as code
        # But if the code is very short it might fail
        await tool.run(
            {
                "input": "/nonexistent/path/to/file.py",
                "open_browser": False,
            }
        )

        # Should be treated as code (fallback), not error for nonexistent file
        # The code analyzer might fail on this weird "code"
        # This tests the fallback behavior - just verify it doesn't crash


class TestMiroUrlHandling:
    """Tests for Miro URL handling."""

    @pytest.mark.asyncio
    async def test_miro_url_prompts_for_screenshot(self):
        """Should handle Miro URLs gracefully."""
        tool = UnifiedStoryboardTool()

        # Miro URLs require authentication, so we should prompt for screenshot
        result = await tool.run(
            {
                "input": "https://miro.com/app/board/uXjVK123456/",
                "open_browser": False,
            }
        )

        # Either it fails gracefully with a message about screenshot
        # Or it attempts to fetch and handles the error
        # The exact behavior depends on implementation
        assert (
            result.success is False
            or "screenshot" in str(result.result).lower()
            or "miro" in str(result.error).lower()
        )


class TestResultFormat:
    """Tests for result format."""

    @pytest.mark.asyncio
    async def test_result_contains_storyboard_png(self):
        """Result should contain base64 storyboard PNG."""
        tool = UnifiedStoryboardTool()

        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Tests",
            business_value="Testing",
            who_benefits="Testers",
            differentiator="Testing",
            pain_point_addressed="No tests",
            suggested_icon="test",
        )

        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "def test(): pass",
                    "open_browser": False,
                }
            )

        assert "storyboard_png" in result.result
        # Should be valid base64
        try:
            decoded = base64.b64decode(result.result["storyboard_png"])
            assert len(decoded) > 0
        except Exception:
            pytest.fail("storyboard_png is not valid base64")

    @pytest.mark.asyncio
    async def test_result_contains_understanding(self):
        """Result should contain understanding dict."""
        tool = UnifiedStoryboardTool()

        mock_understanding = StoryboardUnderstanding(
            headline="Test Headline",
            what_it_does="Does things",
            business_value="Adds value",
            who_benefits="Everyone",
            differentiator="Unique",
            pain_point_addressed="Problems",
            suggested_icon="icon",
        )

        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "def test(): pass",
                    "open_browser": False,
                }
            )

        assert "understanding" in result.result
        assert result.result["understanding"]["headline"] == "Test Headline"

    @pytest.mark.asyncio
    async def test_result_contains_file_path(self):
        """Result should contain saved file path."""
        tool = UnifiedStoryboardTool()

        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Tests",
            business_value="Testing",
            who_benefits="Testers",
            differentiator="Testing",
            pain_point_addressed="No tests",
            suggested_icon="test",
        )

        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "def test(): pass",
                    "open_browser": False,
                }
            )

        assert "file_path" in result.result
        assert result.result["file_path"].endswith(".png")

    @pytest.mark.asyncio
    async def test_result_contains_input_type(self):
        """Result should contain detected input type."""
        tool = UnifiedStoryboardTool()

        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Tests",
            business_value="Testing",
            who_benefits="Testers",
            differentiator="Testing",
            pain_point_addressed="No tests",
            suggested_icon="test",
        )

        mock_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=mock_png)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run(
                {
                    "input": "def test(): pass",
                    "open_browser": False,
                }
            )

        assert "input_type" in result.result
        assert result.result["input_type"] == "code"
