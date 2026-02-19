"""Tests for HubSpot connector."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.connectors.base import ConnectorInstance, ConnectorType
from src.connectors.hubspot.connector import HubSpotConnector
from src.connectors.hubspot.schemas import HubSpotCall, HubSpotCallProperties

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hubspot_instance() -> ConnectorInstance:
    """Create HubSpot connector instance with api_key."""
    return ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.HUBSPOT,
        config={"api_key": "pat-na1-test-token"},
    )


def _make_call(call_id: str, body: str | None = "Transcript body") -> HubSpotCall:
    """Helper to create a HubSpotCall."""
    return HubSpotCall(
        id=call_id,
        properties=HubSpotCallProperties(
            hs_call_body=body,
            hs_call_title=f"Call {call_id}",
            hs_call_duration=120000,
            hs_timestamp="2026-01-15T10:00:00Z",
            hs_call_status="COMPLETED",
        ),
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_connector_metadata() -> None:
    """Test connector metadata fields."""
    conn = HubSpotConnector()

    assert conn.connector_type == ConnectorType.HUBSPOT
    assert conn.display_name == "HubSpot"
    assert conn.description == "Sync call transcripts from HubSpot CRM (SalesMSG)"
    assert conn.auth_type.value == "api_key"
    assert conn.supports_webhook is False


def test_get_required_config_fields() -> None:
    """Test get_required_config_fields returns api_key."""
    conn = HubSpotConnector()
    fields = conn.get_required_config_fields()

    assert fields == ["api_key"]


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_connection_success(hubspot_instance: ConnectorInstance) -> None:
    """Test successful connection test."""
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(
            return_value=Mock(results=[], paging=None)
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await conn.test_connection(hubspot_instance)

    assert result is True
    mock_client.get_calls.assert_called_once_with(limit=1)


@pytest.mark.asyncio
async def test_test_connection_no_api_key() -> None:
    """Test connection test fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.HUBSPOT,
        config={},
    )

    conn = HubSpotConnector()
    result = await conn.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_api_error(hubspot_instance: ConnectorInstance) -> None:
    """Test connection test returns False on API error."""
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get_calls = AsyncMock(side_effect=Exception("401 Unauthorized"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await conn.test_connection(hubspot_instance)

    assert result is False


# ---------------------------------------------------------------------------
# sync (incremental)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_incremental_with_cursor(hubspot_instance: ConnectorInstance) -> None:
    """Test incremental sync uses provided cursor as from_date."""
    hubspot_instance.sync_cursor = "2026-01-10T00:00:00+00:00"
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class, \
         patch("src.connectors.hubspot.connector.HubSpotTransformer") as mock_transformer_class, \
         patch("src.connectors.hubspot.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_client = AsyncMock()
        mock_client.search_calls = AsyncMock(return_value=[
            _make_call("call_a"),
            _make_call("call_b"),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_transformer = Mock()
        mock_source = Mock()
        mock_source.content_hash = "hash_abc"
        mock_source.id = None
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[])
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source-id")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        result = await conn.sync(hubspot_instance)

    assert result.success is True
    assert result.items_fetched == 2

    call_args = mock_client.search_calls.call_args
    assert call_args.kwargs["from_date"] == "2026-01-10T00:00:00+00:00"


@pytest.mark.asyncio
async def test_sync_incremental_no_cursor(hubspot_instance: ConnectorInstance) -> None:
    """Test incremental sync defaults to last 7 days when no cursor."""
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class, \
         patch("src.connectors.hubspot.connector.HubSpotTransformer"), \
         patch("src.connectors.hubspot.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_client = AsyncMock()
        mock_client.search_calls = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await conn.sync(hubspot_instance)

    assert result.success is True
    call_args = mock_client.search_calls.call_args
    assert call_args is not None
    assert "from_date" in call_args.kwargs


@pytest.mark.asyncio
async def test_full_sync(hubspot_instance: ConnectorInstance) -> None:
    """Test full sync fetches last 30 days."""
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class, \
         patch("src.connectors.hubspot.connector.HubSpotTransformer"), \
         patch("src.connectors.hubspot.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService"):

        mock_client = AsyncMock()
        mock_client.search_calls = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        result = await conn.full_sync(hubspot_instance)

    assert result.success is True
    assert result.items_fetched == 0
    mock_client.search_calls.assert_called_once()


# ---------------------------------------------------------------------------
# Filtering / dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_skips_calls_without_body(hubspot_instance: ConnectorInstance) -> None:
    """Test sync skips calls that have no hs_call_body."""
    conn = HubSpotConnector()

    with patch("src.connectors.hubspot.connector.HubSpotAPIClient") as mock_client_class, \
         patch("src.connectors.hubspot.connector.HubSpotTransformer") as mock_transformer_class, \
         patch("src.connectors.hubspot.connector.KnowledgeExtractor"), \
         patch("src.knowledge.service.KnowledgeIngestionService") as mock_service_class:

        mock_client = AsyncMock()
        mock_client.search_calls = AsyncMock(return_value=[
            _make_call("call_with_body", body="Hello there"),
            _make_call("call_no_body", body=None),
        ])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        mock_transformer = Mock()
        mock_source = Mock()
        mock_source.content_hash = "hash_xyz"
        mock_source.id = None
        mock_transformer.call_to_source = Mock(return_value=mock_source)
        mock_transformer.extract_knowledge = AsyncMock(return_value=[])
        mock_transformer_class.return_value = mock_transformer

        mock_service = Mock()
        mock_service.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_service._save_source = AsyncMock(return_value="source-id")
        mock_service._save_entries = AsyncMock(return_value=0)
        mock_service_class.return_value = mock_service

        result = await conn.sync(hubspot_instance)

    assert result.success is True
    assert result.items_fetched == 2
    assert result.items_skipped == 1   # call_no_body skipped
    assert result.items_extracted == 1  # only call_with_body processed


@pytest.mark.asyncio
async def test_sync_no_api_key() -> None:
    """Test sync fails without API key."""
    instance = ConnectorInstance.create_new(
        org_id="test-org",
        connector_type=ConnectorType.HUBSPOT,
        config={},
    )

    conn = HubSpotConnector()
    result = await conn.sync(instance)

    assert result.success is False
    assert "api key" in result.error_message.lower()
