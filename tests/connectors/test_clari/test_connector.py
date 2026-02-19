"""Tests for Clari Copilot connector."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.connectors.base import AuthType, ConnectorInstance, ConnectorType
from src.connectors.clari.connector import ClariConnector
from src.connectors.clari.schemas import ClariCall, ClariCallDetails, ClariCallsResponse


@pytest.fixture
def clari_instance():
    """Create Clari connector instance with valid credentials."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLARI,
        config={"api_key": "test-api-key", "api_password": "test-password"},
    )


def test_connector_metadata():
    """Test connector metadata fields."""
    connector = ClariConnector()

    assert connector.connector_type == ConnectorType.CLARI
    assert connector.display_name == "Clari Copilot"
    assert connector.description == "Sync AE call recordings and transcripts from Clari Copilot"
    assert connector.auth_type == AuthType.API_KEY
    assert connector.supports_webhook is False


def test_get_required_config_fields():
    """Test that required config fields are api_key and api_password."""
    connector = ClariConnector()
    fields = connector.get_required_config_fields()

    assert fields == ["api_key", "api_password"]


@pytest.mark.asyncio
async def test_test_connection_success(clari_instance):
    """Test successful connection test."""
    connector = ClariConnector()

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.total = 42
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(clari_instance)

    assert result is True
    mock_client.get_calls.assert_called_once_with(page=1, limit=1)


@pytest.mark.asyncio
async def test_test_connection_no_credentials():
    """Test connection test fails when credentials are missing."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLARI,
        config={},
    )

    connector = ClariConnector()
    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_no_password():
    """Test connection test fails when only api_key is provided."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLARI,
        config={"api_key": "key-only"},
    )

    connector = ClariConnector()
    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(clari_instance):
    """Test connection test handles API errors gracefully."""
    connector = ClariConnector()

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.test_connection(clari_instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_success(clari_instance):
    """Test successful incremental sync with cursor."""
    clari_instance.sync_cursor = "2"  # resume from page 2

    connector = ClariConnector()

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class, \
         patch("src.connectors.clari.connector.ClariTransformer"), \
         patch("src.connectors.clari.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        # Build a minimal ClariCall and ClariCallDetails
        mock_call = ClariCall(id="call1", title="Test", participants=[])
        mock_details = ClariCallDetails(call=mock_call, transcript=[])

        mock_response = ClariCallsResponse(
            calls=[mock_call],
            total=1,
            page=2,
            has_more=False,
        )

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_call_details = AsyncMock(return_value=mock_details)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        # Call with empty transcript — should be skipped
        result = await connector.sync(clari_instance)

    assert result.success is True
    # Empty transcript → skipped
    assert result.items_skipped == 1
    assert result.items_fetched == 1
    # Verify start page came from cursor
    mock_client.get_calls.assert_called_once_with(page=2, limit=50)


@pytest.mark.asyncio
async def test_full_sync(clari_instance):
    """Test full sync starts from page 1 regardless of cursor."""
    clari_instance.sync_cursor = "5"  # cursor should be ignored for full_sync

    connector = ClariConnector()

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class, \
         patch("src.connectors.clari.connector.ClariTransformer"), \
         patch("src.connectors.clari.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_response = ClariCallsResponse(
            calls=[],
            total=0,
            page=1,
            has_more=False,
        )

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.full_sync(clari_instance)

    assert result.success is True
    assert result.items_fetched == 0
    # full_sync always starts from page 1
    mock_client.get_calls.assert_called_once_with(page=1, limit=50)


@pytest.mark.asyncio
async def test_sync_skips_empty_transcripts(clari_instance):
    """Test that calls with empty transcripts are skipped."""
    connector = ClariConnector()

    mock_call = ClariCall(id="callA", title="Empty", participants=[])
    # transcript_to_text() returns "" for empty transcript
    mock_details = ClariCallDetails(call=mock_call, transcript=[])

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class, \
         patch("src.connectors.clari.connector.ClariTransformer"), \
         patch("src.connectors.clari.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_response = ClariCallsResponse(
            calls=[mock_call],
            total=1,
            page=1,
            has_more=False,
        )

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_call_details = AsyncMock(return_value=mock_details)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await connector.sync(clari_instance)

    assert result.success is True
    assert result.items_skipped == 1
    assert result.items_extracted == 0


@pytest.mark.asyncio
async def test_sync_no_credentials():
    """Test sync fails without credentials."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.CLARI,
        config={},
    )

    connector = ClariConnector()
    result = await connector.sync(instance)

    assert result.success is False
    assert "api key" in result.error_message.lower() or "password" in result.error_message.lower()


@pytest.mark.asyncio
async def test_sync_processes_calls_with_transcript(clari_instance):
    """Test _sync_calls fully processes a call that has transcript content."""
    from src.connectors.clari.schemas import ClariParticipant, ClariTranscriptEntry

    connector = ClariConnector()

    participant = ClariParticipant(name="Prospect", email="p@example.com", role="attendee")
    entry = ClariTranscriptEntry(
        speakerId="spk1",
        speakerName="Prospect",
        start=0.0,
        end=5.0,
        text="We need a better streaming solution.",
    )
    mock_call = ClariCall(id="call_xyz", title="Real Call", participants=[participant])
    mock_details = ClariCallDetails(call=mock_call, transcript=[entry])

    with patch("src.connectors.clari.connector.ClariCopilotClient") as mock_client_class, \
         patch("src.connectors.clari.connector.ClariTransformer") as mock_transformer_class, \
         patch("src.connectors.clari.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_response = ClariCallsResponse(
            calls=[mock_call],
            total=1,
            page=1,
            has_more=False,
        )

        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(return_value=mock_response)
        mock_client.get_call_details = AsyncMock(return_value=mock_details)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_source = Mock()
        mock_source.id = None
        mock_source.content_hash = "abc123"
        mock_transformer = Mock()
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[Mock(), Mock()])
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        # No existing record — not a duplicate
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source_id_1")
        mock_service._save_entries = AsyncMock(return_value=2)
        mock_service_class.return_value = mock_service

        result = await connector._sync_calls(clari_instance, "key", "pass", start_page=1)

    assert result.success is True
    assert result.items_extracted == 1
    assert result.items_created == 2
    mock_service._save_source.assert_called_once()
    mock_service._save_entries.assert_called_once()
