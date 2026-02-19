"""Tests for Gong transformer."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from src.connectors.gong.schemas import (
    GongCall,
    GongParty,
    GongTranscript,
    GongTranscriptSentence,
    GongTranscriptTopic,
)
from src.connectors.gong.transformer import GongTransformer
from src.knowledge.base import KnowledgeType, SourceType


@pytest.fixture
def sample_call():
    """Create sample GongCall."""
    return GongCall(
        metaData="call123",
        title="Customer Discovery Call",
        started=datetime(2025, 12, 5, 10, 0, 0, tzinfo=timezone.utc),
        duration=1800,
        url="https://app.gong.io/call?id=call123",
        parties=[
            GongParty(id="p1", name="Sales Rep", email="sales@company.com", role="COMPANY_MEMBER"),
            GongParty(id="p2", name="Customer Lead", email="customer@example.com", role="EXTERNAL_PARTY"),
        ],
    )


@pytest.fixture
def sample_transcript():
    """Create sample GongTranscript."""
    topic = GongTranscriptTopic(
        topicName="Product Discussion",
        sentences=[
            GongTranscriptSentence(
                start=0,
                end=3000,
                text="We're spending too much time on manual data entry.",
                speakerId="p2",
            ),
            GongTranscriptSentence(
                start=3000,
                end=6000,
                text="Our solution reduces data entry by 80%.",
                speakerId="p1",
            ),
        ],
    )
    return GongTranscript(callId="call123", topics=[topic])


def test_call_to_source(sample_call, sample_transcript):
    """Test converting call + transcript to KnowledgeSource."""
    transformer = GongTransformer()
    source = transformer.call_to_source(call=sample_call, transcript=sample_transcript)

    assert source.source_type == SourceType.GONG_TRANSCRIPT
    assert source.external_id == "call123"
    assert source.external_url == "https://app.gong.io/call?id=call123"
    assert source.source_title == "Customer Discovery Call"
    assert source.duration_seconds == 1800
    assert len(source.participant_names) == 2
    assert "Sales Rep" in source.participant_names
    assert "Customer Lead" in source.participant_names


def test_call_to_source_transcript_text(sample_call, sample_transcript):
    """Test transcript text formatting in source."""
    transformer = GongTransformer()
    source = transformer.call_to_source(call=sample_call, transcript=sample_transcript)

    # Check transcript text includes speaker names
    assert "[Sales Rep]:" in source.raw_content
    assert "[Customer Lead]:" in source.raw_content
    assert "spending too much time on manual data entry" in source.raw_content
    assert "=== Product Discussion ===" in source.raw_content


def test_call_to_source_missing_party_info():
    """Test call_to_source handles parties with missing info."""
    call = GongCall(
        metaData="call456",
        title="Test Call",
        parties=[
            GongParty(id="p1", name=None, email="test@example.com"),
            GongParty(id="p2", name="John", email=None),
        ],
    )
    transcript = GongTranscript(callId="call456", topics=[])

    transformer = GongTransformer()
    source = transformer.call_to_source(call=call, transcript=transcript)

    # Should use email when name is missing
    assert "test@example.com" in source.participant_names
    assert "John" in source.participant_names


def test_call_to_source_content_hash():
    """Test content hash is generated."""
    call = GongCall(metaData="call789", parties=[])
    transcript = GongTranscript(callId="call789", topics=[])

    transformer = GongTransformer()
    source = transformer.call_to_source(call=call, transcript=transcript)

    assert source.content_hash is not None
    assert len(source.content_hash) == 64  # SHA256 hex digest


@pytest.mark.asyncio
async def test_extract_knowledge(sample_call, sample_transcript):
    """Test extracting knowledge from source."""
    # Mock extractor
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 2
    mock_result.entries = [
        Mock(knowledge_type=KnowledgeType.PAIN_POINT, content="Too much manual data entry"),
        Mock(knowledge_type=KnowledgeType.METRIC, content="80% reduction"),
    ]
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = GongTransformer(extractor=mock_extractor)
    source = transformer.call_to_source(call=sample_call, transcript=sample_transcript)

    entries = await transformer.extract_knowledge(source)

    # Verify extractor was called with correct context
    mock_extractor.extract.assert_called_once()
    call_args = mock_extractor.extract.call_args
    assert call_args.kwargs["source"] == source
    assert "Sales call transcript from Gong" in call_args.kwargs["additional_context"]
    assert "30 minutes" in call_args.kwargs["additional_context"]  # 1800 seconds = 30 min

    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT


@pytest.mark.asyncio
async def test_extract_knowledge_handles_error():
    """Test extract_knowledge handles extraction errors gracefully."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = "LLM API error"
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = GongTransformer(extractor=mock_extractor)

    # Create minimal source
    from src.knowledge.base import KnowledgeSource

    source = KnowledgeSource(
        source_type=SourceType.GONG_TRANSCRIPT,
        external_id="call999",
        raw_content="Test content",
    )

    entries = await transformer.extract_knowledge(source)

    # Should return empty list on error
    assert entries == []


@pytest.mark.asyncio
async def test_extract_knowledge_builds_context():
    """Test extract_knowledge builds proper context string."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 0
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = GongTransformer(extractor=mock_extractor)

    from src.knowledge.base import KnowledgeSource

    source = KnowledgeSource(
        source_type=SourceType.GONG_TRANSCRIPT,
        external_id="call555",
        participant_names=["Alice", "Bob", "Charlie"],
        duration_seconds=3600,  # 60 minutes
        raw_content="Test",
    )

    await transformer.extract_knowledge(source)

    call_args = mock_extractor.extract.call_args
    context = call_args.kwargs["additional_context"]

    assert "Alice, Bob, Charlie" in context
    assert "60 minutes" in context
    assert "Sales call transcript from Gong" in context
