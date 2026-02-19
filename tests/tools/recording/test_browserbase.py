"""
Tests for BrowserbaseClient.

Following TDD: Write tests FIRST, watch them fail, then implement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


class TestBrowserbaseClientInit:
    """Tests for BrowserbaseClient initialization."""

    def test_init_with_default_config(self):
        """BrowserbaseClient should initialize with default config."""
        from src.tools.recording.browserbase import BrowserbaseClient

        client = BrowserbaseClient()
        assert client.config is not None
        assert client.config.base_url == "https://www.browserbase.com/v1"

    def test_init_with_custom_config(self):
        """BrowserbaseClient should accept custom config."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(
            api_key="custom_key",
            project_id="custom_project",
            timeout=60,
        )
        client = BrowserbaseClient(config=config)
        assert client.config.api_key == "custom_key"
        assert client.config.project_id == "custom_project"
        assert client.config.timeout == 60


class TestBrowserbaseClientCreateSession:
    """Tests for session creation."""

    @pytest.mark.asyncio
    async def test_create_session_requires_api_key(self, monkeypatch):
        """create_session should raise if API key missing."""
        # Clear any env vars that might interfere
        monkeypatch.delenv("BROWSERBASE_API_KEY", raising=False)
        monkeypatch.delenv("BROWSERBASE_PROJECT_ID", raising=False)

        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key=None, project_id="proj")
        client = BrowserbaseClient(config=config)

        with pytest.raises(ValueError, match="API key"):
            await client.create_session()

    @pytest.mark.asyncio
    async def test_create_session_requires_project_id(self, monkeypatch):
        """create_session should raise if project ID missing."""
        # Clear any env vars that might interfere
        monkeypatch.delenv("BROWSERBASE_API_KEY", raising=False)
        monkeypatch.delenv("BROWSERBASE_PROJECT_ID", raising=False)

        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="key", project_id=None)
        client = BrowserbaseClient(config=config)

        with pytest.raises(ValueError, match="project"):
            await client.create_session()

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """create_session should return session dict on success."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        mock_response = {
            "id": "session_123",
            "connectUrl": "wss://connect.browserbase.com?sessionId=session_123",
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            session = await client.create_session()

        assert session["id"] == "session_123"
        assert "connectUrl" in session

    @pytest.mark.asyncio
    async def test_create_session_stores_active_session(self):
        """create_session should track active sessions."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        mock_response = {
            "id": "session_123",
            "connectUrl": "wss://connect.browserbase.com?sessionId=session_123",
        }

        with patch.object(client, "_call_api_with_retry", return_value=mock_response):
            await client.create_session()

        assert "session_123" in client._active_sessions


class TestBrowserbaseClientAPIRetry:
    """Tests for API retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Should retry with exponential backoff on 429."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        # Mock httpx to return 429 twice, then success
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            if call_count < 3:
                mock_resp.status_code = 429
                mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Rate limited", request=MagicMock(), response=mock_resp
                )
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"id": "session_123"}
                mock_resp.raise_for_status.return_value = None
            return mock_resp

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual sleep
                result = await client._call_api_with_retry("POST", "/sessions", {"projectId": "test"})

        assert result["id"] == "session_123"
        assert call_count == 3  # 2 retries + 1 success

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Should raise after max retries exceeded."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj", max_retries=2)
        client = BrowserbaseClient(config=config)

        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limited", request=MagicMock(), response=mock_resp
            )
            return mock_resp

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(httpx.HTTPStatusError):
                    await client._call_api_with_retry("POST", "/sessions", {"projectId": "test"})


class TestBrowserbaseClientCloseSession:
    """Tests for session cleanup."""

    @pytest.mark.asyncio
    async def test_close_session_removes_from_active(self):
        """close_session should remove session from active sessions."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        # Add a session manually
        client._active_sessions["session_123"] = {"id": "session_123"}

        with patch.object(client, "_call_api_with_retry", return_value={}):
            await client.close_session("session_123")

        assert "session_123" not in client._active_sessions

    @pytest.mark.asyncio
    async def test_close_session_nonexistent_is_noop(self):
        """close_session should not raise for nonexistent session."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        # Should not raise
        await client.close_session("nonexistent_session")


class TestBrowserbaseClientConnect:
    """Tests for Playwright connection."""

    @pytest.mark.asyncio
    async def test_connect_requires_valid_session(self):
        """connect should raise if session doesn't exist."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        with pytest.raises(ValueError, match="session"):
            await client.connect("nonexistent_session")

    @pytest.mark.asyncio
    async def test_connect_returns_page(self):
        """connect should return Playwright Page object."""
        from src.tools.recording.browserbase import BrowserbaseClient
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="test_key", project_id="test_proj")
        client = BrowserbaseClient(config=config)

        # Add a session
        client._active_sessions["session_123"] = {
            "id": "session_123",
            "connectUrl": "wss://connect.browserbase.com?sessionId=session_123",
        }

        # Mock Playwright
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]

        mock_chromium = MagicMock()
        mock_chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium

        with patch("playwright.async_api.async_playwright") as mock_async_pw:
            mock_async_pw.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_async_pw.return_value.__aexit__ = AsyncMock(return_value=None)

            # Store playwright instance for the test
            client._playwright = mock_playwright

            page = await client.connect("session_123")

        assert page is mock_page
