"""
API Key Authentication & Rate Limiting Module

Provides API key validation, user identification for billing,
and per-key rate limiting for abuse prevention.
"""

import os
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict

logging.basicConfig(level=logging.INFO)


@dataclass
class APIKeyInfo:
    """Information about an API key"""
    key_id: str
    user_id: str
    organization_id: Optional[str] = None
    tier: str = "free"  # free, basic, pro, enterprise
    rate_limit_rpm: int = 60  # requests per minute
    rate_limit_tpd: int = 100000  # tokens per day
    is_active: bool = True
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """Result of authentication attempt"""
    authenticated: bool
    key_info: Optional[APIKeyInfo] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class RateLimiter:
    """
    In-memory rate limiter with sliding window.

    For production, replace with Redis-based implementation.
    """

    def __init__(self):
        # Track requests per key: {key_id: [(timestamp, tokens), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._daily_tokens: Dict[str, int] = defaultdict(int)
        self._daily_reset: Dict[str, float] = {}

    def check_rate_limit(
        self,
        key_id: str,
        rate_limit_rpm: int,
        rate_limit_tpd: int,
        estimated_tokens: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.

        Returns:
            (allowed, error_message)
        """
        now = time.time()

        # Clean old requests (older than 1 minute)
        self._requests[key_id] = [
            (ts, tokens) for ts, tokens in self._requests[key_id]
            if now - ts < 60
        ]

        # Check RPM
        if len(self._requests[key_id]) >= rate_limit_rpm:
            return False, f"Rate limit exceeded: {rate_limit_rpm} requests per minute"

        # Check daily token limit
        self._reset_daily_if_needed(key_id, now)
        if self._daily_tokens[key_id] + estimated_tokens > rate_limit_tpd:
            return False, f"Daily token limit exceeded: {rate_limit_tpd} tokens per day"

        return True, None

    def record_request(self, key_id: str, tokens: int = 0):
        """Record a request for rate limiting"""
        now = time.time()
        self._requests[key_id].append((now, tokens))
        self._reset_daily_if_needed(key_id, now)
        self._daily_tokens[key_id] += tokens

    def _reset_daily_if_needed(self, key_id: str, now: float):
        """Reset daily counters if 24h have passed"""
        if key_id not in self._daily_reset:
            self._daily_reset[key_id] = now
        elif now - self._daily_reset[key_id] >= 86400:  # 24 hours
            self._daily_tokens[key_id] = 0
            self._daily_reset[key_id] = now


class APIKeyAuthenticator:
    """
    API Key authentication and rate limiting.

    Configure via environment variables:
    - AUTH_ENABLED: Enable/disable authentication (default: false)
    - AUTH_KEYS: JSON map of API keys to user info, or
    - AUTH_KEYS_FILE: Path to JSON file with key mappings
    - AUTH_WEBHOOK_URL: URL to validate keys externally
    - AUTH_DEFAULT_RPM: Default requests per minute (default: 60)
    - AUTH_DEFAULT_TPD: Default tokens per day (default: 100000)
    """

    def __init__(self):
        self.enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
        self.default_rpm = int(os.getenv("AUTH_DEFAULT_RPM", "60"))
        self.default_tpd = int(os.getenv("AUTH_DEFAULT_TPD", "100000"))

        # In-memory key store (for demo/development)
        self._keys: Dict[str, APIKeyInfo] = {}
        self._rate_limiter = RateLimiter()

        # Load keys from environment or file
        self._load_keys()

        if self.enabled:
            logging.info(f"[AUTH] Authentication enabled with {len(self._keys)} keys loaded")
        else:
            logging.info("[AUTH] Authentication disabled")

    def _load_keys(self):
        """Load API keys from configuration"""
        import json

        # Try loading from JSON string in env
        keys_json = os.getenv("AUTH_KEYS", "")
        if keys_json:
            try:
                keys_data = json.loads(keys_json)
                self._parse_keys(keys_data)
                return
            except json.JSONDecodeError as e:
                logging.error(f"[AUTH] Failed to parse AUTH_KEYS: {e}")

        # Try loading from file
        keys_file = os.getenv("AUTH_KEYS_FILE", "")
        if keys_file and os.path.exists(keys_file):
            try:
                with open(keys_file) as f:
                    keys_data = json.load(f)
                self._parse_keys(keys_data)
                return
            except Exception as e:
                logging.error(f"[AUTH] Failed to load AUTH_KEYS_FILE: {e}")

        # Add a default development key if none configured
        if self.enabled and not self._keys:
            dev_key = "sk-dev-" + hashlib.sha256(b"development").hexdigest()[:32]
            self._keys[dev_key] = APIKeyInfo(
                key_id="dev-key",
                user_id="dev-user",
                tier="enterprise",
                rate_limit_rpm=1000,
                rate_limit_tpd=10000000,
            )
            logging.warning(f"[AUTH] No keys configured, using development key: {dev_key[:20]}...")

    def _parse_keys(self, keys_data: Dict[str, Any]):
        """Parse keys from configuration data"""
        for key, info in keys_data.items():
            if isinstance(info, dict):
                self._keys[key] = APIKeyInfo(
                    key_id=info.get("key_id", hashlib.sha256(key.encode()).hexdigest()[:16]),
                    user_id=info.get("user_id", "unknown"),
                    organization_id=info.get("organization_id"),
                    tier=info.get("tier", "free"),
                    rate_limit_rpm=info.get("rate_limit_rpm", self.default_rpm),
                    rate_limit_tpd=info.get("rate_limit_tpd", self.default_tpd),
                    is_active=info.get("is_active", True),
                    metadata=info.get("metadata", {}),
                )
            else:
                # Simple format: key -> user_id
                self._keys[key] = APIKeyInfo(
                    key_id=hashlib.sha256(key.encode()).hexdigest()[:16],
                    user_id=str(info),
                    rate_limit_rpm=self.default_rpm,
                    rate_limit_tpd=self.default_tpd,
                )

    def authenticate(
        self,
        api_key: Optional[str],
        estimated_tokens: int = 0
    ) -> AuthResult:
        """
        Authenticate an API key and check rate limits.

        Args:
            api_key: The API key from request header
            estimated_tokens: Estimated tokens for rate limit check

        Returns:
            AuthResult with authentication status
        """
        # Skip if auth disabled
        if not self.enabled:
            return AuthResult(
                authenticated=True,
                key_info=APIKeyInfo(
                    key_id="anonymous",
                    user_id="anonymous",
                    tier="unlimited",
                    rate_limit_rpm=999999,
                    rate_limit_tpd=999999999,
                )
            )

        # Check if key provided
        if not api_key:
            return AuthResult(
                authenticated=False,
                error_code="MISSING_API_KEY",
                error_message="API key is required. Provide via 'Authorization: Bearer <key>' header."
            )

        # Strip Bearer prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]

        # Look up key
        key_info = self._keys.get(api_key)
        if not key_info:
            return AuthResult(
                authenticated=False,
                error_code="INVALID_API_KEY",
                error_message="Invalid API key"
            )

        # Check if key is active
        if not key_info.is_active:
            return AuthResult(
                authenticated=False,
                error_code="API_KEY_DISABLED",
                error_message="API key has been disabled"
            )

        # Check rate limits
        allowed, error_msg = self._rate_limiter.check_rate_limit(
            key_info.key_id,
            key_info.rate_limit_rpm,
            key_info.rate_limit_tpd,
            estimated_tokens
        )

        if not allowed:
            return AuthResult(
                authenticated=False,
                key_info=key_info,
                error_code="RATE_LIMIT_EXCEEDED",
                error_message=error_msg
            )

        return AuthResult(
            authenticated=True,
            key_info=key_info
        )

    def record_usage(self, key_id: str, tokens: int):
        """Record token usage for rate limiting"""
        self._rate_limiter.record_request(key_id, tokens)

    def get_usage_stats(self, key_id: str) -> Dict[str, Any]:
        """Get usage statistics for a key"""
        return {
            "requests_last_minute": len(self._rate_limiter._requests.get(key_id, [])),
            "tokens_today": self._rate_limiter._daily_tokens.get(key_id, 0),
        }


# Global authenticator instance
_authenticator: Optional[APIKeyAuthenticator] = None


def get_authenticator() -> APIKeyAuthenticator:
    """Get or create the global authenticator"""
    global _authenticator
    if _authenticator is None:
        _authenticator = APIKeyAuthenticator()
    return _authenticator
