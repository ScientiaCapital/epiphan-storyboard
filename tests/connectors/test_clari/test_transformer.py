"""Tests for Clari Copilot transformer."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.connectors.clari.schemas import (
    ClariCall,
    ClariCallDetails,
    ClariParticipant,
    ClariTranscriptEntry,
)
from src.connectors.clari.transformer import ClariTransformer
from src.knowledge.base import KnowledgeSource, KnowledgeType, SourceType


@pytest.fixture
def sample_call_details():
    """Create a ClariCallDetails with participants and transcript."""
    participants = [
        ClariParticipant(name="AE Rep", email="ae@company.com", role="host"),
        ClariParticipant(name="IT Director", email="itd@prospect.com", role="attendee"),
    ]
    call = ClariCall(
        id="clari_call_001",
        title="Epiphan Discovery Call",
        date="2025-12-15T10:00:00Z",
        duration=2700,
        participants=participants,
    )
    transcript = [
        ClariTranscriptEntry(
            speakerId="spk_ae",
            speakerName="AE Rep",
            start=0.0,
            end=8.5,
            text="Thanks for joining. Can you tell me about your current setup?",
        ),
        ClariTranscriptEntry(
            speakerId="spk_itd",
            speakerName="IT Director",
            start=9.0,
            end=20.3,
            text="We're streaming three campuses but the hardware keeps failing us.",
        ),
    ]
    return ClariCallDetails(call=call, transcript=transcript)


def test_call_to_source(sample_call_details):
    """Test converting ClariCallDetails to KnowledgeSource — verify all fields mapped."""
    transformer = ClariTransformer()
    source = transformer.call_to_source(sample_call_details)

    assert source.source_type == SourceType.CLARI_CALL
    assert source.external_id == "clari_call_001"
    assert source.source_title == "Epiphan Discovery Call"
    assert source.duration_seconds == 2700
    assert len(source.participant_names) == 2
    assert "AE Rep" in source.participant_names
    assert "IT Director" in source.participant_names
    assert source.raw_content is not None
    assert "AE Rep" in source.raw_content
    assert source.content_hash is not None


def test_call_to_source_content_hash(sample_call_details):
    """Test that content_hash is a 64-char SHA256 hex digest."""
    transformer = ClariTransformer()
    source = transformer.call_to_source(sample_call_details)

    assert source.content_hash is not None
    assert len(source.content_hash) == 64  # SHA256 hex digest length


def test_call_to_source_content_hash_uses_call_id_and_transcript():
    """Test content_hash changes when call ID or transcript changes."""

    call_a = ClariCall(id="id_a", participants=[])
    details_a = ClariCallDetails(
        call=call_a,
        transcript=[
            ClariTranscriptEntry(
                speakerId="s1", speakerName="Alice", start=0.0, end=5.0, text="Hello world"
            )
        ],
    )
    call_b = ClariCall(id="id_b", participants=[])
    details_b = ClariCallDetails(
        call=call_b,
        transcript=[
            ClariTranscriptEntry(
                speakerId="s1", speakerName="Alice", start=0.0, end=5.0, text="Hello world"
            )
        ],
    )

    transformer = ClariTransformer()
    source_a = transformer.call_to_source(details_a)
    source_b = transformer.call_to_source(details_b)

    # Different call IDs → different hashes even with same transcript
    assert source_a.content_hash != source_b.content_hash


def test_call_to_source_no_title():
    """Test call_to_source falls back to 'Clari Call <id>' when title is None."""
    call = ClariCall(id="xyz789", title=None, participants=[])
    details = ClariCallDetails(call=call, transcript=[])

    transformer = ClariTransformer()
    source = transformer.call_to_source(details)

    assert source.source_title == "Clari Call xyz789"


def test_call_to_transcript_request(sample_call_details):
    """Test call_to_transcript_request returns correct keys and picks external participant."""
    transformer = ClariTransformer()
    request = transformer.call_to_transcript_request(sample_call_details)

    assert "transcript" in request
    assert "prospect_name" in request
    # First non-host is IT Director
    assert request["prospect_name"] == "IT Director"
    assert "AE Rep" in request["transcript"]
    assert "IT Director" in request["transcript"]


def test_call_to_transcript_request_no_external_participant():
    """Test call_to_transcript_request falls back when all participants are hosts."""
    participants = [
        ClariParticipant(name="Host 1", email="h1@co.com", role="host"),
        ClariParticipant(name="Host 2", email="h2@co.com", role="host"),
    ]
    call = ClariCall(id="call_hosts", participants=participants)
    details = ClariCallDetails(
        call=call,
        transcript=[
            ClariTranscriptEntry(
                speakerId="s1", speakerName="Host 1", start=0.0, end=3.0, text="Testing."
            )
        ],
    )

    transformer = ClariTransformer()
    request = transformer.call_to_transcript_request(details)

    # Falls back to first named participant
    assert request["prospect_name"] in ("Host 1", "Host 2")


def test_transcript_to_text_formatting(sample_call_details):
    """Test ClariCallDetails.transcript_to_text produces correct format."""
    text = sample_call_details.transcript_to_text()

    assert "AE Rep: Thanks for joining." in text
    assert "IT Director: We're streaming three campuses" in text
    # Lines joined by newline
    lines = text.split("\n")
    assert len(lines) == 2


def test_transcript_to_text_uses_speaker_id_when_name_missing():
    """Test transcript_to_text falls back to speaker_id when speaker_name is None."""
    call = ClariCall(id="c1", participants=[])
    transcript = [
        ClariTranscriptEntry(
            speakerId="spk_unknown",
            speakerName=None,
            start=0.0,
            end=4.0,
            text="Anonymous message.",
        )
    ]
    details = ClariCallDetails(call=call, transcript=transcript)

    text = details.transcript_to_text()
    assert "spk_unknown: Anonymous message." in text


@pytest.mark.asyncio
async def test_extract_knowledge(sample_call_details):
    """Test extract_knowledge calls extractor with correct context and returns entries."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 2
    mock_result.entries = [
        Mock(knowledge_type=KnowledgeType.PAIN_POINT, content="Hardware failures during streams"),
        Mock(knowledge_type=KnowledgeType.USE_CASE, content="Multi-campus streaming"),
    ]
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = ClariTransformer(extractor=mock_extractor)
    source = transformer.call_to_source(sample_call_details)

    entries = await transformer.extract_knowledge(source)

    # Extractor called with source and context
    mock_extractor.extract.assert_called_once()
    call_args = mock_extractor.extract.call_args
    assert call_args.kwargs["source"] == source
    assert "AE sales call transcript from Clari Copilot" in call_args.kwargs["additional_context"]
    assert "45 minutes" in call_args.kwargs["additional_context"]  # 2700 // 60 = 45

    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT
    assert entries[1].knowledge_type == KnowledgeType.USE_CASE


@pytest.mark.asyncio
async def test_extract_knowledge_handles_error():
    """Test extract_knowledge returns empty list when extractor reports an error."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = "LLM timeout"
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = ClariTransformer(extractor=mock_extractor)

    source = KnowledgeSource(
        source_type=SourceType.CLARI_CALL,
        external_id="call_error",
        raw_content="Some transcript text",
    )

    entries = await transformer.extract_knowledge(source)

    assert entries == []


@pytest.mark.asyncio
async def test_extract_knowledge_builds_full_context():
    """Test extract_knowledge includes participants, duration, and source label in context."""
    mock_extractor = Mock()
    mock_result = Mock()
    mock_result.error = None
    mock_result.items_extracted = 0
    mock_result.entries = []
    mock_extractor.extract = AsyncMock(return_value=mock_result)

    transformer = ClariTransformer(extractor=mock_extractor)

    source = KnowledgeSource(
        source_type=SourceType.CLARI_CALL,
        external_id="call_ctx",
        participant_names=["Alice", "Bob"],
        duration_seconds=3600,
        raw_content="Test content",
    )

    await transformer.extract_knowledge(source)

    call_args = mock_extractor.extract.call_args
    context = call_args.kwargs["additional_context"]

    assert "Alice, Bob" in context
    assert "60 minutes" in context
    assert "AE sales call transcript from Clari Copilot" in context
