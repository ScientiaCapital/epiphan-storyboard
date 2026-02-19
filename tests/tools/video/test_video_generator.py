"""Tests for VideoGeneratorTool and BatchVideoGeneratorTool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.video.video_generator import (
    VideoGeneratorTool,
    BatchVideoGeneratorTool,
    VideoProvider,
    VideoAspectRatio,
    VideoStyle,
)
from src.tools.base import ToolCategory, BaseTool


class TestVideoGeneratorDefinition:
    """Tests for VideoGeneratorTool definition."""

    def test_definition_name(self):
        tool = VideoGeneratorTool()
        assert tool.definition.name == "video_generator"

    def test_definition_category(self):
        tool = VideoGeneratorTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_parameters(self):
        tool = VideoGeneratorTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "prompt" in params["properties"]
        assert "provider" in params["properties"]

    def test_inherits_from_base_tool(self):
        tool = VideoGeneratorTool()
        assert isinstance(tool, BaseTool)


class TestBatchVideoGeneratorDefinition:
    """Tests for BatchVideoGeneratorTool definition."""

    def test_definition_name(self):
        tool = BatchVideoGeneratorTool()
        assert tool.definition.name == "batch_video_generator"

    def test_definition_category(self):
        tool = BatchVideoGeneratorTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_inherits_from_base_tool(self):
        tool = BatchVideoGeneratorTool()
        assert isinstance(tool, BaseTool)


class TestVideoProviderEnums:
    """Tests for video provider enums."""

    def test_kling_provider(self):
        assert VideoProvider.KLING.value == "kling"

    def test_hailuo_provider(self):
        assert VideoProvider.HAILUO.value == "hailuo"

    def test_runway_provider(self):
        assert VideoProvider.RUNWAY.value == "runway"

    def test_pika_provider(self):
        assert VideoProvider.PIKA.value == "pika"

    def test_luma_provider(self):
        assert VideoProvider.LUMA.value == "luma"


class TestVideoAspectRatioEnums:
    """Tests for aspect ratio enums."""

    def test_landscape_16_9(self):
        assert VideoAspectRatio.LANDSCAPE_16_9.value == "16:9"

    def test_portrait_9_16(self):
        assert VideoAspectRatio.PORTRAIT_9_16.value == "9:16"

    def test_square_1_1(self):
        assert VideoAspectRatio.SQUARE_1_1.value == "1:1"


class TestVideoStyleEnums:
    """Tests for video style enums."""

    def test_realistic_style(self):
        assert VideoStyle.REALISTIC.value == "realistic"

    def test_professional_style(self):
        assert VideoStyle.PROFESSIONAL.value == "professional"


class TestSSRFValidation:
    """Tests for SSRF protection."""

    @pytest.mark.asyncio
    async def test_ssrf_blocks_localhost(self):
        """Test that localhost URLs are blocked."""
        tool = VideoGeneratorTool()

        with patch.dict("os.environ", {"KLING_API_KEY": "test-key"}):
            result = await tool.run({
                "prompt": "Test video",
                "provider": "kling",
                "reference_image_url": "http://localhost:8080/image.png",
            })

        assert result.success is False
        assert "SSRF" in result.error or "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_ssrf_blocks_internal_ip(self):
        """Test that internal IPs are blocked."""
        tool = VideoGeneratorTool()

        with patch.dict("os.environ", {"KLING_API_KEY": "test-key"}):
            result = await tool.run({
                "prompt": "Test video",
                "provider": "kling",
                "reference_image_url": "http://192.168.1.1/image.png",
            })

        assert result.success is False
        assert "SSRF" in result.error or "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_ssrf_blocks_metadata_endpoint(self):
        """Test that cloud metadata endpoints are blocked."""
        tool = VideoGeneratorTool()

        with patch.dict("os.environ", {"KLING_API_KEY": "test-key"}):
            result = await tool.run({
                "prompt": "Test video",
                "provider": "kling",
                "reference_image_url": "http://169.254.169.254/latest/meta-data/",
            })

        assert result.success is False
        assert "SSRF" in result.error or "blocked" in result.error.lower()


class TestVideoGeneratorRun:
    """Tests for VideoGeneratorTool execution."""

    @pytest.mark.asyncio
    async def test_missing_prompt(self):
        """Test error when prompt is missing."""
        tool = VideoGeneratorTool()
        result = await tool.run({
            "provider": "kling",
        })
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test error when API key is missing."""
        tool = VideoGeneratorTool()

        with patch.dict("os.environ", {}, clear=True):
            result = await tool.run({
                "prompt": "Test video",
                "provider": "kling",
            })

        assert result.success is False
        assert "API key" in result.error or "key" in result.error.lower()

    @pytest.mark.asyncio
    async def test_default_provider_is_kling(self):
        """Test that default provider is Kling (cost-optimized)."""
        tool = VideoGeneratorTool()
        best_provider = tool._select_best_provider()
        # Without any API keys, defaults to KLING
        assert best_provider == VideoProvider.KLING


class TestBatchVideoGeneratorRun:
    """Tests for BatchVideoGeneratorTool execution."""

    @pytest.mark.asyncio
    async def test_no_scenes_error(self):
        """Test error when no scenes provided."""
        tool = BatchVideoGeneratorTool()
        result = await tool.run({
            "scenes": [],
        })
        assert result.success is False
        assert "scene" in result.error.lower()

    @pytest.mark.asyncio
    async def test_batch_returns_array_results(self):
        """Test batch returns results for each scene."""
        tool = BatchVideoGeneratorTool()

        # Mock the VideoGeneratorTool to fail (no API key)
        with patch.dict("os.environ", {}, clear=True):
            result = await tool.run({
                "scenes": [
                    {"prompt": "Scene 1", "name": "intro"},
                    {"prompt": "Scene 2", "name": "outro"},
                ],
                "provider": "kling",
            })

        # Should have attempted both scenes
        assert "scenes" in result.result
        assert len(result.result["scenes"]) == 2
