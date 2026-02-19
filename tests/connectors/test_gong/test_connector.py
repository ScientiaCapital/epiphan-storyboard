"""Tests for Gong connector."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.base import ConnectorInstance, ConnectorType, OAuthTokens
from src.connectors.gong.connector import GongConnector


@pytest.fixture
def gong_instance():
    """Create Gong connector instance."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GONG,
        oauth_tokens=OAuthTokens(access_token="test-token"),
    )


def test_connector_metadata():
    """Test connector metadata."""
    connector = GongConnector()

    assert connector.connector_type == ConnectorType.GONG
    assert connector.display_name == "Gong"
    assert connector.auth_type.value == "oauth2"
    assert connector.supports_webhook is False


def test_get_oauth_config():
    """Test get_oauth_config returns Gong OAuth configuration."""
    connector = GongConnector()
    oauth_config = connector.get_oauth_config()

    assert oauth_config is not None
    assert "gong.io" in oauth_config.authorize_url
    assert "gong.io" in oauth_config.token_url
    assert "api:calls:read:transcript" in oauth_config.scopes


@pytest.mark.asyncio
async def test_test_connection_success(gong_instance):
    """Test successful connection test."""
    connector = GongConnector()

    # Mock GongAPIClient
    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.calls = [{"metaData": {"id": "call1"}}]
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(gong_instance)

    assert result is True
    mock_client.get_calls.assert_called_once()


@pytest.mark.asyncio
async def test_test_connection_no_token():
    """Test connection test fails without OAuth token."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GONG,
    )

    connector = GongConnector()
    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(gong_instance):
    """Test connection test handles API errors."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(gong_instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_incremental_with_cursor(gong_instance):
    """Test incremental sync with existing cursor."""
    gong_instance.sync_cursor = "2025-12-01T00:00:00Z"

    connector = GongConnector()

    # Mock all dependencies
    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer") as mock_transformer_class, \
         patch("src.connectors.gong.connector.KnowledgeExtractor") as mock_extractor_class:

        # Setup mocks
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.calls = []
        mock_response.cursor = None
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_transcripts = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(gong_instance)

    assert result.success is True
    # Verify from_date was parsed from cursor
    call_args = mock_client.get_calls.call_args
    from_date = call_args.kwargs["from_date"]
    assert from_date.year == 2025
    assert from_date.month == 12
    assert from_date.day == 1


@pytest.mark.asyncio
async def test_sync_incremental_no_cursor(gong_instance):
    """Test incremental sync without cursor defaults to 7 days."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer"), \
         patch("src.connectors.gong.connector.KnowledgeExtractor"):

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.calls = []
        mock_response.cursor = None
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_transcripts = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(gong_instance)

    assert result.success is True
    # Verify from_date is ~7 days ago
    call_args = mock_client.get_calls.call_args
    from_date = call_args.kwargs["from_date"]
    now = datetime.now(timezone.utc)
    assert (now - from_date).days >= 6


@pytest.mark.asyncio
async def test_full_sync(gong_instance):
    """Test full sync fetches last 30 days."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer"), \
         patch("src.connectors.gong.connector.KnowledgeExtractor"):

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.calls = []
        mock_response.cursor = None
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_transcripts = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.full_sync(gong_instance)

    assert result.success is True
    # Verify from_date is ~30 days ago
    call_args = mock_client.get_calls.call_args
    from_date = call_args.kwargs["from_date"]
    now = datetime.now(timezone.utc)
    assert (now - from_date).days >= 29


@pytest.mark.asyncio
async def test_sync_calls_pagination(gong_instance):
    """Test _sync_calls handles pagination correctly."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer") as mock_transformer_class, \
         patch("src.connectors.gong.connector.KnowledgeExtractor") as mock_service_class:

        # First page has cursor, second page doesn't
        mock_response_1 = Mock()
        mock_response_1.calls = [
            {"metaData": {"id": "call1", "title": "Call 1"}},
        ]
        mock_response_1.cursor = "page2-cursor"

        mock_response_2 = Mock()
        mock_response_2.calls = [
            {"metaData": {"id": "call2", "title": "Call 2"}},
        ]
        mock_response_2.cursor = None

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        mock_client.get_transcripts = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from_date = datetime.now(timezone.utc) - timedelta(days=7)
        to_date = datetime.now(timezone.utc)

        result = await connector._sync_calls(gong_instance, from_date, to_date)

    assert result.items_fetched == 2
    assert mock_client.get_calls.call_count == 2


@pytest.mark.asyncio
async def test_sync_calls_processes_transcripts(gong_instance):
    """Test _sync_calls processes calls and transcripts."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer") as mock_transformer_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        # Mock API calls
        from src.connectors.gong.schemas import GongTranscript

        mock_response = Mock()
        mock_response.calls = [
            {"metaData": {"id": "call1", "title": "Test Call"}},
        ]
        mock_response.cursor = None

        mock_transcript = Mock(spec=GongTranscript)
        mock_transcript.call_id = "call1"

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_transcripts = AsyncMock(return_value=[mock_transcript])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Mock transformer
        mock_source = Mock()
        mock_source.id = "source123"
        mock_transformer = Mock()
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[Mock(), Mock()])
        mock_transformer_class.return_value = mock_transformer

        # Mock knowledge service
        mock_service = Mock()
        mock_service._save_source = AsyncMock(return_value="source123")
        mock_service._save_entries = AsyncMock(return_value=2)
        mock_service_class.return_value = mock_service

        from_date = datetime.now(timezone.utc) - timedelta(days=1)
        to_date = datetime.now(timezone.utc)

        result = await connector._sync_calls(gong_instance, from_date, to_date)

    assert result.success is True
    assert result.items_extracted == 1
    assert result.items_created == 2
    mock_service._save_source.assert_called_once()
    mock_service._save_entries.assert_called_once()


@pytest.mark.asyncio
async def test_sync_calls_handles_missing_transcript(gong_instance):
    """Test _sync_calls skips calls without transcripts."""
    connector = GongConnector()

    with patch("src.connectors.gong.connector.GongAPIClient") as mock_client_class, \
         patch("src.connectors.gong.connector.GongTransformer"), \
         patch("src.connectors.gong.connector.KnowledgeExtractor"):

        mock_response = Mock()
        mock_response.calls = [
            {"metaData": {"id": "call1"}},
        ]
        mock_response.cursor = None

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_transcripts = AsyncMock(return_value=[])  # No transcripts
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        from_date = datetime.now(timezone.utc) - timedelta(days=1)
        to_date = datetime.now(timezone.utc)

        result = await connector._sync_calls(gong_instance, from_date, to_date)

    assert result.items_skipped == 1
    assert result.items_extracted == 0


@pytest.mark.asyncio
async def test_sync_no_oauth_token():
    """Test sync fails without OAuth token."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.GONG,
    )

    connector = GongConnector()
    result = await connector.sync(instance)

    assert result.success is False
    assert "OAuth access token" in result.error_message
