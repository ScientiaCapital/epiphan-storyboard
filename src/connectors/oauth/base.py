"""Base OAuth2 provider for connector authentication."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OAuthTokenResponse:
    """OAuth2 token response data."""

    access_token: str
    token_type: str = "Bearer"
    refresh_token: str | None = None
    expires_in: int | None = None
    expires_at: datetime | None = None
    scope: str | None = None
    raw_response: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if self.expires_at is None:
            return False
        # Add 60 second buffer for clock skew
        return datetime.now(UTC) + timedelta(seconds=60) >= self.expires_at


class OAuthProvider(ABC):
    """Base OAuth2 provider for connector authentication."""

    provider_name: str  # 'gong', 'linear', 'notion', 'google'

    @property
    @abstractmethod
    def authorize_url(self) -> str:
        """Authorization endpoint URL."""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """Token endpoint URL."""
        pass

    @property
    @abstractmethod
    def scopes(self) -> list[str]:
        """Required OAuth scopes."""
        pass

    def get_client_id(self) -> str:
        """Get client ID from environment."""
        key = f"{self.provider_name.upper()}_CLIENT_ID"
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing environment variable: {key}")
        return value

    def get_client_secret(self) -> str:
        """Get client secret from environment."""
        key = f"{self.provider_name.upper()}_CLIENT_SECRET"
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing environment variable: {key}")
        return value

    def build_authorize_url(self, redirect_uri: str, state: str) -> str:
        """Build complete authorization URL with params."""
        from urllib.parse import urlencode

        params = {
            "client_id": self.get_client_id(),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }

        # Add scopes if provider has any
        if self.scopes:
            params["scope"] = " ".join(self.scopes)

        # Add provider-specific params
        params.update(self.get_extra_authorize_params())

        return f"{self.authorize_url}?{urlencode(params)}"

    def get_extra_authorize_params(self) -> dict:
        """Override to add provider-specific authorize params."""
        return {}

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokenResponse:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.get_client_id(),
                "client_secret": self.get_client_secret(),
                "code": code,
                "redirect_uri": redirect_uri,
            }

            headers = self._get_token_request_headers()

            logger.info(
                f"Exchanging authorization code for {self.provider_name}",
                extra={"redirect_uri": redirect_uri},
            )

            response = await client.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(f"Successfully obtained tokens for {self.provider_name}")
            return self._parse_token_response(response.json())

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokenResponse:
        """Refresh access token using refresh token."""
        async with httpx.AsyncClient() as client:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.get_client_id(),
                "client_secret": self.get_client_secret(),
                "refresh_token": refresh_token,
            }

            headers = self._get_token_request_headers()

            logger.info(f"Refreshing tokens for {self.provider_name}")

            response = await client.post(
                self.token_url,
                data=data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(f"Successfully refreshed tokens for {self.provider_name}")
            return self._parse_token_response(response.json())

    def _get_token_request_headers(self) -> dict:
        """Get headers for token request. Override for custom auth."""
        return {"Content-Type": "application/x-www-form-urlencoded"}

    def _parse_token_response(self, data: dict) -> OAuthTokenResponse:
        """Parse token response into structured object."""
        expires_at = None
        if expires_in := data.get("expires_in"):
            expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))

        return OAuthTokenResponse(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            expires_at=expires_at,
            scope=data.get("scope"),
            raw_response=data,
        )
