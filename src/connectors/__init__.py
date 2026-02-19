"""Enterprise Data Connectors - Public API

This module provides the base framework for connecting to enterprise data sources
like Gong, Fireflies, Linear, Notion, etc.

Example:
    from src.connectors import (
        BaseConnector,
        ConnectorType,
        ConnectorRegistry,
        connector,
    )

    @connector
    class GongConnector(BaseConnector):
        connector_type = ConnectorType.GONG
        display_name = "Gong"
        description = "Sync sales call recordings and transcripts"
        auth_type = AuthType.OAUTH2

        async def test_connection(self, instance):
            # Implementation
            pass

        async def sync(self, instance):
            # Implementation
            pass
"""

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
# Import all connectors to trigger @connector decorator registration
from src.connectors.clari.connector import ClariConnector  # noqa: F401
from src.connectors.close.connector import CloseConnector  # noqa: F401
from src.connectors.fireflies.connector import FirefliesConnector  # noqa: F401
from src.connectors.gong.connector import GongConnector  # noqa: F401
from src.connectors.hubspot.connector import HubSpotConnector  # noqa: F401
from src.connectors.registry import ConnectorRegistry, connector

__all__ = [
    # Core types
    "BaseConnector",
    "ConnectorType",
    "AuthType",
    "ConnectorStatus",
    # Data classes
    "ConnectorInstance",
    "OAuthTokens",
    "OAuthConfig",
    "SyncResult",
    # Registry
    "ConnectorRegistry",
    "connector",
]
