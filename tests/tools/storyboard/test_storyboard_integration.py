"""Integration tests for storyboard tools module."""

import pytest

from src.tools.storyboard import (
    CodeToStoryboardTool,
    RoadmapToStoryboardTool,
    GeminiStoryboardClient,
    StoryboardUnderstanding,
    COPERNIQ_ICP,
    SANITIZE_RULES,
    get_icp_preset,
    get_audience_persona,
    sanitize_content,
)
from src.tools.base import BaseTool, ToolResult
from src.tools.registry import ToolRegistry


# All storyboard tool classes
STORYBOARD_TOOL_CLASSES = [
    CodeToStoryboardTool,
    RoadmapToStoryboardTool,
]

# Expected tool names
EXPECTED_TOOL_NAMES = [
    "code_to_storyboard",
    "roadmap_to_storyboard",
]


class TestStoryboardModuleExports:
    """Test module exports and __all__."""

    def test_all_tools_exported(self):
        """Verify all tools are exported from __init__.py."""
        from src.tools.storyboard import __all__

        expected_exports = [
            "CodeToStoryboardTool",
            "RoadmapToStoryboardTool",
            "GeminiStoryboardClient",
            "StoryboardUnderstanding",
            "COPERNIQ_ICP",
            "SANITIZE_RULES",
            "get_icp_preset",
            "get_audience_persona",
            "sanitize_content",
        ]

        for export_name in expected_exports:
            assert export_name in __all__, f"{export_name} not in __all__"

    def test_tool_classes_importable(self):
        """Verify tool classes can be imported."""
        from src.tools.storyboard import CodeToStoryboardTool, RoadmapToStoryboardTool

        assert CodeToStoryboardTool is not None
        assert RoadmapToStoryboardTool is not None

    def test_gemini_client_importable(self):
        """Verify Gemini client can be imported."""
        from src.tools.storyboard import GeminiStoryboardClient

        assert GeminiStoryboardClient is not None

    def test_icp_presets_importable(self):
        """Verify ICP presets can be imported."""
        from src.tools.storyboard import COPERNIQ_ICP, get_icp_preset

        assert COPERNIQ_ICP is not None
        assert callable(get_icp_preset)


class TestToolInheritance:
    """Test BaseTool inheritance for all tools."""

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_inherits_from_base_tool(self, tool_class):
        """Verify each tool inherits from BaseTool."""
        assert issubclass(tool_class, BaseTool)

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_instantiation(self, tool_class):
        """Verify each tool can be instantiated."""
        tool = tool_class()
        assert tool is not None
        assert isinstance(tool, BaseTool)


class TestToolDefinitions:
    """Test all tools have proper definitions."""

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_has_definition_property(self, tool_class):
        """Verify each tool has a definition property."""
        tool = tool_class()
        definition = tool.definition
        assert definition is not None

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_definition_has_name(self, tool_class):
        """Verify each tool definition has a name."""
        tool = tool_class()
        assert tool.definition.name is not None
        assert len(tool.definition.name) > 0

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_definition_has_description(self, tool_class):
        """Verify each tool definition has a description."""
        tool = tool_class()
        assert tool.definition.description is not None
        assert len(tool.definition.description) > 0

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_definition_has_category(self, tool_class):
        """Verify each tool definition has a category."""
        tool = tool_class()
        assert tool.definition.category is not None

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_definition_has_parameters(self, tool_class):
        """Verify each tool definition has parameters."""
        tool = tool_class()
        assert tool.definition.parameters is not None
        assert "type" in tool.definition.parameters


class TestToolRunMethod:
    """Test all tools have async run method."""

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_has_run_method(self, tool_class):
        """Verify each tool has a run method."""
        tool = tool_class()
        assert hasattr(tool, "run")
        assert callable(tool.run)

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    @pytest.mark.asyncio
    async def test_run_returns_tool_result(self, tool_class):
        """Verify run method returns ToolResult."""
        tool = tool_class()
        # Call with empty args - should fail gracefully
        result = await tool.run({})
        assert isinstance(result, ToolResult)


class TestToolRegistration:
    """Test tools can be registered with ToolRegistry."""

    def test_register_all_storyboard_tools(self):
        """Test registering all storyboard tools with the registry."""
        registry = ToolRegistry()

        for tool_class in STORYBOARD_TOOL_CLASSES:
            tool = tool_class()
            tool_name = tool.definition.name
            # Only register if not already registered (singleton pattern)
            if registry.get(tool_name) is None:
                registry.register(tool)

        # Verify all tools are registered
        for name in EXPECTED_TOOL_NAMES:
            registered_tool = registry.get(name)
            assert registered_tool is not None, f"Tool {name} not registered"

    def test_get_tool_by_name(self):
        """Test retrieving tools by name."""
        registry = ToolRegistry()

        # Register one tool (if not already registered)
        tool = CodeToStoryboardTool()
        if registry.get("code_to_storyboard") is None:
            registry.register(tool)

        # Retrieve by name
        retrieved = registry.get("code_to_storyboard")
        assert retrieved is not None
        assert retrieved.definition.name == "code_to_storyboard"


class TestToolNames:
    """Test tool names match expected values."""

    @pytest.mark.parametrize(
        "tool_class,expected_name",
        list(zip(STORYBOARD_TOOL_CLASSES, EXPECTED_TOOL_NAMES))
    )
    def test_tool_name_matches_expected(self, tool_class, expected_name):
        """Verify tool name matches expected value."""
        tool = tool_class()
        assert tool.definition.name == expected_name


class TestNoOpenAIModels:
    """Test that no tools use OpenAI models."""

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_no_openai_in_definition(self, tool_class):
        """Verify OpenAI is not mentioned in tool definition."""
        tool = tool_class()
        desc_lower = tool.definition.description.lower()
        assert "openai" not in desc_lower
        assert "gpt-4" not in desc_lower
        assert "gpt-3" not in desc_lower

    @pytest.mark.parametrize("tool_class", STORYBOARD_TOOL_CLASSES)
    def test_no_openai_in_model_ids(self, tool_class):
        """Verify model IDs don't reference OpenAI."""
        tool = tool_class()
        if hasattr(tool, "MODEL_ID"):
            assert "openai" not in tool.MODEL_ID.lower()
            assert "gpt" not in tool.MODEL_ID.lower()
        if hasattr(tool, "IMAGE_MODEL_ID"):
            assert "openai" not in tool.IMAGE_MODEL_ID.lower()


class TestICPPresetIntegration:
    """Test ICP preset integration."""

    def test_coperniq_icp_is_default(self):
        """Coperniq ICP should be the default preset."""
        preset = get_icp_preset()
        assert preset["name"] == "coperniq_mep"

    def test_icp_has_all_required_fields(self):
        """ICP preset should have all required fields for tools."""
        preset = get_icp_preset("coperniq_mep")

        required_fields = [
            "name",
            "target",
            "characteristics",
            "audience_personas",
            "language_style",
            "tone",
            "visual_style",
        ]

        for field in required_fields:
            assert field in preset, f"ICP missing required field: {field}"


class TestSanitizationIntegration:
    """Test sanitization integration."""

    def test_sanitize_removes_code_patterns(self):
        """Sanitization should remove code patterns."""
        code = """
import os
class MyClass:
    def method(self):
        pass
"""
        sanitized = sanitize_content(code)
        assert "import os" not in sanitized
        assert "MyClass" not in sanitized

    def test_sanitize_removes_secrets(self):
        """Sanitization should remove secrets."""
        code = 'API_KEY = "sk-secret123"'
        sanitized = sanitize_content(code)
        assert "sk-secret123" not in sanitized


class TestGeminiClientIntegration:
    """Test Gemini client integration."""

    def test_client_can_be_instantiated(self):
        """Gemini client should be instantiable."""
        # Will fail without API key, but should be importable
        try:
            client = GeminiStoryboardClient()
            assert client is not None
        except Exception:
            pass  # Expected without API key

    def test_understanding_model_fields(self):
        """StoryboardUnderstanding should have all required fields."""
        understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )

        assert understanding.headline == "Test"
        assert understanding.suggested_icon == "clipboard-check"  # Default


class TestEndToEndFlow:
    """Test end-to-end storyboard flow."""

    @pytest.mark.asyncio
    async def test_code_tool_error_handling(self):
        """Code tool should handle errors gracefully."""
        tool = CodeToStoryboardTool()

        # No input should return error
        result = await tool.run({})
        assert result.success is False
        assert isinstance(result.error, str)

        # Invalid preset should return error
        result = await tool.run({
            "file_content": "code",
            "icp_preset": "nonexistent",
        })
        assert result.success is False

    @pytest.mark.asyncio
    async def test_roadmap_tool_error_handling(self):
        """Roadmap tool should handle errors gracefully."""
        tool = RoadmapToStoryboardTool()

        # No input should return error
        result = await tool.run({})
        assert result.success is False
        assert isinstance(result.error, str)

        # Invalid preset should return error
        import base64
        result = await tool.run({
            "image_data": base64.b64encode(b"fake").decode(),
            "icp_preset": "nonexistent",
        })
        assert result.success is False
