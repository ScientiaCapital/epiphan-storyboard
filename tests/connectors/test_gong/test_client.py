"""Tests for Gong API client."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import httpx
import respx

from src.connectors.gong.client import GongAPIClient
from src.connectors.gong.schemas import GongCallsResponse, GongTranscript


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_success():
    """Test successful get_calls request."""
    from_date = datetime(2025, 12, 1, tzinfo=timezone.utc)
    to_date = datetime(2025, 12, 9, tzinfo=timezone.utc)

    # Mock API response
    mock_response = {
        "calls": [
            {
                "metaData": {
                    "id": "call1",
                    "title": "Sales Call",
                    "started": "2025-12-05T10:00:00Z",
                    "duration": 1800,
                }
            }
        ],
        "records": {
            "totalRecords": 1,
            "cursor": None,
        },
    }

    respx.post("https://api.gong.io/v2/calls").mock(return_value=httpx.Response(200, json=mock_response))

    async with GongAPIClient(access_token="test-token") as client:
        response = await client.get_calls(from_date=from_date, to_date=to_date)

    assert isinstance(response, GongCallsResponse)
    assert len(response.calls) == 1
    assert response.calls[0]["metaData"]["id"] == "call1"
    assert response.cursor is None


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_with_cursor():
    """Test get_calls with pagination cursor."""
    from_date = datetime(2025, 12, 1, tzinfo=timezone.utc)

    mock_response = {
        "calls": [{"metaData": {"id": "call2"}}],
        "records": {
            "totalRecords": 50,
            "cursor": "next-cursor-token",
        },
    }

    route = respx.post("https://api.gong.io/v2/calls").mock(return_value=httpx.Response(200, json=mock_response))

    async with GongAPIClient(access_token="test-token") as client:
        response = await client.get_calls(from_date=from_date, cursor="previous-cursor")

    # Verify cursor was included in request
    request = route.calls.last.request
    request_json = request.read().decode()
    assert "previous-cursor" in request_json

    assert response.cursor == "next-cursor-token"


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_rate_limit_retry():
    """Test get_calls retries on 429 rate limit."""
    from_date = datetime(2025, 12, 1, tzinfo=timezone.utc)

    # First two attempts return 429, third succeeds
    respx.post("https://api.gong.io/v2/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(200, json={
                "calls": [],
                "records": {"totalRecords": 0, "cursor": None},
            }),
        ]
    )

    async with GongAPIClient(access_token="test-token") as client:
        response = await client.get_calls(from_date=from_date)

    assert len(response.calls) == 0


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_auth_error():
    """Test get_calls handles auth errors."""
    from_date = datetime(2025, 12, 1, tzinfo=timezone.utc)

    respx.post("https://api.gong.io/v2/calls").mock(return_value=httpx.Response(401, json={"error": "Unauthorized"}))

    async with GongAPIClient(access_token="bad-token") as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.get_calls(from_date=from_date)

    assert exc_info.value.response.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_get_transcripts_success():
    """Test successful get_transcripts request."""
    call_ids = ["call1", "call2"]

    mock_response = {
        "callTranscripts": [
            {
                "callId": "call1",
                "transcript": [
                    {
                        "topic": "Introduction",
                        "sentences": [
                            {
                                "start": 0,
                                "end": 2000,
                                "text": "Hello there.",
                                "speakerId": "p1",
                            }
                        ],
                    }
                ],
            },
            {
                "callId": "call2",
                "transcript": [
                    {
                        "topic": "Discussion",
                        "sentences": [
                            {
                                "start": 0,
                                "end": 1500,
                                "text": "Let's talk.",
                                "speakerId": "p2",
                            }
                        ],
                    }
                ],
            },
        ]
    }

    respx.post("https://api.gong.io/v2/calls/transcript").mock(return_value=httpx.Response(200, json=mock_response))

    async with GongAPIClient(access_token="test-token") as client:
        transcripts = await client.get_transcripts(call_ids)

    assert len(transcripts) == 2
    assert transcripts[0].call_id == "call1"
    assert transcripts[1].call_id == "call2"
    assert len(transcripts[0].topics) == 1
    assert transcripts[0].topics[0].topic_name == "Introduction"


@pytest.mark.asyncio
@respx.mock
async def test_get_transcripts_batch_limit():
    """Test get_transcripts batches requests at 100 call IDs."""
    # Create 150 call IDs
    call_ids = [f"call{i}" for i in range(150)]

    # Mock response (empty transcripts)
    mock_response = {"callTranscripts": []}

    route = respx.post("https://api.gong.io/v2/calls/transcript").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with GongAPIClient(access_token="test-token") as client:
        transcripts = await client.get_transcripts(call_ids)

    # Should have made 2 requests (100 + 50)
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_get_transcripts_empty_list():
    """Test get_transcripts with empty call_ids list."""
    async with GongAPIClient(access_token="test-token") as client:
        transcripts = await client.get_transcripts([])

    assert transcripts == []


@pytest.mark.asyncio
@respx.mock
async def test_get_transcripts_parse_error_handling():
    """Test get_transcripts handles malformed transcript data."""
    mock_response = {
        "callTranscripts": [
            {
                "callId": "call1",
                "transcript": [
                    {
                        # Missing required fields
                        "sentences": [],
                    }
                ],
            }
        ]
    }

    respx.post("https://api.gong.io/v2/calls/transcript").mock(return_value=httpx.Response(200, json=mock_response))

    async with GongAPIClient(access_token="test-token") as client:
        # Should not raise, just return empty list
        transcripts = await client.get_transcripts(["call1"])

    # Malformed transcript should be skipped
    assert len(transcripts) == 1  # Still creates transcript even if topic parsing fails


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client async context manager lifecycle."""
    client = GongAPIClient(access_token="test-token")

    assert client._client is None

    async with client:
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

    # Client should be closed after context exit
    # Note: Can't directly check if closed, but no errors should occur


@pytest.mark.asyncio
@respx.mock
async def test_retry_after_cap_at_60s():
    """Test that Retry-After header is capped at 60 seconds."""
    import asyncio
    from unittest.mock import patch

    from_date = datetime(2025, 12, 1, tzinfo=timezone.utc)

    respx.post("https://api.gong.io/v2/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3600"}),
            httpx.Response(200, json={
                "calls": [],
                "records": {"totalRecords": 0, "cursor": None},
            }),
        ]
    )

    sleep_times: list[float] = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds: float) -> None:
        sleep_times.append(seconds)
        await original_sleep(0)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        async with GongAPIClient(access_token="test-token") as client:
            await client.get_calls(from_date=from_date)

    assert len(sleep_times) == 1
    assert sleep_times[0] == 60


@pytest.mark.asyncio
async def test_call_without_context_manager_raises():
    """Test calling methods without context manager raises error."""
    client = GongAPIClient(access_token="test-token")

    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client._call_with_retry("GET", "/test")
