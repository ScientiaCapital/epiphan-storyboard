"""HTTP client for interacting with conductor-ai API.

Provides async methods for:
- Running agents with specific tools
- Polling session status
- Cancelling sessions
- Listing available tools

Usage:
    from conductor_ai.sdk import ConductorClient

    client = ConductorClient(
        base_url="http://localhost:8000",
        org_id="my-org",
    )

    # Start an agent run
    session = await client.run_agent(
        messages=[{"role": "user", "content": "Fetch https://example.com"}],
        tools=["web_fetch"],
    )
    print(f"Started session: {session.session_id}")

    # Poll until complete
    while session.status in ("pending", "running"):
        await asyncio.sleep(1)
        session = await client.get_session(session.session_id)

    # Get final answer
    if session.status == "completed":
        final_step = session.steps[-1]
        print(f"Answer: {final_step['final_answer']}")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx


class SessionStatus(str, Enum):
    """Session status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentSessionResponse:
    """Response from get_session or run_agent.

    Attributes:
        session_id: Unique session identifier
        status: Current session status
        steps: List of reasoning steps (thought, action, observation)
        input_tokens: Total input tokens consumed
        output_tokens: Total output tokens generated
        total_cost_usd: Total cost in USD
        poll_url: URL to poll for updates (only on run_agent)
    """

    session_id: str
    status: str
    steps: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    poll_url: str | None = None


@dataclass
class ToolInfo:
    """Information about an available tool.

    Attributes:
        name: Tool name (e.g., "web_fetch")
        description: What the tool does
        category: Tool category (web, data, code, etc.)
        parameters: JSON Schema for tool arguments
        requires_approval: Whether execution needs user approval
    """

    name: str
    description: str
    category: str
    parameters: dict[str, Any]
    requires_approval: bool


class ConductorClientError(Exception):
    """Base exception for ConductorClient errors."""

    pass


class SessionNotFoundError(ConductorClientError):
    """Session with given ID was not found."""

    pass


class ToolNotFoundError(ConductorClientError):
    """Requested tool not found in registry."""

    pass


class SessionConflictError(ConductorClientError):
    """Cannot perform operation on session (e.g., cancel completed session)."""

    pass


class ConductorClient:
    """Async HTTP client for conductor-ai API.

    Thread-safe and supports connection pooling via httpx.

    Args:
        base_url: Base URL of conductor-ai API (e.g., "http://localhost:8000")
        org_id: Organization ID for multi-tenant isolation
        timeout: Request timeout in seconds (default: 60)
    """

    def __init__(
        self,
        base_url: str,
        org_id: str,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API base URL
            org_id: Organization identifier (required for all requests)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"X-Org-ID": self.org_id},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client.

        Call this when you're done using the client to release resources.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ConductorClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit."""
        await self.close()

    async def run_agent(
        self,
        messages: list[dict[str, Any]],
        tools: list[str] | None = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_steps: int = 10,
    ) -> AgentSessionResponse:
        """Start an agent execution.

        Returns immediately with session ID. Use get_session() to poll for results.

        Args:
            messages: Conversation history in OpenAI format
                      e.g., [{"role": "user", "content": "Hello"}]
            tools: List of tool names to enable (None for all)
            model: Model identifier (default: claude-sonnet-4.5)
            max_steps: Maximum reasoning steps (default: 10)

        Returns:
            AgentSessionResponse with session_id and poll_url

        Raises:
            ToolNotFoundError: If a requested tool doesn't exist
            ConductorClientError: For other API errors
        """
        client = await self._get_client()

        payload = {
            "messages": messages,
            "model": model,
            "max_steps": max_steps,
        }
        if tools:
            payload["tools"] = tools

        response = await client.post("/agents/run", json=payload)

        if response.status_code == 400:
            error = response.json().get("detail", "Bad request")
            if "not found in registry" in error:
                raise ToolNotFoundError(error)
            raise ConductorClientError(error)

        if response.status_code == 422:
            raise ConductorClientError(f"Validation error: {response.json()}")

        response.raise_for_status()
        data = response.json()

        return AgentSessionResponse(
            session_id=data["session_id"],
            status=data["status"],
            steps=[],
            input_tokens=0,
            output_tokens=0,
            total_cost_usd=0.0,
            poll_url=data["poll_url"],
        )

    async def get_session(self, session_id: str) -> AgentSessionResponse:
        """Get session status and steps.

        Use this to poll for completion after run_agent().

        Args:
            session_id: Session ID from run_agent()

        Returns:
            AgentSessionResponse with current status and steps

        Raises:
            SessionNotFoundError: If session doesn't exist
            ConductorClientError: For other API errors
        """
        client = await self._get_client()

        response = await client.get(f"/agents/{session_id}")

        if response.status_code == 404:
            raise SessionNotFoundError(f"Session '{session_id}' not found")

        response.raise_for_status()
        data = response.json()

        return AgentSessionResponse(
            session_id=data["session_id"],
            status=data["status"],
            steps=data["steps"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            total_cost_usd=data["total_cost_usd"],
        )

    async def cancel_session(self, session_id: str) -> AgentSessionResponse:
        """Cancel a running session.

        Idempotent for already cancelled sessions.

        Args:
            session_id: Session ID to cancel

        Returns:
            AgentSessionResponse with cancelled status

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionConflictError: If session is already completed/failed
            ConductorClientError: For other API errors
        """
        client = await self._get_client()

        response = await client.post(f"/agents/{session_id}/cancel")

        if response.status_code == 404:
            raise SessionNotFoundError(f"Session '{session_id}' not found")

        if response.status_code == 409:
            error = response.json().get("detail", "Cannot cancel")
            raise SessionConflictError(error)

        response.raise_for_status()
        data = response.json()

        return AgentSessionResponse(
            session_id=data["session_id"],
            status=data["status"],
            steps=[],
            input_tokens=0,
            output_tokens=0,
            total_cost_usd=0.0,
        )

    async def list_tools(
        self,
        category: str | None = None,
    ) -> list[ToolInfo]:
        """List available tools.

        Args:
            category: Optional filter by category (web, data, code, etc.)

        Returns:
            List of ToolInfo objects

        Raises:
            ConductorClientError: For API errors
        """
        client = await self._get_client()

        params = {}
        if category:
            params["category"] = category

        response = await client.get("/tools", params=params)
        response.raise_for_status()
        data = response.json()

        return [
            ToolInfo(
                name=t["name"],
                description=t["description"],
                category=t["category"],
                parameters=t["parameters"],
                requires_approval=t["requires_approval"],
            )
            for t in data["tools"]
        ]

    async def wait_for_completion(
        self,
        session_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
    ) -> AgentSessionResponse:
        """Wait for a session to complete.

        Convenience method that polls get_session() until the session
        reaches a terminal state (completed, failed, or cancelled).

        Args:
            session_id: Session ID to wait for
            poll_interval: Seconds between polls (default: 1.0)
            timeout: Maximum seconds to wait (default: 300)

        Returns:
            Final AgentSessionResponse

        Raises:
            TimeoutError: If session doesn't complete within timeout
            SessionNotFoundError: If session doesn't exist
            ConductorClientError: For other API errors
        """
        start_time = asyncio.get_event_loop().time()
        terminal_states = {"completed", "failed", "cancelled"}

        while True:
            session = await self.get_session(session_id)

            if session.status in terminal_states:
                return session

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Session {session_id} did not complete within {timeout}s"
                )

            await asyncio.sleep(poll_interval)

    async def health_check(self) -> bool:
        """Check if the API is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
