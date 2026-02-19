"""HubSpot API Client - REST API wrapper."""

import asyncio
import logging

import httpx

from src.connectors.hubspot.schemas import HubSpotCall, HubSpotCallsResponse

logger = logging.getLogger(__name__)


class HubSpotAPIClient:
    """
    Async client for HubSpot CRM API v3.

    Handles:
    - Call listing with cursor-based pagination
    - Call search with date range filtering
    - Exponential backoff retry
    - Rate limit handling via Retry-After header

    Example:
        async with HubSpotAPIClient(access_token="...") as client:
            calls = await client.search_calls(from_date="2026-01-01T00:00:00Z")
    """

    BASE_URL = "https://api.hubapi.com"
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 5, 10]  # seconds
    CALL_PROPERTIES = (
        "hs_call_body,hs_call_title,hs_call_duration,"
        "hs_timestamp,hs_call_status,hs_call_direction"
    )

    def __init__(self, access_token: str):
        """
        Initialize HubSpot API client.

        Args:
            access_token: HubSpot Private App Token (Bearer)
        """
        self.access_token = access_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def get_calls(
        self,
        after_cursor: str | None = None,
        limit: int = 100,
    ) -> HubSpotCallsResponse:
        """
        Fetch a page of calls from HubSpot.

        Args:
            after_cursor: Cursor value from previous response paging.next.after
            limit: Number of results per page (max 100)

        Returns:
            HubSpotCallsResponse with results and optional paging cursor

        Raises:
            httpx.HTTPStatusError: On API error
        """
        params: dict = {
            "properties": self.CALL_PROPERTIES,
            "limit": limit,
        }
        if after_cursor:
            params["after"] = after_cursor

        response = await self._call_with_retry(
            method="GET",
            endpoint="/crm/v3/objects/calls",
            params=params,
        )

        return HubSpotCallsResponse.model_validate(response)

    async def get_call_with_associations(self, call_id: str) -> dict:
        """
        Fetch a single call with its contact and company associations.

        Args:
            call_id: HubSpot call object ID

        Returns:
            Raw API response dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        params: dict = {
            "properties": self.CALL_PROPERTIES,
            "associations": "contacts,companies",
        }

        return await self._call_with_retry(
            method="GET",
            endpoint=f"/crm/v3/objects/calls/{call_id}",
            params=params,
        )

    async def search_calls(
        self,
        from_date: str,
        to_date: str | None = None,
    ) -> list[HubSpotCall]:
        """
        Search calls by date range using the HubSpot search endpoint.

        Filters on hs_timestamp (ISO 8601 string). Handles pagination
        automatically via the "after" cursor in search responses.

        Args:
            from_date: ISO 8601 timestamp string (e.g. "2026-01-01T00:00:00Z")
            to_date: ISO 8601 timestamp string, optional upper bound

        Returns:
            List of HubSpotCall objects

        Raises:
            httpx.HTTPStatusError: On API error
        """
        filters = [
            {
                "propertyName": "hs_timestamp",
                "operator": "GTE",
                "value": from_date,
            }
        ]

        if to_date:
            filters.append(
                {
                    "propertyName": "hs_timestamp",
                    "operator": "LTE",
                    "value": to_date,
                }
            )

        all_calls: list[HubSpotCall] = []
        after_cursor: str | None = None

        while True:
            payload: dict = {
                "filterGroups": [{"filters": filters}],
                "properties": self.CALL_PROPERTIES.split(","),
                "limit": 100,
            }

            if after_cursor:
                payload["after"] = after_cursor

            response = await self._call_with_retry(
                method="POST",
                endpoint="/crm/v3/objects/calls/search",
                json=payload,
            )

            results = response.get("results", [])
            for item in results:
                try:
                    call = HubSpotCall.model_validate(item)
                    all_calls.append(call)
                except Exception as e:
                    logger.warning(f"[HUBSPOT] Failed to parse call: {e}")
                    continue

            # Check for next page
            paging = response.get("paging")
            if paging and paging.get("next"):
                after_cursor = paging["next"].get("after")
                if not after_cursor:
                    break
            else:
                break

        logger.info(f"[HUBSPOT] search_calls returned {len(all_calls)} calls")
        return all_calls

    async def _call_with_retry(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """
        Call HubSpot API with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path (relative to BASE_URL)
            json: Request body for POST requests
            params: Query parameters for GET requests

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: If all retries fail
            RuntimeError: If client not initialized
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}{endpoint}"
        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == "POST":
                    response = await self._client.post(url, json=json, params=params)
                elif method.upper() == "GET":
                    response = await self._client.get(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited - use Retry-After header or exponential backoff
                    wait_time = self.RETRY_DELAYS[
                        min(attempt, len(self.RETRY_DELAYS) - 1)
                    ]

                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = min(int(retry_after), 60)

                    logger.warning(
                        f"[HUBSPOT] Rate limited, waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Other HTTP error - don't retry
                    logger.error(
                        f"[HUBSPOT] API error {e.response.status_code}: {e.response.text}"
                    )
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[HUBSPOT] Unexpected error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")
