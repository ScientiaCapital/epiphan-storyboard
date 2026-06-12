"""Tests for the same-origin Söhne font proxy (src/brand/fonts.py)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

import src.brand.fonts as fonts
from src.api import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_font_cache():
    """Each test starts with a cold font cache."""
    fonts._cache.clear()
    yield
    fonts._cache.clear()


def _mock_async_client(get_side_effect):
    """Build a patchable stand-in for ``httpx.AsyncClient(...)`` as a context manager."""
    instance = AsyncMock()
    instance.get = AsyncMock(side_effect=get_side_effect)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=instance)
    ctx.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=ctx)
    return factory, instance


def _otf_response(
    content: bytes = b"OTF-BYTES", status_code: int = 200
) -> httpx.Response:
    return httpx.Response(
        status_code,
        content=content,
        request=httpx.Request("GET", "https://chat.epiphan.com/api/brand/asset/x"),
    )


# ============================================================================
# GET /brand/fonts.css
# ============================================================================


def test_fonts_css_serves_font_face_rules(client):
    response = client.get("/brand/fonts.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "@font-face" in response.text
    assert "/brand/font/sohne-buch.otf" in response.text


# ============================================================================
# GET /brand/font/{key}.otf — happy path + cache
# ============================================================================


def test_unknown_font_key_returns_404(client):
    response = client.get("/brand/font/comic-sans.otf")

    assert response.status_code == 404


def test_font_is_proxied_with_long_cache_headers(client):
    factory, instance = _mock_async_client([_otf_response()])

    with patch.object(fonts.httpx, "AsyncClient", factory):
        response = client.get("/brand/font/sohne-buch.otf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("font/otf")
    assert "immutable" in response.headers["cache-control"]
    assert response.content == b"OTF-BYTES"


def test_second_request_served_from_cache_without_upstream_call(client):
    factory, instance = _mock_async_client([_otf_response()])

    with patch.object(fonts.httpx, "AsyncClient", factory):
        first = client.get("/brand/font/sohne-buch.otf")
        second = client.get("/brand/font/sohne-buch.otf")

    assert first.status_code == 200
    assert second.status_code == 200
    assert instance.get.await_count == 1


# ============================================================================
# Upstream failure modes — auth/status errors must be distinguishable from
# network errors (observer CRITICAL 2026-06-12)
# ============================================================================


def test_upstream_status_error_surfaces_status_in_detail(client):
    """A 403 from upstream must not be reported as generic 'unavailable'."""
    factory, _ = _mock_async_client([_otf_response(status_code=403)])

    with patch.object(fonts.httpx, "AsyncClient", factory):
        response = client.get("/brand/font/sohne-buch.otf")

    assert response.status_code == 502
    assert "403" in response.json()["detail"]


def test_upstream_network_error_returns_502_unavailable(client):
    factory, _ = _mock_async_client(httpx.ConnectError("boom"))

    with patch.object(fonts.httpx, "AsyncClient", factory):
        response = client.get("/brand/font/sohne-buch.otf")

    assert response.status_code == 502
    assert response.json()["detail"] == "Font upstream unavailable"


def test_failed_fetch_is_not_cached(client):
    """After an upstream failure, a retry must hit upstream again (and can succeed)."""
    factory, instance = _mock_async_client(
        [httpx.ConnectError("boom"), _otf_response()]
    )

    with patch.object(fonts.httpx, "AsyncClient", factory):
        first = client.get("/brand/font/sohne-buch.otf")
        second = client.get("/brand/font/sohne-buch.otf")

    assert first.status_code == 502
    assert second.status_code == 200
    assert instance.get.await_count == 2


# ============================================================================
# Concurrency — cold-start stampede must collapse to a single upstream fetch
# (observer RISK 2026-06-12)
# ============================================================================


async def test_concurrent_requests_fetch_upstream_once():
    fetches = 0

    async def slow_get(url):
        nonlocal fetches
        fetches += 1
        await asyncio.sleep(0.01)  # yield so all coroutines reach the cache check
        return _otf_response()

    factory, _ = _mock_async_client(None)
    instance = factory.return_value.__aenter__.return_value
    instance.get = AsyncMock(side_effect=slow_get)

    with patch.object(fonts.httpx, "AsyncClient", factory):
        responses = await asyncio.gather(
            *(fonts.brand_font("sohne-buch") for _ in range(5))
        )

    assert all(r.status_code == 200 for r in responses)
    assert fetches == 1
