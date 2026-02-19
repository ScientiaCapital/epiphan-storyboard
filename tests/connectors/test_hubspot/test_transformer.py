"""Tests for HubSpot transformer."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.connectors.hubspot.schemas import HubSpotCall, HubSpotCallProperties
from src.connectors.hubspot.transformer import HubSpotTransformer
from src.knowledge.base import KnowledgeSource, KnowledgeType, SourceType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_call() -> HubSpotCall:
    """Create a sample HubSpotCall with full transcript body."""
    return HubSpotCall(
        id="hs-call-123",
        properties=HubSpotCallProperties(
            hs_call_body="Rep: Hi, thanks for your time.\nProspect: Sure, happy to chat.",
            hs_call_title="Discovery Call - Acme Corp",
            hs_call_duration=180000,  # 3 minutes in ms
            hs_timestamp="2026-01-15T10:00:00Z",
            hs_call_status="COMPLETED",
            hs_call_direction="OUTBOUND",
        ),
        createdAt="2026-01-15T10:00:00Z",
        updatedAt="2026-01-15T10:05:00Z",
    )


@pytest.fixture
def call_no_body() -> HubSpotCall:
    """Create a HubSpotCall with no transcript body."""
    return HubSpotCall(
        id="hs-call-456",
        properties=HubSpotCallProperties(
            hs_call_body=None,
            hs_call_title="Voicemail",
            hs_call_duration=15000,
            hs_timestamp="2026-01-16T11:00:00Z",
            hs_call_status="BUSY",
        ),
    )


# ---------------------------------------------------------------------------
# call_to_source
# ---------------------------------------------------------------------------


def test_call_to_source(sample_call: HubSpotCall) -> None:
    """Test converting a full HubSpotCall to KnowledgeSource."""
    transformer = HubSpotTransformer()
    source = transformer.call_to_source(sample_call)

    assert source.source_type == SourceType.HUBSPOT_CALL
    assert source.external_id == "hs-call-123"
    assert source.source_title == "Discovery Call - Acme Corp"
    assert source.duration_seconds == 180  # 180000 ms -> 180 s
    assert source.raw_content == sample_call.properties.hs_call_body
    assert source.source_date is not None
    assert source.source_date.year == 2026


def test_call_to_source_content_hash(sample_call: HubSpotCall) -> None:
    """Test content hash is generated correctly."""
    transformer = HubSpotTransformer()
    source = transformer.call_to_source(sample_call)

    assert source.content_hash is not None
    assert len(source.content_hash) == 64  # SHA256 hex digest

    # Same call should produce same hash
    source2 = transformer.call_to_source(sample_call)
    assert source.content_hash == source2.content_hash


def test_call_to_source_missing_body(call_no_body: HubSpotCall) -> None:
    """Test call_to_source handles missing hs_call_body gracefully."""
    transformer = HubSpotTransformer()
    source = transformer.call_to_source(call_no_body)

    assert source.source_type == SourceType.HUBSPOT_CALL
    assert source.external_id == "hs-call-456"
    assert source.raw_content == ""
    assert source.content_hash is not None  # Hash is still generated (of empty body)


def test_call_to_source_default_title() -> None:
    """Test call_to_source uses fallback title when hs_call_title is None."""
    call = HubSpotCall(
        id="hs-call-789",
        properties=HubSpotCallProperties(
            hs_call_body="Some transcript",
            hs_call_title=None,
        ),
    )
    transformer = HubSpotTransformer()
    source = transformer.call_to_source(call)

    assert source.source_title == "HubSpot Call hs-call-789"


# ---------------------------------------------------------------------------
# call_to_transcript_request
# ---------------------------------------------------------------------------


def test_call_to_transcript_request(sample_call: HubSpotCall) -> None:
    """Test building a transcript request dict for TranscriptToScenariosTool."""
    transformer = HubSpotTransformer()
    req = transformer.call_to_transcript_request(
        call=sample_call,
        contact_name="Jane Smith",
        company_name="Acme Corp",
    )

    assert req["transcript"] == sample_call.properties.hs_call_body
    assert req["prospect_name"] == "Jane Smith"
    assert req["prospect_company"] == "Acme Corp"


def test_call_to_transcript_request_no_contact(sample_call: HubSpotCall) -> None:
    """Test transcript request without optional contact/company."""
    transformer = HubSpotTransformer()
    req = transformer.call_to_transcript_request(sample_call)

    assert req["transcript"] == sample_call.properties.hs_call_body
    assert req["prospect_name"] is None
    assert req["prospect_company"] is None


# ---------------------------------------------------------------------------
# extract_knowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_knowledge(sample_call: HubSpotCall) -> None:
    """Test extracting knowledge from a HubSpot source."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 2
    mock_result.entries = [
        Mock(knowledge_type=KnowledgeType.PAIN_POINT, content="Manual reporting overhead"),
        Mock(knowledge_type=KnowledgeType.QUOTE, content="We need this done yesterday"),
    ]
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = HubSpotTransformer(extractor=mock_extractor)
    source = transformer.call_to_source(sample_call)
    entries = await transformer.extract_knowledge(source)

    # Verify extractor was called
    mock_extractor.extract.assert_called_once()
    call_args = mock_extractor.extract.call_args
    assert call_args.kwargs["source"] == source
    assert "Sales call transcript from HubSpot (SalesMSG)" in call_args.kwargs["additional_context"]
    assert "3 minutes" in call_args.kwargs["additional_context"]  # 180 s = 3 min

    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT


@pytest.mark.asyncio
async def test_extract_knowledge_handles_error(sample_call: HubSpotCall) -> None:
    """Test extract_knowledge returns empty list when extractor errors."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = "LLM API unavailable"
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = HubSpotTransformer(extractor=mock_extractor)

    source = KnowledgeSource(
        source_type=SourceType.HUBSPOT_CALL,
        external_id="hs-call-err",
        raw_content="Some transcript",
    )

    entries = await transformer.extract_knowledge(source)

    # Should return empty list on error
    assert entries == []
