# Enterprise Data Connectors Framework

Base framework for connecting to enterprise data sources like Gong, Fireflies, Linear, Notion, etc.

## Quick Start

### Creating a New Connector

```python
from src.connectors import BaseConnector, ConnectorType, AuthType, connector

@connector
class MyConnector(BaseConnector):
    """My custom connector implementation."""

    connector_type = ConnectorType.GONG
    display_name = "Gong"
    description = "Sync sales call recordings and transcripts"
    auth_type = AuthType.OAUTH2
    supports_webhook = True

    def get_oauth_config(self):
        """Return OAuth config for this connector."""
        return OAuthConfig(
            authorize_url="https://api.gong.io/oauth/authorize",
            token_url="https://api.gong.io/oauth/token",
            client_id=os.getenv("GONG_CLIENT_ID"),
            client_secret=os.getenv("GONG_CLIENT_SECRET"),
            scopes=["api:calls:read", "api:transcripts:read"],
        )

    def get_required_config_fields(self):
        """Return required config field names."""
        return ["workspace_id"]

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """Verify credentials are valid."""
        try:
            # Test API call with instance.oauth_tokens.access_token
            response = await self._api_call("/v2/users/me", instance)
            return response.status == 200
        except Exception:
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform incremental sync from cursor."""
        try:
            # Fetch new items since instance.sync_cursor
            items = await self._fetch_items(instance, cursor=instance.sync_cursor)

            # Extract knowledge from items
            for item in items:
                await self._extract_and_store(item, instance.org_id)

            return SyncResult(
                success=True,
                items_fetched=len(items),
                items_created=len(items),
                cursor_after=items[-1]["id"] if items else instance.sync_cursor,
            )
        except Exception as e:
            return SyncResult(
                success=False,
                error_message=str(e),
            )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform full historical sync."""
        # Similar to sync() but without cursor
        pass
```

### Using the Connector

```python
from src.connectors import ConnectorRegistry, ConnectorInstance

# Get connector from registry
registry = ConnectorRegistry.get()
gong = registry.get_connector(ConnectorType.GONG)

# Create instance for an org
instance = ConnectorInstance.create_new(
    org_id="my-org-123",
    connector_type=ConnectorType.GONG,
    config={"workspace_id": "ws-456"},
    oauth_tokens=OAuthTokens(
        access_token="access_token_here",
        refresh_token="refresh_token_here",
    ),
)

# Test connection
connected = await gong.test_connection(instance)
if not connected:
    print("Failed to connect")
    return

# Perform sync
result = await gong.sync(instance)
print(f"Synced {result.items_created} items")

# Update instance with new cursor
instance.sync_cursor = result.cursor_after
```

## Core Types

### ConnectorType (Enum)
Supported connector types:
- `GONG` - Gong sales calls
- `FIREFLIES` - Fireflies meeting transcripts
- `LINEAR` - Linear issues and project data
- `NOTION` - Notion documents
- `GOOGLE_DOCS` - Google Docs
- `LOOM` - Loom videos
- `MIRO` - Miro boards
- `CLOSE` - Close CRM

### AuthType (Enum)
Authentication methods:
- `OAUTH2` - OAuth 2.0 flow
- `API_KEY` - API key authentication
- `MANUAL` - Manual upload (screenshots, etc.)

### ConnectorStatus (Enum)
Connector instance states:
- `PENDING` - Not yet connected
- `CONNECTED` - Connected and ready
- `SYNCING` - Currently syncing
- `ERROR` - Error state
- `DISABLED` - Disabled by user

### ConnectorInstance (DataClass)
A configured instance of a connector for a specific org.

**Key Fields:**
- `id`: Unique instance ID
- `org_id`: Organization owner
- `connector_type`: Type of connector
- `status`: Current status
- `oauth_tokens`: OAuth tokens (if OAuth2)
- `config`: Connector-specific config
- `sync_cursor`: Cursor for incremental sync
- `items_synced`: Total items synced
- `last_sync_at`: Last sync timestamp
- `next_sync_at`: Next scheduled sync

### SyncResult (DataClass)
Result of a sync operation.

**Key Fields:**
- `success`: Whether sync succeeded
- `items_fetched`: Items fetched from source
- `items_extracted`: Items processed
- `items_created`: New knowledge entries
- `items_skipped`: Duplicates/filtered
- `cursor_after`: New cursor position
- `error_message`: Error if failed

### OAuthTokens (DataClass)
OAuth 2.0 token storage.

**Key Fields:**
- `access_token`: Access token
- `refresh_token`: Refresh token (optional)
- `expires_at`: Expiration datetime (optional)
- `token_type`: Token type (default: "Bearer")
- `scope`: OAuth scopes (optional)

### OAuthConfig (DataClass)
OAuth 2.0 configuration.

**Key Fields:**
- `authorize_url`: Authorization URL
- `token_url`: Token exchange URL
- `client_id`: OAuth client ID
- `client_secret`: OAuth client secret
- `scopes`: Required scopes
- `redirect_uri`: Redirect URI (optional)

## Registry

### ConnectorRegistry
Singleton registry for managing connectors.

**Methods:**
- `get()`: Get singleton instance
- `register(connector_class)`: Register a connector
- `get_connector(connector_type)`: Get connector instance
- `list_available()`: List all registered connectors
- `is_registered(connector_type)`: Check if registered

### @connector Decorator
Auto-registers connector classes on import.

```python
@connector
class MyConnector(BaseConnector):
    connector_type = ConnectorType.GONG
    ...
```

## Testing

Run tests:
```bash
python3 -m pytest tests/connectors/ -v
```

All 61 tests should pass with 100% coverage.

## Architecture

```
┌─────────────────────────────────────────────┐
│         Connector Framework                  │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  ConnectorRegistry (Singleton)         │ │
│  │  - register()                          │ │
│  │  - get_connector()                     │ │
│  │  - list_available()                    │ │
│  └────────────────────────────────────────┘ │
│                    │                         │
│                    ▼                         │
│  ┌────────────────────────────────────────┐ │
│  │  BaseConnector (Abstract)              │ │
│  │  - test_connection()                   │ │
│  │  - sync()                              │ │
│  │  - full_sync()                         │ │
│  └────────────────────────────────────────┘ │
│            │            │            │       │
│            ▼            ▼            ▼       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Gong    │  │Fireflies │  │  Linear  │  │
│  │Connector │  │Connector │  │Connector │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
```

## Next Steps

Ready to implement specific connectors:
1. GongConnector (OAuth2 + webhooks)
2. FirefliesConnector (API key)
3. LinearConnector (OAuth2)
4. NotionConnector (OAuth2)
5. GoogleDocsConnector (OAuth2)
6. LoomConnector (API key)
7. MiroConnector (OAuth2)
8. CloseConnector (API key)
