"""Tests for FastAPI endpoints - Agent orchestration API.

TDD Red Phase: All tests written BEFORE implementation.
Uses FastAPI TestClient with dependency overrides.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
# Mock Tool for Testing
# ============================================================================


class MockTestTool(BaseTool):
    """A simple mock tool for API testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="test_tool",
            description="A test tool for API testing",
            parameters={
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Test input"}
                },
                "required": ["input"],
            },
            category=ToolCategory.DATA,
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        return ToolResult(
            tool_name="test_tool",
            success=True,
            result="test output",
            execution_time_ms=1,
        )


class MockWebTool(BaseTool):
    """A mock web tool for category filtering tests."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_tool",
            description="A web tool for testing",
            parameters={"type": "object", "properties": {}},
            category=ToolCategory.WEB,
            requires_approval=True,
        )

    async def run(self, arguments: dict) -> ToolResult:
        return ToolResult(
            tool_name="web_tool",
            success=True,
            result="web result",
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
    mock.single = MagicMock(return_value=mock)
    mock.execute = MagicMock(return_value=MagicMock(data=None))
    return mock


@pytest.fixture
def mock_state_manager(mock_redis, mock_supabase):
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
def mock_tool_registry():
    """Create a tool registry with test tools."""
    registry = ToolRegistry()
    registry.clear()
    registry.register(MockTestTool())
    registry.register(MockWebTool())
    return registry


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock = MagicMock()
    mock.messages = MagicMock()
    mock.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text=json.dumps({
            "thought": "Test response",
            "is_final": True,
            "final_answer": "Test answer"
        }))],
        usage=MagicMock(input_tokens=100, output_tokens=50),
    ))
    return mock


@pytest.fixture
def mock_openrouter_client():
    """Create a mock OpenRouter client."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def test_client(mock_state_manager, mock_tool_registry, mock_anthropic_client, mock_openrouter_client):
    """Create FastAPI test client with dependency overrides."""
    from src.api import app, get_state_manager, get_tool_registry, get_anthropic_client, get_openrouter_client

    # Override dependencies
    app.dependency_overrides[get_state_manager] = lambda: mock_state_manager
    app.dependency_overrides[get_tool_registry] = lambda: mock_tool_registry
    app.dependency_overrides[get_anthropic_client] = lambda: mock_anthropic_client
    app.dependency_overrides[get_openrouter_client] = lambda: mock_openrouter_client

    client = TestClient(app)
    yield client

    # Clean up overrides
    app.dependency_overrides.clear()


# ============================================================================
# TestRunEndpoint
# ============================================================================


class TestRunEndpoint:
    """Test POST /agents/run endpoint."""

    def test_post_agents_run_returns_session_id(self, test_client):
        """Test that running an agent returns a session ID."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "claude-sonnet-4-5-20250929",
            },
            headers={"X-Org-ID": "test-org"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_post_agents_run_validates_messages(self, test_client):
        """Test that empty messages returns 422."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [],  # Empty messages
                "model": "claude-sonnet-4-5-20250929",
            },
            headers={"X-Org-ID": "test-org"},
        )

        assert response.status_code == 422

    def test_post_agents_run_validates_tools_exist(self, test_client):
        """Test that non-existent tools returns 400."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "tools": ["nonexistent_tool"],
            },
            headers={"X-Org-ID": "test-org"},
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_post_agents_run_starts_background_task(self, test_client):
        """Test that run starts execution (returns 202 Accepted)."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"X-Org-ID": "test-org"},
        )

        # 202 indicates async processing started
        assert response.status_code == 202
        data = response.json()
        assert data["status"] in ["pending", "running"]

    def test_post_agents_run_returns_poll_url(self, test_client):
        """Test that response includes poll URL."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"X-Org-ID": "test-org"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "poll_url" in data
        assert "/agents/" in data["poll_url"]

    def test_post_agents_run_requires_org_id(self, test_client):
        """Test that missing X-Org-ID header returns 400."""
        response = test_client.post(
            "/agents/run",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
            # No X-Org-ID header
        )

        assert response.status_code == 400


# ============================================================================
# TestPollEndpoint
# ============================================================================


class TestPollEndpoint:
    """Test GET /agents/{session_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_session_returns_steps(self, test_client, mock_state_manager):
        """Test that polling returns session steps."""
        # Create a session with steps
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        step = AgentStep(
            thought="Test thought",
            is_final=True,
            final_answer="Test answer",
        )
        await mock_state_manager.add_step(session.session_id, step)

        response = test_client.get(f"/agents/{session.session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert len(data["steps"]) >= 1

    @pytest.mark.asyncio
    async def test_get_session_includes_status(self, test_client, mock_state_manager):
        """Test that polling includes session status."""
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.RUNNING
        await mock_state_manager.update_session(session)

        response = test_client.get(f"/agents/{session.session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"

    def test_get_session_not_found_404(self, test_client):
        """Test that non-existent session returns 404."""
        response = test_client.get("/agents/nonexistent-session-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_session_includes_final_answer(self, test_client, mock_state_manager):
        """Test that completed session includes final answer."""
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        step = AgentStep(
            thought="Final thought",
            is_final=True,
            final_answer="The answer is 42",
        )
        session.steps.append(step)
        session.status = SessionStatus.COMPLETED
        await mock_state_manager.update_session(session)

        response = test_client.get(f"/agents/{session.session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert any(s.get("final_answer") for s in data["steps"])


# ============================================================================
# TestCancelEndpoint
# ============================================================================


class TestCancelEndpoint:
    """Test POST /agents/{session_id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_running_session(self, test_client, mock_state_manager):
        """Test cancelling a running session."""
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.RUNNING
        await mock_state_manager.update_session(session)

        response = test_client.post(f"/agents/{session.session_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_idempotent(self, test_client, mock_state_manager):
        """Test that cancelling already cancelled session is idempotent."""
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.CANCELLED
        await mock_state_manager.update_session(session)

        response = test_client.post(f"/agents/{session.session_id}/cancel")

        # Should return 200 (idempotent)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_returns_409(self, test_client, mock_state_manager):
        """Test that cancelling completed session returns 409 Conflict."""
        session = await mock_state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.COMPLETED
        await mock_state_manager.update_session(session)

        response = test_client.post(f"/agents/{session.session_id}/cancel")

        assert response.status_code == 409
        assert "cannot cancel" in response.json()["detail"].lower()

    def test_cancel_not_found_404(self, test_client):
        """Test that cancelling non-existent session returns 404."""
        response = test_client.post("/agents/nonexistent-session-id/cancel")

        assert response.status_code == 404


# ============================================================================
# TestToolsEndpoint
# ============================================================================


class TestToolsEndpoint:
    """Test GET /tools endpoint."""

    def test_list_tools_returns_all(self, test_client):
        """Test that listing tools returns all registered tools."""
        response = test_client.get("/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        tool_names = [t["name"] for t in data["tools"]]
        assert "test_tool" in tool_names
        assert "web_tool" in tool_names

    def test_list_tools_filter_by_category(self, test_client):
        """Test filtering tools by category."""
        response = test_client.get("/tools?category=web")

        assert response.status_code == 200
        data = response.json()
        assert all(t["category"] == "web" for t in data["tools"])

    def test_tools_include_parameters_schema(self, test_client):
        """Test that tool listing includes parameter schemas."""
        response = test_client.get("/tools")

        assert response.status_code == 200
        data = response.json()
        for tool in data["tools"]:
            assert "parameters" in tool
            assert "type" in tool["parameters"]


# ============================================================================
# TestHealthEndpoint
# ============================================================================


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_returns_ok(self, test_client):
        """Test that health check returns ok."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
