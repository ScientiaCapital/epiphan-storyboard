"""Tests for RoadmapToStoryboardTool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import base64
import tempfile
import os

from src.tools.storyboard.roadmap_to_storyboard import RoadmapToStoryboardTool
from src.tools.storyboard.gemini_client import StoryboardUnderstanding
from src.tools.base import BaseTool, ToolCategory, ToolResult


class TestRoadmapToStoryboardDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        """Tool should have correct name."""
        tool = RoadmapToStoryboardTool()
        assert tool.definition.name == "roadmap_to_storyboard"

    def test_definition_category(self):
        """Tool should be in DATA category."""
        tool = RoadmapToStoryboardTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_description(self):
        """Tool should have meaningful description."""
        tool = RoadmapToStoryboardTool()
        desc = tool.definition.description
        assert "roadmap" in desc.lower()
        assert len(desc) > 50

    def test_definition_has_parameters(self):
        """Tool should have parameters schema."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "properties" in params
        assert "image_data" in params["properties"]
        assert "image_path" in params["properties"]

    def test_inherits_from_base_tool(self):
        """Tool should inherit from BaseTool."""
        tool = RoadmapToStoryboardTool()
        assert isinstance(tool, BaseTool)

    def test_does_not_require_approval(self):
        """Tool should not require approval."""
        tool = RoadmapToStoryboardTool()
        assert tool.definition.requires_approval is False


class TestRoadmapToStoryboardParameters:
    """Tests for parameter handling."""

    def test_accepts_image_data_parameter(self):
        """Tool should accept image_data parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "image_data" in params
        assert params["image_data"]["type"] == "string"

    def test_accepts_image_path_parameter(self):
        """Tool should accept image_path parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "image_path" in params
        assert params["image_path"]["type"] == "string"

    def test_accepts_audience_parameter(self):
        """Tool should accept audience parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "audience" in params
        assert "business_owner" in params["audience"]["enum"]
        assert "c_suite" in params["audience"]["enum"]
        assert "btl_champion" in params["audience"]["enum"]

    def test_accepts_icp_preset_parameter(self):
        """Tool should accept icp_preset parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "icp_preset" in params

    def test_accepts_sanitize_ip_parameter(self):
        """Tool should accept sanitize_ip parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "sanitize_ip" in params
        assert params["sanitize_ip"]["type"] == "boolean"

    def test_accepts_custom_headline_parameter(self):
        """Tool should accept custom_headline parameter."""
        tool = RoadmapToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "custom_headline" in params


class TestRoadmapToStoryboardRun:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_missing_input_returns_error(self):
        """Should return error when no input provided."""
        tool = RoadmapToStoryboardTool()
        result = await tool.run({})

        assert result.success is False
        assert "image_data" in result.error.lower() or "image_path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self):
        """Should return error when image file not found."""
        tool = RoadmapToStoryboardTool()
        result = await tool.run({
            "image_path": "/nonexistent/path/to/image.png"
        })

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_icp_preset_returns_error(self):
        """Should return error for invalid ICP preset."""
        tool = RoadmapToStoryboardTool()
        result = await tool.run({
            "image_data": base64.b64encode(b"fake image").decode(),
            "icp_preset": "invalid_preset_name",
        })

        assert result.success is False
        assert "Unknown ICP preset" in result.error

    @pytest.mark.asyncio
    async def test_reads_image_from_path(self):
        """Should read image from path."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            f.write(b"fake PNG image data")
            temp_path = f.name

        try:
            tool = RoadmapToStoryboardTool()

            # Mock the Gemini client
            mock_client = MagicMock()
            mock_understanding = StoryboardUnderstanding(
                headline="Test",
                what_it_does="Test",
                business_value="Test",
                who_benefits="Test",
                differentiator="Test",
                pain_point_addressed="Test",
            )
            mock_client.understand_image = AsyncMock(return_value=mock_understanding)
            mock_client.generate_storyboard = AsyncMock(return_value=b"PNG bytes")
            tool._gemini_client = mock_client

            result = await tool.run({"image_path": temp_path})

            # Should have called understand_image
            assert mock_client.understand_image.called

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_successful_execution_returns_png(self):
        """Should return base64 PNG on success."""
        tool = RoadmapToStoryboardTool()

        # Mock the Gemini client
        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Exciting Updates Coming",
            what_it_does="Amazing new features",
            business_value="Transform your workflow",
            who_benefits="Everyone",
            differentiator="Built for you",
            pain_point_addressed="Current limitations",
        )
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG image bytes")
        tool._gemini_client = mock_client

        result = await tool.run({
            "image_data": base64.b64encode(b"fake image").decode(),
            "audience": "c_suite",
        })

        assert result.success is True
        assert "storyboard_png" in result.result
        assert "understanding" in result.result
        assert result.result["stage"] == "preview"  # Always preview for roadmaps
        assert result.result["is_teaser"] is True

    @pytest.mark.asyncio
    async def test_always_uses_preview_stage(self):
        """Roadmap tool should always use preview stage."""
        tool = RoadmapToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG")
        tool._gemini_client = mock_client

        result = await tool.run({
            "image_data": base64.b64encode(b"fake").decode(),
        })

        # Verify generate_storyboard was called with preview stage
        call_args = mock_client.generate_storyboard.call_args
        stage_arg = call_args.kwargs.get("stage", call_args[0][1] if len(call_args[0]) > 1 else "preview")
        assert stage_arg == "preview"

    @pytest.mark.asyncio
    async def test_ip_sanitization_enabled_by_default(self):
        """IP sanitization should be enabled by default."""
        tool = RoadmapToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG")
        tool._gemini_client = mock_client

        result = await tool.run({
            "image_data": base64.b64encode(b"fake").decode(),
        })

        # Verify understand_image was called with sanitize_ip=True
        call_args = mock_client.understand_image.call_args
        sanitize_arg = call_args.kwargs.get("sanitize_ip", True)
        assert sanitize_arg is True
        assert result.result["ip_sanitized"] is True

    @pytest.mark.asyncio
    async def test_custom_headline_override(self):
        """Should use custom headline when provided."""
        tool = RoadmapToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Original Headline",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG")
        tool._gemini_client = mock_client

        result = await tool.run({
            "image_data": base64.b64encode(b"fake").decode(),
            "custom_headline": "My Custom Teaser",
        })

        # The generate_storyboard should receive the custom headline
        call_args = mock_client.generate_storyboard.call_args
        understanding_arg = call_args.kwargs.get("understanding", call_args[0][0] if call_args[0] else None)
        assert understanding_arg.headline == "My Custom Teaser"


class TestRoadmapToStoryboardModelConfig:
    """Tests for model configuration."""

    def test_uses_gemini_flash_model(self):
        """Should use Gemini Flash for understanding."""
        tool = RoadmapToStoryboardTool()
        assert "gemini" in tool.MODEL_ID.lower()

    def test_uses_image_generation_model(self):
        """Should use Gemini image generation model."""
        tool = RoadmapToStoryboardTool()
        assert "image" in tool.IMAGE_MODEL_ID.lower()

    def test_no_openai_in_models(self):
        """Should not use OpenAI models."""
        tool = RoadmapToStoryboardTool()
        assert "openai" not in tool.MODEL_ID.lower()
        assert "gpt" not in tool.MODEL_ID.lower()
        assert "openai" not in tool.IMAGE_MODEL_ID.lower()

    def test_default_timeout(self):
        """Should have reasonable default timeout."""
        tool = RoadmapToStoryboardTool()
        assert tool.DEFAULT_TIMEOUT >= 60
        assert tool.DEFAULT_TIMEOUT <= 180


class TestRoadmapToStoryboardLLMSchema:
    """Tests for LLM schema generation."""

    def test_get_llm_schema_format(self):
        """Should return valid LLM schema."""
        tool = RoadmapToStoryboardTool()
        schema = tool.get_llm_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "roadmap_to_storyboard"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_schema_description_is_useful(self):
        """Schema description should be useful for LLM."""
        tool = RoadmapToStoryboardTool()
        schema = tool.get_llm_schema()
        desc = schema["function"]["description"]

        # Should mention key capabilities
        assert "roadmap" in desc.lower() or "miro" in desc.lower()


class TestRoadmapToStoryboardIntegration:
    """Integration tests for the tool."""

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Should return properly structured result."""
        tool = RoadmapToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Test Headline",
            what_it_does="Test description",
            business_value="Test value",
            who_benefits="Test audience",
            differentiator="Test diff",
            pain_point_addressed="Test pain",
            suggested_icon="test-icon",
        )
        mock_client.understand_image = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"test-png")
        tool._gemini_client = mock_client

        result = await tool.run({
            "image_data": base64.b64encode(b"fake").decode(),
        })

        assert isinstance(result, ToolResult)
        assert result.tool_name == "roadmap_to_storyboard"
        assert result.execution_time_ms >= 0

        # Check result structure
        data = result.result
        assert "storyboard_png" in data
        assert "understanding" in data
        assert "stage" in data
        assert data["stage"] == "preview"  # Always preview
        assert "audience" in data
        assert "icp_preset" in data
        assert "is_teaser" in data
        assert data["is_teaser"] is True
        assert "ip_sanitized" in data

        # Check understanding structure
        understanding = data["understanding"]
        assert "headline" in understanding
        assert "what_it_does" in understanding
        assert "business_value" in understanding
        assert "who_benefits" in understanding
        assert "differentiator" in understanding
        assert "pain_point_addressed" in understanding
        assert "suggested_icon" in understanding


class TestRoadmapVsCodeTool:
    """Tests comparing roadmap tool to code tool."""

    def test_roadmap_is_always_teaser(self):
        """Roadmap results should always be teasers."""
        from src.tools.storyboard.code_to_storyboard import CodeToStoryboardTool

        code_tool = CodeToStoryboardTool()
        roadmap_tool = RoadmapToStoryboardTool()

        # Code tool supports multiple stages
        code_params = code_tool.definition.parameters["properties"]
        assert "stage" in code_params
        assert "demo" in code_params["stage"]["enum"]
        assert "shipped" in code_params["stage"]["enum"]

        # Roadmap tool doesn't expose stage parameter (always preview)
        roadmap_params = roadmap_tool.definition.parameters["properties"]
        assert "stage" not in roadmap_params

    def test_roadmap_has_sanitize_ip_param(self):
        """Roadmap tool should have explicit sanitize_ip parameter."""
        from src.tools.storyboard.code_to_storyboard import CodeToStoryboardTool

        code_tool = CodeToStoryboardTool()
        roadmap_tool = RoadmapToStoryboardTool()

        # Roadmap has explicit sanitize_ip
        roadmap_params = roadmap_tool.definition.parameters["properties"]
        assert "sanitize_ip" in roadmap_params

        # Code tool does sanitization implicitly
        code_params = code_tool.definition.parameters["properties"]
        assert "sanitize_ip" not in code_params  # Implicit sanitization
