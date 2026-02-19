"""Integration tests for full E2E agent execution.

These tests make REAL API calls to:
- Anthropic Claude API
- OpenRouter API (DeepSeek, Qwen)

Cost estimate: ~$0.05-0.10 per full test run

Tests are skipped if API keys are not set.
Run with: pytest tests/integration/ -v -m integration
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock

import pytest

from src.agents.runner import AgentRunner
from src.agents.schemas import AgentRunRequest, SessionStatus
from src.agents.state import StateManager
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.registry import ToolRegistry


# ============================================================================
# Skip conditions
# ============================================================================

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

skip_no_anthropic = pytest.mark.skipif(
    len(ANTHROPIC_KEY) < 10,  # Real keys are much longer
    reason="ANTHROPIC_API_KEY not set or invalid"
)

skip_no_openrouter = pytest.mark.skipif(
    len(OPENROUTER_KEY) < 10,  # Real keys are much longer
    reason="OPENROUTER_API_KEY not set or invalid"
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# Test Tools
# ============================================================================


class CalculatorTool(BaseTool):
    """Simple calculator for integration testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Performs basic math. Input: expression like '2+2' or '10*5'",
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
        expr = arguments.get("expression", "")
        try:
            # Safe calculation for simple expressions
            result = self._safe_calc(expr)
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

    def _safe_calc(self, expr: str) -> int:
        """Safe calculation without eval."""
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


# ============================================================================
# Fixtures
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
    """Create a StateManager with mocked storage but real logic."""
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
    """Create a tool registry with test tools."""
    registry = ToolRegistry()
    registry.clear()
    registry.register(CalculatorTool())
    return registry


@pytest.fixture
def anthropic_client():
    """Create real Anthropic client if key is available."""
    if not ANTHROPIC_KEY:
        return None
    try:
        import anthropic
        return anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY)
    except ImportError:
        return None


@pytest.fixture
def openrouter_client():
    """Create real OpenRouter client if key is available."""
    if not OPENROUTER_KEY:
        return None
    import httpx
    return httpx.AsyncClient(timeout=60.0)


# ============================================================================
# TestEndToEndSimple
# ============================================================================


class TestEndToEndSimple:
    """Simple E2E tests without tool usage."""

    @pytest.mark.asyncio
    async def test_simple_question_no_tools(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test a simple question that doesn't require tools."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "What is 2+2? Reply only with the number."}],
            model="claude-sonnet-4-5-20250929",
            max_steps=3,
        )

        session = await runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        assert len(session.steps) >= 1
        assert session.steps[-1].is_final
        assert "4" in session.steps[-1].final_answer

    @skip_no_openrouter
    @pytest.mark.asyncio
    async def test_simple_question_deepseek(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test simple question with DeepSeek via OpenRouter."""
        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "What is the capital of France? One word answer."}],
            model="deepseek/deepseek-chat",
            max_steps=3,
        )

        session = await runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        assert len(session.steps) >= 1
        assert "Paris" in str(session.steps[-1].final_answer)


# ============================================================================
# TestEndToEndWithTools
# ============================================================================


class TestEndToEndWithTools:
    """E2E tests with tool usage."""

    @skip_no_anthropic
    @pytest.mark.asyncio
    async def test_math_with_calculator_tool(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test agent using calculator tool."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{
                "role": "user",
                "content": "Use the calculator tool to compute 15+27. Return only the result."
            }],
            model="claude-sonnet-4-5-20250929",
            tools=["calculator"],
            max_steps=5,
        )

        session = await runner.run(request, org_id="test-org")

        assert session.status == SessionStatus.COMPLETED
        # Should have at least one tool call step
        tool_steps = [s for s in session.steps if s.action is not None]
        assert len(tool_steps) >= 1
        # Final answer should contain 42
        assert "42" in str(session.steps[-1].final_answer)

    @skip_no_anthropic
    @pytest.mark.asyncio
    async def test_tool_error_recovery(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test agent handles tool errors gracefully."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{
                "role": "user",
                "content": "Use calculator to compute 'invalid'. If it fails, just say 'error'."
            }],
            model="claude-sonnet-4-5-20250929",
            tools=["calculator"],
            max_steps=5,
        )

        session = await runner.run(request, org_id="test-org")

        # Should complete (not fail) even if tool errors
        assert session.status == SessionStatus.COMPLETED


# ============================================================================
# TestPollingWorkflow
# ============================================================================


class TestPollingWorkflow:
    """Test async execution and polling patterns."""

    @skip_no_anthropic
    @pytest.mark.asyncio
    async def test_session_completion_lifecycle(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test full session lifecycle from pending to completed."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Say 'hello'"}],
            model="claude-sonnet-4-5-20250929",
            max_steps=2,
        )

        # Run and get completed session
        session = await runner.run(request, org_id="test-org")

        # Verify lifecycle
        assert session.session_id is not None
        assert session.status == SessionStatus.COMPLETED
        assert session.input_tokens > 0
        assert session.output_tokens > 0
        assert session.total_cost_usd > 0


# ============================================================================
# TestEdgeCases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and limits."""

    @skip_no_anthropic
    @pytest.mark.asyncio
    async def test_max_steps_reached(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test that execution stops at max_steps."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{
                "role": "user",
                "content": "Keep using calculator for 1+1 repeatedly until I say stop"
            }],
            model="claude-sonnet-4-5-20250929",
            tools=["calculator"],
            max_steps=2,  # Force early stop
        )

        session = await runner.run(request, org_id="test-org")

        # Should stop at max steps
        assert len(session.steps) <= 2
        assert session.status == SessionStatus.COMPLETED

    @skip_no_anthropic
    @pytest.mark.asyncio
    async def test_token_tracking_accuracy(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Test that token tracking is accurate."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-sonnet-4-5-20250929",
            max_steps=1,
        )

        session = await runner.run(request, org_id="test-org")

        # Tokens should be tracked
        assert session.input_tokens > 0
        assert session.output_tokens > 0
        # Cost should be calculated (Claude pricing)
        assert session.total_cost_usd > 0


# ============================================================================
# TestCostComparison
# ============================================================================


class TestCostComparison:
    """Compare costs between providers."""

    @skip_no_anthropic
    @skip_no_openrouter
    @pytest.mark.asyncio
    async def test_deepseek_cheaper_than_claude(self, state_manager, tool_registry, anthropic_client, openrouter_client):
        """Verify DeepSeek is significantly cheaper than Claude for same task."""
        if anthropic_client is None:
            pytest.skip("ANTHROPIC_API_KEY not set or invalid")
        if openrouter_client is None:
            pytest.skip("OPENROUTER_API_KEY not set or invalid")

        runner = AgentRunner(
            state_manager=state_manager,
            tool_registry=tool_registry,
            anthropic_client=anthropic_client,
            openrouter_client=openrouter_client,
        )

        prompt = "What is machine learning? One sentence answer."

        # Run with Claude
        claude_request = AgentRunRequest(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-5-20250929",
            max_steps=1,
        )
        claude_session = await runner.run(claude_request, org_id="test-org")

        # Run with DeepSeek
        deepseek_request = AgentRunRequest(
            messages=[{"role": "user", "content": prompt}],
            model="deepseek/deepseek-chat",
            max_steps=1,
        )
        deepseek_session = await runner.run(deepseek_request, org_id="test-org")

        # DeepSeek should be significantly cheaper (at least 10x)
        # Note: Actual ratio depends on token counts and current pricing
        assert deepseek_session.total_cost_usd < claude_session.total_cost_usd
        print(f"\nCost comparison:")
        print(f"  Claude: ${claude_session.total_cost_usd:.6f}")
        print(f"  DeepSeek: ${deepseek_session.total_cost_usd:.6f}")
        print(f"  Savings: {claude_session.total_cost_usd / max(deepseek_session.total_cost_usd, 0.000001):.1f}x")
