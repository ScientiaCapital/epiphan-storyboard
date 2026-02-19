"""Gong OAuth2 provider."""

from .base import OAuthProvider


class GongOAuthProvider(OAuthProvider):
    """OAuth2 provider for Gong API."""

    provider_name = "gong"

    @property
    def authorize_url(self) -> str:
        """Gong authorization endpoint."""
        return "https://app.gong.io/oauth2/authorize"

    @property
    def token_url(self) -> str:
        """Gong token endpoint."""
        return "https://app.gong.io/oauth2/generate-customer-token"

    @property
    def scopes(self) -> list[str]:
        """Required Gong OAuth scopes."""
        return [
            "api:calls:read:transcript",
            "api:calls:read:extensive",
            "api:users:read",
        ]
