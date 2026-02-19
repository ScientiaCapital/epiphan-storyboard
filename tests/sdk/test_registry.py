"""Tests for SDK plugin registry and loader."""

import pytest
import tempfile
from pathlib import Path

from src.sdk.registry import PluginRegistry, PluginLoader
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.sdk.testing import MockRegistry


class DummyTool(BaseTool):
    """Dummy tool for testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dummy_tool",
            description="A dummy tool for testing",
            category=ToolCategory.SYSTEM,
            parameters={"type": "object", "properties": {}},
        )

    async def run(self, arguments: dict) -> ToolResult:
        return ToolResult(
            tool_name="dummy_tool",
            success=True,
            result="dummy result",
            execution_time_ms=1,
        )


class AnotherTool(BaseTool):
    """Another dummy tool for testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="another_tool",
            description="Another dummy tool",
            category=ToolCategory.DATA,
            parameters={"type": "object", "properties": {}},
        )

    async def run(self, arguments: dict) -> ToolResult:
        return ToolResult(
            tool_name="another_tool",
            success=True,
            result="another result",
            execution_time_ms=1,
        )


class TestPluginRegistry:
    """Tests for PluginRegistry."""

    def test_init_empty(self):
        """PluginRegistry starts empty."""
        registry = PluginRegistry()
        assert len(registry.tools) == 0

    def test_register_tool(self):
        """Can register a tool."""
        registry = PluginRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert len(registry.tools) == 1
        assert registry.tools[0].definition.name == "dummy_tool"

    def test_register_multiple_tools(self):
        """Can register multiple tools."""
        registry = PluginRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())
        assert len(registry.tools) == 2

    def test_decorator_registration(self):
        """@registry.tool decorator registers tool."""
        registry = PluginRegistry()

        @registry.tool
        class DecoratedTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="decorated_tool",
                    description="Decorated",
                    category=ToolCategory.CODE,
                    parameters={},
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="decorated_tool",
                    success=True,
                    result=None,
                    execution_time_ms=1,
                )

        assert len(registry.tools) == 1
        assert registry.tools[0].definition.name == "decorated_tool"

    def test_tools_returns_copy(self):
        """tools property returns a copy, not the internal list."""
        registry = PluginRegistry()
        registry.register(DummyTool())

        tools = registry.tools
        tools.append(AnotherTool())  # Should not affect internal state

        assert len(registry.tools) == 1

    def test_clear(self):
        """Can clear all tools."""
        registry = PluginRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())
        assert len(registry.tools) == 2

        registry.clear()
        assert len(registry.tools) == 0


class TestPluginLoader:
    """Tests for PluginLoader."""

    def test_init_empty(self):
        """PluginLoader starts with no loaded plugins."""
        loader = PluginLoader()
        assert len(loader.loaded_plugins) == 0

    def test_is_loaded(self):
        """is_loaded returns correct status."""
        loader = PluginLoader()
        assert not loader.is_loaded("some_plugin")

    def test_load_from_directory_missing(self):
        """Raises FileNotFoundError for missing directory."""
        loader = PluginLoader()
        registry = MockRegistry()

        with pytest.raises(FileNotFoundError):
            loader.load_from_directory("/nonexistent/path", registry)

    def test_load_from_directory_empty(self):
        """Returns empty list for directory with no plugins."""
        loader = PluginLoader()
        registry = MockRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = loader.load_from_directory(tmpdir, registry)
            assert loaded == []

    def test_load_from_directory_skips_files(self):
        """Skips regular files in plugin directory."""
        loader = PluginLoader()
        registry = MockRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a regular file (not a directory)
            Path(tmpdir, "not_a_plugin.py").write_text("# Just a file")

            loaded = loader.load_from_directory(tmpdir, registry)
            assert loaded == []

    def test_load_from_directory_skips_no_init(self):
        """Skips directories without __init__.py."""
        loader = PluginLoader()
        registry = MockRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory without __init__.py
            Path(tmpdir, "no_init_plugin").mkdir()

            loaded = loader.load_from_directory(tmpdir, registry)
            assert loaded == []

    def test_load_from_package_not_installed(self):
        """Raises ImportError for uninstalled package."""
        loader = PluginLoader()
        registry = MockRegistry()

        with pytest.raises(ImportError):
            loader.load_from_package("nonexistent_package_xyz", registry)


class TestMockRegistry:
    """Tests for MockRegistry testing utility."""

    def test_register_and_get(self):
        """Can register and retrieve tools."""
        registry = MockRegistry()
        tool = DummyTool()

        registry.register(tool)
        retrieved = registry.get("dummy_tool")

        assert retrieved is tool

    def test_get_missing_returns_none(self):
        """get() returns None for missing tools."""
        registry = MockRegistry()
        assert registry.get("nonexistent") is None

    def test_has(self):
        """has() returns correct status."""
        registry = MockRegistry()
        registry.register(DummyTool())

        assert registry.has("dummy_tool")
        assert not registry.has("nonexistent")

    def test_duplicate_registration_raises(self):
        """Raises ValueError on duplicate registration."""
        registry = MockRegistry()
        registry.register(DummyTool())

        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyTool())

    def test_list_tools(self):
        """list_tools returns all definitions."""
        registry = MockRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())

        tools = registry.list_tools()
        names = {t.name for t in tools}

        assert names == {"dummy_tool", "another_tool"}

    def test_get_tools_for_llm(self):
        """get_tools_for_llm returns correct schemas."""
        registry = MockRegistry()
        registry.register(DummyTool())

        schemas = registry.get_tools_for_llm()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy_tool"

    def test_get_tools_for_llm_filtered(self):
        """get_tools_for_llm can filter by name."""
        registry = MockRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())

        schemas = registry.get_tools_for_llm(["dummy_tool"])
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy_tool"

    def test_count(self):
        """count() returns number of tools."""
        registry = MockRegistry()
        assert registry.count() == 0

        registry.register(DummyTool())
        assert registry.count() == 1

    def test_clear(self):
        """clear() removes all tools."""
        registry = MockRegistry()
        registry.register(DummyTool())
        registry.clear()

        assert registry.count() == 0
        assert registry.get("dummy_tool") is None
