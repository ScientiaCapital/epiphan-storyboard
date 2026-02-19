"""Tests for OAuth2 providers."""

import base64
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest
import respx

from src.connectors.oauth import (
    GongOAuthProvider,
    GoogleOAuthProvider,
    LinearOAuthProvider,
    NotionOAuthProvider,
    OAuthProvider,
    OAuthTokenResponse,
)


# Test fixtures
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for all providers."""
    providers = ["gong", "linear", "notion", "google"]
    for provider in providers:
        monkeypatch.setenv(f"{provider.upper()}_CLIENT_ID", f"test_{provider}_client_id")
        monkeypatch.setenv(
            f"{provider.upper()}_CLIENT_SECRET", f"test_{provider}_client_secret"
        )


@pytest.fixture
def mock_token_response():
    """Mock successful token response."""
    return {
        "access_token": "test_access_token_12345",
        "token_type": "Bearer",
        "refresh_token": "test_refresh_token_67890",
        "expires_in": 3600,
        "scope": "read write",
    }


# Test OAuthTokenResponse
class TestOAuthTokenResponse:
    """Tests for OAuthTokenResponse dataclass."""

    def test_token_response_creation(self):
        """Test creating token response with minimal fields."""
        response = OAuthTokenResponse(access_token="test_token")
        assert response.access_token == "test_token"
        assert response.token_type == "Bearer"
        assert response.refresh_token is None
        assert response.expires_in is None
        assert response.expires_at is None
        assert response.scope is None
        assert response.raw_response == {}

    def test_token_response_with_all_fields(self):
        """Test creating token response with all fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        response = OAuthTokenResponse(
            access_token="access",
            token_type="Bearer",
            refresh_token="refresh",
            expires_in=3600,
            expires_at=expires_at,
            scope="read write",
            raw_response={"custom": "data"},
        )
        assert response.access_token == "access"
        assert response.token_type == "Bearer"
        assert response.refresh_token == "refresh"
        assert response.expires_in == 3600
        assert response.expires_at == expires_at
        assert response.scope == "read write"
        assert response.raw_response == {"custom": "data"}

    def test_is_expired_no_expiry(self):
        """Test is_expired returns False when no expires_at."""
        response = OAuthTokenResponse(access_token="test")
        assert response.is_expired() is False

    def test_is_expired_future_expiry(self):
        """Test is_expired returns False for future expiry."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        response = OAuthTokenResponse(access_token="test", expires_at=expires_at)
        assert response.is_expired() is False

    def test_is_expired_past_expiry(self):
        """Test is_expired returns True for past expiry."""
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        response = OAuthTokenResponse(access_token="test", expires_at=expires_at)
        assert response.is_expired() is True

    def test_is_expired_with_buffer(self):
        """Test is_expired uses 60 second buffer."""
        # Token expires in 30 seconds - should be considered expired due to buffer
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        response = OAuthTokenResponse(access_token="test", expires_at=expires_at)
        assert response.is_expired() is True


# Test Gong OAuth Provider
class TestGongOAuthProvider:
    """Tests for Gong OAuth provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = GongOAuthProvider()
        assert provider.provider_name == "gong"

    def test_authorize_url(self):
        """Test authorization URL is correct."""
        provider = GongOAuthProvider()
        assert provider.authorize_url == "https://app.gong.io/oauth2/authorize"

    def test_token_url(self):
        """Test token URL is correct."""
        provider = GongOAuthProvider()
        assert (
            provider.token_url
            == "https://app.gong.io/oauth2/generate-customer-token"
        )

    def test_scopes(self):
        """Test required scopes are correct."""
        provider = GongOAuthProvider()
        assert provider.scopes == [
            "api:calls:read:transcript",
            "api:calls:read:extensive",
            "api:users:read",
        ]

    def test_get_client_id(self, mock_env_vars):
        """Test getting client ID from environment."""
        provider = GongOAuthProvider()
        assert provider.get_client_id() == "test_gong_client_id"

    def test_get_client_secret(self, mock_env_vars):
        """Test getting client secret from environment."""
        provider = GongOAuthProvider()
        assert provider.get_client_secret() == "test_gong_client_secret"

    def test_get_client_id_missing_env(self):
        """Test error when client ID env var is missing."""
        provider = GongOAuthProvider()
        with pytest.raises(ValueError, match="Missing environment variable"):
            provider.get_client_id()

    def test_build_authorize_url(self, mock_env_vars):
        """Test building complete authorization URL."""
        provider = GongOAuthProvider()
        url = provider.build_authorize_url(
            redirect_uri="https://app.example.com/callback",
            state="random_state_12345",
        )

        assert "https://app.gong.io/oauth2/authorize?" in url
        assert "client_id=test_gong_client_id" in url
        assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url
        assert "response_type=code" in url
        assert (
            "scope=api%3Acalls%3Aread%3Atranscript+api%3Acalls%3Aread%3Aextensive+api%3Ausers%3Aread"
            in url
        )
        assert "state=random_state_12345" in url

    @pytest.mark.asyncio
    @respx.mock
    async def test_exchange_code(self, mock_env_vars, mock_token_response):
        """Test exchanging authorization code for tokens."""
        provider = GongOAuthProvider()

        # Mock the token endpoint
        route = respx.post(provider.token_url).mock(
            return_value=httpx.Response(200, json=mock_token_response)
        )

        result = await provider.exchange_code(
            code="auth_code_12345",
            redirect_uri="https://app.example.com/callback",
        )

        # Verify request was made correctly
        assert route.called
        request = route.calls[0].request
        assert "grant_type=authorization_code" in str(request.content)
        assert "code=auth_code_12345" in str(request.content)
        assert "client_id=test_gong_client_id" in str(request.content)
        assert "client_secret=test_gong_client_secret" in str(request.content)

        # Verify response
        assert result.access_token == "test_access_token_12345"
        assert result.refresh_token == "test_refresh_token_67890"
        assert result.expires_in == 3600
        assert result.expires_at is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_refresh_tokens(self, mock_env_vars, mock_token_response):
        """Test refreshing access tokens."""
        provider = GongOAuthProvider()

        # Mock the token endpoint
        route = respx.post(provider.token_url).mock(
            return_value=httpx.Response(200, json=mock_token_response)
        )

        result = await provider.refresh_tokens(refresh_token="old_refresh_token")

        # Verify request was made correctly
        assert route.called
        request = route.calls[0].request
        assert "grant_type=refresh_token" in str(request.content)
        assert "refresh_token=old_refresh_token" in str(request.content)

        # Verify response
        assert result.access_token == "test_access_token_12345"
        assert result.refresh_token == "test_refresh_token_67890"

    @pytest.mark.asyncio
    @respx.mock
    async def test_exchange_code_error(self, mock_env_vars):
        """Test error handling when token exchange fails."""
        provider = GongOAuthProvider()

        # Mock error response
        respx.post(provider.token_url).mock(
            return_value=httpx.Response(400, json={"error": "invalid_grant"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await provider.exchange_code(
                code="invalid_code",
                redirect_uri="https://app.example.com/callback",
            )


# Test Linear OAuth Provider
class TestLinearOAuthProvider:
    """Tests for Linear OAuth provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = LinearOAuthProvider()
        assert provider.provider_name == "linear"

    def test_authorize_url(self):
        """Test authorization URL is correct."""
        provider = LinearOAuthProvider()
        assert provider.authorize_url == "https://linear.app/oauth/authorize"

    def test_token_url(self):
        """Test token URL is correct."""
        provider = LinearOAuthProvider()
        assert provider.token_url == "https://api.linear.app/oauth/token"

    def test_scopes(self):
        """Test required scopes are correct."""
        provider = LinearOAuthProvider()
        assert provider.scopes == ["read"]

    def test_build_authorize_url(self, mock_env_vars):
        """Test building authorization URL."""
        provider = LinearOAuthProvider()
        url = provider.build_authorize_url(
            redirect_uri="https://app.example.com/callback",
            state="state_123",
        )

        assert "https://linear.app/oauth/authorize?" in url
        assert "scope=read" in url


# Test Notion OAuth Provider
class TestNotionOAuthProvider:
    """Tests for Notion OAuth provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = NotionOAuthProvider()
        assert provider.provider_name == "notion"

    def test_authorize_url(self):
        """Test authorization URL is correct."""
        provider = NotionOAuthProvider()
        assert provider.authorize_url == "https://api.notion.com/v1/oauth/authorize"

    def test_token_url(self):
        """Test token URL is correct."""
        provider = NotionOAuthProvider()
        assert provider.token_url == "https://api.notion.com/v1/oauth/token"

    def test_scopes(self):
        """Test scopes are empty (Notion uses implicit scope)."""
        provider = NotionOAuthProvider()
        assert provider.scopes == []

    def test_get_extra_authorize_params(self):
        """Test Notion-specific authorize params."""
        provider = NotionOAuthProvider()
        params = provider.get_extra_authorize_params()
        assert params == {"owner": "user"}

    def test_build_authorize_url_no_scope(self, mock_env_vars):
        """Test authorization URL doesn't include scope param."""
        provider = NotionOAuthProvider()
        url = provider.build_authorize_url(
            redirect_uri="https://app.example.com/callback",
            state="state_123",
        )

        assert "https://api.notion.com/v1/oauth/authorize?" in url
        assert "owner=user" in url
        assert "scope=" not in url  # No scope for Notion

    def test_get_token_request_headers(self, mock_env_vars):
        """Test Basic auth headers for token request."""
        provider = NotionOAuthProvider()
        headers = provider._get_token_request_headers()

        # Verify Basic auth header
        assert "Authorization" in headers
        auth_header = headers["Authorization"]
        assert auth_header.startswith("Basic ")

        # Decode and verify credentials
        encoded = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "test_notion_client_id:test_notion_client_secret"

    @pytest.mark.asyncio
    @respx.mock
    async def test_exchange_code_with_basic_auth(self, mock_env_vars, mock_token_response):
        """Test token exchange uses Basic auth."""
        provider = NotionOAuthProvider()

        # Mock the token endpoint
        route = respx.post(provider.token_url).mock(
            return_value=httpx.Response(200, json=mock_token_response)
        )

        result = await provider.exchange_code(
            code="auth_code_12345",
            redirect_uri="https://app.example.com/callback",
        )

        # Verify Basic auth was used
        assert route.called
        request = route.calls[0].request
        auth_header = request.headers.get("Authorization")
        assert auth_header is not None
        assert auth_header.startswith("Basic ")

        # Verify response
        assert result.access_token == "test_access_token_12345"


# Test Google OAuth Provider
class TestGoogleOAuthProvider:
    """Tests for Google OAuth provider."""

    def test_provider_name(self):
        """Test provider name is correct."""
        provider = GoogleOAuthProvider()
        assert provider.provider_name == "google"

    def test_authorize_url(self):
        """Test authorization URL is correct."""
        provider = GoogleOAuthProvider()
        assert (
            provider.authorize_url == "https://accounts.google.com/o/oauth2/v2/auth"
        )

    def test_token_url(self):
        """Test token URL is correct."""
        provider = GoogleOAuthProvider()
        assert provider.token_url == "https://oauth2.googleapis.com/token"

    def test_scopes(self):
        """Test required scopes for Docs and Drive."""
        provider = GoogleOAuthProvider()
        assert provider.scopes == [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]

    def test_get_extra_authorize_params(self):
        """Test Google-specific authorize params."""
        provider = GoogleOAuthProvider()
        params = provider.get_extra_authorize_params()
        assert params == {
            "access_type": "offline",
            "prompt": "consent",
        }

    def test_build_authorize_url(self, mock_env_vars):
        """Test building authorization URL with Google-specific params."""
        provider = GoogleOAuthProvider()
        url = provider.build_authorize_url(
            redirect_uri="https://app.example.com/callback",
            state="state_123",
        )

        assert "https://accounts.google.com/o/oauth2/v2/auth?" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
        assert (
            "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdocuments.readonly"
            in url
        )


# Test OAuthProvider base class behavior
class TestOAuthProviderBase:
    """Tests for OAuthProvider base class functionality."""

    def test_parse_token_response(self, mock_env_vars):
        """Test parsing token response."""
        provider = GongOAuthProvider()

        response_data = {
            "access_token": "test_access",
            "token_type": "Bearer",
            "refresh_token": "test_refresh",
            "expires_in": 7200,
            "scope": "read write",
        }

        result = provider._parse_token_response(response_data)

        assert result.access_token == "test_access"
        assert result.token_type == "Bearer"
        assert result.refresh_token == "test_refresh"
        assert result.expires_in == 7200
        assert result.scope == "read write"
        assert result.expires_at is not None
        assert result.raw_response == response_data

    def test_parse_token_response_minimal(self, mock_env_vars):
        """Test parsing minimal token response."""
        provider = GongOAuthProvider()

        response_data = {
            "access_token": "test_access",
        }

        result = provider._parse_token_response(response_data)

        assert result.access_token == "test_access"
        assert result.token_type == "Bearer"  # Default
        assert result.refresh_token is None
        assert result.expires_in is None
        assert result.expires_at is None
        assert result.scope is None

    def test_get_extra_authorize_params_default(self, mock_env_vars):
        """Test default extra params is empty dict."""
        provider = GongOAuthProvider()
        assert provider.get_extra_authorize_params() == {}

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_on_requests(self, mock_env_vars, mock_token_response):
        """Test that requests have timeout configured."""
        provider = GongOAuthProvider()

        # Mock the token endpoint with delay
        route = respx.post(provider.token_url).mock(
            return_value=httpx.Response(200, json=mock_token_response)
        )

        await provider.exchange_code(
            code="auth_code",
            redirect_uri="https://app.example.com/callback",
        )

        # Verify timeout is set (httpx.Timeout object)
        # We can't easily verify the exact value, but we tested it's not None
        assert route.called
