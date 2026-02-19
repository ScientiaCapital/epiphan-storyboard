"""Tests for ConductorClient HTTP client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.sdk.client import (
    ConductorClient,
    AgentSessionResponse,
    ToolInfo,
    ConductorClientError,
    SessionNotFoundError,
    ToolNotFoundError,
    SessionConflictError,
)


def make_mock_response(status_code: int, json_data: dict):
    """Helper to create a mock HTTP response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


class TestConductorClientInit:
    """Tests for ConductorClient initialization."""

    def test_init_with_defaults(self):
        """Client initializes with required args."""
        client = ConductorClient("http://localhost:8000", "test-org")
        assert client.base_url == "http://localhost:8000"
        assert client.org_id == "test-org"
        assert client.timeout == 60.0

    def test_init_with_custom_timeout(self):
        """Client accepts custom timeout."""
        client = ConductorClient("http://localhost:8000", "org", timeout=120.0)
        assert client.timeout == 120.0

    def test_init_strips_trailing_slash(self):
        """Base URL trailing slash is stripped."""
        client = ConductorClient("http://localhost:8000/", "org")
        assert client.base_url == "http://localhost:8000"


class TestConductorClientRunAgent:
    """Tests for run_agent method."""

    @pytest.mark.asyncio
    async def test_run_agent_success(self):
        """run_agent returns session on success."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(202, {
            "session_id": "sess-123",
            "status": "pending",
            "poll_url": "/agents/sess-123",
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            session = await client.run_agent(
                messages=[{"role": "user", "content": "Hello"}],
                tools=["web_fetch"],
            )

            assert session.session_id == "sess-123"
            assert session.status == "pending"
            assert session.poll_url == "/agents/sess-123"

    @pytest.mark.asyncio
    async def test_run_agent_tool_not_found(self):
        """run_agent raises ToolNotFoundError for missing tool."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(400, {
            "detail": "Tool 'nonexistent' not found in registry"
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(ToolNotFoundError, match="nonexistent"):
                await client.run_agent(
                    messages=[{"role": "user", "content": "Hello"}],
                    tools=["nonexistent"],
                )


class TestConductorClientGetSession:
    """Tests for get_session method."""

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """get_session returns session details."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(200, {
            "session_id": "sess-123",
            "status": "completed",
            "steps": [{"thought": "Thinking...", "is_final": True, "final_answer": "Done"}],
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost_usd": 0.001,
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            session = await client.get_session("sess-123")

            assert session.session_id == "sess-123"
            assert session.status == "completed"
            assert len(session.steps) == 1
            assert session.input_tokens == 100
            assert session.total_cost_usd == 0.001

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """get_session raises SessionNotFoundError."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(404, {})

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(SessionNotFoundError, match="sess-999"):
                await client.get_session("sess-999")


class TestConductorClientCancelSession:
    """Tests for cancel_session method."""

    @pytest.mark.asyncio
    async def test_cancel_session_success(self):
        """cancel_session returns cancelled status."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(200, {
            "session_id": "sess-123",
            "status": "cancelled",
            "message": "Session cancelled successfully",
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            session = await client.cancel_session("sess-123")
            assert session.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_session_conflict(self):
        """cancel_session raises SessionConflictError for completed session."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(409, {
            "detail": "Cannot cancel session with status 'completed'"
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            with pytest.raises(SessionConflictError):
                await client.cancel_session("sess-123")


class TestConductorClientListTools:
    """Tests for list_tools method."""

    @pytest.mark.asyncio
    async def test_list_tools_success(self):
        """list_tools returns tool info."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(200, {
            "tools": [
                {
                    "name": "web_fetch",
                    "description": "Fetch web pages",
                    "category": "web",
                    "parameters": {},
                    "requires_approval": False,
                },
                {
                    "name": "code_run",
                    "description": "Run code",
                    "category": "code",
                    "parameters": {},
                    "requires_approval": True,
                },
            ]
        })

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            tools = await client.list_tools()

            assert len(tools) == 2
            assert tools[0].name == "web_fetch"
            assert tools[1].requires_approval is True


class TestConductorClientHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """health_check returns True when healthy."""
        client = ConductorClient("http://localhost:8000", "test-org")
        mock_response = make_mock_response(200, {"status": "healthy"})

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_http

            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """health_check returns False on error."""
        client = ConductorClient("http://localhost:8000", "test-org")

        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_get.return_value = mock_http

            assert await client.health_check() is False


class TestConductorClientContextManager:
    """Tests for context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        async with ConductorClient("http://localhost:8000", "test-org") as client:
            assert client.org_id == "test-org"
        # Client should be closed after context
