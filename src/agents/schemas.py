"""Pydantic v2 schemas for agent orchestration system.

This module defines the core data models for the agent system including:
- Session management and status tracking
- Tool calls and agent reasoning steps
- Request/response models for agent execution
- Token usage and cost tracking
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class SessionStatus(str, Enum):
    """Status of an agent session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCall(BaseModel):
    """Represents a tool invocation by the agent.

    Attributes:
        tool_name: Name of the tool to invoke
        arguments: Dictionary of arguments to pass to the tool
    """

    tool_name: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments to pass to the tool"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name is not empty."""
        if not v or not v.strip():
            raise ValueError("tool_name cannot be empty")
        return v.strip()


class AgentStep(BaseModel):
    """Represents a single step in the agent's reasoning process.

    Each step includes the agent's thought process, an optional tool call action,
    the observation from executing that action, and potentially a final answer.

    Attributes:
        thought: The agent's reasoning about what to do next
        action: Optional tool call to execute
        observation: Result from executing the action (if any)
        is_final: Whether this step contains the final answer
        final_answer: The final answer to the user's query (only when is_final=True)
    """

    thought: str = Field(..., description="The agent's reasoning")
    action: ToolCall | None = Field(
        None, description="Optional tool call to execute"
    )
    observation: str | None = Field(
        None, description="Result from tool execution"
    )
    is_final: bool = Field(
        default=False, description="True if this is the final answer"
    )
    final_answer: str | None = Field(
        None, description="Final answer when is_final=True"
    )

    @model_validator(mode="after")
    def validate_final_answer(self) -> "AgentStep":
        """Validate that final_answer is set when is_final=True."""
        if self.is_final and not self.final_answer:
            raise ValueError("final_answer must be set when is_final=True")
        if not self.is_final and self.final_answer:
            raise ValueError("final_answer should only be set when is_final=True")
        return self


class AgentSession(BaseModel):
    """Represents a complete agent execution session.

    Tracks the full lifecycle of an agent run including all reasoning steps,
    token usage, costs, and timestamps.

    Attributes:
        session_id: Unique identifier for this session
        org_id: Organization identifier
        status: Current session status
        steps: List of reasoning steps taken by the agent
        input_tokens: Total input tokens consumed
        output_tokens: Total output tokens generated
        total_cost_usd: Total cost in USD for this session
        created_at: When the session was created
        updated_at: When the session was last updated
    """

    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session identifier",
    )
    org_id: str = Field(..., description="Organization identifier")
    status: SessionStatus = Field(
        default=SessionStatus.PENDING, description="Current session status"
    )
    steps: list[AgentStep] = Field(
        default_factory=list, description="Agent reasoning steps"
    )
    input_tokens: int = Field(
        default=0, ge=0, description="Total input tokens consumed"
    )
    output_tokens: int = Field(
        default=0, ge=0, description="Total output tokens generated"
    )
    total_cost_usd: float = Field(
        default=0.0, ge=0.0, description="Total cost in USD"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation time",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update time",
    )

    @field_validator("org_id")
    @classmethod
    def validate_org_id(cls, v: str) -> str:
        """Validate org_id is not empty."""
        if not v or not v.strip():
            raise ValueError("org_id cannot be empty")
        return v.strip()


class AgentRunRequest(BaseModel):
    """Request to run an agent with specific configuration.

    Attributes:
        messages: Conversation history in OpenAI format
        model: Model identifier to use
        tools: Optional list of tool names to enable
        max_steps: Maximum number of reasoning steps allowed
    """

    messages: list[dict[str, Any]] = Field(
        ..., description="Conversation history", min_length=1
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Model identifier",
    )
    tools: list[str] | None = Field(
        None, description="Tool names to enable"
    )
    max_steps: int = Field(
        default=10, ge=1, le=100, description="Maximum reasoning steps"
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate messages have required fields."""
        for i, msg in enumerate(v):
            if "role" not in msg:
                raise ValueError(f"Message {i} missing 'role' field")
            if "content" not in msg:
                raise ValueError(f"Message {i} missing 'content' field")
            if msg["role"] not in ("user", "assistant", "system"):
                raise ValueError(
                    f"Message {i} has invalid role: {msg['role']}"
                )
        return v


class AgentRunResponse(BaseModel):
    """Response from initiating an agent run.

    Attributes:
        session_id: Unique identifier for the created session
        status: Initial session status
        poll_url: URL to poll for session updates
    """

    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(..., description="Session status")
    poll_url: str = Field(..., description="URL to poll for updates")

    @field_validator("poll_url")
    @classmethod
    def validate_poll_url(cls, v: str) -> str:
        """Validate poll_url is not empty."""
        if not v or not v.strip():
            raise ValueError("poll_url cannot be empty")
        return v.strip()
