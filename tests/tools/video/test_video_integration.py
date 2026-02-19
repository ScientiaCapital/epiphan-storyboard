"""Integration tests for video tools module."""

import pytest

from src.tools.video import (
    VideoScriptGeneratorTool,
    VideoGeneratorTool,
    BatchVideoGeneratorTool,
    LoomViewTrackerTool,
    ViewerEnrichmentTool,
    VideoSchedulerTool,
    VideoTemplateManagerTool,
)
from src.tools.base import BaseTool, ToolResult
from src.tools.registry import ToolRegistry


# All video tool classes
VIDEO_TOOL_CLASSES = [
    VideoScriptGeneratorTool,
    VideoGeneratorTool,
    BatchVideoGeneratorTool,
    LoomViewTrackerTool,
    ViewerEnrichmentTool,
    VideoSchedulerTool,
    VideoTemplateManagerTool,
]

# Expected tool names
EXPECTED_TOOL_NAMES = [
    "video_script_generator",
    "video_generator",
    "batch_video_generator",
    "loom_view_tracker",
    "viewer_enrichment",
    "video_scheduler",
    "video_template_manager",
]


class TestVideoModuleExports:
    """Test module exports and __all__."""

    def test_all_tools_exported(self):
        """Verify all 7 tools are exported from __init__.py."""
        from src.tools.video import __all__

        expected_exports = [
            "VideoScriptGeneratorTool",
            "VideoGeneratorTool",
            "BatchVideoGeneratorTool",
            "LoomViewTrackerTool",
            "ViewerEnrichmentTool",
            "VideoSchedulerTool",
            "VideoTemplateManagerTool",
        ]

        for tool_name in expected_exports:
            assert tool_name in __all__, f"{tool_name} not in __all__"

    def test_export_count(self):
        """Verify exactly 7 tools are exported."""
        from src.tools.video import __all__
        assert len(__all__) == 7


class TestToolInheritance:
    """Test BaseTool inheritance for all tools."""

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_inherits_from_base_tool(self, tool_class):
        """Verify each tool inherits from BaseTool."""
        assert issubclass(tool_class, BaseTool)

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_instantiation(self, tool_class):
        """Verify each tool can be instantiated."""
        tool = tool_class()
        assert tool is not None
        assert isinstance(tool, BaseTool)


class TestToolDefinitions:
    """Test all tools have proper definitions."""

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_has_definition_property(self, tool_class):
        """Verify each tool has a definition property."""
        tool = tool_class()
        definition = tool.definition
        assert definition is not None

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_definition_has_name(self, tool_class):
        """Verify each tool definition has a name."""
        tool = tool_class()
        assert tool.definition.name is not None
        assert len(tool.definition.name) > 0

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_definition_has_description(self, tool_class):
        """Verify each tool definition has a description."""
        tool = tool_class()
        assert tool.definition.description is not None
        assert len(tool.definition.description) > 0

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_definition_has_category(self, tool_class):
        """Verify each tool definition has a category."""
        tool = tool_class()
        assert tool.definition.category is not None

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_definition_has_parameters(self, tool_class):
        """Verify each tool definition has parameters."""
        tool = tool_class()
        assert tool.definition.parameters is not None
        assert "type" in tool.definition.parameters


class TestToolRunMethod:
    """Test all tools have async run method."""

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_has_run_method(self, tool_class):
        """Verify each tool has a run method."""
        tool = tool_class()
        assert hasattr(tool, "run")
        assert callable(tool.run)

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    @pytest.mark.asyncio
    async def test_run_returns_tool_result(self, tool_class):
        """Verify run method returns ToolResult."""
        tool = tool_class()
        # Call with empty args - should fail gracefully
        result = await tool.run({})
        assert isinstance(result, ToolResult)


class TestToolRegistration:
    """Test tools can be registered with ToolRegistry."""

    def test_register_all_video_tools(self):
        """Test registering all video tools with the registry.

        Note: ToolRegistry is a singleton, so we verify tools were registered
        by checking they can be retrieved. If tests run in any order,
        tools may already be registered.
        """
        registry = ToolRegistry()

        for tool_class in VIDEO_TOOL_CLASSES:
            tool = tool_class()
            tool_name = tool.definition.name
            # Only register if not already registered (singleton pattern)
            if registry.get(tool_name) is None:
                registry.register(tool)

        # Verify all tools are registered
        for name in EXPECTED_TOOL_NAMES:
            registered_tool = registry.get(name)
            assert registered_tool is not None, f"Tool {name} not registered"

    def test_registry_tool_count(self):
        """Test correct number of tools registered."""
        registry = ToolRegistry()

        for tool_class in VIDEO_TOOL_CLASSES:
            tool = tool_class()
            tool_name = tool.definition.name
            # Only register if not already registered (singleton pattern)
            if registry.get(tool_name) is None:
                registry.register(tool)

        # Should have at least 7 tools
        tools = registry.list_tools()
        assert len(tools) >= 7

    def test_get_tool_by_name(self):
        """Test retrieving tools by name."""
        registry = ToolRegistry()

        # Register one tool (if not already registered)
        tool = VideoScriptGeneratorTool()
        if registry.get("video_script_generator") is None:
            registry.register(tool)

        # Retrieve by name
        retrieved = registry.get("video_script_generator")
        assert retrieved is not None
        assert retrieved.definition.name == "video_script_generator"


class TestToolNames:
    """Test tool names match expected values."""

    @pytest.mark.parametrize(
        "tool_class,expected_name",
        list(zip(VIDEO_TOOL_CLASSES, EXPECTED_TOOL_NAMES))
    )
    def test_tool_name_matches_expected(self, tool_class, expected_name):
        """Verify tool name matches expected value."""
        tool = tool_class()
        assert tool.definition.name == expected_name


class TestNoOpenAIModels:
    """Test that no tools use OpenAI models."""

    @pytest.mark.parametrize("tool_class", VIDEO_TOOL_CLASSES)
    def test_no_openai_in_definition(self, tool_class):
        """Verify OpenAI is not mentioned in tool definition."""
        tool = tool_class()
        desc_lower = tool.definition.description.lower()
        assert "openai" not in desc_lower
        assert "gpt-4" not in desc_lower
        assert "gpt-3" not in desc_lower
