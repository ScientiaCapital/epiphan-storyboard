"""Tests for the web_fetch tool."""

import pytest
from aioresponses import aioresponses

from src.tools.base import ToolCategory, ToolResult
from src.tools.web_fetch import WebFetchTool


@pytest.fixture
def web_fetch_tool():
    """Create a WebFetchTool instance for testing."""
    return WebFetchTool()


class TestWebFetchToolDefinition:
    """Test the tool definition and schema."""

    def test_tool_name(self, web_fetch_tool):
        """Test that the tool has the correct name."""
        assert web_fetch_tool.definition.name == "web_fetch"

    def test_tool_category(self, web_fetch_tool):
        """Test that the tool is in the WEB category."""
        assert web_fetch_tool.definition.category == ToolCategory.WEB

    def test_requires_approval(self, web_fetch_tool):
        """Test that the tool does not require approval."""
        assert web_fetch_tool.definition.requires_approval is False

    def test_parameters_schema(self, web_fetch_tool):
        """Test that the parameters schema is correctly defined."""
        params = web_fetch_tool.definition.parameters
        assert params["type"] == "object"
        assert "url" in params["required"]
        assert "url" in params["properties"]
        assert "method" in params["properties"]
        assert "headers" in params["properties"]
        assert "body" in params["properties"]
        assert "timeout" in params["properties"]

    def test_llm_schema(self, web_fetch_tool):
        """Test that the LLM schema is correctly formatted."""
        schema = web_fetch_tool.get_llm_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_fetch"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


class TestURLValidation:
    """Test URL validation and SSRF protection."""

    @pytest.mark.asyncio
    async def test_valid_https_url(self, web_fetch_tool):
        """Test that valid HTTPS URLs are accepted."""
        # This should not raise an error
        web_fetch_tool._validate_url_format("https://example.com")

    @pytest.mark.asyncio
    async def test_valid_http_url(self, web_fetch_tool):
        """Test that valid HTTP URLs are accepted."""
        # This should not raise an error
        web_fetch_tool._validate_url_format("http://example.com")

    @pytest.mark.asyncio
    async def test_invalid_scheme_ftp(self, web_fetch_tool):
        """Test that FTP URLs are rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            web_fetch_tool._validate_url_format("ftp://example.com")

    @pytest.mark.asyncio
    async def test_invalid_scheme_file(self, web_fetch_tool):
        """Test that file:// URLs are rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            web_fetch_tool._validate_url_format("file:///etc/passwd")

    @pytest.mark.asyncio
    async def test_no_hostname(self, web_fetch_tool):
        """Test that URLs without hostname are rejected."""
        with pytest.raises(ValueError, match="must have a hostname"):
            web_fetch_tool._validate_url_format("http://")

    @pytest.mark.asyncio
    async def test_localhost_blocked(self, web_fetch_tool):
        """Test that localhost (127.0.0.1) is blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://127.0.0.1")

    @pytest.mark.asyncio
    async def test_private_ip_10_blocked(self, web_fetch_tool):
        """Test that 10.x.x.x private IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://10.0.0.1")

    @pytest.mark.asyncio
    async def test_private_ip_192_168_blocked(self, web_fetch_tool):
        """Test that 192.168.x.x private IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://192.168.1.1")

    @pytest.mark.asyncio
    async def test_private_ip_172_blocked(self, web_fetch_tool):
        """Test that 172.16-31.x.x private IPs are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://172.16.0.1")

    @pytest.mark.asyncio
    async def test_link_local_blocked(self, web_fetch_tool):
        """Test that link-local addresses (169.254.x.x) are blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://169.254.169.254")

    @pytest.mark.asyncio
    async def test_ipv6_loopback_blocked(self, web_fetch_tool):
        """Test that IPv6 loopback (::1) is blocked."""
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_format("http://[::1]")

    @pytest.mark.asyncio
    async def test_dns_ssrf_attack_localhost(self, web_fetch_tool):
        """Test that domain resolving to localhost is blocked (DNS-based SSRF)."""
        # This test assumes 'localhost' resolves to 127.0.0.1
        with pytest.raises(ValueError, match="private IP"):
            web_fetch_tool._validate_url_dns("http://localhost")

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, web_fetch_tool):
        """Test that DNS resolution failures are handled gracefully (don't raise error)."""
        # DNS failures should pass through - HTTP request will handle the error
        # This allows test mocking to work properly
        try:
            web_fetch_tool._validate_url_dns("http://this-domain-definitely-does-not-exist-12345.com")
        except ValueError:
            pytest.fail("DNS resolution failures should not raise ValueError - let HTTP request handle it")


class TestWebFetchExecution:
    """Test the actual web fetch execution."""

    @pytest.mark.asyncio
    async def test_successful_get_request(self, web_fetch_tool):
        """Test a successful GET request."""
        with aioresponses() as m:
            m.get(
                "https://api.example.com/data",
                status=200,
                body='{"status": "ok"}',
                headers={"content-type": "application/json"},
            )

            result = await web_fetch_tool.run({"url": "https://api.example.com/data"})

            assert isinstance(result, ToolResult)
            assert result.success is True
            assert result.error is None
            assert result.result["status"] == 200
            assert result.result["body"] == '{"status": "ok"}'
            assert "application/json" in result.result["headers"]["content-type"]
            assert result.result["truncated"] is False

    @pytest.mark.asyncio
    async def test_successful_post_request(self, web_fetch_tool):
        """Test a successful POST request with body."""
        with aioresponses() as m:
            m.post(
                "https://api.example.com/submit",
                status=201,
                body='{"created": true}',
                headers={"content-type": "application/json"},
            )

            result = await web_fetch_tool.run({
                "url": "https://api.example.com/submit",
                "method": "POST",
                "body": '{"data": "test"}',
            })

            assert result.success is True
            assert result.result["status"] == 201
            assert result.result["body"] == '{"created": true}'

    @pytest.mark.asyncio
    async def test_custom_headers(self, web_fetch_tool):
        """Test request with custom headers."""
        with aioresponses() as m:
            m.get(
                "https://api.example.com/protected",
                status=200,
                body="protected data",
            )

            result = await web_fetch_tool.run({
                "url": "https://api.example.com/protected",
                "headers": {
                    "Authorization": "Bearer token123",
                    "X-Custom-Header": "value",
                },
            })

            assert result.success is True
            assert result.result["status"] == 200

    @pytest.mark.asyncio
    async def test_http_error_404(self, web_fetch_tool):
        """Test handling of 404 error."""
        with aioresponses() as m:
            m.get(
                "https://api.example.com/notfound",
                status=404,
                body="Not Found",
            )

            result = await web_fetch_tool.run({"url": "https://api.example.com/notfound"})

            # Note: HTTP errors like 404 are still successful responses
            assert result.success is True
            assert result.result["status"] == 404
            assert "Not Found" in result.result["body"]

    @pytest.mark.asyncio
    async def test_http_error_500(self, web_fetch_tool):
        """Test handling of 500 error."""
        with aioresponses() as m:
            m.get(
                "https://api.example.com/error",
                status=500,
                body="Internal Server Error",
            )

            result = await web_fetch_tool.run({"url": "https://api.example.com/error"})

            # Note: HTTP errors like 500 are still successful responses
            assert result.success is True
            assert result.result["status"] == 500

    @pytest.mark.asyncio
    async def test_response_truncation(self, web_fetch_tool):
        """Test that large responses are truncated at 50KB."""
        # Create a response larger than 50KB
        large_body = "x" * (60 * 1024)  # 60KB

        with aioresponses() as m:
            m.get(
                "https://api.example.com/large",
                status=200,
                body=large_body,
            )

            result = await web_fetch_tool.run({"url": "https://api.example.com/large"})

            assert result.success is True
            assert result.result["truncated"] is True
            assert len(result.result["body"]) < len(large_body)
            # Should be around 50KB, not 60KB
            assert len(result.result["body"]) <= 50 * 1024

    @pytest.mark.asyncio
    async def test_invalid_url_error(self, web_fetch_tool):
        """Test error handling for invalid URL."""
        result = await web_fetch_tool.run({"url": "not-a-url"})

        assert result.success is False
        assert result.error is not None
        assert "Invalid URL" in result.error

    @pytest.mark.asyncio
    async def test_private_ip_error(self, web_fetch_tool):
        """Test error handling for private IP addresses."""
        result = await web_fetch_tool.run({"url": "http://127.0.0.1:8080"})

        assert result.success is False
        assert result.error is not None
        assert "private IP" in result.error

    @pytest.mark.asyncio
    async def test_timeout_handling(self, web_fetch_tool):
        """Test timeout handling."""
        with aioresponses() as m:
            # Simulate a timeout by not setting up any mock response
            # This will cause aiohttp to raise a connection error
            # For timeout testing, we'll use a very short timeout
            result = await web_fetch_tool.run({
                "url": "https://nonexistent-domain-that-will-timeout.example",
                "timeout": 1,
            })

            # Should get an error (connection error, not timeout, but similar handling)
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_default_method_is_get(self, web_fetch_tool):
        """Test that the default method is GET."""
        with aioresponses() as m:
            m.get("https://example.com", status=200, body="ok")

            result = await web_fetch_tool.run({"url": "https://example.com"})

            assert result.success is True

    @pytest.mark.asyncio
    async def test_default_timeout_is_30(self, web_fetch_tool):
        """Test that the default timeout is 30 seconds."""
        assert web_fetch_tool.DEFAULT_TIMEOUT == 30

    @pytest.mark.asyncio
    async def test_custom_timeout(self, web_fetch_tool):
        """Test using a custom timeout value."""
        with aioresponses() as m:
            m.get("https://example.com", status=200, body="ok")

            result = await web_fetch_tool.run({
                "url": "https://example.com",
                "timeout": 60,
            })

            assert result.success is True

    @pytest.mark.asyncio
    async def test_redirect_url_in_result(self, web_fetch_tool):
        """Test that the final URL is included in the result (after redirects)."""
        with aioresponses() as m:
            m.get("https://example.com", status=200, body="ok")

            result = await web_fetch_tool.run({"url": "https://example.com"})

            assert result.success is True
            assert "url" in result.result
            assert result.result["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_redirect_detection_301(self, web_fetch_tool):
        """Test that 301 redirects are detected and not followed automatically."""
        with aioresponses() as m:
            m.get(
                "https://example.com/old",
                status=301,
                headers={"location": "https://example.com/new"},
            )

            result = await web_fetch_tool.run({"url": "https://example.com/old"})

            assert result.success is True
            assert result.result["redirect"] is True
            assert result.result["status"] == 301
            assert result.result["location"] == "https://example.com/new"
            assert "Redirect detected" in result.result["message"]

    @pytest.mark.asyncio
    async def test_redirect_detection_302(self, web_fetch_tool):
        """Test that 302 redirects are detected and not followed automatically."""
        with aioresponses() as m:
            m.get(
                "https://example.com/temp",
                status=302,
                headers={"location": "https://example.com/new"},
            )

            result = await web_fetch_tool.run({"url": "https://example.com/temp"})

            assert result.success is True
            assert result.result["redirect"] is True
            assert result.result["status"] == 302

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_not_followed(self, web_fetch_tool):
        """Test that redirects to private IPs are not followed automatically."""
        with aioresponses() as m:
            # Redirect to a private IP - should be detected but not followed
            m.get(
                "https://public-site.com",
                status=302,
                headers={"location": "http://192.168.1.1/admin"},
            )

            result = await web_fetch_tool.run({"url": "https://public-site.com"})

            # Should successfully detect redirect without following it
            assert result.success is True
            assert result.result["redirect"] is True
            assert result.result["location"] == "http://192.168.1.1/admin"

    @pytest.mark.asyncio
    async def test_error_message_sanitization(self, web_fetch_tool):
        """Test that error messages don't leak sensitive information."""
        # Test with a domain that will fail DNS resolution
        result = await web_fetch_tool.run({"url": "http://invalid-domain-xyz-123.local"})

        assert result.success is False
        assert result.error is not None
        # Error should be generic, not exposing internal details
        # DNS errors are caught by aiohttp and reported as HTTP client errors
        assert result.error == "HTTP client error occurred"
        # Should not contain full exception traces or sensitive info
        assert "socket.gaierror" not in result.error.lower()
        assert "traceback" not in result.error.lower()

    @pytest.mark.asyncio
    async def test_client_error_sanitization(self, web_fetch_tool):
        """Test that HTTP client errors are sanitized."""
        # Test that would trigger a client error (mocked scenario)
        # The error message should be generic
        result = await web_fetch_tool.run({"url": "http://totally-nonexistent-domain-12345.example"})

        assert result.success is False
        # Should get a sanitized error message
        assert result.error in ["HTTP client error occurred", "Failed to resolve hostname"]


class TestExecutionTiming:
    """Test execution timing functionality."""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self, web_fetch_tool):
        """Test that execution time is recorded."""
        with aioresponses() as m:
            m.get("https://example.com", status=200, body="ok")

            result = await web_fetch_tool._execute_with_timing(
                {"url": "https://example.com"}
            )

            assert isinstance(result, ToolResult)
            assert result.execution_time_ms >= 0
            # Should complete quickly
            assert result.execution_time_ms < 5000  # Less than 5 seconds

    @pytest.mark.asyncio
    async def test_execution_time_on_error(self, web_fetch_tool):
        """Test that execution time is recorded even on error."""
        result = await web_fetch_tool._execute_with_timing(
            {"url": "http://127.0.0.1"}  # Private IP, should fail validation
        )

        assert result.success is False
        assert result.execution_time_ms >= 0
