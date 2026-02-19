"""Close CRM API Client."""

import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class CloseCRMClient:
    """
    Async client for Close CRM API.

    Authentication: API Key (Basic auth with API key as username, empty password)
    Base URL: https://api.close.com/api/v1/

    API Docs: https://developer.close.com/

    Example:
        async with CloseCRMClient(api_key="...") as client:
            calls = await client.get_calls(since_date="2024-01-01", limit=100)
    """

    BASE_URL = "https://api.close.com/api/v1"
    DEFAULT_LIMIT = 100

    def __init__(self, api_key: str):
        """
        Initialize Close CRM client.

        Args:
            api_key: Close CRM API key
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            auth=(self.api_key, ""),  # API key as username, empty password
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def test_connection(self) -> bool:
        """
        Test connection by fetching current user.

        Returns:
            True if connection successful
        """
        try:
            response = await self._client.get(f"{self.BASE_URL}/me/")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"[CLOSE] Connection test failed: {e}")
            return False

    async def get_calls(
        self,
        since_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Fetch calls from Close CRM.

        Args:
            since_date: ISO date string (YYYY-MM-DD) to fetch calls from
            limit: Maximum number of calls to fetch

        Returns:
            List of call dicts
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        calls = []
        skip = 0
        fetch_limit = limit or 1000  # Default max

        params = {
            "_limit": min(self.DEFAULT_LIMIT, fetch_limit),
            "_skip": skip,
        }
        if since_date:
            params["date_created__gte"] = since_date

        while len(calls) < fetch_limit:
            params["_skip"] = skip
            params["_limit"] = min(self.DEFAULT_LIMIT, fetch_limit - len(calls))

            response = await self._client.get(
                f"{self.BASE_URL}/activity/call/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            batch = data.get("data", [])
            if not batch:
                break

            calls.extend(batch)
            skip += len(batch)

            if not data.get("has_more", False):
                break

        logger.info(f"[CLOSE] Fetched {len(calls)} calls")
        return calls[:fetch_limit]

    async def get_notes(
        self,
        since_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Fetch notes from Close CRM.

        Args:
            since_date: ISO date string (YYYY-MM-DD) to fetch notes from
            limit: Maximum number of notes to fetch

        Returns:
            List of note dicts
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        notes = []
        skip = 0
        fetch_limit = limit or 1000

        params = {
            "_limit": min(self.DEFAULT_LIMIT, fetch_limit),
            "_skip": skip,
        }
        if since_date:
            params["date_created__gte"] = since_date

        while len(notes) < fetch_limit:
            params["_skip"] = skip
            params["_limit"] = min(self.DEFAULT_LIMIT, fetch_limit - len(notes))

            response = await self._client.get(
                f"{self.BASE_URL}/activity/note/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            batch = data.get("data", [])
            if not batch:
                break

            notes.extend(batch)
            skip += len(batch)

            if not data.get("has_more", False):
                break

        logger.info(f"[CLOSE] Fetched {len(notes)} notes")
        return notes[:fetch_limit]

    async def stream_calls(
        self,
        since_date: str | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[list[dict]]:
        """
        Stream calls from Close CRM in batches.

        Args:
            since_date: ISO date string to fetch calls from
            batch_size: Number of calls per batch

        Yields:
            Batches of call dicts
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        skip = 0
        has_more = True

        params = {
            "_limit": batch_size,
        }
        if since_date:
            params["date_created__gte"] = since_date

        while has_more:
            params["_skip"] = skip

            response = await self._client.get(
                f"{self.BASE_URL}/activity/call/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            batch = data.get("data", [])
            if not batch:
                break

            yield batch

            skip += len(batch)
            has_more = data.get("has_more", False)

    async def stream_notes(
        self,
        since_date: str | None = None,
        batch_size: int = 100,
    ) -> AsyncIterator[list[dict]]:
        """
        Stream notes from Close CRM in batches.

        Args:
            since_date: ISO date string to fetch notes from
            batch_size: Number of notes per batch

        Yields:
            Batches of note dicts
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        skip = 0
        has_more = True

        params = {
            "_limit": batch_size,
        }
        if since_date:
            params["date_created__gte"] = since_date

        while has_more:
            params["_skip"] = skip

            response = await self._client.get(
                f"{self.BASE_URL}/activity/note/",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            batch = data.get("data", [])
            if not batch:
                break

            yield batch

            skip += len(batch)
            has_more = data.get("has_more", False)
