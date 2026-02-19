"""Tests for audit logging - TDD RED phase."""

import pytest
from datetime import datetime
from uuid import UUID

from src.observability.audit import (
    AuditLogger,
    AuditRecord,
    audit_logged,
)


class TestAuditRecord:
    """Tests for AuditRecord data model."""

    def test_create_audit_record(self):
        """Can create an audit record with required fields."""
        record = AuditRecord(
            action="tool_call",
            tool_name="web_fetch",
            org_id="scientia",
            success=True,
        )

        assert record.action == "tool_call"
        assert record.tool_name == "web_fetch"
        assert record.org_id == "scientia"
        assert record.success is True
        assert isinstance(record.id, UUID)
        assert isinstance(record.timestamp, datetime)

    def test_audit_record_with_optional_fields(self):
        """Can create audit record with all optional fields."""
        record = AuditRecord(
            action="scrape",
            tool_name="dealer_locator",
            org_id="scientia",
            success=True,
            session_id="sess-123",
            input_params={"oem": "generac", "zip": "53202"},
            output_summary="Found 15 dealers",
            target_entity="lead:456",
            source_project="dealer-scraper",
            duration_ms=1500,
            cost_usd=0.002,
        )

        assert record.session_id == "sess-123"
        assert record.input_params == {"oem": "generac", "zip": "53202"}
        assert record.output_summary == "Found 15 dealers"
        assert record.target_entity == "lead:456"
        assert record.source_project == "dealer-scraper"
        assert record.duration_ms == 1500
        assert record.cost_usd == 0.002

    def test_audit_record_failure_with_error(self):
        """Failed record includes error message."""
        record = AuditRecord(
            action="tool_call",
            tool_name="web_fetch",
            org_id="scientia",
            success=False,
            error_message="Connection timeout after 30s",
        )

        assert record.success is False
        assert record.error_message == "Connection timeout after 30s"

    def test_audit_record_to_dict(self):
        """Can convert audit record to dict for storage."""
        record = AuditRecord(
            action="tool_call",
            tool_name="web_fetch",
            org_id="scientia",
            success=True,
        )

        data = record.to_dict()

        assert data["action"] == "tool_call"
        assert data["tool_name"] == "web_fetch"
        assert data["org_id"] == "scientia"
        assert data["success"] is True
        assert "id" in data
        assert "timestamp" in data


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_create_logger(self):
        """Can create an audit logger."""
        logger = AuditLogger(org_id="scientia")
        assert logger.org_id == "scientia"

    def test_log_tool_call(self):
        """Can log a tool call."""
        logger = AuditLogger(org_id="scientia")

        record = logger.log_tool_call(
            tool_name="web_fetch",
            input_params={"url": "https://example.com"},
            success=True,
            output_summary="Fetched 5KB",
            duration_ms=250,
        )

        assert record.action == "tool_call"
        assert record.tool_name == "web_fetch"
        assert record.success is True
        assert record.duration_ms == 250

    def test_log_tool_call_failure(self):
        """Can log a failed tool call."""
        logger = AuditLogger(org_id="scientia")

        record = logger.log_tool_call(
            tool_name="web_fetch",
            input_params={"url": "https://bad.com"},
            success=False,
            error_message="SSRF blocked",
            duration_ms=5,
        )

        assert record.success is False
        assert record.error_message == "SSRF blocked"

    def test_get_recent_logs(self):
        """Can retrieve recent logs."""
        logger = AuditLogger(org_id="scientia")

        logger.log_tool_call(
            tool_name="web_fetch",
            input_params={},
            success=True,
        )
        logger.log_tool_call(
            tool_name="code_run",
            input_params={},
            success=True,
        )

        logs = logger.get_recent_logs(limit=10)

        assert len(logs) == 2
        assert logs[0].tool_name in ["web_fetch", "code_run"]

    def test_get_logs_by_tool(self):
        """Can filter logs by tool name."""
        logger = AuditLogger(org_id="scientia")

        logger.log_tool_call(tool_name="web_fetch", input_params={}, success=True)
        logger.log_tool_call(tool_name="code_run", input_params={}, success=True)
        logger.log_tool_call(tool_name="web_fetch", input_params={}, success=True)

        logs = logger.get_logs_by_tool("web_fetch")

        assert len(logs) == 2
        assert all(log.tool_name == "web_fetch" for log in logs)

    def test_get_failure_logs(self):
        """Can filter to only failed logs."""
        logger = AuditLogger(org_id="scientia")

        logger.log_tool_call(tool_name="web_fetch", input_params={}, success=True)
        logger.log_tool_call(tool_name="code_run", input_params={}, success=False, error_message="Error")
        logger.log_tool_call(tool_name="web_fetch", input_params={}, success=False, error_message="Error")

        logs = logger.get_failure_logs()

        assert len(logs) == 2
        assert all(log.success is False for log in logs)


class TestAuditLoggedDecorator:
    """Tests for @audit_logged decorator."""

    @pytest.mark.asyncio
    async def test_decorator_logs_successful_call(self):
        """Decorator logs successful function calls."""
        logger = AuditLogger(org_id="scientia")

        @audit_logged(logger, tool_name="test_tool")
        async def my_tool(x: int) -> int:
            return x * 2

        result = await my_tool(5)

        assert result == 10
        logs = logger.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0].tool_name == "test_tool"
        assert logs[0].success is True

    @pytest.mark.asyncio
    async def test_decorator_logs_failed_call(self):
        """Decorator logs failed function calls."""
        logger = AuditLogger(org_id="scientia")

        @audit_logged(logger, tool_name="failing_tool")
        async def my_failing_tool() -> None:
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError):
            await my_failing_tool()

        logs = logger.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0].tool_name == "failing_tool"
        assert logs[0].success is False
        assert "Something went wrong" in logs[0].error_message

    @pytest.mark.asyncio
    async def test_decorator_captures_duration(self):
        """Decorator captures execution duration."""
        import asyncio
        logger = AuditLogger(org_id="scientia")

        @audit_logged(logger, tool_name="slow_tool")
        async def slow_tool() -> str:
            await asyncio.sleep(0.1)
            return "done"

        await slow_tool()

        logs = logger.get_recent_logs(limit=1)
        assert logs[0].duration_ms >= 100

    @pytest.mark.asyncio
    async def test_decorator_captures_input_params(self):
        """Decorator captures input parameters."""
        logger = AuditLogger(org_id="scientia")

        @audit_logged(logger, tool_name="param_tool")
        async def param_tool(url: str, timeout: int = 30) -> str:
            return f"fetched {url}"

        await param_tool("https://example.com", timeout=60)

        logs = logger.get_recent_logs(limit=1)
        assert logs[0].input_params["url"] == "https://example.com"
        assert logs[0].input_params["timeout"] == 60
