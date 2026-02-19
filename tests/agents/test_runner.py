"""Tests for AgentRunner - ReAct execution loop with multi-provider LLM support.

TDD Red Phase: All tests written BEFORE implementation.
Tests mock the Claude API, OpenRouter API, and use fakeredis for StateManager.

Supports:
- Anthropic (Claude) for complex reasoning
- OpenRouter for cost-optimized inference (DeepSeek, Qwen, Mistral)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.schemas import (
    AgentRunRequest,
    AgentSession,
    AgentStep,
    SessionStatus,
    ToolCall,
)
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.registry import ToolRegistry


# ============================================================================
# Mock Tools for Testing (No eval - safe implementation)
# ============================================================================


class MockCalculatorTool(BaseTool):
    """A simple mock tool for testing - uses safe string parsing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Performs basic math calculations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"],
            },
            category=ToolCategory.DATA,
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        expression = arguments.get("expression", "")
        try:
            # Safe parsing for test expressions (no eval)
            # Only handles simple cases like "2+2", "10*5" for testing
            result = self._safe_calculate(expression)
            return ToolResult(
                tool_name="calculator",
                success=True,
                result=str(result),
                execution_time_ms=1,
            )
        except Exception as e:
            return ToolResult(
                tool_name="calculator",
                success=False,
                error=str(e),
                execution_time_ms=1,
            )

    def _safe_calculate(self, expr: str) -> int:
        """Safe calculation for test expressions only."""
        expr = expr.strip()
        if "+" in expr:
            parts = expr.split("+")
            return int(parts[0].strip()) + int(parts[1].strip())
        elif "*" in expr:
            parts = expr.split("*")
            return int(parts[0].strip()) * int(parts[1].strip())
        elif "-" in expr:
            parts = expr.split("-")
            return int(parts[0].strip()) - int(parts[1].strip())
        else:
            return int(expr)


class MockFailingTool(BaseTool):
    """A tool that always fails for testing error handling."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="failing_tool",
            description="A tool that always fails",
            parameters={"type": "object", "properties": {}},
            category=ToolCategory.SYSTEM,
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        return ToolResult(
            tool_name="failing_tool",
            success=False,
            error="Tool execution failed intentionally",
            execution_time_ms=1,
        )


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    import fakeredis.aioredis
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    mock.table = MagicMock(return_value=mock)
    mock.insert = MagicMock(return_value=mock)
    mock.update = MagicMock(return_value=mock)
    mock.select = MagicMock(return_value=mock)
    mock.eq = MagicMock(return_value=mock)
    mock.upsert = MagicMock(return_value=mock)
    mock.execute = MagicMock(return_value=MagicMock(data=[]))
    return mock


@pytest.fixture
def state_manager(mock_redis, mock_supabase):
    """Create a StateManager with mocked dependencies."""
    from src.agents.state import StateManager

    manager = StateManager(
        redis_url="redis://localhost:6379",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )
    manager._redis = mock_redis
    manager._supabase = mock_supabase
    return manager


@pytest.fixture
def tool_registry():
    """Create a fresh tool registry with mock tools."""
    registry = ToolRegistry()
    registry.clear()  # Clear singleton state
    registry.register(MockCalculatorTool())
    registry.register(MockFailingTool())
    return registry


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock = MagicMock()
    mock.messages = MagicMock()
    mock.messages.create = AsyncMock()
    return mock


@pytest.fixture
def mock_openrouter_client():
    """Create a mock OpenRouter client (httpx-based)."""
    mock = AsyncMock()
    mock.post = AsyncMock()
    return mock


@pytest.fixture
def agent_runner(state_manager, tool_registry, mock_anthropic_client, mock_openrouter_client):
    """Create an AgentRunner with mocked dependencies."""
    from src.agents.runner import AgentRunner

    runner = AgentRunner(
        state_manager=state_manager,
        tool_registry=tool_registry,
        anthropic_client=mock_anthropic_client,
        openrouter_client=mock_openrouter_client,
    )
    return runner


# ============================================================================
# TestAgentRunnerInit
# ============================================================================


class TestAgentRunnerInit:
    """Test AgentRunner initialization."""

    def test_init_with_state_manager(self, state_manager, tool_registry, mock_anthropic_client, mock_openrouter_client):
        """Test initialization with explicit StateManager."""
        from src.agents.runner import AgentRunner

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=mock_anthropic_client,
            openrouter_client=mock_openrouter_client,
        )

        assert runner._state_manager is state_manager

    def test_init_registers_tools(self, state_manager, tool_registry, mock_anthropic_client, mock_openrouter_client):
        """Test that tools from registry are available."""
        from src.agents.runner import AgentRunner

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=mock_anthropic_client,
            openrouter_client=mock_openrouter_client,
        )

        assert runner._tool_registry.has("calculator")
        assert runner._tool_registry.has("failing_tool")

    def test_init_default_model(self, state_manager, tool_registry, mock_anthropic_client, mock_openrouter_client):
        """Test default model is claude-sonnet-4-5-20250929."""
        from src.agents.runner import AgentRunner

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=mock_anthropic_client,
            openrouter_client=mock_openrouter_client,
        )

        assert runner._default_model == "claude-sonnet-4-5-20250929"

    def test_init_supports_openrouter_models(self, state_manager, tool_registry, mock_anthropic_client, mock_openrouter_client):
        """Test that OpenRouter models are supported for cost optimization."""
        from src.agents.runner import AgentRunner

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=mock_anthropic_client,
            openrouter_client=mock_openrouter_client,
        )

        # OpenRouter models should be recognized
        assert runner.is_openrouter_model("deepseek/deepseek-chat")
        assert runner.is_openrouter_model("qwen/qwen-2.5-72b-instruct")
        assert runner.is_openrouter_model("mistralai/mistral-large-latest")
        assert not runner.is_openrouter_model("claude-sonnet-4-5-20250929")


# ============================================================================
# TestSystemPromptBuilding
# ============================================================================


class TestSystemPromptBuilding:
    """Test system prompt construction."""

    def test_build_system_prompt_includes_tools(self, agent_runner):
        """Test that system prompt includes tool descriptions."""
        prompt = agent_runner.build_system_prompt(tool_names=["calculator"])

        assert "calculator" in prompt
        assert "math calculations" in prompt.lower()

    def test_build_system_prompt_json_format_instructions(self, agent_runner):
        """Test that prompt includes JSON format instructions for ReAct."""
        prompt = agent_runner.build_system_prompt()

        assert "thought" in prompt.lower()
        assert "action" in prompt.lower()
        assert "json" in prompt.lower()

    def test_build_system_prompt_custom_override(self, agent_runner):
        """Test custom system prompt override."""
        custom_prompt = "You are a helpful assistant."
        prompt = agent_runner.build_system_prompt(custom_system_prompt=custom_prompt)

        assert custom_prompt in prompt


# ============================================================================
# TestLLMResponseParsing
# ============================================================================


class TestLLMResponseParsing:
    """Test parsing LLM responses into AgentStep."""

    def test_parse_valid_thought_action_response(self, agent_runner):
        """Test parsing a response with thought and action."""
        response_text = json.dumps({
            "thought": "I need to calculate 2+2",
            "action": {
                "tool_name": "calculator",
                "arguments": {"expression": "2+2"}
            }
        })

        step = agent_runner.parse_llm_response(response_text)

        assert step.thought == "I need to calculate 2+2"
        assert step.action is not None
        assert step.action.tool_name == "calculator"
        assert step.is_final is False

    def test_parse_final_answer_response(self, agent_runner):
        """Test parsing a final answer response."""
        response_text = json.dumps({
            "thought": "I now have the answer",
            "is_final": True,
            "final_answer": "The result is 4"
        })

        step = agent_runner.parse_llm_response(response_text)

        assert step.thought == "I now have the answer"
        assert step.is_final is True
        assert step.final_answer == "The result is 4"

    def test_parse_invalid_json_raises(self, agent_runner):
        """Test that invalid JSON raises ParseError."""
        from src.agents.runner import ParseError

        with pytest.raises(ParseError, match="Invalid JSON"):
            agent_runner.parse_llm_response("not valid json {")

    def test_parse_missing_thought_raises(self, agent_runner):
        """Test that missing thought field raises ParseError."""
        from src.agents.runner import ParseError

        response_text = json.dumps({
            "action": {"tool_name": "calculator", "arguments": {}}
        })

        with pytest.raises(ParseError, match="thought"):
            agent_runner.parse_llm_response(response_text)


# ============================================================================
# TestToolExecution
# ============================================================================


class TestToolExecution:
    """Test tool execution within the runner."""

    @pytest.mark.asyncio
    async def test_execute_tool_calls_registry(self, agent_runner):
        """Test that execute_tool properly calls the tool from registry."""
        tool_call = ToolCall(tool_name="calculator", arguments={"expression": "2+2"})

        result = await agent_runner.execute_tool(tool_call)

        assert result.success is True
        assert result.result == "4"

    @pytest.mark.asyncio
    async def test_execute_tool_captures_observation(self, agent_runner):
        """Test that tool result is captured as observation."""
        tool_call = ToolCall(tool_name="calculator", arguments={"expression": "10*5"})

        result = await agent_runner.execute_tool(tool_call)

        assert result.result == "50"

    @pytest.mark.asyncio
    async def test_execute_tool_handles_error(self, agent_runner):
        """Test that tool errors are captured properly."""
        tool_call = ToolCall(tool_name="failing_tool", arguments={})

        result = await agent_runner.execute_tool(tool_call)

        assert result.success is False
        assert "failed intentionally" in result.error

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_raises(self, agent_runner):
        """Test that unknown tool raises ToolNotFoundError."""
        from src.agents.runner import ToolNotFoundError

        tool_call = ToolCall(tool_name="nonexistent_tool", arguments={})

        with pytest.raises(ToolNotFoundError, match="nonexistent_tool"):
            await agent_runner.execute_tool(tool_call)


# ============================================================================
# TestReActLoop
# ============================================================================


class TestReActLoop:
    """Test the main ReAct execution loop."""

    @pytest.mark.asyncio
    async def test_run_single_step_final_answer(self, agent_runner, mock_anthropic_client):
        """Test run with single step that returns final answer."""
        # Mock LLM to return final answer immediately
        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "thought": "The user asked a simple question",
                "is_final": True,
                "final_answer": "Hello! I'm happy to help."
            }))],
            usage=MagicMock(input_tokens=100, output_tokens=50),
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4-5-20250929",
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        assert len(session.steps) == 1
        assert session.steps[0].is_final is True

    @pytest.mark.asyncio
    async def test_run_multi_step_with_tool_calls(self, agent_runner, mock_anthropic_client):
        """Test run with multiple steps including tool calls."""
        # Mock LLM responses - first with tool call, then final answer
        mock_anthropic_client.messages.create.side_effect = [
            MagicMock(
                content=[MagicMock(text=json.dumps({
                    "thought": "I need to calculate this",
                    "action": {"tool_name": "calculator", "arguments": {"expression": "2+2"}}
                }))],
                usage=MagicMock(input_tokens=100, output_tokens=50),
            ),
            MagicMock(
                content=[MagicMock(text=json.dumps({
                    "thought": "Now I have the answer",
                    "is_final": True,
                    "final_answer": "2+2 = 4"
                }))],
                usage=MagicMock(input_tokens=150, output_tokens=30),
            ),
        ]

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        assert len(session.steps) == 2
        assert session.steps[0].action is not None
        assert session.steps[1].is_final is True

    @pytest.mark.asyncio
    async def test_run_respects_max_steps(self, agent_runner, mock_anthropic_client):
        """Test that run stops after max_steps is reached."""
        # Mock LLM to always return tool calls (never final)
        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "thought": "Let me try another calculation",
                "action": {"tool_name": "calculator", "arguments": {"expression": "1+1"}}
            }))],
            usage=MagicMock(input_tokens=100, output_tokens=50),
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Keep calculating forever"}],
            max_steps=3,
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert len(session.steps) == 3
        assert session.status == SessionStatus.COMPLETED  # Completes at max steps

    @pytest.mark.asyncio
    async def test_run_updates_session_status(self, agent_runner, mock_anthropic_client, state_manager, mock_supabase):
        """Test that session status is updated throughout execution."""
        mock_anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "thought": "Simple answer",
                "is_final": True,
                "final_answer": "Done"
            }))],
            usage=MagicMock(input_tokens=100, output_tokens=50),
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        session = await agent_runner.run(request, org_id="test-org")

        # Session should be COMPLETED
        assert session.status == SessionStatus.COMPLETED

        # Verify persist was called (session moves to Supabase after completion)
        mock_supabase.table.assert_called()
        # The returned session from run() should have COMPLETED status
        assert session.session_id is not None

    @pytest.mark.asyncio
    async def test_run_tracks_token_usage(self, agent_runner, mock_anthropic_client):
        """Test that token usage is accumulated across steps."""
        mock_anthropic_client.messages.create.side_effect = [
            MagicMock(
                content=[MagicMock(text=json.dumps({
                    "thought": "Step 1",
                    "action": {"tool_name": "calculator", "arguments": {"expression": "1+1"}}
                }))],
                usage=MagicMock(input_tokens=100, output_tokens=50),
            ),
            MagicMock(
                content=[MagicMock(text=json.dumps({
                    "thought": "Done",
                    "is_final": True,
                    "final_answer": "2"
                }))],
                usage=MagicMock(input_tokens=200, output_tokens=100),
            ),
        ]

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Calculate"}],
        )

        session = await agent_runner.run(request, org_id="test-org")

        # Total should be accumulated
        assert session.input_tokens == 300  # 100 + 200
        assert session.output_tokens == 150  # 50 + 100


# ============================================================================
# TestOpenRouterIntegration
# ============================================================================


class TestOpenRouterIntegration:
    """Test OpenRouter integration for cost-optimized inference."""

    @pytest.mark.asyncio
    async def test_run_with_deepseek_model(self, agent_runner, mock_openrouter_client):
        """Test running with DeepSeek model via OpenRouter."""
        # Mock OpenRouter response format
        mock_openrouter_client.post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "thought": "DeepSeek processing",
                            "is_final": True,
                            "final_answer": "Processed by DeepSeek"
                        })
                    }
                }],
                "usage": {"prompt_tokens": 50, "completion_tokens": 25}
            },
            status_code=200,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="deepseek/deepseek-chat",
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        # Verify OpenRouter was called, not Anthropic
        mock_openrouter_client.post.assert_called()

    @pytest.mark.asyncio
    async def test_run_with_qwen_model(self, agent_runner, mock_openrouter_client):
        """Test running with Qwen model via OpenRouter."""
        mock_openrouter_client.post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "thought": "Qwen processing",
                            "is_final": True,
                            "final_answer": "Processed by Qwen"
                        })
                    }
                }],
                "usage": {"prompt_tokens": 60, "completion_tokens": 30}
            },
            status_code=200,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="qwen/qwen-2.5-72b-instruct",
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cost_calculation_openrouter(self, agent_runner, mock_openrouter_client):
        """Test that cost is calculated correctly for OpenRouter models."""
        mock_openrouter_client.post.return_value = MagicMock(
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "thought": "Done",
                            "is_final": True,
                            "final_answer": "Done"
                        })
                    }
                }],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 500}
            },
            status_code=200,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="deepseek/deepseek-chat",
        )

        session = await agent_runner.run(request, org_id="test-org")

        # DeepSeek is ~10x cheaper than Claude
        # Verify cost is calculated (exact value depends on pricing)
        assert session.total_cost_usd >= 0
        assert session.input_tokens == 1000
        assert session.output_tokens == 500


# ============================================================================
# TestErrorHandling
# ============================================================================


class TestErrorHandling:
    """Test error handling in the runner."""

    @pytest.mark.asyncio
    async def test_run_sets_failed_status_on_error(self, agent_runner, mock_anthropic_client):
        """Test that errors during run set FAILED status."""
        # Mock LLM to raise an exception
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.FAILED

    @pytest.mark.asyncio
    async def test_run_persists_on_failure(self, agent_runner, mock_anthropic_client, mock_supabase):
        """Test that failed sessions are persisted to Supabase."""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        session = await agent_runner.run(request, org_id="test-org")

        # Verify persist was called (via Supabase mock)
        mock_supabase.table.assert_called()

    @pytest.mark.asyncio
    async def test_cancelled_session_stops_loop(self, agent_runner, mock_anthropic_client, state_manager):
        """Test that cancelling a session stops the execution loop."""
        # Mock LLM with a tool call response
        call_count = 0

        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # After first call, simulate session being cancelled
            if call_count == 1:
                # Get the session and cancel it
                sessions = await state_manager._redis.keys("session:*")
                if sessions:
                    session_key = sessions[0]
                    session_data = await state_manager._redis.get(session_key)
                    if session_data:
                        session = AgentSession.model_validate_json(session_data)
                        session.status = SessionStatus.CANCELLED
                        await state_manager.update_session(session)

            return MagicMock(
                content=[MagicMock(text=json.dumps({
                    "thought": "Processing",
                    "action": {"tool_name": "calculator", "arguments": {"expression": "1+1"}}
                }))],
                usage=MagicMock(input_tokens=100, output_tokens=50),
            )

        mock_anthropic_client.messages.create = mock_create

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Keep going"}],
            max_steps=10,
        )

        session = await agent_runner.run(request, org_id="test-org")

        # Session should be cancelled and stopped early
        assert session.status == SessionStatus.CANCELLED
        assert len(session.steps) < 10  # Stopped before max

    @pytest.mark.asyncio
    async def test_openrouter_error_handling(self, agent_runner, mock_openrouter_client):
        """Test handling OpenRouter API errors."""
        mock_openrouter_client.post.side_effect = Exception("OpenRouter API unavailable")

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="deepseek/deepseek-chat",
        )

        session = await agent_runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.FAILED
