"""Tests for agent orchestration schemas."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.agents.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentSession,
    AgentStep,
    SessionStatus,
    ToolCall,
)


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_all_status_values(self):
        """Test all status enum values exist."""
        assert SessionStatus.PENDING == "pending"
        assert SessionStatus.RUNNING == "running"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.FAILED == "failed"
        assert SessionStatus.CANCELLED == "cancelled"

    def test_status_values_are_strings(self):
        """Test that status values are strings."""
        for status in SessionStatus:
            assert isinstance(status.value, str)

    def test_status_from_string(self):
        """Test creating status from string."""
        assert SessionStatus("pending") == SessionStatus.PENDING
        assert SessionStatus("running") == SessionStatus.RUNNING


class TestToolCall:
    """Tests for ToolCall schema."""

    def test_create_tool_call_minimal(self):
        """Test creating tool call with minimal data."""
        tool_call = ToolCall(tool_name="search")
        assert tool_call.tool_name == "search"
        assert tool_call.arguments == {}

    def test_create_tool_call_with_arguments(self):
        """Test creating tool call with arguments."""
        tool_call = ToolCall(
            tool_name="search",
            arguments={"query": "test", "limit": 10},
        )
        assert tool_call.tool_name == "search"
        assert tool_call.arguments == {"query": "test", "limit": 10}

    def test_tool_call_serialization(self):
        """Test serializing tool call to dict."""
        tool_call = ToolCall(
            tool_name="calculator",
            arguments={"operation": "add", "x": 5, "y": 3},
        )
        data = tool_call.model_dump()
        assert data["tool_name"] == "calculator"
        assert data["arguments"] == {"operation": "add", "x": 5, "y": 3}

    def test_tool_call_json_serialization(self):
        """Test serializing tool call to JSON."""
        tool_call = ToolCall(
            tool_name="search",
            arguments={"query": "test"},
        )
        json_str = tool_call.model_dump_json()
        assert "search" in json_str
        assert "test" in json_str

    def test_tool_name_cannot_be_empty(self):
        """Test that tool_name cannot be empty string."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCall(tool_name="")
        assert "tool_name cannot be empty" in str(exc_info.value)

    def test_tool_name_whitespace_trimmed(self):
        """Test that tool_name whitespace is trimmed."""
        tool_call = ToolCall(tool_name="  search  ")
        assert tool_call.tool_name == "search"

    def test_tool_name_only_whitespace_fails(self):
        """Test that tool_name with only whitespace fails."""
        with pytest.raises(ValidationError) as exc_info:
            ToolCall(tool_name="   ")
        assert "tool_name cannot be empty" in str(exc_info.value)


class TestAgentStep:
    """Tests for AgentStep schema."""

    def test_create_step_minimal(self):
        """Test creating step with minimal required data."""
        step = AgentStep(thought="I need to search for information")
        assert step.thought == "I need to search for information"
        assert step.action is None
        assert step.observation is None
        assert step.is_final is False
        assert step.final_answer is None

    def test_create_step_with_action(self):
        """Test creating step with tool action."""
        step = AgentStep(
            thought="I'll search for the answer",
            action=ToolCall(tool_name="search", arguments={"query": "test"}),
        )
        assert step.thought == "I'll search for the answer"
        assert step.action is not None
        assert step.action.tool_name == "search"

    def test_create_step_with_observation(self):
        """Test creating step with observation."""
        step = AgentStep(
            thought="Let me analyze this",
            action=ToolCall(tool_name="search", arguments={"query": "test"}),
            observation="Found 10 results",
        )
        assert step.observation == "Found 10 results"

    def test_create_final_step(self):
        """Test creating final step with answer."""
        step = AgentStep(
            thought="I have enough information",
            is_final=True,
            final_answer="The answer is 42",
        )
        assert step.is_final is True
        assert step.final_answer == "The answer is 42"

    def test_final_step_requires_answer(self):
        """Test that is_final=True requires final_answer."""
        with pytest.raises(ValidationError) as exc_info:
            AgentStep(
                thought="Done",
                is_final=True,
            )
        assert "final_answer must be set when is_final=True" in str(exc_info.value)

    def test_final_answer_without_is_final_fails(self):
        """Test that final_answer without is_final=True fails."""
        with pytest.raises(ValidationError) as exc_info:
            AgentStep(
                thought="Not done yet",
                final_answer="Answer",
            )
        assert "final_answer should only be set when is_final=True" in str(
            exc_info.value
        )

    def test_step_serialization(self):
        """Test serializing step to dict."""
        step = AgentStep(
            thought="Thinking",
            action=ToolCall(tool_name="calc", arguments={"x": 1}),
            observation="Result: 1",
        )
        data = step.model_dump()
        assert data["thought"] == "Thinking"
        assert data["action"]["tool_name"] == "calc"
        assert data["observation"] == "Result: 1"
        assert data["is_final"] is False


class TestAgentSession:
    """Tests for AgentSession schema."""

    def test_create_session_minimal(self):
        """Test creating session with minimal required data."""
        session = AgentSession(org_id="org-123")
        assert session.org_id == "org-123"
        assert session.status == SessionStatus.PENDING
        assert session.steps == []
        assert session.input_tokens == 0
        assert session.output_tokens == 0
        assert session.total_cost_usd == 0.0

    def test_session_id_auto_generated(self):
        """Test that session_id is auto-generated as UUID."""
        session = AgentSession(org_id="org-123")
        # Should be valid UUID
        UUID(session.session_id)

    def test_session_id_unique(self):
        """Test that each session gets unique ID."""
        session1 = AgentSession(org_id="org-123")
        session2 = AgentSession(org_id="org-123")
        assert session1.session_id != session2.session_id

    def test_timestamps_auto_generated(self):
        """Test that timestamps are auto-generated."""
        session = AgentSession(org_id="org-123")
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_create_session_with_steps(self):
        """Test creating session with steps."""
        steps = [
            AgentStep(thought="Step 1"),
            AgentStep(thought="Step 2"),
        ]
        session = AgentSession(org_id="org-123", steps=steps)
        assert len(session.steps) == 2
        assert session.steps[0].thought == "Step 1"

    def test_create_session_with_token_counts(self):
        """Test creating session with token counts."""
        session = AgentSession(
            org_id="org-123",
            input_tokens=100,
            output_tokens=50,
            total_cost_usd=0.005,
        )
        assert session.input_tokens == 100
        assert session.output_tokens == 50
        assert session.total_cost_usd == 0.005

    def test_negative_tokens_not_allowed(self):
        """Test that negative token counts are not allowed."""
        with pytest.raises(ValidationError):
            AgentSession(org_id="org-123", input_tokens=-1)

    def test_negative_cost_not_allowed(self):
        """Test that negative cost is not allowed."""
        with pytest.raises(ValidationError):
            AgentSession(org_id="org-123", total_cost_usd=-0.01)

    def test_org_id_cannot_be_empty(self):
        """Test that org_id cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AgentSession(org_id="")
        assert "org_id cannot be empty" in str(exc_info.value)

    def test_org_id_whitespace_trimmed(self):
        """Test that org_id whitespace is trimmed."""
        session = AgentSession(org_id="  org-123  ")
        assert session.org_id == "org-123"

    def test_session_serialization(self):
        """Test serializing session to dict."""
        session = AgentSession(
            org_id="org-123",
            status=SessionStatus.COMPLETED,
            steps=[AgentStep(thought="Done", is_final=True, final_answer="42")],
        )
        data = session.model_dump()
        assert data["org_id"] == "org-123"
        assert data["status"] == "completed"
        assert len(data["steps"]) == 1


class TestAgentRunRequest:
    """Tests for AgentRunRequest schema."""

    def test_create_request_minimal(self):
        """Test creating request with minimal required data."""
        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert len(request.messages) == 1
        assert request.model == "claude-sonnet-4-5-20250929"
        assert request.tools is None
        assert request.max_steps == 10

    def test_create_request_with_custom_model(self):
        """Test creating request with custom model."""
        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-opus-4-20250514",
        )
        assert request.model == "claude-opus-4-20250514"

    def test_create_request_with_tools(self):
        """Test creating request with tools."""
        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            tools=["search", "calculator"],
        )
        assert request.tools == ["search", "calculator"]

    def test_create_request_with_max_steps(self):
        """Test creating request with custom max_steps."""
        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_steps=20,
        )
        assert request.max_steps == 20

    def test_messages_cannot_be_empty(self):
        """Test that messages list cannot be empty."""
        with pytest.raises(ValidationError):
            AgentRunRequest(messages=[])

    def test_messages_must_have_role(self):
        """Test that messages must have role field."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRunRequest(messages=[{"content": "Hello"}])
        assert "missing 'role' field" in str(exc_info.value)

    def test_messages_must_have_content(self):
        """Test that messages must have content field."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRunRequest(messages=[{"role": "user"}])
        assert "missing 'content' field" in str(exc_info.value)

    def test_messages_role_must_be_valid(self):
        """Test that message role must be valid."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRunRequest(
                messages=[{"role": "invalid", "content": "Hello"}]
            )
        assert "invalid role" in str(exc_info.value)

    def test_max_steps_must_be_positive(self):
        """Test that max_steps must be positive."""
        with pytest.raises(ValidationError):
            AgentRunRequest(
                messages=[{"role": "user", "content": "Hello"}],
                max_steps=0,
            )

    def test_max_steps_has_upper_limit(self):
        """Test that max_steps has upper limit."""
        with pytest.raises(ValidationError):
            AgentRunRequest(
                messages=[{"role": "user", "content": "Hello"}],
                max_steps=101,
            )

    def test_request_serialization(self):
        """Test serializing request to dict."""
        request = AgentRunRequest(
            messages=[{"role": "user", "content": "Hello"}],
            tools=["search"],
            max_steps=15,
        )
        data = request.model_dump()
        assert data["messages"] == [{"role": "user", "content": "Hello"}]
        assert data["tools"] == ["search"]
        assert data["max_steps"] == 15


class TestAgentRunResponse:
    """Tests for AgentRunResponse schema."""

    def test_create_response(self):
        """Test creating response."""
        response = AgentRunResponse(
            session_id="session-123",
            status=SessionStatus.PENDING,
            poll_url="/api/sessions/session-123",
        )
        assert response.session_id == "session-123"
        assert response.status == SessionStatus.PENDING
        assert response.poll_url == "/api/sessions/session-123"

    def test_poll_url_cannot_be_empty(self):
        """Test that poll_url cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            AgentRunResponse(
                session_id="session-123",
                status=SessionStatus.PENDING,
                poll_url="",
            )
        assert "poll_url cannot be empty" in str(exc_info.value)

    def test_poll_url_whitespace_trimmed(self):
        """Test that poll_url whitespace is trimmed."""
        response = AgentRunResponse(
            session_id="session-123",
            status=SessionStatus.PENDING,
            poll_url="  /api/sessions/session-123  ",
        )
        assert response.poll_url == "/api/sessions/session-123"

    def test_response_serialization(self):
        """Test serializing response to dict."""
        response = AgentRunResponse(
            session_id="session-123",
            status=SessionStatus.RUNNING,
            poll_url="/api/sessions/session-123",
        )
        data = response.model_dump()
        assert data["session_id"] == "session-123"
        assert data["status"] == "running"
        assert data["poll_url"] == "/api/sessions/session-123"

    def test_response_json_serialization(self):
        """Test serializing response to JSON."""
        response = AgentRunResponse(
            session_id="session-123",
            status=SessionStatus.COMPLETED,
            poll_url="/api/sessions/session-123",
        )
        json_str = response.model_dump_json()
        assert "session-123" in json_str
        assert "completed" in json_str
