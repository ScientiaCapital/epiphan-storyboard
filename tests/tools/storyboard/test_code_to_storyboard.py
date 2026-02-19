"""Tests for CodeToStoryboardTool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import base64
import tempfile
import os

from src.tools.storyboard.code_to_storyboard import CodeToStoryboardTool
from src.tools.storyboard.gemini_client import StoryboardUnderstanding
from src.tools.base import BaseTool, ToolCategory, ToolResult


class TestCodeToStoryboardDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        """Tool should have correct name."""
        tool = CodeToStoryboardTool()
        assert tool.definition.name == "code_to_storyboard"

    def test_definition_category(self):
        """Tool should be in DATA category."""
        tool = CodeToStoryboardTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_description(self):
        """Tool should have meaningful description."""
        tool = CodeToStoryboardTool()
        desc = tool.definition.description
        assert "code" in desc.lower()
        assert "storyboard" in desc.lower()
        assert len(desc) > 50

    def test_definition_has_parameters(self):
        """Tool should have parameters schema."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "properties" in params
        assert "file_content" in params["properties"]
        assert "file_path" in params["properties"]

    def test_inherits_from_base_tool(self):
        """Tool should inherit from BaseTool."""
        tool = CodeToStoryboardTool()
        assert isinstance(tool, BaseTool)

    def test_does_not_require_approval(self):
        """Tool should not require approval."""
        tool = CodeToStoryboardTool()
        assert tool.definition.requires_approval is False


class TestCodeToStoryboardParameters:
    """Tests for parameter handling."""

    def test_accepts_file_content_parameter(self):
        """Tool should accept file_content parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "file_content" in params
        assert params["file_content"]["type"] == "string"

    def test_accepts_file_path_parameter(self):
        """Tool should accept file_path parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "file_path" in params
        assert params["file_path"]["type"] == "string"

    def test_accepts_stage_parameter(self):
        """Tool should accept stage parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "stage" in params
        assert params["stage"]["enum"] == ["preview", "demo", "shipped"]

    def test_accepts_audience_parameter(self):
        """Tool should accept audience parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "audience" in params
        assert "business_owner" in params["audience"]["enum"]
        assert "c_suite" in params["audience"]["enum"]
        assert "btl_champion" in params["audience"]["enum"]

    def test_accepts_icp_preset_parameter(self):
        """Tool should accept icp_preset parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "icp_preset" in params

    def test_accepts_custom_headline_parameter(self):
        """Tool should accept custom_headline parameter."""
        tool = CodeToStoryboardTool()
        params = tool.definition.parameters["properties"]
        assert "custom_headline" in params


class TestCodeToStoryboardRun:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_missing_input_returns_error(self):
        """Should return error when no input provided."""
        tool = CodeToStoryboardTool()
        result = await tool.run({})

        assert result.success is False
        assert "file_content" in result.error.lower() or "file_path" in result.error.lower()

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self):
        """Should return error when file not found."""
        tool = CodeToStoryboardTool()
        result = await tool.run({
            "file_path": "/nonexistent/path/to/file.py"
        })

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_icp_preset_returns_error(self):
        """Should return error for invalid ICP preset."""
        tool = CodeToStoryboardTool()
        result = await tool.run({
            "file_content": "def test(): pass",
            "icp_preset": "invalid_preset_name",
        })

        assert result.success is False
        assert "Unknown ICP preset" in result.error

    @pytest.mark.asyncio
    async def test_reads_file_from_path(self):
        """Should read file content from path."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def calculate_savings(): return 5")
            temp_path = f.name

        try:
            tool = CodeToStoryboardTool()

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
            mock_client.understand_code = AsyncMock(return_value=mock_understanding)
            mock_client.generate_storyboard = AsyncMock(return_value=b"PNG bytes")
            tool._gemini_client = mock_client

            result = await tool.run({"file_path": temp_path})

            # Should have called understand_code
            assert mock_client.understand_code.called
            # Result should be successful
            assert result.success is True

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_successful_execution_returns_png(self):
        """Should return base64 PNG on success."""
        tool = CodeToStoryboardTool()

        # Mock the Gemini client
        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Track Your Jobs",
            what_it_does="See everything in one place",
            business_value="Save 5 hours/week",
            who_benefits="Project managers",
            differentiator="Works anywhere",
            pain_point_addressed="Spreadsheet chaos",
        )
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG image bytes")
        tool._gemini_client = mock_client

        result = await tool.run({
            "file_content": "def track_job(): return True",
            "file_name": "tracker.py",
            "stage": "preview",
            "audience": "c_suite",
        })

        assert result.success is True
        assert "storyboard_png" in result.result
        assert "understanding" in result.result
        assert result.result["stage"] == "preview"
        assert result.result["audience"] == "c_suite"

    @pytest.mark.asyncio
    async def test_custom_headline_override(self):
        """Should use custom headline when provided."""
        tool = CodeToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Original Headline",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG")
        tool._gemini_client = mock_client

        result = await tool.run({
            "file_content": "code",
            "custom_headline": "My Custom Headline",
        })

        # The generate_storyboard should receive the custom headline
        call_args = mock_client.generate_storyboard.call_args
        understanding_arg = call_args.kwargs.get("understanding", call_args[0][0] if call_args[0] else None)
        assert understanding_arg.headline == "My Custom Headline"

    @pytest.mark.asyncio
    async def test_sanitizes_code_content(self):
        """Should sanitize code content before processing."""
        tool = CodeToStoryboardTool()

        mock_client = MagicMock()
        mock_understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"PNG")
        tool._gemini_client = mock_client

        # Code with sensitive patterns
        sensitive_code = '''
import os
from secret_module import API_KEY
class SecretClass:
    SECRET_TOKEN = "sk-abc123"
    def internal_method(self):
        pass
'''
        result = await tool.run({"file_content": sensitive_code})

        # Verify understand_code was called with sanitized content
        call_args = mock_client.understand_code.call_args
        code_content = call_args.kwargs.get("code_content", "")

        # Sensitive items should be sanitized
        assert "import os" not in code_content
        assert "sk-abc123" not in code_content


class TestCodeToStoryboardModelConfig:
    """Tests for model configuration."""

    def test_uses_gemini_flash_model(self):
        """Should use Gemini Flash for understanding."""
        tool = CodeToStoryboardTool()
        assert "gemini" in tool.MODEL_ID.lower()

    def test_uses_image_generation_model(self):
        """Should use Gemini image generation model."""
        tool = CodeToStoryboardTool()
        assert "image" in tool.IMAGE_MODEL_ID.lower()

    def test_no_openai_in_models(self):
        """Should not use OpenAI models."""
        tool = CodeToStoryboardTool()
        assert "openai" not in tool.MODEL_ID.lower()
        assert "gpt" not in tool.MODEL_ID.lower()
        assert "openai" not in tool.IMAGE_MODEL_ID.lower()

    def test_default_timeout(self):
        """Should have reasonable default timeout."""
        tool = CodeToStoryboardTool()
        assert tool.DEFAULT_TIMEOUT >= 60
        assert tool.DEFAULT_TIMEOUT <= 180


class TestCodeToStoryboardLLMSchema:
    """Tests for LLM schema generation."""

    def test_get_llm_schema_format(self):
        """Should return valid LLM schema."""
        tool = CodeToStoryboardTool()
        schema = tool.get_llm_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "code_to_storyboard"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_schema_description_is_useful(self):
        """Schema description should be useful for LLM."""
        tool = CodeToStoryboardTool()
        schema = tool.get_llm_schema()
        desc = schema["function"]["description"]

        # Should mention key capabilities
        assert "code" in desc.lower()
        assert "storyboard" in desc.lower()


class TestCodeToStoryboardIntegration:
    """Integration tests for the tool."""

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Should return properly structured result."""
        tool = CodeToStoryboardTool()

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
        mock_client.understand_code = AsyncMock(return_value=mock_understanding)
        mock_client.generate_storyboard = AsyncMock(return_value=b"test-png")
        tool._gemini_client = mock_client

        result = await tool.run({
            "file_content": "code",
            "file_name": "test.py",
        })

        assert isinstance(result, ToolResult)
        assert result.tool_name == "code_to_storyboard"
        assert result.execution_time_ms >= 0

        # Check result structure
        data = result.result
        assert "storyboard_png" in data
        assert "understanding" in data
        assert "stage" in data
        assert "audience" in data
        assert "icp_preset" in data
        assert "file_name" in data

        # Check understanding structure
        understanding = data["understanding"]
        assert "headline" in understanding
        assert "what_it_does" in understanding
        assert "business_value" in understanding
        assert "who_benefits" in understanding
        assert "differentiator" in understanding
        assert "pain_point_addressed" in understanding
        assert "suggested_icon" in understanding
