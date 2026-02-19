"""Linear OAuth2 provider."""

from .base import OAuthProvider


class LinearOAuthProvider(OAuthProvider):
    """OAuth2 provider for Linear API."""

    provider_name = "linear"

    @property
    def authorize_url(self) -> str:
        """Linear authorization endpoint."""
        return "https://linear.app/oauth/authorize"

    @property
    def token_url(self) -> str:
        """Linear token endpoint."""
        return "https://api.linear.app/oauth/token"

    @property
    def scopes(self) -> list[str]:
        """Required Linear OAuth scopes."""
        return ["read"]
