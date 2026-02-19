"""Conductor-AI SDK for building plugins and integrations.

This module provides the public API for external projects to:
- Create custom tools that integrate with conductor-ai agents
- Register tools via PluginLoader for auto-discovery
- Use ConductorClient to interact with the conductor-ai API

Basic usage:
    from conductor_ai.sdk import BaseTool, ToolCategory, ToolResult, ConductorClient

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
    client = ConductorClient("http://localhost:8000", org_id="my-org")
    session = await client.run_agent(
        messages=[{"role": "user", "content": "Do something"}],
        tools=["my_tool", "web_fetch"]
    )
"""

from __future__ import annotations

# Version for compatibility checking
__version__ = "0.1.0"

# Core tool classes (re-exported from internal modules)
from src.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolResult,
)

# Registry and plugin loading
from src.sdk.registry import PluginLoader, PluginRegistry

# HTTP client for remote API
from src.sdk.client import ConductorClient

# Agent schemas (useful for type hints in plugins)
from src.agents.schemas import (
    AgentSession,
    AgentStep,
    SessionStatus,
    ToolCall,
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
    "ConductorClient",
    # Schemas
    "AgentSession",
    "AgentStep",
    "SessionStatus",
    "ToolCall",
]
