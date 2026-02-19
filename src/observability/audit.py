"""Audit logging for tool executions and agent actions.

Provides full audit trail for all tool calls with:
- Input parameters (sanitized)
- Output summaries
- Duration and cost tracking
- Error capture
"""

import functools
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class AuditRecord:
    """Record of a single auditable action.

    Captures what happened, when, where, and outcome.
    """

    # Required fields
    action: str  # 'tool_call', 'scrape', 'enrich', 'outreach'
    tool_name: str  # Tool that was executed
    org_id: str  # Organization context
    success: bool  # Whether action succeeded

    # Auto-generated fields
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Optional context fields
    session_id: str | None = None  # Links to agent session
    input_params: dict | None = None  # Input arguments (sanitized)
    output_summary: str | None = None  # Brief result description
    target_entity: str | None = None  # 'lead:123', 'contractor:456'
    source_project: str | None = None  # 'dealer-scraper', 'sales-agent'

    # Outcome details
    error_message: str | None = None  # Error if failed
    duration_ms: int | None = None  # Execution time
    cost_usd: float | None = None  # API cost if applicable

    def to_dict(self) -> dict:
        """Convert to dictionary for storage/serialization."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "tool_name": self.tool_name,
            "org_id": self.org_id,
            "success": self.success,
            "session_id": self.session_id,
            "input_params": self.input_params,
            "output_summary": self.output_summary,
            "target_entity": self.target_entity,
            "source_project": self.source_project,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "cost_usd": self.cost_usd,
        }


class AuditLogger:
    """Logger for audit records.

    Stores audit records in memory (can be extended to persist to Supabase).

    Usage:
        logger = AuditLogger(org_id="scientia")

        record = logger.log_tool_call(
            tool_name="web_fetch",
            input_params={"url": "https://example.com"},
            success=True,
            duration_ms=250,
        )

        # Query logs
        recent = logger.get_recent_logs(limit=10)
        failures = logger.get_failure_logs()
    """

    def __init__(self, org_id: str, source_project: str | None = None):
        """Initialize logger.

        Args:
            org_id: Organization identifier for all logs
            source_project: Default source project tag
        """
        self.org_id = org_id
        self.source_project = source_project
        self._records: list[AuditRecord] = []

    def log_tool_call(
        self,
        tool_name: str,
        input_params: dict,
        success: bool,
        output_summary: str | None = None,
        error_message: str | None = None,
        duration_ms: int | None = None,
        cost_usd: float | None = None,
        session_id: str | None = None,
        target_entity: str | None = None,
    ) -> AuditRecord:
        """Log a tool execution.

        Args:
            tool_name: Name of the tool executed
            input_params: Input arguments (will be sanitized)
            success: Whether execution succeeded
            output_summary: Brief description of output
            error_message: Error message if failed
            duration_ms: Execution time in milliseconds
            cost_usd: API cost if applicable
            session_id: Agent session ID if applicable
            target_entity: Entity being operated on

        Returns:
            The created AuditRecord
        """
        record = AuditRecord(
            action="tool_call",
            tool_name=tool_name,
            org_id=self.org_id,
            success=success,
            session_id=session_id,
            input_params=self._sanitize_params(input_params),
            output_summary=output_summary,
            target_entity=target_entity,
            source_project=self.source_project,
            error_message=error_message,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
        )

        self._records.append(record)
        return record

    def get_recent_logs(self, limit: int = 100) -> list[AuditRecord]:
        """Get most recent audit records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent AuditRecords (newest first)
        """
        return list(reversed(self._records[-limit:]))

    def get_logs_by_tool(self, tool_name: str) -> list[AuditRecord]:
        """Get all logs for a specific tool.

        Args:
            tool_name: Tool name to filter by

        Returns:
            List of AuditRecords for that tool
        """
        return [r for r in self._records if r.tool_name == tool_name]

    def get_failure_logs(self) -> list[AuditRecord]:
        """Get all failed audit records.

        Returns:
            List of AuditRecords where success=False
        """
        return [r for r in self._records if not r.success]

    def _sanitize_params(self, params: dict) -> dict:
        """Sanitize input parameters for logging.

        Redacts sensitive fields like API keys, passwords.

        Args:
            params: Raw input parameters

        Returns:
            Sanitized parameters safe for logging
        """
        if not params:
            return {}

        sensitive_keys = {
            "api_key",
            "apikey",
            "api-key",
            "password",
            "passwd",
            "secret",
            "token",
            "auth",
            "authorization",
            "credential",
            "key",
        }

        sanitized = {}
        for key, value in params.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value

        return sanitized


def audit_logged(
    logger: AuditLogger,
    tool_name: str,
) -> Callable:
    """Decorator to automatically log function calls.

    Captures input parameters, duration, success/failure.

    Usage:
        logger = AuditLogger(org_id="scientia")

        @audit_logged(logger, tool_name="my_tool")
        async def my_tool(url: str) -> str:
            return await fetch(url)

    Args:
        logger: AuditLogger instance to log to
        tool_name: Name to use in audit logs

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Capture input parameters
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            input_params = dict(bound.arguments)

            # Execute and time
            start_time = time.time()
            error_message = None
            success = True
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)

                logger.log_tool_call(
                    tool_name=tool_name,
                    input_params=input_params,
                    success=success,
                    error_message=error_message,
                    duration_ms=duration_ms,
                )

        return wrapper

    return decorator
