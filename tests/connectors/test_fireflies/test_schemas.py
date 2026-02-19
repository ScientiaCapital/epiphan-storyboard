"""Tests for Fireflies schemas."""

import pytest
from datetime import datetime, timezone

from src.connectors.fireflies.schemas import (
    FirefliesActionItem,
    FirefliesKeyword,
    FirefliesSentence,
    FirefliesTranscript,
    FirefliesTranscriptsResponse,
    FirefliesUser,
)


def test_fireflies_sentence_basic():
    """Test basic FirefliesSentence creation."""
    sentence = FirefliesSentence(
        text="This is a test sentence.",
        speaker_name="John Doe",
        speaker_id="speaker123",
        start_time=10.5,
        end_time=15.2,
    )

    assert sentence.text == "This is a test sentence."
    assert sentence.speaker_name == "John Doe"
    assert sentence.speaker_id == "speaker123"
    assert sentence.start_time == 10.5
    assert sentence.end_time == 15.2


def test_fireflies_sentence_minimal():
    """Test FirefliesSentence with minimal fields."""
    sentence = FirefliesSentence(text="Hello")

    assert sentence.text == "Hello"
    assert sentence.speaker_name is None
    assert sentence.start_time is None


def test_fireflies_action_item():
    """Test FirefliesActionItem."""
    item = FirefliesActionItem(
        text="Follow up with customer",
        assignee="sales@company.com",
    )

    assert item.text == "Follow up with customer"
    assert item.assignee == "sales@company.com"


def test_fireflies_keyword():
    """Test FirefliesKeyword."""
    keyword = FirefliesKeyword(text="pricing", score=0.85)

    assert keyword.text == "pricing"
    assert keyword.score == 0.85


def test_fireflies_user():
    """Test FirefliesUser."""
    user = FirefliesUser(
        user_id="user123",
        name="Jane Smith",
        email="jane@example.com",
    )

    assert user.user_id == "user123"
    assert user.name == "Jane Smith"
    assert user.email == "jane@example.com"


def test_fireflies_transcript_basic():
    """Test basic FirefliesTranscript creation."""
    transcript = FirefliesTranscript(
        id="transcript123",
        title="Team Meeting",
        date=datetime(2025, 12, 5, 14, 0, 0, tzinfo=timezone.utc),
        duration=1800,
        participants=["Alice", "Bob", "Charlie"],
    )

    assert transcript.id == "transcript123"
    assert transcript.title == "Team Meeting"
    assert transcript.duration == 1800
    assert len(transcript.participants) == 3


def test_fireflies_transcript_to_text():
    """Test FirefliesTranscript to_text conversion."""
    transcript = FirefliesTranscript(
        id="t123",
        title="Sales Call",
        date=datetime(2025, 12, 5, 10, 0, 0, tzinfo=timezone.utc),
        duration=900,
        participants=["Sales Rep", "Customer"],
        sentences=[
            FirefliesSentence(text="Hello there.", speaker_name="Sales Rep"),
            FirefliesSentence(text="Hi, how are you?", speaker_name="Customer"),
            FirefliesSentence(text="Great, thanks!", speaker_name="Sales Rep"),
        ],
        action_items=[
            FirefliesActionItem(text="Send pricing proposal", assignee="sales@company.com"),
        ],
        keywords=[
            FirefliesKeyword(text="pricing"),
            FirefliesKeyword(text="proposal"),
        ],
    )

    text = transcript.to_text()

    # Check header
    assert "Meeting: Sales Call" in text
    assert "Date: 2025-12-05 10:00" in text
    assert "Duration: 15 minutes" in text
    assert "Participants: Sales Rep, Customer" in text

    # Check transcript
    assert "[Sales Rep]:" in text
    assert "Hello there." in text
    assert "[Customer]:" in text
    assert "Hi, how are you?" in text

    # Check action items
    assert "=== ACTION ITEMS ===" in text
    assert "Send pricing proposal (sales@company.com)" in text

    # Check keywords
    assert "=== KEYWORDS ===" in text
    assert "pricing, proposal" in text


def test_fireflies_transcript_to_text_minimal():
    """Test to_text with minimal data."""
    transcript = FirefliesTranscript(
        id="t456",
        sentences=[
            FirefliesSentence(text="Test sentence."),
        ],
    )

    text = transcript.to_text()

    assert "Meeting: Untitled" in text
    assert "[Unknown]:" in text
    assert "Test sentence." in text


def test_fireflies_transcript_to_text_speaker_grouping():
    """Test to_text groups consecutive sentences by same speaker."""
    transcript = FirefliesTranscript(
        id="t789",
        sentences=[
            FirefliesSentence(text="First sentence.", speaker_name="Alice"),
            FirefliesSentence(text="Second sentence.", speaker_name="Alice"),
            FirefliesSentence(text="Third sentence.", speaker_name="Bob"),
            FirefliesSentence(text="Fourth sentence.", speaker_name="Alice"),
        ],
    )

    text = transcript.to_text()

    # Alice should appear twice (interrupted by Bob)
    assert text.count("[Alice]:") == 2
    assert text.count("[Bob]:") == 1


def test_fireflies_transcripts_response():
    """Test FirefliesTranscriptsResponse."""
    response = FirefliesTranscriptsResponse(
        transcripts=[
            FirefliesTranscript(id="t1", title="Meeting 1"),
            FirefliesTranscript(id="t2", title="Meeting 2"),
        ]
    )

    assert len(response.transcripts) == 2
    assert response.transcripts[0].id == "t1"


def test_fireflies_transcripts_response_empty():
    """Test empty FirefliesTranscriptsResponse."""
    response = FirefliesTranscriptsResponse()

    assert response.transcripts == []
