"""Tests for Close CRM connector."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.base import ConnectorInstance, ConnectorType
from src.connectors.close.connector import CloseConnector


@pytest.fixture
def close_instance():
    """Create Close CRM connector instance."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLOSE,
        config={"api_key": "test-api-key"},
    )


def test_connector_metadata():
    """Test connector metadata."""
    connector = CloseConnector()

    assert connector.connector_type == ConnectorType.CLOSE
    assert connector.display_name == "Close CRM"
    assert connector.auth_type.value == "api_key"
    assert connector.supports_webhook is False


def test_get_required_config_fields():
    """Test get_required_config_fields returns api_key."""
    connector = CloseConnector()
    fields = connector.get_required_config_fields()

    assert fields == ["api_key"]


@pytest.mark.asyncio
async def test_test_connection_success(close_instance):
    """Test successful connection test."""
    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(return_value=True)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(close_instance)

    assert result is True
    mock_client.test_connection.assert_called_once()


@pytest.mark.asyncio
async def test_test_connection_no_api_key():
    """Test connection test fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLOSE,
        config={},
    )

    connector = CloseConnector()
    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(close_instance):
    """Test connection test handles API errors."""
    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.test_connection = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(close_instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_incremental_with_cursor(close_instance):
    """Test incremental sync with existing cursor."""
    close_instance.sync_cursor = "2024-01-01"

    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class, \
         patch("src.connectors.close.connector.CloseTransformer") as mock_transformer_class, \
         patch("src.connectors.close.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        # Mock client
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=[
            {
                "id": "call_123",
                "note": "Test call note",
                "contact_name": "John Doe",
                "date_created": "2024-01-15T10:00:00Z",
                "duration": 300,
            }
        ])
        mock_client.get_notes = AsyncMock(return_value=[
            {
                "id": "note_456",
                "note": "Test note content",
                "contact_name": "Jane Smith",
                "date_created": "2024-01-16T11:00:00Z",
            }
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Mock transformer
        mock_transformer = Mock()
        mock_source = Mock()
        mock_source.content_hash = "hash123"
        mock_source.id = None
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer.note_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[])
        mock_transformer_class.return_value = mock_transformer

        # Mock knowledge service
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        result = await connector.sync(close_instance)

    assert result.success is True
    assert result.items_fetched == 2  # 1 call + 1 note
    mock_client.get_calls.assert_called_once_with(since_date="2024-01-01", limit=100)
    mock_client.get_notes.assert_called_once_with(since_date="2024-01-01", limit=100)


@pytest.mark.asyncio
async def test_sync_incremental_no_cursor(close_instance):
    """Test incremental sync without cursor defaults to last 7 days."""
    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class, \
         patch("src.connectors.close.connector.CloseTransformer"), \
         patch("src.connectors.close.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=[])
        mock_client.get_notes = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(close_instance)

    assert result.success is True
    # Verify it called with a date (should be ~7 days ago)
    call_args = mock_client.get_calls.call_args
    assert call_args is not None
    assert "since_date" in call_args.kwargs


@pytest.mark.asyncio
async def test_full_sync(close_instance):
    """Test full sync fetches last 30 days."""
    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class, \
         patch("src.connectors.close.connector.CloseTransformer"), \
         patch("src.connectors.close.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=[])
        mock_client.get_notes = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.full_sync(close_instance)

    assert result.success is True
    assert result.items_fetched == 0
    mock_client.get_calls.assert_called_once()
    mock_client.get_notes.assert_called_once()


@pytest.mark.asyncio
async def test_sync_handles_duplicates(close_instance):
    """Test sync skips duplicate content."""
    close_instance.sync_cursor = "2024-01-01"

    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class, \
         patch("src.connectors.close.connector.CloseTransformer") as mock_transformer_class, \
         patch("src.connectors.close.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=[
            {"id": "call_123", "note": "Duplicate call"}
        ])
        mock_client.get_notes = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_transformer = Mock()
        mock_source = Mock()
        mock_source.content_hash = "hash123"
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer_class.return_value = mock_transformer

        # Mock as duplicate
        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]
        mock_service_class.return_value = mock_service

        result = await connector.sync(close_instance)

    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_skipped == 1
    assert result.items_extracted == 0


@pytest.mark.asyncio
async def test_sync_handles_extraction_errors(close_instance):
    """Test sync continues after extraction errors."""
    close_instance.sync_cursor = "2024-01-01"

    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class, \
         patch("src.connectors.close.connector.CloseTransformer") as mock_transformer_class, \
         patch("src.connectors.close.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=[
            {"id": "call_1", "note": "Call 1"},
            {"id": "call_2", "note": "Call 2"},
        ])
        mock_client.get_notes = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_transformer = Mock()
        mock_transformer.call_to_source = Mock(side_effect=Exception("Transform error"))
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        mock_service_class.return_value = mock_service

        result = await connector.sync(close_instance)

    assert result.success is True
    assert result.items_fetched == 2
    assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_sync_no_api_key():
    """Test sync fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLOSE,
        config={},
    )

    connector = CloseConnector()
    result = await connector.sync(instance)

    assert result.success is False
    assert "api key" in result.error_message.lower()


@pytest.mark.asyncio
async def test_sync_api_error(close_instance):
    """Test sync handles API errors gracefully."""
    connector = CloseConnector()

    with patch("src.connectors.close.connector.CloseCRMClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(close_instance)

    assert result.success is False
    assert result.error_message == "API Error"
