"""Tests for Google Docs connector."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.base import (
    ConnectorInstance,
    ConnectorType,
    OAuthTokens,
    SyncResult,
)
from src.connectors.google_docs.connector import GoogleDocsConnector
from src.connectors.google_docs.schemas import GoogleDocument, GoogleDriveFile
from src.knowledge.base import (
    ExtractionResult,
    KnowledgeEntry,
    KnowledgeSource,
    KnowledgeType,
)


@pytest.fixture
def connector():
    """Create GoogleDocsConnector instance."""
    return GoogleDocsConnector()


@pytest.fixture
def connector_instance():
    """Create connector instance with OAuth tokens."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GOOGLE_DOCS,
        oauth_tokens=OAuthTokens(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
        ),
        config={"page_size": 50},
    )


@pytest.fixture
def mock_drive_file():
    """Mock GoogleDriveFile."""
    return GoogleDriveFile(
        id="doc_123",
        name="Product Roadmap 2025",
        mimeType="application/vnd.google-apps.document",
        modifiedTime=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
        createdTime=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        webViewLink="https://docs.google.com/document/d/doc_123/edit",
    )


@pytest.fixture
def mock_document():
    """Mock GoogleDocument."""
    return GoogleDocument(
        documentId="doc_123",
        title="Product Roadmap 2025",
        body={"content": []},
        revisionId="rev_123",
    )


def test_connector_metadata(connector):
    """Test connector metadata."""
    assert connector.connector_type == ConnectorType.GOOGLE_DOCS
    assert connector.display_name == "Google Docs"
    assert "documents" in connector.description.lower()
    assert not connector.supports_webhook


def test_get_oauth_config(connector):
    """Test OAuth configuration."""
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "test_client_id",
            "GOOGLE_CLIENT_SECRET": "test_client_secret",
            "GOOGLE_REDIRECT_URI": "https://example.com/callback",
        },
    ):
        config = connector.get_oauth_config()

    assert config is not None
    assert config.client_id == "test_client_id"
    assert config.client_secret == "test_client_secret"
    assert config.authorize_url == "https://accounts.google.com/o/oauth2/v2/auth"
    assert config.token_url == "https://oauth2.googleapis.com/token"
    assert "documents.readonly" in config.scopes[0]
    assert "drive.readonly" in config.scopes[1]


def test_get_oauth_config_missing_credentials(connector):
    """Test OAuth config when credentials are missing."""
    with patch.dict("os.environ", {}, clear=True):
        config = connector.get_oauth_config()

    assert config is None


@pytest.mark.asyncio
async def test_test_connection_success(connector, connector_instance):
    """Test successful connection test."""
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(return_value=([], None))

    with patch(
        "src.connectors.google_docs.connector.GoogleDocsAPIClient",
        return_value=mock_client,
    ):
        result = await connector.test_connection(connector_instance)

    assert result is True
    mock_client.list_documents.assert_called_once_with(page_size=1)


@pytest.mark.asyncio
async def test_test_connection_no_oauth_tokens(connector):
    """Test connection test without OAuth tokens."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GOOGLE_DOCS,
    )

    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(connector, connector_instance):
    """Test connection test with API error."""
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(side_effect=Exception("API Error"))

    with patch(
        "src.connectors.google_docs.connector.GoogleDocsAPIClient",
        return_value=mock_client,
    ):
        result = await connector.test_connection(connector_instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_incremental(
    connector,
    connector_instance,
    mock_drive_file,
    mock_document,
):
    """Test incremental sync."""
    connector_instance.sync_cursor = "modified_after:2025-01-01T00:00:00Z|page_token:token_123"

    # Mock client
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(return_value=([mock_drive_file], "next_token"))
    mock_client.get_document = AsyncMock(return_value=mock_document)
    mock_client.extract_text_from_body = MagicMock(
        return_value="Product Roadmap 2025\nQ1 Goals: Launch AI assistant."
    )

    # Mock transformer
    mock_source = KnowledgeSource(
        source_type="manual_entry",
        external_id="doc_123",
        source_title="Product Roadmap 2025",
    )
    mock_entry = KnowledgeEntry(
        knowledge_type=KnowledgeType.FEATURE,
        content="AI assistant feature",
        source_id="source_1",
    )

    mock_transformer = MagicMock()
    mock_transformer.transform_document = AsyncMock(return_value=(mock_source, [mock_entry]))

    # Mock knowledge service
    mock_service = MagicMock()
    mock_service.ingest_source = AsyncMock(
        return_value=ExtractionResult(
            source_id="source_1",
            items_created=1,
            items_skipped=0,
        )
    )

    with (
        patch(
            "src.connectors.google_docs.connector.GoogleDocsAPIClient",
            return_value=mock_client,
        ),
        patch.object(connector, "transformer", mock_transformer),
        patch.object(connector, "knowledge_service", mock_service),
    ):
        result = await connector.sync(connector_instance)

    # Verify result
    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_extracted == 1
    assert result.items_created == 1
    assert result.items_skipped == 0
    assert "modified_after" in result.cursor_after
    assert "page_token:next_token" in result.cursor_after

    # Verify API calls
    mock_client.list_documents.assert_called_once()
    call_kwargs = mock_client.list_documents.call_args.kwargs
    assert call_kwargs["page_token"] == "token_123"
    assert call_kwargs["modified_after"] == "2025-01-01T00:00:00Z"

    mock_client.get_document.assert_called_once_with("doc_123")


@pytest.mark.asyncio
async def test_sync_first_sync_no_cursor(
    connector,
    connector_instance,
    mock_drive_file,
    mock_document,
):
    """Test first sync without cursor (defaults to 7 days)."""
    connector_instance.sync_cursor = None

    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(return_value=([mock_drive_file], None))
    mock_client.get_document = AsyncMock(return_value=mock_document)
    mock_client.extract_text_from_body = MagicMock(return_value="Content here")

    mock_transformer = MagicMock()
    mock_source = KnowledgeSource(
        source_type="manual_entry",
        external_id="doc_123",
    )
    mock_transformer.transform_document = AsyncMock(return_value=(mock_source, []))

    mock_service = MagicMock()
    mock_service.ingest_source = AsyncMock(
        return_value=ExtractionResult(source_id="source_1", items_created=0, items_skipped=0)
    )

    with (
        patch(
            "src.connectors.google_docs.connector.GoogleDocsAPIClient",
            return_value=mock_client,
        ),
        patch.object(connector, "transformer", mock_transformer),
        patch.object(connector, "knowledge_service", mock_service),
    ):
        result = await connector.sync(connector_instance)

    assert result.success is True

    # Verify list_documents called with modified_after (7 days ago)
    call_kwargs = mock_client.list_documents.call_args.kwargs
    assert call_kwargs["modified_after"] is not None
    assert "2025-" in call_kwargs["modified_after"]  # Should be recent date


@pytest.mark.asyncio
async def test_sync_empty_document_skipped(
    connector,
    connector_instance,
    mock_drive_file,
    mock_document,
):
    """Test that documents with no text content are skipped."""
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(return_value=([mock_drive_file], None))
    mock_client.get_document = AsyncMock(return_value=mock_document)
    mock_client.extract_text_from_body = MagicMock(return_value="")  # Empty text

    with patch(
        "src.connectors.google_docs.connector.GoogleDocsAPIClient",
        return_value=mock_client,
    ):
        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_skipped == 1
    assert result.items_created == 0


@pytest.mark.asyncio
async def test_sync_document_processing_error(
    connector,
    connector_instance,
    mock_drive_file,
):
    """Test handling of document processing errors."""
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(return_value=([mock_drive_file], None))
    mock_client.get_document = AsyncMock(side_effect=Exception("API Error"))

    with patch(
        "src.connectors.google_docs.connector.GoogleDocsAPIClient",
        return_value=mock_client,
    ):
        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 1
    assert len(result.errors) == 1
    assert result.errors[0]["document_id"] == "doc_123"


@pytest.mark.asyncio
async def test_full_sync(
    connector,
    connector_instance,
    mock_drive_file,
    mock_document,
):
    """Test full sync (no time filter, paginate all)."""
    # Mock multiple pages
    mock_drive_file_2 = GoogleDriveFile(
        id="doc_456",
        name="Feature Spec",
        mimeType="application/vnd.google-apps.document",
        modifiedTime=datetime.now(timezone.utc),
    )

    mock_client = MagicMock()
    # First page has next_token, second page doesn't
    mock_client.list_documents = AsyncMock(
        side_effect=[
            ([mock_drive_file], "next_token"),
            ([mock_drive_file_2], None),
        ]
    )
    mock_client.get_document = AsyncMock(return_value=mock_document)
    mock_client.extract_text_from_body = MagicMock(return_value="Content")

    mock_transformer = MagicMock()
    mock_source = KnowledgeSource(source_type="manual_entry", external_id="doc_123")
    mock_transformer.transform_document = AsyncMock(return_value=(mock_source, []))

    mock_service = MagicMock()
    mock_service.ingest_source = AsyncMock(
        return_value=ExtractionResult(source_id="source_1", items_created=0, items_skipped=0)
    )

    with (
        patch(
            "src.connectors.google_docs.connector.GoogleDocsAPIClient",
            return_value=mock_client,
        ),
        patch.object(connector, "transformer", mock_transformer),
        patch.object(connector, "knowledge_service", mock_service),
    ):
        result = await connector.full_sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 2

    # Verify both pages were fetched
    assert mock_client.list_documents.call_count == 2

    # First call should have no modified_after filter
    first_call = mock_client.list_documents.call_args_list[0].kwargs
    assert first_call["modified_after"] is None


@pytest.mark.asyncio
async def test_sync_no_oauth_tokens(connector):
    """Test sync without OAuth tokens."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GOOGLE_DOCS,
    )

    result = await connector.sync(instance)

    assert result.success is False
    assert "OAuth tokens" in result.error_message


@pytest.mark.asyncio
async def test_sync_api_exception(connector, connector_instance):
    """Test sync with client exception."""
    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(side_effect=Exception("Network error"))

    with patch(
        "src.connectors.google_docs.connector.GoogleDocsAPIClient",
        return_value=mock_client,
    ):
        result = await connector.sync(connector_instance)

    assert result.success is False
    assert "Network error" in result.error_message


@pytest.mark.asyncio
async def test_sync_cursor_update_on_completion(
    connector,
    connector_instance,
    mock_drive_file,
    mock_document,
):
    """Test that cursor is updated to current time when pagination completes."""
    connector_instance.sync_cursor = "modified_after:2025-01-01T00:00:00Z"

    mock_client = MagicMock()
    mock_client.list_documents = AsyncMock(
        return_value=([mock_drive_file], None)  # No next_token
    )
    mock_client.get_document = AsyncMock(return_value=mock_document)
    mock_client.extract_text_from_body = MagicMock(return_value="Content")

    mock_transformer = MagicMock()
    mock_source = KnowledgeSource(source_type="manual_entry", external_id="doc_123")
    mock_transformer.transform_document = AsyncMock(return_value=(mock_source, []))

    mock_service = MagicMock()
    mock_service.ingest_source = AsyncMock(
        return_value=ExtractionResult(source_id="source_1", items_created=0, items_skipped=0)
    )

    with (
        patch(
            "src.connectors.google_docs.connector.GoogleDocsAPIClient",
            return_value=mock_client,
        ),
        patch.object(connector, "transformer", mock_transformer),
        patch.object(connector, "knowledge_service", mock_service),
    ):
        result = await connector.sync(connector_instance)

    # Cursor should be updated to current time
    assert result.cursor_after.startswith("modified_after:2025-")
    assert "page_token" not in result.cursor_after
