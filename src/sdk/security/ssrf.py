"""SSRF (Server-Side Request Forgery) validation for URLs.

Validates URLs to prevent:
- Requests to internal IPs (127.0.0.1, 10.x.x.x, etc.)
- Requests to localhost variants
- DNS rebinding attacks
- File:// and other dangerous protocols

Usage:
    from conductor_ai.sdk.security import validate_url, is_safe_url

    # Validate and raise on error
    validate_url("https://example.com")  # OK
    validate_url("http://127.0.0.1")  # Raises SSRFError

    # Check without raising
    if is_safe_url("https://api.github.com"):
        # Safe to fetch
        pass
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class SSRFError(Exception):
    """Raised when a URL fails SSRF validation."""

    pass


class SSRFValidator:
    """Configurable SSRF validator for URLs.

    Args:
        allow_private_ips: Allow requests to private IP ranges (default: False)
        allow_localhost: Allow requests to localhost (default: False)
        allowed_protocols: Set of allowed URL schemes (default: http, https)
        allowed_ports: Set of allowed ports (default: 80, 443, 8080, 8443)
        blocked_hosts: Set of hostnames to block
    """

    # Private IP ranges (RFC 1918 + localhost + link-local)
    PRIVATE_RANGES = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
        ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
        ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local
        ipaddress.ip_network("::1/128"),          # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),         # IPv6 private
        ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ]

    LOCALHOST_VARIANTS = {
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "::1",
        "[::1]",
        "0.0.0.0",
    }

    DEFAULT_PROTOCOLS = {"http", "https"}
    DEFAULT_PORTS = {80, 443, 8080, 8443}

    def __init__(
        self,
        allow_private_ips: bool = False,
        allow_localhost: bool = False,
        allowed_protocols: set[str] | None = None,
        allowed_ports: set[int] | None = None,
        blocked_hosts: set[str] | None = None,
    ) -> None:
        """Initialize the validator with configuration."""
        self.allow_private_ips = allow_private_ips
        self.allow_localhost = allow_localhost
        self.allowed_protocols = allowed_protocols or self.DEFAULT_PROTOCOLS
        self.allowed_ports = allowed_ports or self.DEFAULT_PORTS
        self.blocked_hosts = blocked_hosts or set()

    def validate(self, url: str) -> None:
        """Validate a URL for SSRF vulnerabilities.

        Args:
            url: The URL to validate

        Raises:
            SSRFError: If the URL fails validation
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise SSRFError(f"Invalid URL format: {e}")

        # Check protocol
        if parsed.scheme not in self.allowed_protocols:
            raise SSRFError(
                f"Protocol '{parsed.scheme}' not allowed. "
                f"Allowed: {self.allowed_protocols}"
            )

        # Check for missing host
        if not parsed.hostname:
            raise SSRFError("URL must have a hostname")

        hostname = parsed.hostname.lower()

        # Check blocked hosts
        if hostname in self.blocked_hosts:
            raise SSRFError(f"Host '{hostname}' is blocked")

        # Check localhost variants
        if not self.allow_localhost:
            if hostname in self.LOCALHOST_VARIANTS:
                raise SSRFError(f"Localhost access not allowed: {hostname}")

            # Check for localhost subdomains
            if hostname.endswith(".localhost") or hostname.endswith(".local"):
                raise SSRFError(f"Local hostname not allowed: {hostname}")

        # Check port
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80

        if port not in self.allowed_ports:
            raise SSRFError(
                f"Port {port} not allowed. Allowed: {self.allowed_ports}"
            )

        # Resolve hostname and check IP
        if not self.allow_private_ips:
            self._check_resolved_ip(hostname)

    def _check_resolved_ip(self, hostname: str) -> None:
        """Check if the hostname resolves to a private IP.

        Args:
            hostname: The hostname to check

        Raises:
            SSRFError: If hostname resolves to a private IP
        """
        try:
            # Get all IPs the hostname resolves to
            infos = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except socket.gaierror as e:
            raise SSRFError(f"Cannot resolve hostname '{hostname}': {e}")

        for info in infos:
            ip_str = info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            for private_range in self.PRIVATE_RANGES:
                if ip in private_range:
                    raise SSRFError(
                        f"URL resolves to private IP {ip_str} "
                        f"(in {private_range})"
                    )

    def is_safe(self, url: str) -> bool:
        """Check if a URL is safe without raising.

        Args:
            url: The URL to check

        Returns:
            True if safe, False if blocked
        """
        try:
            self.validate(url)
            return True
        except SSRFError:
            return False


# Default validator instance
_default_validator = SSRFValidator()


def validate_url(url: str) -> None:
    """Validate a URL using the default validator.

    Args:
        url: The URL to validate

    Raises:
        SSRFError: If the URL fails validation
    """
    _default_validator.validate(url)


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe using the default validator.

    Args:
        url: The URL to check

    Returns:
        True if safe, False if blocked
    """
    return _default_validator.is_safe(url)
