"""Mock objects and test utilities for conductor-ai plugins.

Provides isolated testing infrastructure so plugin tests don't
affect the global registry or require real API connections.

Usage:
    from conductor_ai.sdk.testing import MockRegistry, ToolTestBase

    class TestMyTool(ToolTestBase):
        def setup_method(self):
            self.registry = MockRegistry()
            self.tool = MyTool()
            self.registry.register(self.tool)

        async def test_my_tool(self):
            result = await self.tool.run({"arg": "value"})
            self.assert_success(result)
            assert result.result == expected_value
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.tools.base import BaseTool, ToolDefinition, ToolResult
from src.agents.schemas import AgentSession, AgentStep, SessionStatus


class MockRegistry:
    """Isolated registry for testing.

    Unlike the global ToolRegistry singleton, MockRegistry creates
    a completely isolated instance for each test.

    Usage:
        registry = MockRegistry()
        registry.register(MyTool())

        tool = registry.get("my_tool")
        assert tool is not None
    """

    def __init__(self) -> None:
        """Initialize an empty mock registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool in this mock registry.

        Args:
            tool: The tool instance to register

        Raises:
            ValueError: If tool name already registered
        """
        name = tool.definition.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        self._tools[name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name to look up

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name to check

        Returns:
            True if registered
        """
        return name in self._tools

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools.

        Returns:
            List of ToolDefinition objects
        """
        return [tool.definition for tool in self._tools.values()]

    def get_tools_for_llm(
        self, tool_names: list[str] | None = None
    ) -> list[dict]:
        """Get LLM-compatible schemas for tools.

        Args:
            tool_names: Optional list of tool names to include

        Returns:
            List of function calling schemas
        """
        if tool_names is None:
            return [tool.get_llm_schema() for tool in self._tools.values()]

        schemas = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                schemas.append(tool.get_llm_schema())
        return schemas

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()

    def count(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)


class MockStateManager:
    """In-memory state manager for testing.

    Stores sessions and steps in memory without Redis or Supabase.
    Useful for integration tests that need state management.

    Usage:
        state = MockStateManager()
        session = await state.create_session("test-org", "claude-4")
        await state.add_step(session.session_id, step)
    """

    def __init__(self) -> None:
        """Initialize empty state storage."""
        self._sessions: dict[str, AgentSession] = {}
        self._steps: dict[str, list[AgentStep]] = {}

    async def create_session(
        self,
        org_id: str,
        model: str,
    ) -> AgentSession:
        """Create a new session.

        Args:
            org_id: Organization identifier
            model: Model to use

        Returns:
            New AgentSession
        """
        session = AgentSession(
            session_id=str(uuid4()),
            org_id=org_id,
            status=SessionStatus.PENDING,
        )
        self._sessions[session.session_id] = session
        self._steps[session.session_id] = []
        return session

    async def get_session(self, session_id: str) -> AgentSession | None:
        """Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            # Attach steps
            session.steps = self._steps.get(session_id, [])
        return session

    async def update_session(self, session: AgentSession) -> None:
        """Update a session.

        Args:
            session: Updated session object
        """
        session.updated_at = datetime.now(timezone.utc)
        self._sessions[session.session_id] = session

    async def add_step(self, session_id: str, step: AgentStep) -> None:
        """Add a step to a session.

        Args:
            session_id: Session to add step to
            step: Step to add
        """
        if session_id not in self._steps:
            self._steps[session_id] = []
        self._steps[session_id].append(step)

    async def get_steps(self, session_id: str) -> list[AgentStep]:
        """Get all steps for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of steps
        """
        return self._steps.get(session_id, [])

    async def update_token_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Update token usage for a session.

        Args:
            session_id: Session identifier
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
            cost: Cost in USD to add
        """
        session = self._sessions.get(session_id)
        if session:
            session.input_tokens += input_tokens
            session.output_tokens += output_tokens
            session.total_cost_usd += cost

    def clear(self) -> None:
        """Clear all state."""
        self._sessions.clear()
        self._steps.clear()


class ToolTestBase:
    """Base class for tool unit tests.

    Provides common setup, teardown, and assertion helpers
    for testing conductor-ai tools.

    Usage:
        class TestMyTool(ToolTestBase):
            def setup_method(self):
                super().setup_method()
                self.tool = MyTool()
                self.registry.register(self.tool)

            async def test_success(self):
                result = await self.tool.run({"url": "https://example.com"})
                self.assert_success(result)

            async def test_error(self):
                result = await self.tool.run({"url": "invalid"})
                self.assert_error(result, "Invalid URL")
    """

    registry: MockRegistry
    state: MockStateManager

    def setup_method(self) -> None:
        """Set up test fixtures.

        Creates fresh MockRegistry and MockStateManager for each test.
        Override this to add your tool.
        """
        self.registry = MockRegistry()
        self.state = MockStateManager()

    def teardown_method(self) -> None:
        """Tear down test fixtures.

        Clears registry and state to prevent leaks between tests.
        """
        self.registry.clear()
        self.state.clear()

    def assert_success(
        self,
        result: ToolResult,
        expected_result: Any = None,
    ) -> None:
        """Assert that a tool result indicates success.

        Args:
            result: The ToolResult to check
            expected_result: Optional expected result value

        Raises:
            AssertionError: If result is not successful
        """
        assert result.success, f"Expected success but got error: {result.error}"
        assert result.error is None, f"Success result should have no error"

        if expected_result is not None:
            assert result.result == expected_result, (
                f"Expected result {expected_result}, got {result.result}"
            )

    def assert_error(
        self,
        result: ToolResult,
        error_contains: str | None = None,
    ) -> None:
        """Assert that a tool result indicates failure.

        Args:
            result: The ToolResult to check
            error_contains: Optional substring that should be in error message

        Raises:
            AssertionError: If result is successful
        """
        assert not result.success, f"Expected error but got success: {result.result}"
        assert result.error is not None, "Error result should have error message"

        if error_contains is not None:
            assert error_contains in result.error, (
                f"Expected error containing '{error_contains}', got: {result.error}"
            )


def assert_tool_success(
    result: ToolResult,
    expected_result: Any = None,
) -> None:
    """Assert that a ToolResult indicates success.

    Standalone function version of ToolTestBase.assert_success.

    Args:
        result: The ToolResult to check
        expected_result: Optional expected result value

    Raises:
        AssertionError: If result is not successful
    """
    assert result.success, f"Expected success but got error: {result.error}"
    assert result.error is None

    if expected_result is not None:
        assert result.result == expected_result


def assert_tool_error(
    result: ToolResult,
    error_contains: str | None = None,
) -> None:
    """Assert that a ToolResult indicates failure.

    Standalone function version of ToolTestBase.assert_error.

    Args:
        result: The ToolResult to check
        error_contains: Optional substring that should be in error message

    Raises:
        AssertionError: If result is successful
    """
    assert not result.success, f"Expected error but got success: {result.result}"
    assert result.error is not None

    if error_contains is not None:
        assert error_contains in result.error
