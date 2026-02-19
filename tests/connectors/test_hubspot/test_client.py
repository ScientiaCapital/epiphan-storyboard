"""Tests for HubSpot API client."""

import httpx
import pytest
import respx

from src.connectors.hubspot.client import HubSpotAPIClient
from src.connectors.hubspot.schemas import HubSpotCall, HubSpotCallsResponse

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_call_result(call_id: str, body: str | None = "Transcript text") -> dict:
    """Helper to build a HubSpot call result dict."""
    return {
        "id": call_id,
        "properties": {
            "hs_call_body": body,
            "hs_call_title": f"Call {call_id}",
            "hs_call_duration": 120000,
            "hs_timestamp": "2026-01-15T10:00:00Z",
            "hs_call_status": "COMPLETED",
            "hs_call_direction": "OUTBOUND",
        },
        "createdAt": "2026-01-15T10:00:00Z",
        "updatedAt": "2026-01-15T10:05:00Z",
    }


# ---------------------------------------------------------------------------
# get_calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_success():
    """Test successful get_calls request."""
    mock_response = {
        "results": [_make_call_result("call1")],
        "paging": None,
    }

    respx.get("https://api.hubapi.com/crm/v3/objects/calls").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        response = await client.get_calls()

    assert isinstance(response, HubSpotCallsResponse)
    assert len(response.results) == 1
    assert response.results[0].id == "call1"
    assert response.paging is None


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_with_cursor():
    """Test get_calls sends after param when cursor provided."""
    mock_response = {
        "results": [_make_call_result("call2")],
        "paging": {"next": {"after": "next-cursor"}},
    }

    route = respx.get("https://api.hubapi.com/crm/v3/objects/calls").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        response = await client.get_calls(after_cursor="my-cursor")

    # Verify after param was sent
    request = route.calls.last.request
    assert b"after=my-cursor" in request.url.query

    assert response.results[0].id == "call2"
    assert response.paging.next_link == {"after": "next-cursor"}


@pytest.mark.asyncio
@respx.mock
async def test_get_calls_rate_limit_retry():
    """Test get_calls retries on 429 rate limit responses."""
    mock_response = {
        "results": [],
        "paging": None,
    }

    respx.get("https://api.hubapi.com/crm/v3/objects/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(200, json=mock_response),
        ]
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        response = await client.get_calls()

    assert len(response.results) == 0


# ---------------------------------------------------------------------------
# search_calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_search_calls_success():
    """Test successful search_calls request."""
    mock_response = {
        "results": [
            _make_call_result("call3"),
            _make_call_result("call4"),
        ],
        "paging": None,
    }

    respx.post("https://api.hubapi.com/crm/v3/objects/calls/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        calls = await client.search_calls(from_date="2026-01-01T00:00:00Z")

    assert len(calls) == 2
    assert isinstance(calls[0], HubSpotCall)
    assert calls[0].id == "call3"
    assert calls[1].id == "call4"


@pytest.mark.asyncio
@respx.mock
async def test_search_calls_date_filter():
    """Test search_calls sends correct filterGroups payload."""
    mock_response = {"results": [], "paging": None}

    route = respx.post("https://api.hubapi.com/crm/v3/objects/calls/search").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        await client.search_calls(
            from_date="2026-01-01T00:00:00Z",
            to_date="2026-01-31T23:59:59Z",
        )

    # Verify payload structure
    import json

    request_body = json.loads(route.calls.last.request.content)
    filter_groups = request_body["filterGroups"]

    assert len(filter_groups) == 1
    filters = filter_groups[0]["filters"]

    # Should have GTE and LTE filters
    filter_ops = {f["operator"] for f in filters}
    assert "GTE" in filter_ops
    assert "LTE" in filter_ops

    gte_filter = next(f for f in filters if f["operator"] == "GTE")
    assert gte_filter["propertyName"] == "hs_timestamp"
    assert gte_filter["value"] == "2026-01-01T00:00:00Z"

    lte_filter = next(f for f in filters if f["operator"] == "LTE")
    assert lte_filter["value"] == "2026-01-31T23:59:59Z"


@pytest.mark.asyncio
@respx.mock
async def test_search_calls_pagination():
    """Test search_calls handles multi-page responses."""
    page1 = {
        "results": [_make_call_result("call5")],
        "paging": {"next": {"after": "cursor-page2"}},
    }
    page2 = {
        "results": [_make_call_result("call6")],
        "paging": None,
    }

    route = respx.post("https://api.hubapi.com/crm/v3/objects/calls/search").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )

    async with HubSpotAPIClient(access_token="test-token") as client:
        calls = await client.search_calls(from_date="2026-01-01T00:00:00Z")

    assert len(calls) == 2
    assert route.call_count == 2


# ---------------------------------------------------------------------------
# Context manager lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client async context manager lifecycle."""
    client = HubSpotAPIClient(access_token="test-token")

    assert client._client is None

    async with client:
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

    # After exit the internal client should be replaced (aclose called)
    # No assertion on closed state since httpx doesn't expose it directly


@pytest.mark.asyncio
@respx.mock
async def test_retry_after_cap_at_60s():
    """Test that Retry-After header is capped at 60 seconds."""
    import asyncio
    from unittest.mock import patch

    mock_response = {"results": [], "paging": None}

    respx.get("https://api.hubapi.com/crm/v3/objects/calls").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3600"}),
            httpx.Response(200, json=mock_response),
        ]
    )

    sleep_times: list[float] = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds: float) -> None:
        sleep_times.append(seconds)
        await original_sleep(0)  # Don't actually wait

    with patch("asyncio.sleep", side_effect=mock_sleep):
        async with HubSpotAPIClient(access_token="test-token") as client:
            await client.get_calls()

    # Server sent 3600s but client should cap at 60s
    assert len(sleep_times) == 1
    assert sleep_times[0] == 60


@pytest.mark.asyncio
async def test_call_without_context_manager_raises():
    """Test calling methods without context manager raises RuntimeError."""
    client = HubSpotAPIClient(access_token="test-token")

    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client._call_with_retry("GET", "/crm/v3/objects/calls")
