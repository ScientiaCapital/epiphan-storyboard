"""
Browserbase Client for Cloud Browser Sessions
==============================================

Manages cloud browser sessions for authenticated app access and recording.
Uses httpx.AsyncClient following codebase patterns.

NO OpenAI - uses Playwright over CDP.
"""

import asyncio
import base64
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from src.tools.recording.config import BrowserbaseConfig
from src.tools.recording.schemas import AuthConfig, AuthType

logger = logging.getLogger(__name__)


class BrowserbaseClient:
    """
    Cloud browser client for authenticated web app access.

    Features:
    - Session creation/management via Browserbase API
    - Playwright connection over CDP
    - Auth injection (cookies, headers, OAuth)
    - Exponential backoff retry (5s, 10s, 15s)

    Example:
        client = BrowserbaseClient()
        session = await client.create_session()
        page = await client.connect(session["id"])
        # ... interact with page ...
        await client.close_session(session["id"])
    """

    def __init__(self, config: BrowserbaseConfig | None = None):
        """
        Initialize Browserbase client.

        Args:
            config: Optional configuration. If not provided, uses defaults
                   and reads from environment variables.
        """
        self.config = config or BrowserbaseConfig()
        self._playwright = None
        self._browser = None
        self._active_sessions: dict[str, dict] = {}

    async def create_session(
        self,
        auth_config: AuthConfig | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Browserbase session.

        Args:
            auth_config: Optional authentication configuration

        Returns:
            Session dict with "id" and "connectUrl"

        Raises:
            ValueError: If API key or project ID not configured
            httpx.HTTPStatusError: On API error
        """
        # Validate before making API call
        if not self.config.api_key:
            raise ValueError("Browserbase API key not configured")
        if not self.config.project_id:
            raise ValueError("Browserbase project ID not configured")

        payload = {
            "projectId": self.config.project_id,
        }

        result = await self._call_api_with_retry(
            method="POST",
            endpoint="/sessions",
            payload=payload,
        )

        session_id = result.get("id")
        if session_id:
            self._active_sessions[session_id] = result

        logger.info(f"[BROWSERBASE] Created session: {session_id}")
        return result

    async def connect(
        self,
        session_id: str,
        auth_config: AuthConfig | None = None,
    ):
        """
        Connect Playwright to a Browserbase session.

        Args:
            session_id: Session ID from create_session()
            auth_config: Optional auth to inject before returning page

        Returns:
            Playwright Page object ready for interaction

        Raises:
            ValueError: If session doesn't exist
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found. Call create_session() first.")

        session = self._active_sessions[session_id]
        connect_url = session.get("connectUrl")

        if not connect_url:
            raise ValueError(f"Session {session_id} has no connectUrl")

        # Lazy import playwright to avoid import errors if not installed
        from playwright.async_api import async_playwright

        if self._playwright is None:
            pw = await async_playwright().start()
            self._playwright = pw

        # Connect to Browserbase via CDP
        browser = await self._playwright.chromium.connect_over_cdp(connect_url)
        self._browser = browser

        # Get the default page
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        # Inject auth if provided
        if auth_config:
            await self._inject_auth(page, auth_config)

        logger.info(f"[BROWSERBASE] Connected to session: {session_id}")
        return page

    async def close_session(self, session_id: str) -> None:
        """
        Close a Browserbase session and cleanup resources.

        Args:
            session_id: Session ID to close
        """
        if session_id not in self._active_sessions:
            logger.debug(f"[BROWSERBASE] Session {session_id} not in active sessions, skipping close")
            return

        try:
            # Close browser connection
            if self._browser:
                await self._browser.close()
                self._browser = None

            # Call Browserbase API to close session
            await self._call_api_with_retry(
                method="POST",
                endpoint=f"/sessions/{session_id}/close",
                payload={},
            )
        except Exception as e:
            logger.warning(f"[BROWSERBASE] Error closing session {session_id}: {e}")
        finally:
            # Always remove from active sessions
            self._active_sessions.pop(session_id, None)

        logger.info(f"[BROWSERBASE] Closed session: {session_id}")

    async def _call_api_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: dict | None = None,
        max_retries: int | None = None,
    ) -> dict:
        """
        Call Browserbase API with exponential backoff retry.

        Follows codebase pattern from gemini_client._call_openrouter_with_retry()

        Args:
            method: HTTP method (POST, GET, etc.)
            endpoint: API endpoint (e.g., "/sessions")
            payload: Request body
            max_retries: Override default max retries

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: If all retries fail
        """
        if max_retries is None:
            max_retries = self.config.max_retries

        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "x-bb-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    if method.upper() == "POST":
                        response = await client.post(url, json=payload, headers=headers)
                    elif method.upper() == "GET":
                        response = await client.get(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                    logger.warning(
                        f"[BROWSERBASE] Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Other HTTP error - don't retry
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[BROWSERBASE] API error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")

    async def _inject_auth(
        self,
        page,
        auth_config: AuthConfig,
        target_url: str | None = None,
    ) -> None:
        """
        Inject authentication into page context.

        Args:
            page: Playwright Page object
            auth_config: Authentication configuration
            target_url: Target URL to extract cookie domain from (if not in auth_config)
        """
        if auth_config.type == AuthType.COOKIES and auth_config.cookies:
            # Determine cookie domain: explicit > extracted from URL > fallback
            if auth_config.cookie_domain:
                domain = auth_config.cookie_domain
            elif target_url:
                parsed = urlparse(target_url)
                domain = f".{parsed.netloc}"
            else:
                domain = ".localhost"
                logger.warning("[BROWSERBASE] No cookie domain specified, using '.localhost'")

            # Add cookies to browser context
            context = page.context
            cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/"}
                for k, v in auth_config.cookies.items()
            ]
            await context.add_cookies(cookies)
            logger.debug(f"[BROWSERBASE] Injected {len(cookies)} cookies for domain {domain}")

        elif auth_config.type == AuthType.HEADERS and auth_config.headers:
            # Set extra HTTP headers
            await page.set_extra_http_headers(auth_config.headers)
            logger.debug(f"[BROWSERBASE] Set {len(auth_config.headers)} headers")

        elif auth_config.type == AuthType.BASIC:
            # Basic auth via HTTP headers
            if auth_config.username and auth_config.password:
                credentials = base64.b64encode(
                    f"{auth_config.username}:{auth_config.password}".encode()
                ).decode()
                await page.set_extra_http_headers({
                    "Authorization": f"Basic {credentials}"
                })
                logger.debug("[BROWSERBASE] Set basic auth header")

        elif auth_config.type == AuthType.OAUTH:
            # OAuth flow would need to be handled separately
            # This is a placeholder for future implementation
            logger.warning(
                f"[BROWSERBASE] OAuth provider '{auth_config.provider}' requires manual flow"
            )

    async def cleanup(self) -> None:
        """Cleanup all resources (browser, playwright)."""
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._active_sessions.clear()
        logger.info("[BROWSERBASE] Cleaned up all resources")
