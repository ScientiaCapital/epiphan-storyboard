"""Example plugin demonstrating conductor-ai SDK usage.

This plugin provides:
- EchoTool: Simple tool that echoes input back (useful for testing)
- RandomNumberTool: Generates random numbers within a range

To use this plugin:
    from conductor_ai.sdk import PluginLoader
    from src.tools.registry import ToolRegistry

    loader = PluginLoader()
    registry = ToolRegistry()

    # Load from directory
    loader.load_from_directory("plugins/", registry)

    # Or load directly
    from plugins.example_plugin import register
    register(registry)
"""

from __future__ import annotations

import random
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.sdk.registry import PluginRegistry

# Plugin-local registry for collecting tools
_registry = PluginRegistry()


@_registry.tool
class EchoTool(BaseTool):
    """Simple tool that echoes input back.

    Useful for testing the agent loop without external dependencies.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Echoes the input message back. Useful for testing.",
            category=ToolCategory.SYSTEM,
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to echo back",
                    },
                },
                "required": ["message"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Echo the input message back.

        Args:
            arguments: {"message": "text to echo"}

        Returns:
            ToolResult with the echoed message
        """
        message = arguments.get("message", "")

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result=f"Echo: {message}",
            error=None,
            execution_time_ms=1,
        )


@_registry.tool
class RandomNumberTool(BaseTool):
    """Tool that generates random numbers.

    Demonstrates parameter validation and numeric results.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="random_number",
            description="Generate a random integer within a range.",
            category=ToolCategory.CODE,
            parameters={
                "type": "object",
                "properties": {
                    "min": {
                        "type": "integer",
                        "description": "Minimum value (inclusive)",
                        "default": 1,
                    },
                    "max": {
                        "type": "integer",
                        "description": "Maximum value (inclusive)",
                        "default": 100,
                    },
                },
                "required": [],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Generate a random number.

        Args:
            arguments: {"min": 1, "max": 100}

        Returns:
            ToolResult with random number
        """
        min_val = arguments.get("min", 1)
        max_val = arguments.get("max", 100)

        # Validate range
        if min_val > max_val:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"min ({min_val}) cannot be greater than max ({max_val})",
                execution_time_ms=1,
            )

        number = random.randint(min_val, max_val)

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result={"number": number, "range": [min_val, max_val]},
            error=None,
            execution_time_ms=1,
        )


def register(global_registry: Any) -> None:
    """Register all tools from this plugin into the global registry.

    This function is called by PluginLoader.

    Args:
        global_registry: The ToolRegistry to register tools into
    """
    for tool in _registry.tools:
        global_registry.register(tool)


# Plugin metadata
__plugin_name__ = "example_plugin"
__plugin_version__ = "0.1.0"
__plugin_tools__ = ["echo", "random_number"]
