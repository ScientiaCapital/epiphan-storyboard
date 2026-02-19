"""Tests for tool registry and base classes."""

import pytest
from pydantic import ValidationError

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.registry import ToolRegistry


class TestToolCategory:
    """Tests for ToolCategory enum."""

    def test_all_category_values(self):
        """Test all category enum values exist."""
        assert ToolCategory.WEB == "web"
        assert ToolCategory.DATA == "data"
        assert ToolCategory.CODE == "code"
        assert ToolCategory.FILE == "file"
        assert ToolCategory.SYSTEM == "system"

    def test_category_values_are_strings(self):
        """Test that category values are strings."""
        for category in ToolCategory:
            assert isinstance(category.value, str)

    def test_category_from_string(self):
        """Test creating category from string."""
        assert ToolCategory("web") == ToolCategory.WEB
        assert ToolCategory("data") == ToolCategory.DATA


class TestToolDefinition:
    """Tests for ToolDefinition schema."""

    def test_create_definition_minimal(self):
        """Test creating tool definition with minimal data."""
        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.WEB,
        )
        assert definition.name == "test_tool"
        assert definition.description == "A test tool"
        assert definition.category == ToolCategory.WEB
        assert definition.parameters == {}
        assert definition.requires_approval is False

    def test_create_definition_with_parameters(self):
        """Test creating tool definition with parameter schema."""
        parameters = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        definition = ToolDefinition(
            name="search",
            description="Search for information",
            parameters=parameters,
            category=ToolCategory.WEB,
        )
        assert definition.parameters == parameters

    def test_create_definition_requiring_approval(self):
        """Test creating tool that requires approval."""
        definition = ToolDefinition(
            name="shell_exec",
            description="Execute shell command",
            category=ToolCategory.SYSTEM,
            requires_approval=True,
        )
        assert definition.requires_approval is True

    def test_definition_serialization(self):
        """Test serializing definition to dict."""
        definition = ToolDefinition(
            name="calc",
            description="Calculator",
            category=ToolCategory.CODE,
            parameters={"type": "object", "properties": {"x": {"type": "number"}}},
        )
        data = definition.model_dump()
        assert data["name"] == "calc"
        assert data["description"] == "Calculator"
        assert data["category"] == "code"
        assert data["requires_approval"] is False


class TestToolResult:
    """Tests for ToolResult schema."""

    def test_create_success_result(self):
        """Test creating successful tool result."""
        result = ToolResult(
            tool_name="search",
            success=True,
            result={"results": ["item1", "item2"]},
            execution_time_ms=150,
        )
        assert result.tool_name == "search"
        assert result.success is True
        assert result.result == {"results": ["item1", "item2"]}
        assert result.error is None
        assert result.execution_time_ms == 150

    def test_create_failure_result(self):
        """Test creating failed tool result."""
        result = ToolResult(
            tool_name="search",
            success=False,
            error="Connection timeout",
            execution_time_ms=5000,
        )
        assert result.tool_name == "search"
        assert result.success is False
        assert result.result is None
        assert result.error == "Connection timeout"
        assert result.execution_time_ms == 5000

    def test_result_with_none_result(self):
        """Test result with None as the result value."""
        result = ToolResult(
            tool_name="void_tool",
            success=True,
            result=None,
            execution_time_ms=10,
        )
        assert result.success is True
        assert result.result is None

    def test_negative_execution_time_not_allowed(self):
        """Test that negative execution time is not allowed."""
        with pytest.raises(ValidationError):
            ToolResult(
                tool_name="test",
                success=True,
                execution_time_ms=-1,
            )

    def test_result_serialization(self):
        """Test serializing result to dict."""
        result = ToolResult(
            tool_name="calc",
            success=True,
            result=42,
            execution_time_ms=5,
        )
        data = result.model_dump()
        assert data["tool_name"] == "calc"
        assert data["success"] is True
        assert data["result"] == 42
        assert data["error"] is None
        assert data["execution_time_ms"] == 5


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    def test_create_simple_tool(self):
        """Test creating a simple tool implementation."""

        class SimpleTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="simple_tool",
                    description="A simple test tool",
                    category=ToolCategory.CODE,
                    parameters={
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                    },
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="simple_tool",
                    success=True,
                    result=f"Processed: {arguments.get('input', '')}",
                    execution_time_ms=0,
                )

        tool = SimpleTool()
        assert tool.definition.name == "simple_tool"
        assert tool.definition.category == ToolCategory.CODE

    @pytest.mark.asyncio
    async def test_tool_run(self):
        """Test running a tool."""

        class EchoTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="echo",
                    description="Echo input",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="echo",
                    success=True,
                    result=arguments,
                    execution_time_ms=0,
                )

        tool = EchoTool()
        result = await tool.run({"message": "hello"})
        assert result.success is True
        assert result.result == {"message": "hello"}

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""

        class FailingTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="failing",
                    description="Always fails",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="failing",
                    success=False,
                    error="Intentional failure",
                    execution_time_ms=0,
                )

        tool = FailingTool()
        result = await tool.run({})
        assert result.success is False
        assert result.error == "Intentional failure"

    def test_get_llm_schema(self):
        """Test getting LLM-compatible schema."""

        class SearchTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="search",
                    description="Search for information",
                    category=ToolCategory.WEB,
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {
                                "type": "integer",
                                "description": "Max results",
                            },
                        },
                        "required": ["query"],
                    },
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="search",
                    success=True,
                    result=[],
                    execution_time_ms=0,
                )

        tool = SearchTool()
        schema = tool.get_llm_schema()

        # Verify OpenAI/Anthropic compatible format
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "search"
        assert schema["function"]["description"] == "Search for information"
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"
        assert "query" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["query"]

    @pytest.mark.asyncio
    async def test_execute_with_timing(self):
        """Test that execution timing is measured."""

        class SlowTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="slow",
                    description="Slow tool",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                import asyncio

                await asyncio.sleep(0.01)  # 10ms
                return ToolResult(
                    tool_name="slow",
                    success=True,
                    result="done",
                    execution_time_ms=0,  # Will be updated
                )

        tool = SlowTool()
        result = await tool._execute_with_timing({})
        assert result.execution_time_ms >= 10  # At least 10ms
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_timing_on_exception(self):
        """Test that timing works even when tool raises exception."""

        class ErrorTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="error",
                    description="Error tool",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                raise ValueError("Something went wrong")

        tool = ErrorTool()
        result = await tool._execute_with_timing({})
        assert result.success is False
        assert "Something went wrong" in result.error
        assert result.execution_time_ms >= 0


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        reg = ToolRegistry()
        reg.clear()  # Ensure clean state
        return reg

    @pytest.fixture
    def sample_tool(self):
        """Create a sample tool for testing."""

        class SampleTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="sample",
                    description="Sample tool",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="sample",
                    success=True,
                    result="sample result",
                    execution_time_ms=0,
                )

        return SampleTool()

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        reg1 = ToolRegistry()
        reg2 = ToolRegistry()
        assert reg1 is reg2

    def test_register_tool(self, registry, sample_tool):
        """Test registering a tool."""
        registry.register(sample_tool)
        assert registry.count() == 1
        assert registry.has("sample")

    def test_register_duplicate_tool_fails(self, registry, sample_tool):
        """Test that registering duplicate tool name fails."""
        registry.register(sample_tool)
        with pytest.raises(ValueError) as exc_info:
            registry.register(sample_tool)
        assert "already registered" in str(exc_info.value)

    def test_get_tool(self, registry, sample_tool):
        """Test retrieving a tool by name."""
        registry.register(sample_tool)
        retrieved = registry.get("sample")
        assert retrieved is sample_tool

    def test_get_nonexistent_tool(self, registry):
        """Test getting tool that doesn't exist returns None."""
        result = registry.get("nonexistent")
        assert result is None

    def test_list_tools(self, registry):
        """Test listing all tool definitions."""

        class Tool1(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="tool1",
                    description="First tool",
                    category=ToolCategory.WEB,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="tool1", success=True, result=None, execution_time_ms=0
                )

        class Tool2(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="tool2",
                    description="Second tool",
                    category=ToolCategory.DATA,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="tool2", success=True, result=None, execution_time_ms=0
                )

        registry.register(Tool1())
        registry.register(Tool2())

        definitions = registry.list_tools()
        assert len(definitions) == 2
        names = [d.name for d in definitions]
        assert "tool1" in names
        assert "tool2" in names

    def test_get_tools_for_llm_all(self, registry):
        """Test getting LLM schemas for all tools."""

        class WebTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="web_fetch",
                    description="Fetch web page",
                    category=ToolCategory.WEB,
                    parameters={"type": "object", "properties": {"url": {"type": "string"}}},
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="web_fetch",
                    success=True,
                    result=None,
                    execution_time_ms=0,
                )

        registry.register(WebTool())
        schemas = registry.get_tools_for_llm()

        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "web_fetch"
        assert schemas[0]["function"]["description"] == "Fetch web page"

    def test_get_tools_for_llm_specific(self, registry):
        """Test getting LLM schemas for specific tools."""

        class Tool1(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="tool1",
                    description="Tool 1",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="tool1", success=True, result=None, execution_time_ms=0
                )

        class Tool2(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="tool2",
                    description="Tool 2",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="tool2", success=True, result=None, execution_time_ms=0
                )

        class Tool3(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="tool3",
                    description="Tool 3",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="tool3", success=True, result=None, execution_time_ms=0
                )

        registry.register(Tool1())
        registry.register(Tool2())
        registry.register(Tool3())

        schemas = registry.get_tools_for_llm(["tool1", "tool3"])
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "tool1" in names
        assert "tool3" in names
        assert "tool2" not in names

    def test_get_tools_for_llm_nonexistent_fails(self, registry, sample_tool):
        """Test that requesting nonexistent tool fails."""
        registry.register(sample_tool)
        with pytest.raises(ValueError) as exc_info:
            registry.get_tools_for_llm(["sample", "nonexistent"])
        assert "not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_tool_decorator(self, registry):
        """Test using decorator to register tool."""

        @registry.tool
        class DecoratedTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="decorated",
                    description="Decorated tool",
                    category=ToolCategory.CODE,
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="decorated",
                    success=True,
                    result=None,
                    execution_time_ms=0,
                )

        # Tool should be automatically registered
        assert registry.has("decorated")
        tool = registry.get("decorated")
        assert tool is not None
        assert tool.definition.name == "decorated"

    def test_clear_registry(self, registry, sample_tool):
        """Test clearing all tools from registry."""
        registry.register(sample_tool)
        assert registry.count() == 1

        registry.clear()
        assert registry.count() == 0
        assert not registry.has("sample")

    def test_has_tool(self, registry, sample_tool):
        """Test checking if tool exists."""
        assert not registry.has("sample")
        registry.register(sample_tool)
        assert registry.has("sample")

    def test_count_tools(self, registry):
        """Test counting registered tools."""
        assert registry.count() == 0

        class Tool1(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="t1", description="T1", category=ToolCategory.CODE
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="t1", success=True, result=None, execution_time_ms=0
                )

        class Tool2(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="t2", description="T2", category=ToolCategory.CODE
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="t2", success=True, result=None, execution_time_ms=0
                )

        registry.register(Tool1())
        assert registry.count() == 1

        registry.register(Tool2())
        assert registry.count() == 2

    def test_llm_schema_format_matches_openai(self, registry):
        """Test that LLM schema format matches OpenAI spec exactly."""

        class CalculatorTool(BaseTool):
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name="calculator",
                    description="Perform arithmetic operations",
                    category=ToolCategory.CODE,
                    parameters={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["add", "subtract", "multiply", "divide"],
                                "description": "The operation to perform",
                            },
                            "x": {"type": "number", "description": "First number"},
                            "y": {"type": "number", "description": "Second number"},
                        },
                        "required": ["operation", "x", "y"],
                    },
                )

            async def run(self, arguments: dict) -> ToolResult:
                return ToolResult(
                    tool_name="calculator",
                    success=True,
                    result=0,
                    execution_time_ms=0,
                )

        registry.register(CalculatorTool())
        schemas = registry.get_tools_for_llm(["calculator"])

        assert len(schemas) == 1
        schema = schemas[0]

        # Validate OpenAI function calling format
        assert schema["type"] == "function"
        assert "function" in schema

        function = schema["function"]
        assert function["name"] == "calculator"
        assert function["description"] == "Perform arithmetic operations"
        assert "parameters" in function

        params = function["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert set(params["required"]) == {"operation", "x", "y"}
        assert "operation" in params["properties"]
        assert "x" in params["properties"]
        assert "y" in params["properties"]
