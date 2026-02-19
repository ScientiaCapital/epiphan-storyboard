"""Tool registry for managing available tools in the agent system."""

from typing import Callable

from src.tools.base import BaseTool, ToolDefinition


class ToolRegistry:
    """
    Singleton registry for managing all available tools.

    The registry allows tools to be registered, retrieved by name,
    and listed for LLM function calling.

    Usage:
        # Create a tool
        class MyTool(BaseTool):
            ...

        # Register it
        registry = ToolRegistry()
        registry.register(MyTool())

        # Or use the decorator
        @registry.tool
        class MyTool(BaseTool):
            ...

        # Retrieve for use
        tool = registry.get("my_tool")
        result = await tool.run({"arg": "value"})

        # Get schemas for LLM
        schemas = registry.get_tools_for_llm(["my_tool", "other_tool"])
    """

    _instance: "ToolRegistry | None" = None
    _tools: dict[str, BaseTool]

    def __new__(cls) -> "ToolRegistry":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: The tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        tool_name = tool.definition.name
        if tool_name in self._tools:
            raise ValueError(
                f"Tool '{tool_name}' is already registered. "
                "Each tool name must be unique."
            )
        self._tools[tool_name] = tool

    def get(self, name: str) -> BaseTool | None:
        """
        Retrieve a tool by name.

        Args:
            name: The name of the tool to retrieve

        Returns:
            The tool instance if found, None otherwise
        """
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """
        Get definitions for all registered tools.

        Returns:
            List of ToolDefinition objects for all registered tools
        """
        return [tool.definition for tool in self._tools.values()]

    def get_tools_for_llm(
        self, tool_names: list[str] | None = None
    ) -> list[dict]:
        """
        Get OpenAI/Anthropic-compatible function schemas for specified tools.

        Args:
            tool_names: List of tool names to include. If None, includes all tools.

        Returns:
            List of function schemas in the format:
            [
                {
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "description": "What it does",
                        "parameters": { ... JSON Schema ... }
                    }
                },
                ...
            ]

        Raises:
            ValueError: If any tool name in tool_names is not found
        """
        if tool_names is None:
            # Return all tools
            return [tool.get_llm_schema() for tool in self._tools.values()]

        # Return specific tools
        schemas = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool is None:
                raise ValueError(
                    f"Tool '{name}' not found in registry. "
                    f"Available tools: {list(self._tools.keys())}"
                )
            schemas.append(tool.get_llm_schema())
        return schemas

    def tool(self, tool_class: type[BaseTool]) -> type[BaseTool]:
        """
        Decorator to automatically register a tool class.

        Usage:
            @registry.tool
            class MyTool(BaseTool):
                ...

        Args:
            tool_class: The tool class to register

        Returns:
            The same tool class (for chaining)
        """
        # Instantiate and register the tool
        tool_instance = tool_class()
        self.register(tool_instance)
        return tool_class

    def clear(self) -> None:
        """
        Clear all registered tools.

        This is primarily useful for testing to ensure a clean state.
        """
        self._tools.clear()

    def count(self) -> int:
        """
        Get the number of registered tools.

        Returns:
            Number of tools currently registered
        """
        return len(self._tools)

    def has(self, name: str) -> bool:
        """
        Check if a tool with the given name is registered.

        Args:
            name: The tool name to check

        Returns:
            True if the tool is registered, False otherwise
        """
        return name in self._tools
