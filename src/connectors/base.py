"""Base connector types and abstract class.

This module defines the core types and base class for all data connectors.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ConnectorType(str, Enum):
    """Supported connector types."""

    GONG = "gong"
    FIREFLIES = "fireflies"
    LINEAR = "linear"
    NOTION = "notion"
    GOOGLE_DOCS = "google_docs"
    LOOM = "loom"
    MIRO = "miro"
    CLOSE = "close"


class AuthType(str, Enum):
    """Authentication methods supported by connectors."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    MANUAL = "manual"


class ConnectorStatus(str, Enum):
    """Connector instance status."""

    PENDING = "pending"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class OAuthTokens:
    """OAuth 2.0 token data."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    token_type: str = "Bearer"
    scope: str | None = None


@dataclass
class ConnectorInstance:
    """A configured instance of a connector for a specific org.

    Attributes:
        id: Unique instance ID
        org_id: Organization that owns this instance
        connector_type: Type of connector
        status: Current connection status
        oauth_tokens: OAuth tokens if using OAuth2 auth
        config: Connector-specific configuration
        last_sync_at: When last sync completed
        next_sync_at: When next sync is scheduled
        sync_cursor: Cursor for incremental syncing
        items_synced: Total items synced lifetime
        error_message: Last error message
        error_count: Consecutive error count
        created_at: When instance was created
        updated_at: When instance was last updated
    """

    id: str
    org_id: str
    connector_type: ConnectorType
    status: ConnectorStatus = ConnectorStatus.PENDING
    oauth_tokens: OAuthTokens | None = None
    config: dict = field(default_factory=dict)
    last_sync_at: datetime | None = None
    next_sync_at: datetime | None = None
    sync_cursor: str | None = None
    items_synced: int = 0
    error_message: str | None = None
    error_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create_new(
        cls,
        org_id: str,
        connector_type: ConnectorType,
        config: dict | None = None,
        oauth_tokens: OAuthTokens | None = None,
    ) -> "ConnectorInstance":
        """Create a new connector instance with generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            org_id=org_id,
            connector_type=connector_type,
            config=config or {},
            oauth_tokens=oauth_tokens,
        )


@dataclass
class SyncResult:
    """Result of a sync operation.

    Attributes:
        success: Whether sync completed successfully
        items_fetched: Number of items fetched from source
        items_extracted: Number of items processed by extraction
        items_created: Number of new knowledge entries created
        items_skipped: Number of items skipped (duplicates, etc.)
        cursor_after: Cursor position after sync for next incremental sync
        error_message: Summary error message if failed
        errors: List of detailed error dicts
    """

    success: bool
    items_fetched: int = 0
    items_extracted: int = 0
    items_created: int = 0
    items_skipped: int = 0
    cursor_after: str | None = None
    error_message: str | None = None
    errors: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "success": self.success,
            "items_fetched": self.items_fetched,
            "items_extracted": self.items_extracted,
            "items_created": self.items_created,
            "items_skipped": self.items_skipped,
            "cursor_after": self.cursor_after,
            "error_message": self.error_message,
            "errors": self.errors,
        }


@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration for a connector.

    Attributes:
        authorize_url: OAuth authorization URL
        token_url: OAuth token exchange URL
        client_id: OAuth client ID
        client_secret: OAuth client secret
        scopes: Required OAuth scopes
        redirect_uri: OAuth redirect URI (optional)
    """

    authorize_url: str
    token_url: str
    client_id: str
    client_secret: str
    scopes: list[str] = field(default_factory=list)
    redirect_uri: str | None = None


class BaseConnector(ABC):
    """Abstract base class for all data connectors.

    Subclasses must define:
        - connector_type: ConnectorType enum value
        - display_name: Human-readable name
        - description: Brief description
        - auth_type: AuthType enum value
        - supports_webhook: Whether webhooks are supported
        - test_connection(): Verify credentials
        - sync(): Incremental sync
        - full_sync(): Full historical sync

    Optional overrides:
        - get_oauth_config(): Return OAuth config if auth_type is OAUTH2
        - get_required_config_fields(): Return required config field names
        - validate_config(): Custom config validation
    """

    connector_type: ConnectorType
    display_name: str
    description: str
    auth_type: AuthType
    supports_webhook: bool = False

    @abstractmethod
    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """Verify credentials are valid.

        Args:
            instance: Connector instance with credentials

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform incremental sync from cursor.

        Args:
            instance: Connector instance with sync cursor

        Returns:
            SyncResult with items synced and new cursor
        """
        pass

    @abstractmethod
    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform full historical sync.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        pass

    def get_oauth_config(self) -> OAuthConfig | None:
        """Return OAuth config if auth_type is OAUTH2.

        Override in subclass if using OAuth2.

        Returns:
            OAuthConfig or None
        """
        return None

    def get_required_config_fields(self) -> list[str]:
        """Return list of required config field names.

        Override in subclass to specify required fields.

        Returns:
            List of required field names
        """
        return []

    def validate_config(self, config: dict) -> tuple[bool, str | None]:
        """Validate connector config.

        Args:
            config: Config dict to validate

        Returns:
            Tuple of (valid, error_message)
        """
        required = self.get_required_config_fields()
        for field in required:
            if field not in config:
                return False, f"Missing required config field: {field}"
        return True, None

    def to_dict(self) -> dict:
        """Return connector metadata as dict.

        Returns:
            Dict with connector metadata
        """
        return {
            "type": self.connector_type.value,
            "display_name": self.display_name,
            "description": self.description,
            "auth_type": self.auth_type.value,
            "supports_webhook": self.supports_webhook,
            "required_config_fields": self.get_required_config_fields(),
        }
