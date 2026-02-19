"""Tests for Fireflies transformer."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from src.connectors.fireflies.schemas import (
    FirefliesActionItem,
    FirefliesKeyword,
    FirefliesSentence,
    FirefliesTranscript,
    FirefliesUser,
)
from src.connectors.fireflies.transformer import FirefliesTransformer
from src.knowledge.base import KnowledgeType, SourceType


@pytest.fixture
def sample_transcript():
    """Create sample FirefliesTranscript."""
    return FirefliesTranscript(
        id="t123",
        title="Customer Discovery Call",
        date=datetime(2025, 12, 5, 14, 30, 0, tzinfo=timezone.utc),
        duration=1500,
        meeting_url="https://fireflies.ai/view/t123",
        organizer=FirefliesUser(user_id="u1", name="Sales Rep", email="sales@company.com"),
        participants=["Sales Rep", "Customer Lead", "Technical Contact"],
        sentences=[
            FirefliesSentence(
                text="We're struggling with manual invoice processing.",
                speaker_name="Customer Lead",
            ),
            FirefliesSentence(
                text="Our platform reduces that by 90%.",
                speaker_name="Sales Rep",
            ),
        ],
        action_items=[
            FirefliesActionItem(text="Send demo video", assignee="sales@company.com"),
        ],
        keywords=[
            FirefliesKeyword(text="invoice processing", score=0.95),
            FirefliesKeyword(text="automation", score=0.88),
        ],
    )


def test_transcript_to_source(sample_transcript):
    """Test converting Fireflies transcript to KnowledgeSource."""
    transformer = FirefliesTransformer()
    source = transformer.transcript_to_source(sample_transcript)

    assert source.source_type == SourceType.GONG_TRANSCRIPT  # Reuses same type
    assert source.external_id == "t123"
    assert source.external_url == "https://fireflies.ai/view/t123"
    assert source.source_title == "Customer Discovery Call"
    assert source.duration_seconds == 1500
    assert len(source.participant_names) == 3
    assert "Sales Rep" in source.participant_names
    assert "Customer Lead" in source.participant_names


def test_transcript_to_source_raw_content(sample_transcript):
    """Test transcript text includes all sections."""
    transformer = FirefliesTransformer()
    source = transformer.transcript_to_source(sample_transcript)

    # Check header
    assert "Meeting: Customer Discovery Call" in source.raw_content
    assert "Date: 2025-12-05 14:30" in source.raw_content
    assert "Duration: 25 minutes" in source.raw_content
    assert "Participants: Sales Rep, Customer Lead, Technical Contact" in source.raw_content

    # Check transcript
    assert "[Customer Lead]:" in source.raw_content
    assert "struggling with manual invoice processing" in source.raw_content
    assert "[Sales Rep]:" in source.raw_content

    # Check action items
    assert "=== ACTION ITEMS ===" in source.raw_content
    assert "Send demo video" in source.raw_content

    # Check keywords
    assert "=== KEYWORDS ===" in source.raw_content
    assert "invoice processing" in source.raw_content


def test_transcript_to_source_minimal_data():
    """Test transcript_to_source handles minimal data."""
    transcript = FirefliesTranscript(
        id="t456",
        sentences=[],
    )

    transformer = FirefliesTransformer()
    source = transformer.transcript_to_source(transcript)

    assert source.external_id == "t456"
    assert source.source_title == "Fireflies Meeting t456"
    assert source.participant_names == []


def test_transcript_to_source_uses_video_url():
    """Test transcript_to_source uses video_url if meeting_url missing."""
    transcript = FirefliesTranscript(
        id="t789",
        meeting_url=None,
        video_url="https://fireflies.ai/video/t789",
    )

    transformer = FirefliesTransformer()
    source = transformer.transcript_to_source(transcript)

    assert source.external_url == "https://fireflies.ai/video/t789"


def test_transcript_to_source_content_hash():
    """Test content hash is generated."""
    transcript = FirefliesTranscript(id="t999", sentences=[])

    transformer = FirefliesTransformer()
    source = transformer.transcript_to_source(transcript)

    assert source.content_hash is not None
    assert len(source.content_hash) == 64  # SHA256 hex digest


@pytest.mark.asyncio
async def test_extract_knowledge(sample_transcript):
    """Test extracting knowledge from source."""
    # Mock extractor
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 3
    mock_result.entries = [
        Mock(knowledge_type=KnowledgeType.PAIN_POINT, content="Manual invoice processing"),
        Mock(knowledge_type=KnowledgeType.METRIC, content="90% reduction"),
        Mock(knowledge_type=KnowledgeType.USE_CASE, content="Invoice automation"),
    ]
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = FirefliesTransformer(extractor=mock_extractor)
    source = transformer.transcript_to_source(sample_transcript)

    entries = await transformer.extract_knowledge(source)

    # Verify extractor was called with correct context
    mock_extractor.extract.assert_called_once()
    call_args = mock_extractor.extract.call_args
    assert call_args.kwargs["source"] == source
    assert "Meeting transcript from Fireflies.ai" in call_args.kwargs["additional_context"]
    assert "25 minutes" in call_args.kwargs["additional_context"]
    assert "Sales Rep, Customer Lead, Technical Contact" in call_args.kwargs["additional_context"]

    assert len(entries) == 3
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT


@pytest.mark.asyncio
async def test_extract_knowledge_handles_error():
    """Test extract_knowledge handles extraction errors gracefully."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = "API timeout"
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = FirefliesTransformer(extractor=mock_extractor)

    from src.knowledge.base import KnowledgeSource

    source = KnowledgeSource(
        source_type=SourceType.GONG_TRANSCRIPT,
        external_id="t888",
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

    transformer = FirefliesTransformer(extractor=mock_extractor)

    from src.knowledge.base import KnowledgeSource

    source = KnowledgeSource(
        source_type=SourceType.GONG_TRANSCRIPT,
        external_id="t555",
        participant_names=["Alice", "Bob"],
        duration_seconds=2400,  # 40 minutes
        raw_content="Test",
    )

    await transformer.extract_knowledge(source)

    call_args = mock_extractor.extract.call_args
    context = call_args.kwargs["additional_context"]

    assert "Alice, Bob" in context
    assert "40 minutes" in context
    assert "Meeting transcript from Fireflies.ai" in context
    assert "action items and keywords" in context


@pytest.mark.asyncio
async def test_extract_knowledge_no_participants():
    """Test extract_knowledge handles empty participants."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 0
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = FirefliesTransformer(extractor=mock_extractor)

    from src.knowledge.base import KnowledgeSource

    source = KnowledgeSource(
        source_type=SourceType.GONG_TRANSCRIPT,
        external_id="t666",
        participant_names=[],
        raw_content="Test",
    )

    await transformer.extract_knowledge(source)

    call_args = mock_extractor.extract.call_args
    context = call_args.kwargs["additional_context"]

    # Should not include "Participants:" if empty
    assert "Context: Meeting transcript from Fireflies.ai" in context
