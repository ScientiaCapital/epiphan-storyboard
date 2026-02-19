"""
Tests for RunwayVideoGeneratorTool.

Following TDD: Write tests FIRST, watch them fail, then implement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestRunwayVideoGeneratorToolDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        """Tool should have correct name."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        assert tool.definition.name == "runway_video_generator"

    def test_definition_category(self):
        """Tool should have WEB category."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool
        from src.tools.base import ToolCategory

        tool = RunwayVideoGeneratorTool()
        assert tool.definition.category == ToolCategory.WEB

    def test_definition_has_required_parameters(self):
        """Definition should require prompt."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        params = tool.definition.parameters
        assert "required" in params
        assert "prompt" in params["required"]

    def test_definition_has_description(self):
        """Tool should have non-empty description."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        assert tool.definition.description
        assert "video" in tool.definition.description.lower()

    def test_definition_does_not_require_approval(self):
        """Tool should not require approval."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        assert tool.definition.requires_approval is False


class TestRunwayVideoGeneratorToolValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_run_requires_prompt(self):
        """run() should fail if prompt missing."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        result = await tool.run({})

        assert result.success is False
        assert "prompt" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_rejects_empty_prompt(self):
        """run() should fail if prompt is empty."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        result = await tool.run({"prompt": ""})

        assert result.success is False
        assert "prompt" in result.error.lower()


class TestRunwayVideoGeneratorToolTextToVideo:
    """Tests for text-to-video generation."""

    @pytest.mark.asyncio
    async def test_text_to_video_success(self):
        """run() should generate video from text prompt."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A futuristic city at sunset",
            })

        assert result.success is True
        assert "video_path" in result.result or "task_id" in result.result

    @pytest.mark.asyncio
    async def test_text_to_video_with_duration(self):
        """run() should accept custom duration."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        called_with = {}

        async def capture_call(*args, **kwargs):
            called_with.update(kwargs)
            return {"id": "task_123", "status": "PENDING"}

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(side_effect=capture_call)
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "duration": 10,
            })

        mock_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_to_video_with_model(self):
        """run() should accept custom model."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "model": "gen3a",
            })

        mock_client.generate_from_text.assert_called_once()


class TestRunwayVideoGeneratorToolImageToVideo:
    """Tests for image-to-video generation."""

    @pytest.mark.asyncio
    async def test_image_to_video_success(self):
        """run() should generate video from image."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_image = AsyncMock(return_value={
            "id": "task_456",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_456",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "Camera slowly zooms in",
                "image": "base64encodeddata",
            })

        assert result.success is True
        mock_client.generate_from_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_image_to_video_requires_prompt(self):
        """run() with image should still require prompt."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        result = await tool.run({
            "image": "base64data",
        })

        assert result.success is False
        assert "prompt" in result.error.lower()


class TestRunwayVideoGeneratorToolStatusPolling:
    """Tests for generation status polling."""

    @pytest.mark.asyncio
    async def test_polls_until_complete(self):
        """run() should poll until generation completes."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "wait_for_completion": True,
            })

        mock_client.wait_for_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_can_skip_polling(self):
        """run() should allow skipping polling."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "wait_for_completion": False,
            })

        assert result.success is True
        assert result.result.get("task_id") == "task_123"
        assert result.result.get("status") == "PENDING"


class TestRunwayVideoGeneratorToolErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_api_key_missing(self):
        """run() should handle missing API key gracefully."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(
            side_effect=ValueError("Runway API key not configured")
        )

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({"prompt": "A sunset"})

        assert result.success is False
        assert "API key" in result.error or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_generation_failure(self):
        """run() should handle generation failure gracefully."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(
            side_effect=RuntimeError("Generation failed: Content policy violation")
        )

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "wait_for_completion": True,
            })

        assert result.success is False
        assert "failed" in result.error.lower() or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_timeout(self):
        """run() should handle timeout gracefully."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(
            side_effect=TimeoutError("Task did not complete within 300s")
        )

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "wait_for_completion": True,
            })

        assert result.success is False
        assert "timeout" in result.error.lower() or "complete" in result.error.lower()


class TestRunwayVideoGeneratorToolDownload:
    """Tests for video download."""

    @pytest.mark.asyncio
    async def test_downloads_video_on_success(self):
        """run() should download video when generation succeeds."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/tmp/generated_video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "wait_for_completion": True,
            })

        assert result.success is True
        assert result.result.get("video_path") == "/tmp/generated_video.mp4"
        mock_client.download_video.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_output_path(self):
        """run() should use custom output path if provided."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()

        mock_client = MagicMock()
        mock_client.generate_from_text = AsyncMock(return_value={
            "id": "task_123",
            "status": "PENDING",
        })
        mock_client.wait_for_completion = AsyncMock(return_value={
            "id": "task_123",
            "status": "SUCCEEDED",
            "output": ["https://cdn.runway.com/video.mp4"],
        })
        mock_client.download_video = AsyncMock(return_value="/custom/path/video.mp4")

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "prompt": "A sunset",
                "output_path": "/custom/path/video.mp4",
                "wait_for_completion": True,
            })

        # download_video should be called with the custom path
        mock_client.download_video.assert_called_once()


class TestRunwayVideoGeneratorToolLLMSchema:
    """Tests for LLM schema generation."""

    def test_get_llm_schema_format(self):
        """get_llm_schema() should return valid schema."""
        from src.tools.recording.video_generator import RunwayVideoGeneratorTool

        tool = RunwayVideoGeneratorTool()
        schema = tool.get_llm_schema()

        assert "type" in schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert schema["function"]["name"] == "runway_video_generator"
