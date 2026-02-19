"""Notion OAuth2 provider."""

import base64

from .base import OAuthProvider


class NotionOAuthProvider(OAuthProvider):
    """OAuth2 provider for Notion API."""

    provider_name = "notion"

    @property
    def authorize_url(self) -> str:
        """Notion authorization endpoint."""
        return "https://api.notion.com/v1/oauth/authorize"

    @property
    def token_url(self) -> str:
        """Notion token endpoint."""
        return "https://api.notion.com/v1/oauth/token"

    @property
    def scopes(self) -> list[str]:
        """Required Notion OAuth scopes.

        Notion uses implicit "all" scope, so return empty list.
        """
        return []

    def get_extra_authorize_params(self) -> dict:
        """Add Notion-specific authorize params."""
        return {"owner": "user"}

    def _get_token_request_headers(self) -> dict:
        """Get headers for token request with Basic auth.

        Notion requires Basic auth with base64 encoded client_id:client_secret.
        """
        client_id = self.get_client_id()
        client_secret = self.get_client_secret()
        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded}",
        }
