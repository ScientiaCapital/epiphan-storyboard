"""Google OAuth2 provider."""

from .base import OAuthProvider


class GoogleOAuthProvider(OAuthProvider):
    """OAuth2 provider for Google APIs (Docs, Drive)."""

    provider_name = "google"

    @property
    def authorize_url(self) -> str:
        """Google authorization endpoint."""
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_url(self) -> str:
        """Google token endpoint."""
        return "https://oauth2.googleapis.com/token"

    @property
    def scopes(self) -> list[str]:
        """Required Google OAuth scopes for Docs and Drive."""
        return [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

    def get_extra_authorize_params(self) -> dict:
        """Add Google-specific authorize params.

        - access_type=offline: Request refresh token
        - prompt=consent: Force consent screen to ensure refresh token
        """
        return {
            "access_type": "offline",
            "prompt": "consent",
        }
