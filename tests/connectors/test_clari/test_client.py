"""Tests for Clari Copilot API client."""

import httpx
import pytest
import respx

from src.connectors.clari.client import ClariCopilotClient
from src.connectors.clari.schemas import ClariCallDetails, ClariCallsResponse


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_success():
    """Test successful get_calls request."""
    mock_response = {
        "calls": [
            {
                "id": "call1",
                "title": "AE Discovery Call",
                "date": "2025-12-05T10:00:00Z",
                "duration": 1800,
                "participants": [
                    {"name": "Sales Rep", "email": "rep@company.com", "role": "host"},
                    {"name": "Prospect", "email": "prospect@example.com", "role": "attendee"},
                ],
            }
        ],
        "total": 1,
        "page": 1,
        "has_more": False,
    }

    respx.get("https://rest-api.copilot.clari.com/calls").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
        response = await client.get_calls(page=1, limit=50)

    assert isinstance(response, ClariCallsResponse)
    assert len(response.calls) == 1
    assert response.calls[0].id == "call1"
    assert response.calls[0].title == "AE Discovery Call"
    assert response.calls[0].duration == 1800
    assert response.total == 1
    assert response.has_more is False


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_pagination():
    """Test get_calls pagination — has_more=True signals more pages."""
    mock_response = {
        "calls": [
            {"id": "call1", "title": "Call 1", "date": "2025-12-01T10:00:00Z", "duration": 900, "participants": []},
            {"id": "call2", "title": "Call 2", "date": "2025-12-02T10:00:00Z", "duration": 1200, "participants": []},
        ],
        "total": 100,
        "page": 1,
        "has_more": True,
    }

    route = respx.get("https://rest-api.copilot.clari.com/calls").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
        response = await client.get_calls(page=1, limit=2)

    assert response.has_more is True
    assert response.total == 100
    assert len(response.calls) == 2
    # Verify query params were sent
    request = route.calls.last.request
    assert "page=1" in str(request.url)
    assert "limit=2" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_call_details_success():
    """Test successful get_call_details request."""
    mock_response = {
        "call": {
            "id": "call123",
            "title": "Product Demo",
            "date": "2025-12-10T14:00:00Z",
            "duration": 2700,
            "participants": [
                {"name": "AE Rep", "email": "ae@company.com", "role": "host"},
                {"name": "IT Manager", "email": "itm@client.com", "role": "attendee"},
            ],
        },
        "transcript": [],
    }

    respx.get("https://rest-api.copilot.clari.com/call-details").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
        details = await client.get_call_details("call123")

    assert isinstance(details, ClariCallDetails)
    assert details.call.id == "call123"
    assert details.call.title == "Product Demo"
    assert details.call.duration == 2700
    assert len(details.call.participants) == 2
    assert details.call.participants[0].name == "AE Rep"
    assert details.transcript == []


@pytest.mark.asyncio
@respx.mock
async def test_get_call_details_with_transcript():
    """Test get_call_details returns transcript entries correctly."""
    mock_response = {
        "call": {
            "id": "call456",
            "title": "Discovery",
            "date": "2025-12-11T09:00:00Z",
            "duration": 1500,
            "participants": [],
        },
        "transcript": [
            {
                "speakerId": "spk_001",
                "speakerName": "Alice",
                "start": 0.0,
                "end": 5.2,
                "text": "Hello, thanks for joining today.",
            },
            {
                "speakerId": "spk_002",
                "speakerName": "Bob",
                "start": 5.5,
                "end": 10.8,
                "text": "Glad to be here. Let's talk about your product.",
            },
        ],
    }

    respx.get("https://rest-api.copilot.clari.com/call-details").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
        details = await client.get_call_details("call456")

    assert len(details.transcript) == 2
    assert details.transcript[0].speaker_id == "spk_001"
    assert details.transcript[0].speaker_name == "Alice"
    assert details.transcript[0].start == 0.0
    assert details.transcript[0].text == "Hello, thanks for joining today."
    assert details.transcript[1].speaker_id == "spk_002"
    assert details.transcript[1].text == "Glad to be here. Let's talk about your product."


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_retry():
    """Test client retries on 429 rate limit responses."""
    respx.get("https://rest-api.copilot.clari.com/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(
                200,
                json={"calls": [], "total": 0, "page": 1, "has_more": False},
            ),
        ]
    )

    async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
        response = await client.get_calls(page=1, limit=50)

    assert len(response.calls) == 0


@pytest.mark.asyncio
@respx.mock
async def test_auth_headers_sent():
    """Test that X-Api-Key and X-Api-Password headers are sent with every request."""
    route = respx.get("https://rest-api.copilot.clari.com/calls").mock(
        return_value=httpx.Response(
            200,
            json={"calls": [], "total": 0, "page": 1, "has_more": False},
        )
    )

    async with ClariCopilotClient(api_key="my-api-key", api_password="my-password") as client:
        await client.get_calls()

    request = route.calls.last.request
    assert request.headers["X-Api-Key"] == "my-api-key"
    assert request.headers["X-Api-Password"] == "my-password"
    assert request.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client async context manager lifecycle."""
    client = ClariCopilotClient(api_key="test-key", api_password="test-pass")

    assert client._client is None

    async with client:
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

    # After exit, _client reference is closed (no assertions on internals needed)


@pytest.mark.asyncio
@respx.mock
async def test_retry_after_cap_at_60s():
    """Test that Retry-After header is capped at 60 seconds."""
    import asyncio
    from unittest.mock import patch

    mock_response = {"calls": [], "metadata": {"total": 0}}

    respx.get("https://rest-api.copilot.clari.com/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3600"}),
            httpx.Response(200, json=mock_response),
        ]
    )

    sleep_times: list[float] = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds: float) -> None:
        sleep_times.append(seconds)
        await original_sleep(0)

    with patch("asyncio.sleep", side_effect=mock_sleep):
        async with ClariCopilotClient(api_key="test-key", api_password="test-pass") as client:
            await client.get_calls()

    assert len(sleep_times) == 1
    assert sleep_times[0] == 60


@pytest.mark.asyncio
async def test_call_without_context_manager_raises():
    """Test calling methods without context manager raises RuntimeError."""
    client = ClariCopilotClient(api_key="test-key", api_password="test-pass")

    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client._call_with_retry("GET", "/calls")
