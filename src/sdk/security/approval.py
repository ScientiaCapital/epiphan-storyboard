"""Approval gate utilities for dangerous tool operations.

Provides mechanisms for tools to request user approval before
executing potentially dangerous operations (external API calls,
data modifications, etc.).

Usage:
    from conductor_ai.sdk.security import requires_approval, ApprovalGate

    class MyDangerousTool(BaseTool):
        @property
        def definition(self):
            return ToolDefinition(
                name="dangerous_tool",
                requires_approval=True,  # Mark tool as requiring approval
                ...
            )

        @requires_approval("Delete user data")
        async def run(self, arguments: dict) -> ToolResult:
            # This will check approval before executing
            ...

    # Or use the gate directly
    gate = ApprovalGate()
    await gate.request_approval("Delete all records?")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar
from uuid import uuid4
import functools

T = TypeVar("T")


class ApprovalRequired(Exception):
    """Raised when an operation requires user approval.

    The agent loop should catch this and prompt for approval.
    """

    def __init__(
        self,
        operation: str,
        request_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the approval request.

        Args:
            operation: Human-readable description of the operation
            request_id: Unique ID to reference this approval request
            details: Additional context about the operation
        """
        self.operation = operation
        self.request_id = request_id
        self.details = details or {}
        super().__init__(f"Approval required: {operation}")


@dataclass
class ApprovalRecord:
    """Record of an approval decision.

    Attributes:
        request_id: Unique request identifier
        operation: Description of the operation
        approved: Whether the operation was approved
        approved_by: Who approved (user ID, "system", etc.)
        approved_at: When the approval was granted
        expires_at: When the approval expires (if applicable)
    """

    request_id: str
    operation: str
    approved: bool
    approved_by: str | None = None
    approved_at: datetime | None = None
    expires_at: datetime | None = None

    def is_valid(self) -> bool:
        """Check if the approval is still valid.

        Returns:
            True if approved and not expired
        """
        if not self.approved:
            return False
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at


class ApprovalGate:
    """Gate for managing tool approval requests.

    Can be used to:
    - Track pending approval requests
    - Store granted approvals (with optional expiration)
    - Check if an operation is pre-approved

    In production, this would integrate with a UI or webhook
    system for user approval. For testing, approvals can be
    pre-granted programmatically.
    """

    def __init__(self) -> None:
        """Initialize the approval gate."""
        self._pending: dict[str, ApprovalRecord] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        self._auto_approve: bool = False

    def set_auto_approve(self, enabled: bool) -> None:
        """Enable or disable auto-approval (for testing).

        WARNING: Only use in tests or development!

        Args:
            enabled: Whether to auto-approve all requests
        """
        self._auto_approve = enabled

    async def request_approval(
        self,
        operation: str,
        details: dict[str, Any] | None = None,
    ) -> ApprovalRecord:
        """Request approval for an operation.

        If auto-approve is enabled or the operation is pre-approved,
        returns immediately. Otherwise, raises ApprovalRequired.

        Args:
            operation: Human-readable description
            details: Additional context

        Returns:
            ApprovalRecord if approved

        Raises:
            ApprovalRequired: If approval is needed
        """
        request_id = str(uuid4())

        # Check for pre-approved operation
        for record in self._approvals.values():
            if record.operation == operation and record.is_valid():
                return record

        # Auto-approve if enabled
        if self._auto_approve:
            record = ApprovalRecord(
                request_id=request_id,
                operation=operation,
                approved=True,
                approved_by="system:auto_approve",
                approved_at=datetime.now(timezone.utc),
            )
            self._approvals[request_id] = record
            return record

        # Create pending request and raise
        record = ApprovalRecord(
            request_id=request_id,
            operation=operation,
            approved=False,
        )
        self._pending[request_id] = record

        raise ApprovalRequired(
            operation=operation,
            request_id=request_id,
            details=details,
        )

    def grant_approval(
        self,
        request_id: str,
        approved_by: str = "user",
        expires_in_seconds: float | None = None,
    ) -> ApprovalRecord:
        """Grant approval for a pending request.

        Args:
            request_id: ID from ApprovalRequired exception
            approved_by: Who is granting approval
            expires_in_seconds: Optional expiration time

        Returns:
            Updated ApprovalRecord

        Raises:
            KeyError: If request_id not found
        """
        if request_id not in self._pending:
            raise KeyError(f"No pending request with ID: {request_id}")

        record = self._pending.pop(request_id)
        record.approved = True
        record.approved_by = approved_by
        record.approved_at = datetime.now(timezone.utc)

        if expires_in_seconds:
            from datetime import timedelta
            record.expires_at = record.approved_at + timedelta(
                seconds=expires_in_seconds
            )

        self._approvals[request_id] = record
        return record

    def deny_approval(self, request_id: str) -> ApprovalRecord:
        """Deny a pending approval request.

        Args:
            request_id: ID from ApprovalRequired exception

        Returns:
            Updated ApprovalRecord with approved=False

        Raises:
            KeyError: If request_id not found
        """
        if request_id not in self._pending:
            raise KeyError(f"No pending request with ID: {request_id}")

        record = self._pending.pop(request_id)
        record.approved = False
        return record

    def pre_approve(
        self,
        operation: str,
        approved_by: str = "system",
        expires_in_seconds: float | None = None,
    ) -> ApprovalRecord:
        """Pre-approve an operation.

        Useful for batch operations or testing.

        Args:
            operation: Operation description to pre-approve
            approved_by: Who is granting approval
            expires_in_seconds: Optional expiration

        Returns:
            ApprovalRecord for the pre-approval
        """
        request_id = str(uuid4())
        now = datetime.now(timezone.utc)

        expires_at = None
        if expires_in_seconds:
            from datetime import timedelta
            expires_at = now + timedelta(seconds=expires_in_seconds)

        record = ApprovalRecord(
            request_id=request_id,
            operation=operation,
            approved=True,
            approved_by=approved_by,
            approved_at=now,
            expires_at=expires_at,
        )
        self._approvals[request_id] = record
        return record

    @property
    def pending_requests(self) -> list[ApprovalRecord]:
        """Get all pending approval requests.

        Returns:
            List of pending ApprovalRecords
        """
        return list(self._pending.values())


# Global approval gate instance
_default_gate = ApprovalGate()


def get_approval_gate() -> ApprovalGate:
    """Get the default approval gate.

    Returns:
        The global ApprovalGate instance
    """
    return _default_gate


def requires_approval(
    operation: str,
    gate: ApprovalGate | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to require approval before executing a function.

    Args:
        operation: Human-readable description of the operation
        gate: ApprovalGate to use (defaults to global gate)

    Returns:
        Decorated function

    Usage:
        @requires_approval("Delete user data")
        async def delete_user(user_id: str):
            ...
    """
    approval_gate = gate or _default_gate

    def decorator(
        func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            await approval_gate.request_approval(operation)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
