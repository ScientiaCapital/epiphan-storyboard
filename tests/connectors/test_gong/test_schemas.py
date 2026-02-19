"""Tests for Gong schemas."""

import pytest
from datetime import datetime, timezone

from src.connectors.gong.schemas import (
    GongCall,
    GongCallsResponse,
    GongParty,
    GongTranscript,
    GongTranscriptSentence,
    GongTranscriptTopic,
)


def test_gong_party_basic():
    """Test basic GongParty creation."""
    party = GongParty(
        id="p1",
        name="John Doe",
        email="john@example.com",
        role="COMPANY_MEMBER",
    )

    assert party.id == "p1"
    assert party.name == "John Doe"
    assert party.email == "john@example.com"
    assert party.role == "COMPANY_MEMBER"


def test_gong_call_from_api_response():
    """Test parsing GongCall from API response."""
    api_response = {
        "metaData": {
            "id": "call123",
            "title": "Customer Discovery Call",
            "started": "2025-12-01T10:00:00Z",
            "duration": 3600,
            "url": "https://app.gong.io/call?id=call123",
        },
        "parties": [
            {
                "id": "p1",
                "name": "Sales Rep",
                "emailAddress": "sales@company.com",
                "affiliation": "COMPANY_MEMBER",
            },
            {
                "id": "p2",
                "name": "Customer",
                "emailAddress": "customer@example.com",
                "affiliation": "EXTERNAL_PARTY",
            },
        ],
    }

    call = GongCall.from_api_response(api_response)

    assert call.id == "call123"
    assert call.title == "Customer Discovery Call"
    assert call.duration == 3600
    assert call.url == "https://app.gong.io/call?id=call123"
    assert len(call.parties) == 2
    assert call.parties[0].name == "Sales Rep"
    assert call.parties[1].role == "EXTERNAL_PARTY"


def test_gong_call_missing_metadata():
    """Test GongCall handles missing metadata gracefully."""
    api_response = {
        "metaData": {},
        "parties": [],
    }

    call = GongCall.from_api_response(api_response)

    assert call.id == ""
    assert call.title is None
    assert call.duration is None
    assert len(call.parties) == 0


def test_gong_transcript_sentence():
    """Test GongTranscriptSentence."""
    sentence = GongTranscriptSentence(
        start=1000,
        end=3000,
        text="This is a test sentence.",
        speakerId="p1",
    )

    assert sentence.start == 1000
    assert sentence.end == 3000
    assert sentence.text == "This is a test sentence."
    assert sentence.speaker_id == "p1"


def test_gong_transcript_topic():
    """Test GongTranscriptTopic."""
    sentences = [
        GongTranscriptSentence(start=0, end=2000, text="Hello there.", speakerId="p1"),
        GongTranscriptSentence(start=2000, end=4000, text="How are you?", speakerId="p2"),
    ]

    topic = GongTranscriptTopic(topicName="Introduction", sentences=sentences)

    assert topic.topic_name == "Introduction"
    assert len(topic.sentences) == 2
    assert topic.sentences[0].text == "Hello there."


def test_gong_transcript_to_text():
    """Test GongTranscript to_text conversion."""
    topic1 = GongTranscriptTopic(
        topicName="Introduction",
        sentences=[
            GongTranscriptSentence(start=0, end=2000, text="Hello!", speakerId="p1"),
        ],
    )
    topic2 = GongTranscriptTopic(
        topicName="Discussion",
        sentences=[
            GongTranscriptSentence(start=2000, end=4000, text="Let's discuss.", speakerId="p2"),
        ],
    )

    transcript = GongTranscript(callId="call123", topics=[topic1, topic2])

    speaker_map = {"p1": "Alice", "p2": "Bob"}
    text = transcript.to_text(speaker_map=speaker_map)

    assert "=== Introduction ===" in text
    assert "[Alice]: Hello!" in text
    assert "=== Discussion ===" in text
    assert "[Bob]: Let's discuss." in text


def test_gong_transcript_to_text_no_speaker_map():
    """Test GongTranscript to_text without speaker map."""
    topic = GongTranscriptTopic(
        topicName="Test",
        sentences=[
            GongTranscriptSentence(start=0, end=1000, text="Test.", speakerId="speaker123"),
        ],
    )

    transcript = GongTranscript(callId="call456", topics=[topic])
    text = transcript.to_text()

    assert "[speaker123]: Test." in text


def test_gong_calls_response_from_api():
    """Test GongCallsResponse parsing."""
    api_response = {
        "calls": [
            {"metaData": {"id": "call1"}},
            {"metaData": {"id": "call2"}},
        ],
        "records": {
            "totalRecords": 100,
            "currentPageSize": 2,
            "currentPageNumber": 1,
            "cursor": "next-page-cursor",
        },
    }

    response = GongCallsResponse.from_api_response(api_response)

    assert len(response.calls) == 2
    assert response.total_records == 100
    assert response.cursor == "next-page-cursor"


def test_gong_calls_response_no_cursor():
    """Test GongCallsResponse with no cursor (last page)."""
    api_response = {
        "calls": [{"metaData": {"id": "call1"}}],
        "records": {
            "totalRecords": 1,
            "cursor": None,
        },
    }

    response = GongCallsResponse.from_api_response(api_response)

    assert len(response.calls) == 1
    assert response.cursor is None
