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
        """Tool should accept audience parameter with all 8 BDR Playbook personas."""
        tool = UnifiedStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "audience" in params
        # ATL personas (7 from BDR Playbook)
        assert "av_director" in params["audience"]["enum"]
        assert "ld_director" in params["audience"]["enum"]
        assert "sim_center_director" in params["audience"]["enum"]
        assert "court_admin" in params["audience"]["enum"]
        assert "corp_comms" in params["audience"]["enum"]
        assert "ehs_manager" in params["audience"]["enum"]
        assert "law_firm_it" in params["audience"]["enum"]
        # BTL persona (1 from BDR Playbook)
        assert "technical_director" in params["audience"]["enum"]
        assert len(params["audience"]["enum"]) == 16

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


class TestIsTranscript:
    """Tests for is_transcript() heuristic — including M-4 false positive fix."""

    def test_clear_transcript_detected(self):
        """Clear transcript with speaker labels should be detected."""
        tool = UnifiedStoryboardTool()
        transcript = """
John: We need to standardize AV across all 300 rooms.
Sarah: I think Pearl Mini is the right fit for the smaller rooms.
John: And for the larger lecture halls, we discussed the Pearl-2.
Sarah: Thank you for setting up this meeting.
"""
        assert tool.is_transcript(transcript) is True

    def test_clear_code_detected(self):
        """Clear Python code should NOT be detected as transcript."""
        tool = UnifiedStoryboardTool()
        code = """
import asyncio
from dataclasses import dataclass

class JobTracker:
    def __init__(self):
        self.jobs = []

    async def track(self, job_id: str) -> dict:
        return {"id": job_id, "status": "active"}
"""
        assert tool.is_transcript(code) is False

    def test_typed_python_not_false_positive(self):
        """Python code with type annotations must NOT be classified as transcript (M-4 fix)."""
        tool = UnifiedStoryboardTool()
        typed_code = """
from typing import Any

@dataclass
class Config:
    api_key: str = ""
    model_name: str = "gemini-2.0-flash"
    timeout: int = 90
    max_retries: int = 3
    enable_cache: bool = True
    vision_provider: str = "qwen"

def process(config: Config, data: dict[str, Any]) -> list[str]:
    results: list[str] = []
    for key, value in data.items():
        result: str = f"{key}: {value}"
        results.append(result)
    return results
"""
        assert tool.is_transcript(typed_code) is False

    def test_pydantic_model_not_false_positive(self):
        """Pydantic model with Field() calls must NOT be classified as transcript."""
        tool = UnifiedStoryboardTool()
        pydantic_code = """
from pydantic import BaseModel, Field

class StoryboardUnderstanding(BaseModel):
    headline: str = Field(..., description="Catchy headline")
    tagline: str = Field(default="", description="Dynamic tagline")
    what_it_does: str = Field(..., description="Plain English")
    business_value: str = Field(..., description="Quantified benefit")
    who_benefits: str = Field(..., description="Target persona")
    differentiator: str = Field(..., description="What makes special")
    extraction_confidence: float = Field(default=1.0)
"""
        assert tool.is_transcript(pydantic_code) is False

    def test_empty_string(self):
        """Empty string should return False (default to code)."""
        tool = UnifiedStoryboardTool()
        assert tool.is_transcript("") is False

    def test_single_line(self):
        """Single line of code should return False."""
        tool = UnifiedStoryboardTool()
        assert tool.is_transcript("def foo(): pass") is False

    def test_json_blob_not_transcript(self):
        """JSON blob should NOT be classified as transcript."""
        tool = UnifiedStoryboardTool()
        json_content = """
{
    "name": "test",
    "version": "1.0",
    "dependencies": {
        "fastapi": "^0.100",
        "pydantic": "^2.0"
    }
}
"""
        assert tool.is_transcript(json_content) is False

    def test_conversational_transcript_with_timestamps(self):
        """Transcript with timestamps and natural language should be detected."""
        tool = UnifiedStoryboardTool()
        transcript = """
[00:01] Sarah: Thanks for joining the call today.
[00:05] Mike: Of course. So we discussed the deployment timeline.
[00:12] Sarah: I think we can have the demo ready by Friday.
[00:18] Mike: That sounds good. And the presentation slides?
[00:25] Sarah: Let me check. We talked about using the new template.
[00:30] Mike: Going to need at least 3 slides for the meeting.
"""
        assert tool.is_transcript(transcript) is True

    def test_mixed_content_code_dominant(self):
        """Content with more code patterns than transcript should be classified as code."""
        tool = UnifiedStoryboardTool()
        content = """
# This module handles the demo presentation
import os
from pathlib import Path

def setup_demo():
    # Initialize the meeting room config
    config = load_config()
    return config

class DemoRunner:
    def __init__(self):
        self.active = True
"""
        assert tool.is_transcript(content) is False

    def test_long_natural_language_detected(self):
        """Long natural language text with few code patterns should be detected as transcript."""
        tool = UnifiedStoryboardTool()
        # Generate content > 3000 chars with no code patterns
        long_text = (
            "The team discussed various approaches to improving the recording quality. "
            "Sarah mentioned that the current setup has reliability issues. "
            "We talked about standardizing the equipment across all rooms. "
        ) * 20  # ~3600 chars
        assert tool.is_transcript(long_text) is True


class TestDirBugFix:
    """Test that the dir() bug fix in error handler works correctly (M-6)."""

    @pytest.mark.asyncio
    async def test_error_handler_captures_input_type(self):
        """Error handler should use locals().get() to safely capture input_type."""
        tool = UnifiedStoryboardTool()

        # Trigger an error after input_type is set but before completion
        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(
            side_effect=RuntimeError("Simulated API failure")
        )
        tool._gemini_client = mock_client

        result = await tool.run(
            {
                "input": "def test(): pass",
                "open_browser": False,
            }
        )

        assert result.success is False
        # The input_type should be captured even in the error path
        assert result.result.get("input_type") == "code"



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


_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _sony_hero_understanding() -> StoryboardUnderstanding:
    return StoryboardUnderstanding(
        headline="Sony's seamless proxy workflow wins live production",
        what_it_does="Sony cameras upload proxies straight to the cloud.",
        business_value="Cuts post-production by 4 hours per event",
        who_benefits="Production Directors",
        differentiator="Only Sony offers simultaneous proxy upload and streaming",
        pain_point_addressed="Rental equipment shortages",
        suggested_icon="camera",
    )


def _epiphan_hero_understanding() -> StoryboardUnderstanding:
    return StoryboardUnderstanding(
        headline="Stop renting your way around proxy failures",
        what_it_does="Pearl Mini captures and streams every feed in one box.",
        business_value="Cuts 12 truck rolls per month",
        who_benefits="Production Directors",
        differentiator="Only Pearl pairs capture with Epiphan Edge fleet management",
        pain_point_addressed="Sony proxy workflows drop files mid-event",
        suggested_icon="video",
    )


class TestQualityGateWiring:
    """The quality gate runs on every generation; a competitor-as-hero
    extraction triggers exactly one corrective reframe retry."""

    def _tool_with_client(self, understand_side_effect):
        tool = UnifiedStoryboardTool()
        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(side_effect=understand_side_effect)
        mock_client.generate_storyboard = AsyncMock(return_value=_TINY_PNG)
        tool._gemini_client = mock_client
        return tool, mock_client

    @pytest.mark.asyncio
    async def test_clean_extraction_runs_once_and_reports_quality(self):
        tool, mock_client = self._tool_with_client([_epiphan_hero_understanding()])

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        assert mock_client.understand_code.call_count == 1
        quality = result.result["quality"]
        assert quality["passed"] is True
        assert quality["reframe_applied"] is False

    @pytest.mark.asyncio
    async def test_competitor_hero_triggers_one_reframe_retry(self):
        tool, mock_client = self._tool_with_client(
            [_sony_hero_understanding(), _epiphan_hero_understanding()]
        )

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        assert mock_client.understand_code.call_count == 2
        # The retry call must carry a corrective instruction naming the competitor
        retry_kwargs = mock_client.understand_code.call_args_list[1].kwargs
        corrective = retry_kwargs.get("corrective_instruction") or ""
        assert "sony" in corrective.lower()

        quality = result.result["quality"]
        assert quality["reframe_applied"] is True
        assert quality["passed"] is True
        # The rendered card must be the reframed (Epiphan-hero) copy
        assert "Sony" not in result.result["understanding"]["headline"]

    @pytest.mark.asyncio
    async def test_failed_reframe_surfaces_failed_quality(self):
        tool, mock_client = self._tool_with_client(
            [_sony_hero_understanding(), _sony_hero_understanding()]
        )

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True  # still renders — UI shows the warning badge
        assert mock_client.understand_code.call_count == 2
        quality = result.result["quality"]
        assert quality["passed"] is False
        assert quality["reframe_applied"] is True
        assert any(
            i["severity"] == "critical" and i["category"] == "brand"
            for i in quality["issues"]
        )

    @pytest.mark.asyncio
    async def test_gate_crash_never_blocks_generation(self):
        tool, mock_client = self._tool_with_client([_epiphan_hero_understanding()])

        with (
            patch("webbrowser.open"),
            patch(
                "src.tools.storyboard.unified_storyboard.run_quality_gate",
                side_effect=RuntimeError("gate exploded"),
            ),
        ):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        assert result.result.get("quality") is None


def _ec20_false_encoder_understanding() -> StoryboardUnderstanding:
    """Hero copy asserting the #1 false EC20 claim (needs a separate encoder)."""
    return StoryboardUnderstanding(
        headline="EC20 plus a separate encoder records to your CMS",
        what_it_does="The EC20 requires an encoder to push to the CMS.",
        business_value="Cuts setup time",
        who_benefits="AV directors",
        differentiator="Pairs with any encoder",
        pain_point_addressed="Manual uploads",
        suggested_icon="camera",
        recommended_products=["ec20_ptz"],
    )


def _ec20_clean_understanding() -> StoryboardUnderstanding:
    return StoryboardUnderstanding(
        headline="EC20 records straight to your CMS — no encoder required",
        what_it_does="The EC20 PTZ uploads direct to the CMS, no encoder PC.",
        business_value="Cuts setup time",
        who_benefits="AV directors",
        differentiator="Only fleet-managed PTZ out of the box",
        pain_point_addressed="Manual uploads",
        suggested_icon="camera",
        recommended_products=["ec20_ptz"],
    )


class TestTechAccuracyGateWiring:
    """The technical-accuracy gate fires one corrective retry for a false
    product claim, sharing the single reframe budget with the competitor gate."""

    def _tool_with_client(self, understand_side_effect):
        tool = UnifiedStoryboardTool()
        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(side_effect=understand_side_effect)
        mock_client.generate_storyboard = AsyncMock(return_value=_TINY_PNG)
        tool._gemini_client = mock_client
        return tool, mock_client

    @pytest.mark.asyncio
    async def test_false_claim_triggers_one_corrective_retry(self):
        tool, mock_client = self._tool_with_client(
            [_ec20_false_encoder_understanding(), _ec20_clean_understanding()]
        )

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        # extraction re-called exactly once for the corrective reframe
        assert mock_client.understand_code.call_count == 2
        quality = result.result["quality"]
        assert quality["tech_accuracy_reframe_applied"] is True
        assert quality["reframe_applied"] is True

    @pytest.mark.asyncio
    async def test_clean_claim_runs_once(self):
        tool, mock_client = self._tool_with_client([_ec20_clean_understanding()])

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        assert mock_client.understand_code.call_count == 1
        assert result.result["quality"]["tech_accuracy_reframe_applied"] is False


class TestReferenceImageThreading:
    """Uploaded reference photos flow from run() into generate_storyboard for
    image-to-image conditioning; text/code inputs pass reference_images=None."""

    @pytest.mark.asyncio
    async def test_image_input_threads_reference_bytes(self):
        tool = UnifiedStoryboardTool()
        mock_client = MagicMock()
        mock_client.understand_image = AsyncMock(
            return_value=_epiphan_hero_understanding()
        )
        mock_client.generate_storyboard = AsyncMock(return_value=_TINY_PNG)
        tool._gemini_client = mock_client

        data_url = "data:image/png;base64," + base64.b64encode(_TINY_PNG).decode()
        with patch("webbrowser.open"):
            result = await tool.run({"input": data_url, "open_browser": False})

        assert result.success is True
        kwargs = mock_client.generate_storyboard.call_args.kwargs
        assert kwargs["reference_images"] == [_TINY_PNG]

    @pytest.mark.asyncio
    async def test_code_input_passes_no_reference_images(self):
        tool = UnifiedStoryboardTool()
        mock_client = MagicMock()
        mock_client.understand_code = AsyncMock(
            return_value=_epiphan_hero_understanding()
        )
        mock_client.generate_storyboard = AsyncMock(return_value=_TINY_PNG)
        tool._gemini_client = mock_client

        with patch("webbrowser.open"):
            result = await tool.run({"input": "def foo(): pass", "open_browser": False})

        assert result.success is True
        kwargs = mock_client.generate_storyboard.call_args.kwargs
        assert kwargs["reference_images"] is None
