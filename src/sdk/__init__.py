"""Epiphan Storyboard SDK for building plugins and integrations.

This module provides the public API for external projects to:
- Create custom tools that integrate with epiphan-storyboard agents
- Register tools via PluginLoader for auto-discovery
- Use StoryboardClient to interact with the epiphan-storyboard API

Basic usage:
    from epiphan_storyboard.sdk import BaseTool, ToolCategory, ToolResult, StoryboardClient

    class MyTool(BaseTool):
        @property
        def definition(self):
            return ToolDefinition(
                name="my_tool",
                description="Does something useful",
                category=ToolCategory.DATA,
                parameters={...}
            )

        async def run(self, arguments: dict) -> ToolResult:
            # Your implementation
            pass

    # Use with API
    client = StoryboardClient("http://localhost:8000", org_id="my-org")
    session = await client.run_agent(
        messages=[{"role": "user", "content": "Do something"}],
        tools=["my_tool", "web_fetch"]
    )
"""

from __future__ import annotations

# Version for compatibility checking
__version__ = "0.1.0"

# Core tool classes (re-exported from internal modules)
# Agent schemas (useful for type hints in plugins)
from src.agents.schemas import (
    AgentSession,
    AgentStep,
    SessionStatus,
    ToolCall,
)

# HTTP client for remote API
from src.sdk.client import StoryboardClient

# Registry and plugin loading
from src.sdk.registry import PluginLoader, PluginRegistry
from src.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolResult,
)

__all__ = [
    # Version
    "__version__",
    # Tools
    "BaseTool",
    "ToolCategory",
    "ToolDefinition",
    "ToolResult",
    # Registry
    "PluginLoader",
    "PluginRegistry",
    # Client
    "StoryboardClient",
    # Schemas
    "AgentSession",
    "AgentStep",
    "SessionStatus",
    "ToolCall",
]
