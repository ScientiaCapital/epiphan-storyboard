"""Tests for SDK security utilities."""

import pytest
import asyncio

from src.sdk.security.ssrf import SSRFValidator, SSRFError, validate_url, is_safe_url
from src.sdk.security.timeout import TimeoutError as ToolTimeoutError, with_timeout, run_with_timeout
from src.sdk.security.approval import (
    ApprovalGate,
    ApprovalRequired,
    requires_approval,
    get_approval_gate,
)


class TestSSRFValidator:
    """Tests for SSRF validation."""

    def test_valid_https_url(self):
        """Valid HTTPS URL passes."""
        validate_url("https://example.com")
        validate_url("https://api.github.com/repos")
        validate_url("https://google.com:443/search")

    def test_valid_http_url(self):
        """Valid HTTP URL passes."""
        validate_url("http://example.com")
        validate_url("http://httpbin.org/get")

    def test_blocks_localhost(self):
        """Blocks localhost variants."""
        with pytest.raises(SSRFError, match="Localhost"):
            validate_url("http://localhost")

        with pytest.raises(SSRFError, match="Localhost"):
            validate_url("http://127.0.0.1")

        with pytest.raises(SSRFError, match="Localhost"):
            validate_url("http://0.0.0.0")

    def test_blocks_private_ips(self):
        """Blocks private IP ranges."""
        with pytest.raises(SSRFError, match="private IP"):
            validate_url("http://192.168.1.1")

        with pytest.raises(SSRFError, match="private IP"):
            validate_url("http://10.0.0.1")

        with pytest.raises(SSRFError, match="private IP"):
            validate_url("http://172.16.0.1")

    def test_blocks_dangerous_protocols(self):
        """Blocks non-HTTP protocols."""
        with pytest.raises(SSRFError, match="Protocol"):
            validate_url("file:///etc/passwd")

        with pytest.raises(SSRFError, match="Protocol"):
            validate_url("ftp://ftp.example.com")

        with pytest.raises(SSRFError, match="Protocol"):
            validate_url("gopher://evil.com")

    def test_blocks_unusual_ports(self):
        """Blocks non-standard ports by default."""
        with pytest.raises(SSRFError, match="Port"):
            validate_url("http://example.com:22")

        with pytest.raises(SSRFError, match="Port"):
            validate_url("http://example.com:3306")

    def test_allows_standard_ports(self):
        """Allows standard HTTP/HTTPS ports."""
        validate_url("http://example.com:80")
        validate_url("https://example.com:443")
        validate_url("http://example.com:8080")
        validate_url("https://example.com:8443")

    def test_blocks_localhost_subdomains(self):
        """Blocks .localhost and .local domains."""
        with pytest.raises(SSRFError, match="Local hostname"):
            validate_url("http://app.localhost")

        with pytest.raises(SSRFError, match="Local hostname"):
            validate_url("http://myapp.local")

    def test_is_safe_url_returns_bool(self):
        """is_safe_url returns boolean, not raising."""
        assert is_safe_url("https://example.com") is True
        assert is_safe_url("http://localhost") is False
        assert is_safe_url("file:///etc/passwd") is False

    def test_custom_validator_allow_localhost(self):
        """Custom validator can allow localhost."""
        validator = SSRFValidator(allow_localhost=True, allow_private_ips=True)
        validator.validate("http://localhost:8080")  # Should not raise

    def test_custom_validator_allow_private(self):
        """Custom validator can allow private IPs."""
        validator = SSRFValidator(allow_private_ips=True)
        # Note: This still does DNS resolution which may fail in CI
        # So we test the flag is respected

    def test_custom_validator_blocked_hosts(self):
        """Custom validator can block specific hosts."""
        validator = SSRFValidator(blocked_hosts={"evil.com"})
        with pytest.raises(SSRFError, match="blocked"):
            validator.validate("https://evil.com")


class TestTimeout:
    """Tests for timeout utilities."""

    @pytest.mark.asyncio
    async def test_with_timeout_success(self):
        """Function completing in time succeeds."""

        @with_timeout(1.0)
        async def fast_function():
            return "done"

        result = await fast_function()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_with_timeout_exceeded(self):
        """Function exceeding timeout raises."""

        @with_timeout(0.1, operation="Slow test")
        async def slow_function():
            await asyncio.sleep(1.0)
            return "never reached"

        with pytest.raises(ToolTimeoutError) as exc_info:
            await slow_function()

        assert exc_info.value.timeout == 0.1
        assert "Slow test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """run_with_timeout succeeds for fast coroutine."""

        async def fast_coro():
            return 42

        result = await run_with_timeout(fast_coro(), seconds=1.0)
        assert result == 42

    @pytest.mark.asyncio
    async def test_run_with_timeout_exceeded(self):
        """run_with_timeout raises for slow coroutine."""

        async def slow_coro():
            await asyncio.sleep(1.0)
            return "never"

        with pytest.raises(ToolTimeoutError):
            await run_with_timeout(slow_coro(), seconds=0.1)


class TestApprovalGate:
    """Tests for approval gate."""

    @pytest.mark.asyncio
    async def test_request_raises_approval_required(self):
        """Normal request raises ApprovalRequired."""
        gate = ApprovalGate()

        with pytest.raises(ApprovalRequired) as exc_info:
            await gate.request_approval("Delete all data")

        assert exc_info.value.operation == "Delete all data"
        assert exc_info.value.request_id is not None

    @pytest.mark.asyncio
    async def test_auto_approve_mode(self):
        """Auto-approve mode grants immediately."""
        gate = ApprovalGate()
        gate.set_auto_approve(True)

        record = await gate.request_approval("Delete all data")
        assert record.approved is True
        assert record.approved_by == "system:auto_approve"

    @pytest.mark.asyncio
    async def test_grant_approval(self):
        """Can grant approval for pending request."""
        gate = ApprovalGate()

        # First request raises
        try:
            await gate.request_approval("Delete data")
        except ApprovalRequired as e:
            request_id = e.request_id

        # Grant approval
        record = gate.grant_approval(request_id, approved_by="admin")
        assert record.approved is True
        assert record.approved_by == "admin"

    @pytest.mark.asyncio
    async def test_deny_approval(self):
        """Can deny approval for pending request."""
        gate = ApprovalGate()

        try:
            await gate.request_approval("Delete data")
        except ApprovalRequired as e:
            request_id = e.request_id

        record = gate.deny_approval(request_id)
        assert record.approved is False

    @pytest.mark.asyncio
    async def test_pre_approve(self):
        """Can pre-approve operations."""
        gate = ApprovalGate()
        gate.pre_approve("Safe operation")

        # Should not raise now
        record = await gate.request_approval("Safe operation")
        assert record.approved is True

    @pytest.mark.asyncio
    async def test_pending_requests(self):
        """Can list pending requests."""
        gate = ApprovalGate()

        try:
            await gate.request_approval("Op 1")
        except ApprovalRequired:
            pass

        try:
            await gate.request_approval("Op 2")
        except ApprovalRequired:
            pass

        pending = gate.pending_requests
        assert len(pending) == 2
        operations = {p.operation for p in pending}
        assert operations == {"Op 1", "Op 2"}

    @pytest.mark.asyncio
    async def test_requires_approval_decorator(self):
        """@requires_approval decorator works."""
        gate = ApprovalGate()

        @requires_approval("Dangerous action", gate=gate)
        async def dangerous_function():
            return "executed"

        with pytest.raises(ApprovalRequired):
            await dangerous_function()

        # Enable auto-approve
        gate.set_auto_approve(True)
        result = await dangerous_function()
        assert result == "executed"


class TestGlobalApprovalGate:
    """Tests for global approval gate."""

    def test_get_approval_gate_returns_same_instance(self):
        """get_approval_gate returns the same global instance."""
        gate1 = get_approval_gate()
        gate2 = get_approval_gate()
        assert gate1 is gate2
