"""Tests for connector base types and abstract class."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    OAuthConfig,
    OAuthTokens,
    SyncResult,
)


class TestConnectorType:
    """Test ConnectorType enum."""

    def test_all_values(self):
        """Test all enum values are correct."""
        assert ConnectorType.GONG.value == "gong"
        assert ConnectorType.FIREFLIES.value == "fireflies"
        assert ConnectorType.LINEAR.value == "linear"
        assert ConnectorType.NOTION.value == "notion"
        assert ConnectorType.GOOGLE_DOCS.value == "google_docs"
        assert ConnectorType.LOOM.value == "loom"
        assert ConnectorType.MIRO.value == "miro"
        assert ConnectorType.CLOSE.value == "close"

    def test_string_representation(self):
        """Test enum can be used as string."""
        connector_type = ConnectorType.GONG
        assert connector_type.value == "gong"
        assert connector_type == "gong"


class TestAuthType:
    """Test AuthType enum."""

    def test_all_values(self):
        """Test all enum values are correct."""
        assert AuthType.OAUTH2.value == "oauth2"
        assert AuthType.API_KEY.value == "api_key"
        assert AuthType.MANUAL.value == "manual"

    def test_string_representation(self):
        """Test enum can be used as string."""
        auth_type = AuthType.OAUTH2
        assert auth_type.value == "oauth2"
        assert auth_type == "oauth2"


class TestConnectorStatus:
    """Test ConnectorStatus enum."""

    def test_all_values(self):
        """Test all enum values are correct."""
        assert ConnectorStatus.PENDING.value == "pending"
        assert ConnectorStatus.CONNECTED.value == "connected"
        assert ConnectorStatus.SYNCING.value == "syncing"
        assert ConnectorStatus.ERROR.value == "error"
        assert ConnectorStatus.DISABLED.value == "disabled"

    def test_string_representation(self):
        """Test enum can be used as string."""
        status = ConnectorStatus.CONNECTED
        assert status.value == "connected"
        assert status == "connected"


class TestOAuthTokens:
    """Test OAuthTokens dataclass."""

    def test_minimal_creation(self):
        """Test creating with only required fields."""
        tokens = OAuthTokens(access_token="abc123")
        assert tokens.access_token == "abc123"
        assert tokens.refresh_token is None
        assert tokens.expires_at is None
        assert tokens.token_type == "Bearer"
        assert tokens.scope is None

    def test_full_creation(self):
        """Test creating with all fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        tokens = OAuthTokens(
            access_token="abc123",
            refresh_token="xyz789",
            expires_at=expires_at,
            token_type="Bearer",
            scope="read write",
        )
        assert tokens.access_token == "abc123"
        assert tokens.refresh_token == "xyz789"
        assert tokens.expires_at == expires_at
        assert tokens.token_type == "Bearer"
        assert tokens.scope == "read write"

    def test_custom_token_type(self):
        """Test custom token type."""
        tokens = OAuthTokens(access_token="abc123", token_type="Custom")
        assert tokens.token_type == "Custom"


class TestConnectorInstance:
    """Test ConnectorInstance dataclass."""

    def test_minimal_creation(self):
        """Test creating with only required fields."""
        instance = ConnectorInstance(
            id="test-id",
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        assert instance.id == "test-id"
        assert instance.org_id == "org-123"
        assert instance.connector_type == ConnectorType.GONG
        assert instance.status == ConnectorStatus.PENDING
        assert instance.oauth_tokens is None
        assert instance.config == {}
        assert instance.last_sync_at is None
        assert instance.next_sync_at is None
        assert instance.sync_cursor is None
        assert instance.items_synced == 0
        assert instance.error_message is None
        assert instance.error_count == 0
        assert isinstance(instance.created_at, datetime)
        assert isinstance(instance.updated_at, datetime)

    def test_full_creation(self):
        """Test creating with all fields."""
        tokens = OAuthTokens(access_token="abc123")
        last_sync = datetime.now(timezone.utc)
        next_sync = datetime.now(timezone.utc) + timedelta(hours=1)
        created = datetime.now(timezone.utc) - timedelta(days=1)
        updated = datetime.now(timezone.utc)

        instance = ConnectorInstance(
            id="test-id",
            org_id="org-123",
            connector_type=ConnectorType.GONG,
            status=ConnectorStatus.CONNECTED,
            oauth_tokens=tokens,
            config={"api_key": "secret"},
            last_sync_at=last_sync,
            next_sync_at=next_sync,
            sync_cursor="cursor-123",
            items_synced=100,
            error_message="Test error",
            error_count=3,
            created_at=created,
            updated_at=updated,
        )
        assert instance.id == "test-id"
        assert instance.org_id == "org-123"
        assert instance.connector_type == ConnectorType.GONG
        assert instance.status == ConnectorStatus.CONNECTED
        assert instance.oauth_tokens == tokens
        assert instance.config == {"api_key": "secret"}
        assert instance.last_sync_at == last_sync
        assert instance.next_sync_at == next_sync
        assert instance.sync_cursor == "cursor-123"
        assert instance.items_synced == 100
        assert instance.error_message == "Test error"
        assert instance.error_count == 3
        assert instance.created_at == created
        assert instance.updated_at == updated

    def test_create_new_minimal(self):
        """Test create_new with minimal args."""
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        assert instance.org_id == "org-123"
        assert instance.connector_type == ConnectorType.GONG
        assert instance.status == ConnectorStatus.PENDING
        assert instance.config == {}
        assert instance.oauth_tokens is None
        # Verify UUID format
        uuid.UUID(instance.id)

    def test_create_new_with_config(self):
        """Test create_new with config."""
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
            config={"workspace_id": "ws-123"},
        )
        assert instance.config == {"workspace_id": "ws-123"}

    def test_create_new_with_oauth_tokens(self):
        """Test create_new with OAuth tokens."""
        tokens = OAuthTokens(access_token="abc123")
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
            oauth_tokens=tokens,
        )
        assert instance.oauth_tokens == tokens

    def test_create_new_generates_unique_ids(self):
        """Test create_new generates unique IDs."""
        instance1 = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        instance2 = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        assert instance1.id != instance2.id


class TestSyncResult:
    """Test SyncResult dataclass."""

    def test_success_minimal(self):
        """Test creating successful result with minimal fields."""
        result = SyncResult(success=True)
        assert result.success is True
        assert result.items_fetched == 0
        assert result.items_extracted == 0
        assert result.items_created == 0
        assert result.items_skipped == 0
        assert result.cursor_after is None
        assert result.error_message is None
        assert result.errors == []

    def test_success_full(self):
        """Test creating successful result with all fields."""
        result = SyncResult(
            success=True,
            items_fetched=100,
            items_extracted=95,
            items_created=50,
            items_skipped=45,
            cursor_after="next-cursor",
        )
        assert result.success is True
        assert result.items_fetched == 100
        assert result.items_extracted == 95
        assert result.items_created == 50
        assert result.items_skipped == 45
        assert result.cursor_after == "next-cursor"
        assert result.error_message is None
        assert result.errors == []

    def test_failure_with_error(self):
        """Test creating failed result with error."""
        result = SyncResult(
            success=False,
            error_message="Connection failed",
            errors=[{"line": 1, "error": "Timeout"}],
        )
        assert result.success is False
        assert result.error_message == "Connection failed"
        assert len(result.errors) == 1
        assert result.errors[0] == {"line": 1, "error": "Timeout"}

    def test_to_dict(self):
        """Test to_dict serialization."""
        result = SyncResult(
            success=True,
            items_fetched=10,
            items_created=5,
            cursor_after="cursor",
        )
        data = result.to_dict()
        assert data == {
            "success": True,
            "items_fetched": 10,
            "items_extracted": 0,
            "items_created": 5,
            "items_skipped": 0,
            "cursor_after": "cursor",
            "error_message": None,
            "errors": [],
        }


class TestOAuthConfig:
    """Test OAuthConfig dataclass."""

    def test_minimal_creation(self):
        """Test creating with required fields."""
        config = OAuthConfig(
            authorize_url="https://auth.example.com/oauth/authorize",
            token_url="https://auth.example.com/oauth/token",
            client_id="client-123",
            client_secret="secret-456",
        )
        assert config.authorize_url == "https://auth.example.com/oauth/authorize"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "client-123"
        assert config.client_secret == "secret-456"
        assert config.scopes == []
        assert config.redirect_uri is None

    def test_full_creation(self):
        """Test creating with all fields."""
        config = OAuthConfig(
            authorize_url="https://auth.example.com/oauth/authorize",
            token_url="https://auth.example.com/oauth/token",
            client_id="client-123",
            client_secret="secret-456",
            scopes=["read", "write"],
            redirect_uri="https://app.example.com/callback",
        )
        assert config.scopes == ["read", "write"]
        assert config.redirect_uri == "https://app.example.com/callback"


class TestBaseConnector:
    """Test BaseConnector abstract class."""

    class MockConnector(BaseConnector):
        """Mock connector for testing."""

        connector_type = ConnectorType.GONG
        display_name = "Mock Gong"
        description = "Mock Gong connector for testing"
        auth_type = AuthType.OAUTH2
        supports_webhook = True

        async def test_connection(self, instance: ConnectorInstance) -> bool:
            return True

        async def sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True, items_fetched=10)

        async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True, items_fetched=100)

    class ConfigConnector(BaseConnector):
        """Mock connector with required config."""

        connector_type = ConnectorType.LINEAR
        display_name = "Mock Linear"
        description = "Mock Linear connector"
        auth_type = AuthType.API_KEY

        def get_required_config_fields(self) -> list[str]:
            return ["api_key", "workspace_id"]

        async def test_connection(self, instance: ConnectorInstance) -> bool:
            return True

        async def sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

        async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

    class OAuthConnector(BaseConnector):
        """Mock connector with OAuth config."""

        connector_type = ConnectorType.NOTION
        display_name = "Mock Notion"
        description = "Mock Notion connector"
        auth_type = AuthType.OAUTH2

        def get_oauth_config(self) -> OAuthConfig:
            return OAuthConfig(
                authorize_url="https://notion.com/oauth/authorize",
                token_url="https://notion.com/oauth/token",
                client_id="notion-client",
                client_secret="notion-secret",
                scopes=["read_content"],
            )

        async def test_connection(self, instance: ConnectorInstance) -> bool:
            return True

        async def sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

        async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
            return SyncResult(success=True)

    def test_cannot_instantiate_abstract_class(self):
        """Test BaseConnector cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseConnector()

    @pytest.mark.asyncio
    async def test_test_connection(self):
        """Test test_connection implementation."""
        connector = self.MockConnector()
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        result = await connector.test_connection(instance)
        assert result is True

    @pytest.mark.asyncio
    async def test_sync(self):
        """Test sync implementation."""
        connector = self.MockConnector()
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        result = await connector.sync(instance)
        assert result.success is True
        assert result.items_fetched == 10

    @pytest.mark.asyncio
    async def test_full_sync(self):
        """Test full_sync implementation."""
        connector = self.MockConnector()
        instance = ConnectorInstance.create_new(
            org_id="org-123",
            connector_type=ConnectorType.GONG,
        )
        result = await connector.full_sync(instance)
        assert result.success is True
        assert result.items_fetched == 100

    def test_get_oauth_config_default(self):
        """Test get_oauth_config returns None by default."""
        connector = self.MockConnector()
        assert connector.get_oauth_config() is None

    def test_get_oauth_config_override(self):
        """Test get_oauth_config override."""
        connector = self.OAuthConnector()
        config = connector.get_oauth_config()
        assert config is not None
        assert config.authorize_url == "https://notion.com/oauth/authorize"
        assert config.client_id == "notion-client"
        assert config.scopes == ["read_content"]

    def test_get_required_config_fields_default(self):
        """Test get_required_config_fields returns empty list by default."""
        connector = self.MockConnector()
        assert connector.get_required_config_fields() == []

    def test_get_required_config_fields_override(self):
        """Test get_required_config_fields override."""
        connector = self.ConfigConnector()
        assert connector.get_required_config_fields() == ["api_key", "workspace_id"]

    def test_validate_config_success(self):
        """Test validate_config with valid config."""
        connector = self.ConfigConnector()
        valid, error = connector.validate_config(
            {"api_key": "secret", "workspace_id": "ws-123"}
        )
        assert valid is True
        assert error is None

    def test_validate_config_missing_field(self):
        """Test validate_config with missing field."""
        connector = self.ConfigConnector()
        valid, error = connector.validate_config({"api_key": "secret"})
        assert valid is False
        assert error == "Missing required config field: workspace_id"

    def test_validate_config_no_required_fields(self):
        """Test validate_config with no required fields."""
        connector = self.MockConnector()
        valid, error = connector.validate_config({})
        assert valid is True
        assert error is None

    def test_to_dict(self):
        """Test to_dict returns correct metadata."""
        connector = self.MockConnector()
        data = connector.to_dict()
        assert data == {
            "type": "gong",
            "display_name": "Mock Gong",
            "description": "Mock Gong connector for testing",
            "auth_type": "oauth2",
            "supports_webhook": True,
            "required_config_fields": [],
        }

    def test_to_dict_with_required_fields(self):
        """Test to_dict includes required config fields."""
        connector = self.ConfigConnector()
        data = connector.to_dict()
        assert data["required_config_fields"] == ["api_key", "workspace_id"]

    def test_class_attributes(self):
        """Test connector class attributes."""
        connector = self.MockConnector()
        assert connector.connector_type == ConnectorType.GONG
        assert connector.display_name == "Mock Gong"
        assert connector.description == "Mock Gong connector for testing"
        assert connector.auth_type == AuthType.OAUTH2
        assert connector.supports_webhook is True

    def test_supports_webhook_default(self):
        """Test supports_webhook defaults to False."""
        connector = self.ConfigConnector()
        assert connector.supports_webhook is False
