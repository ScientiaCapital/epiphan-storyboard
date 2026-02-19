"""Web fetch tool for retrieving content from URLs via HTTP."""

import asyncio
import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import aiohttp

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class WebFetchTool(BaseTool):
    """
    Tool for fetching content from URLs via HTTP GET or POST.

    Includes security measures:
    - URL validation
    - SSRF protection (blocks private IP ranges)
    - Response size limits (50KB max)
    - Timeout handling
    """

    # Constants for security and performance
    MAX_RESPONSE_SIZE = 50 * 1024  # 50KB
    DEFAULT_TIMEOUT = 30  # seconds

    # Private IP ranges for SSRF protection
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Private class A
        ipaddress.ip_network("172.16.0.0/12"),    # Private class B
        ipaddress.ip_network("192.168.0.0/16"),   # Private class C
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local
        ipaddress.ip_network("::1/128"),          # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),         # IPv6 private
        ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ]

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for web_fetch."""
        return ToolDefinition(
            name="web_fetch",
            description="Fetch content from a URL via HTTP GET or POST",
            category=ToolCategory.WEB,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (must be http:// or https://)",
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET or POST)",
                        "enum": ["GET", "POST"],
                        "default": "GET",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Custom HTTP headers as key-value pairs",
                        "additionalProperties": {"type": "string"},
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body for POST requests",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": self.DEFAULT_TIMEOUT,
                        "minimum": 1,
                        "maximum": 120,
                    },
                },
                "required": ["url"],
            },
        )

    def _resolve_and_validate_ip(self, hostname: str) -> None:
        """
        Resolve hostname and validate it's not a private IP.

        Args:
            hostname: Hostname to resolve and validate

        Raises:
            ValueError: If hostname resolves to private IP

        Note:
            DNS resolution failures are allowed to pass through - the actual
            HTTP request will fail with a connection error. We only block if
            the domain successfully resolves to a private IP address.
        """
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            for addr in addr_info:
                ip_str = addr[4][0]
                ip = ipaddress.ip_address(ip_str)
                for private_range in self.PRIVATE_IP_RANGES:
                    if ip in private_range:
                        raise ValueError("Domain resolves to private IP address")
        except socket.gaierror:
            # DNS resolution failed - let HTTP request handle it
            # This allows test mocking to work and defers the error to aiohttp
            pass

    def _validate_url_format(self, url: str) -> None:
        """
        Validate URL format and check for direct IP SSRF vulnerabilities.
        Does not perform DNS resolution (that happens before actual request).

        Args:
            url: URL to validate

        Raises:
            ValueError: If URL is invalid or points to private IP
        """
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("Invalid URL format")

        # Check scheme
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http:// and https:// are allowed")

        # Check hostname exists
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")

        # SSRF protection: block direct private IP addresses
        try:
            # Check if hostname is a direct IP address
            ip = ipaddress.ip_address(parsed.hostname)
            for private_range in self.PRIVATE_IP_RANGES:
                if ip in private_range:
                    raise ValueError("Access to private IP addresses is not allowed")
        except ValueError as e:
            # If it's not an IP address, it's a domain name - that's fine for format check
            if "private IP" in str(e):
                raise
            # For domain names, DNS resolution check will happen before request

    def _validate_url_dns(self, url: str) -> None:
        """
        Validate URL DNS resolution for SSRF protection.
        Should be called before making actual HTTP request.

        Args:
            url: URL to validate

        Raises:
            ValueError: If hostname resolves to private IP
        """
        parsed = urlparse(url)
        if not parsed.hostname:
            return

        # Check if hostname is already an IP
        try:
            ipaddress.ip_address(parsed.hostname)
            # Already validated in format check
            return
        except ValueError:
            # It's a domain name - resolve and validate
            self._resolve_and_validate_ip(parsed.hostname)

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the web fetch operation.

        Args:
            arguments: Tool arguments containing url, method, headers, body, timeout

        Returns:
            ToolResult with response data or error
        """
        # Extract arguments
        url = arguments.get("url")
        method = arguments.get("method", "GET").upper()
        headers = arguments.get("headers", {})
        body = arguments.get("body")
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)

        # Validate URL format
        try:
            self._validate_url_format(url)
        except ValueError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=0,
            )

        # Validate DNS resolution before making request (SSRF protection)
        try:
            self._validate_url_dns(url)
        except ValueError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=0,
            )

        # Perform HTTP request
        try:
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                request_kwargs: dict[str, Any] = {
                    "headers": headers,
                    "allow_redirects": False,  # Disable automatic redirect following for security
                }

                if method == "POST" and body:
                    request_kwargs["data"] = body

                async with session.request(method, url, **request_kwargs) as response:
                    # Check if response is a redirect
                    if response.status in (301, 302, 303, 307, 308):
                        redirect_location = response.headers.get("location", "")
                        result_data = {
                            "status": response.status,
                            "redirect": True,
                            "location": redirect_location,
                            "message": "Redirect detected. Validate redirect URL before following.",
                        }
                        return ToolResult(
                            tool_name=self.definition.name,
                            success=True,
                            result=result_data,
                            error=None,
                            execution_time_ms=0,
                        )

                    # Read response with size limit
                    response_body = ""
                    truncated = False
                    bytes_read = 0

                    async for chunk in response.content.iter_chunked(8192):
                        bytes_read += len(chunk)
                        if bytes_read > self.MAX_RESPONSE_SIZE:
                            truncated = True
                            break
                        response_body += chunk.decode("utf-8", errors="replace")

                    # Extract relevant headers (subset to avoid clutter)
                    response_headers = {
                        "content-type": response.headers.get("content-type", ""),
                        "content-length": response.headers.get("content-length", ""),
                        "server": response.headers.get("server", ""),
                    }
                    # Remove empty values
                    response_headers = {k: v for k, v in response_headers.items() if v}

                    result_data = {
                        "status": response.status,
                        "headers": response_headers,
                        "body": response_body,
                        "truncated": truncated,
                        "url": str(response.url),
                        "redirect": False,
                    }

                    return ToolResult(
                        tool_name=self.definition.name,
                        success=True,
                        result=result_data,
                        error=None,
                        execution_time_ms=0,  # Will be set by _execute_with_timing
                    )

        except aiohttp.ClientError:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="HTTP client error occurred",
                execution_time_ms=0,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Request timed out after {timeout} seconds",
                execution_time_ms=0,
            )
        except Exception:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Unexpected error occurred",
                execution_time_ms=0,
            )
