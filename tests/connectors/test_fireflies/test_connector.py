"""Tests for Fireflies connector."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.connectors.base import ConnectorInstance, ConnectorType
from src.connectors.fireflies.connector import FirefliesConnector


@pytest.fixture
def fireflies_instance():
    """Create Fireflies connector instance."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.FIREFLIES,
        config={"api_key": "test-api-key"},
    )


def test_connector_metadata():
    """Test connector metadata."""
    connector = FirefliesConnector()

    assert connector.connector_type == ConnectorType.FIREFLIES
    assert connector.display_name == "Fireflies.ai"
    assert connector.auth_type.value == "api_key"
    assert connector.supports_webhook is False


def test_get_required_config_fields():
    """Test get_required_config_fields returns api_key."""
    connector = FirefliesConnector()
    fields = connector.get_required_config_fields()

    assert fields == ["api_key"]


@pytest.mark.asyncio
async def test_test_connection_success(fireflies_instance):
    """Test successful connection test."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.transcripts = [Mock(id="t1")]
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(fireflies_instance)

    assert result is True
    mock_client.get_transcripts.assert_called_once_with(limit=1)


@pytest.mark.asyncio
async def test_test_connection_no_api_key():
    """Test connection test fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.FIREFLIES,
        config={},
    )

    connector = FirefliesConnector()
    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(fireflies_instance):
    """Test connection test handles API errors."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(fireflies_instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_incremental_with_cursor(fireflies_instance):
    """Test incremental sync with existing cursor."""
    fireflies_instance.sync_cursor = "100"

    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer"), \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor"):

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.transcripts = []
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(fireflies_instance)

    assert result.success is True
    # Verify skip parameter
    call_args = mock_client.get_transcripts.call_args
    assert call_args.kwargs["skip"] == 100


@pytest.mark.asyncio
async def test_sync_incremental_no_cursor(fireflies_instance):
    """Test incremental sync without cursor starts at 0."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer"), \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor"):

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.transcripts = []
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(fireflies_instance)

    assert result.success is True
    call_args = mock_client.get_transcripts.call_args
    assert call_args.kwargs["skip"] == 0


@pytest.mark.asyncio
async def test_full_sync(fireflies_instance):
    """Test full sync starts from offset 0."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer"), \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor"):

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.transcripts = []
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.full_sync(fireflies_instance)

    assert result.success is True


@pytest.mark.asyncio
async def test_sync_transcripts_pagination(fireflies_instance):
    """Test _sync_transcripts handles pagination for full sync."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer") as mock_transformer_class, \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor") as mock_service_class:

        # First page has transcripts, second page is empty
        mock_response_1 = Mock()
        mock_response_1.transcripts = [Mock(id="t1"), Mock(id="t2")]

        mock_response_2 = Mock()
        mock_response_2.transcripts = []

        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(side_effect=[mock_response_1, mock_response_2])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Mock transformer and service
        mock_transformer = Mock()
        mock_transformer.transcript_to_source = Mock(return_value=Mock(id="source1"))
        mock_transformer.extract_knowledge = AsyncMock(return_value=[])
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        mock_service._save_source = AsyncMock(return_value="source1")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        result = await connector._sync_transcripts(
            fireflies_instance,
            api_key="test-key",
            skip=0,
            limit=50,
            full_sync=True,
        )

    assert result.items_fetched == 2
    assert mock_client.get_transcripts.call_count == 2


@pytest.mark.asyncio
async def test_sync_transcripts_incremental_single_page(fireflies_instance):
    """Test incremental sync only fetches one page."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer"), \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor"):

        mock_response = Mock()
        mock_response.transcripts = [Mock(id="t1")]

        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector._sync_transcripts(
            fireflies_instance,
            api_key="test-key",
            skip=0,
            limit=50,
            full_sync=False,
        )

    # Should only call once for incremental
    assert mock_client.get_transcripts.call_count == 1


@pytest.mark.asyncio
async def test_sync_transcripts_processes_transcripts(fireflies_instance):
    """Test _sync_transcripts processes transcripts correctly."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer") as mock_transformer_class, \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        from src.connectors.fireflies.schemas import FirefliesTranscript

        mock_transcript = Mock(spec=FirefliesTranscript)
        mock_transcript.id = "t1"

        mock_response = Mock()
        mock_response.transcripts = [mock_transcript]

        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Mock transformer
        mock_source = Mock()
        mock_source.id = "source123"
        mock_transformer = Mock()
        mock_transformer.transcript_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[Mock(), Mock()])
        mock_transformer_class.return_value = mock_transformer

        # Mock knowledge service
        mock_service = Mock()
        mock_service._save_source = AsyncMock(return_value="source123")
        mock_service._save_entries = AsyncMock(return_value=2)
        mock_service_class.return_value = mock_service

        result = await connector._sync_transcripts(
            fireflies_instance,
            api_key="test-key",
            skip=0,
            limit=50,
        )

    assert result.success is True
    assert result.items_fetched == 1
    assert result.items_extracted == 1
    assert result.items_created == 2
    mock_service._save_source.assert_called_once()
    mock_service._save_entries.assert_called_once()


@pytest.mark.asyncio
async def test_sync_transcripts_updates_cursor(fireflies_instance):
    """Test _sync_transcripts updates cursor correctly."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer") as mock_transformer_class, \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor") as mock_service_class:

        mock_response = Mock()
        mock_response.transcripts = [Mock(id="t1"), Mock(id="t2")]

        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_transformer = Mock()
        mock_transformer.transcript_to_source = Mock(return_value=Mock(id="s1"))
        mock_transformer.extract_knowledge = AsyncMock(return_value=[])
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        mock_service._save_source = AsyncMock(return_value="s1")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        result = await connector._sync_transcripts(
            fireflies_instance,
            api_key="test-key",
            skip=10,
            limit=50,
            full_sync=False,
        )

    # Cursor should be skip + items fetched
    assert result.cursor_after == "12"


@pytest.mark.asyncio
async def test_sync_transcripts_handles_errors(fireflies_instance):
    """Test _sync_transcripts handles processing errors gracefully."""
    connector = FirefliesConnector()

    with patch("src.connectors.fireflies.connector.FirefliesGraphQLClient") as mock_client_class, \
         patch("src.connectors.fireflies.connector.FirefliesTransformer") as mock_transformer_class, \
         patch("src.connectors.fireflies.connector.KnowledgeExtractor") as mock_service_class:

        mock_response = Mock()
        mock_response.transcripts = [Mock(id="t1")]

        mock_client = AsyncMock()
        mock_client.get_transcripts = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Transformer raises error
        mock_transformer = Mock()
        mock_transformer.transcript_to_source = Mock(side_effect=Exception("Transform error"))
        mock_transformer_class.return_value = mock_transformer

        result = await connector._sync_transcripts(
            fireflies_instance,
            api_key="test-key",
            skip=0,
            limit=50,
        )

    assert result.success is True  # Overall sync succeeds
    assert len(result.errors) == 1
    assert "t1" in str(result.errors[0])


@pytest.mark.asyncio
async def test_sync_no_api_key():
    """Test sync fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.FIREFLIES,
        config={},
    )

    connector = FirefliesConnector()
    result = await connector.sync(instance)

    assert result.success is False
    assert "API key" in result.error_message
