"""Integration tests for Notion connector."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.base import ConnectorInstance, ConnectorType, OAuthTokens
from src.connectors.notion.connector import NotionConnector
from src.connectors.notion.schemas import (
    NotionDatabase,
    NotionPage,
    NotionParent,
    NotionRichText,
)


@pytest.fixture
def connector():
    """Create Notion connector."""
    return NotionConnector()


@pytest.fixture
def connector_instance():
    """Create connector instance with OAuth tokens."""
    return ConnectorInstance(
        id="instance-456",
        org_id="test-org",
        connector_type=ConnectorType.NOTION,
        oauth_tokens=OAuthTokens(access_token="test-token-456"),
        config={
            "sync_pages": True,
            "sync_databases": True,
            "sync_blocks": True,
            "page_size": 100,
        },
    )


@pytest.mark.asyncio
async def test_test_connection_success(connector, connector_instance):
    """Test successful connection test."""
    mock_results = [
        NotionPage(
            id="page-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="workspace"),
            properties={},
            url="https://notion.so/page-1",
        )
    ]

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(return_value=(mock_results, None))

        result = await connector.test_connection(connector_instance)

    assert result is True


@pytest.mark.asyncio
async def test_test_connection_failure(connector, connector_instance):
    """Test failed connection test."""
    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=Exception("Unauthorized"))

        result = await connector.test_connection(connector_instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_no_tokens(connector):
    """Test connection test without OAuth tokens."""
    instance = ConnectorInstance(
        id="instance-456",
        org_id="test-org",
        connector_type=ConnectorType.NOTION,
        oauth_tokens=None,
    )

    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_pages_and_databases(connector, connector_instance):
    """Test syncing pages and databases."""
    # Mock pages
    mock_pages = [
        NotionPage(
            id="page-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="workspace"),
            properties={
                "title": {
                    "type": "title",
                    "title": [{"plain_text": "Product Roadmap"}],
                }
            },
            url="https://notion.so/page-1",
        )
    ]

    # Mock databases
    mock_databases = [
        NotionDatabase(
            id="db-1",
            created_time=datetime(2025, 11, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            title=[NotionRichText(type="text", text={}, plain_text="Features")],
            parent=NotionParent(type="workspace"),
            properties={},
            url="https://notion.so/db-1",
        )
    ]

    # Mock database pages
    mock_db_pages = []

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient, \
         patch.object(connector.transformer, "transform_page", new=AsyncMock(
             return_value=(MagicMock(), [MagicMock()])
         )), \
         patch.object(connector.transformer, "transform_database", new=AsyncMock(
             return_value=(MagicMock(), [MagicMock()])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=1, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=[
            (mock_pages, "cursor-p"),  # Pages search
            (mock_databases, None),    # Databases search
        ])
        mock_client.get_all_blocks = AsyncMock(return_value=[])
        mock_client.query_database = AsyncMock(return_value=(mock_db_pages, None))

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 2  # 1 page + 1 database
    assert result.items_extracted == 2
    assert result.items_created == 2


@pytest.mark.asyncio
async def test_sync_with_cursor(connector, connector_instance):
    """Test incremental sync with cursor."""
    connector_instance.sync_cursor = "pages:prev-page-cursor|databases:prev-db-cursor"

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=[
            ([], None),  # Pages
            ([], None),  # Databases
        ])

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 0
    assert result.cursor_after is None

    # Verify cursors were passed
    calls = mock_client.search.call_args_list
    assert calls[0].kwargs["cursor"] == "prev-page-cursor"
    assert calls[1].kwargs["cursor"] == "prev-db-cursor"


@pytest.mark.asyncio
async def test_sync_pages_only(connector, connector_instance):
    """Test syncing only pages."""
    connector_instance.config["sync_pages"] = True
    connector_instance.config["sync_databases"] = False

    mock_pages = [
        NotionPage(
            id="page-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="workspace"),
            properties={},
            url="https://notion.so/page-1",
        )
    ]

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient, \
         patch.object(connector.transformer, "transform_page", new=AsyncMock(
             return_value=(MagicMock(), [])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=0, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(return_value=(mock_pages, None))
        mock_client.get_all_blocks = AsyncMock(return_value=[])

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 1

    # Verify only one search call (for pages)
    assert mock_client.search.call_count == 1


@pytest.mark.asyncio
async def test_sync_specific_databases(connector, connector_instance):
    """Test syncing specific database IDs."""
    connector_instance.config["database_ids"] = ["db-123", "db-456"]
    connector_instance.config["sync_pages"] = False
    connector_instance.config["sync_databases"] = True

    mock_database = NotionDatabase(
        id="db-123",
        created_time=datetime(2025, 11, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        title=[NotionRichText(type="text", text={}, plain_text="Test DB")],
        parent=NotionParent(type="workspace"),
        properties={},
        url="https://notion.so/db-123",
    )

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient, \
         patch.object(connector.transformer, "transform_database", new=AsyncMock(
             return_value=(MagicMock(), [])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=0, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.get_database = AsyncMock(return_value=mock_database)
        mock_client.query_database = AsyncMock(return_value=([], None))

        result = await connector.sync(connector_instance)

    assert result.success is True

    # Verify get_database was called for each ID
    assert mock_client.get_database.call_count == 2


@pytest.mark.asyncio
async def test_sync_without_blocks(connector, connector_instance):
    """Test syncing pages without fetching blocks."""
    connector_instance.config["sync_blocks"] = False

    mock_pages = [
        NotionPage(
            id="page-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="workspace"),
            properties={},
            url="https://notion.so/page-1",
        )
    ]

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient, \
         patch.object(connector.transformer, "transform_page", new=AsyncMock(
             return_value=(MagicMock(), [])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=0, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=[
            (mock_pages, None),
            ([], None),  # Databases
        ])

        result = await connector.sync(connector_instance)

    assert result.success is True

    # Verify get_all_blocks was not called
    mock_client.get_all_blocks.assert_not_called()


@pytest.mark.asyncio
async def test_full_sync(connector, connector_instance):
    """Test full sync clears cursor."""
    connector_instance.sync_cursor = "pages:old-cursor"

    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=[
            ([], None),
            ([], None),
        ])

        result = await connector.full_sync(connector_instance)

    assert result.success is True

    # Verify sync was called with cleared cursor
    calls = mock_client.search.call_args_list
    assert calls[0].kwargs["cursor"] is None


@pytest.mark.asyncio
async def test_sync_error_handling(connector, connector_instance):
    """Test sync error handling."""
    with patch("src.connectors.notion.connector.NotionAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.search = AsyncMock(side_effect=Exception("API error"))

        result = await connector.sync(connector_instance)

    assert result.success is False
    assert "API error" in result.error_message


def test_get_oauth_config(connector):
    """Test OAuth config retrieval."""
    import os

    # Set environment variables
    os.environ["NOTION_CLIENT_ID"] = "test-client-id"
    os.environ["NOTION_CLIENT_SECRET"] = "test-client-secret"
    os.environ["NOTION_REDIRECT_URI"] = "https://example.com/callback"

    config = connector.get_oauth_config()

    assert config is not None
    assert config.client_id == "test-client-id"
    assert config.client_secret == "test-client-secret"
    assert config.redirect_uri == "https://example.com/callback"
    assert config.authorize_url == "https://api.notion.com/v1/oauth/authorize"
    assert config.token_url == "https://api.notion.com/v1/oauth/token"

    # Cleanup
    del os.environ["NOTION_CLIENT_ID"]
    del os.environ["NOTION_CLIENT_SECRET"]
    del os.environ["NOTION_REDIRECT_URI"]


def test_connector_metadata(connector):
    """Test connector metadata."""
    assert connector.connector_type == ConnectorType.NOTION
    assert connector.display_name == "Notion"
    assert connector.auth_type.value == "oauth2"
    assert connector.supports_webhook is False

    metadata = connector.to_dict()
    assert metadata["type"] == "notion"
    assert metadata["display_name"] == "Notion"
    assert metadata["supports_webhook"] is False
