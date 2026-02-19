"""Clari Copilot API Client - REST API wrapper."""

import asyncio
import logging

import httpx

from src.connectors.clari.schemas import (
    ClariCall,
    ClariCallDetails,
    ClariCallsResponse,
    ClariTranscriptEntry,
)

logger = logging.getLogger(__name__)


class ClariCopilotClient:
    """
    Async client for Clari Copilot REST API.

    Handles:
    - Call listing with pagination
    - Call details and transcript fetching
    - Exponential backoff retry
    - Rate limit handling

    Example:
        async with ClariCopilotClient(api_key="...", api_password="...") as client:
            response = await client.get_calls(page=1, limit=50)
            details = await client.get_call_details(call_id="abc123")
    """

    BASE_URL = "https://rest-api.copilot.clari.com"
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 5, 10]  # seconds

    def __init__(self, api_key: str, api_password: str):
        """
        Initialize Clari Copilot API client.

        Args:
            api_key: Clari API key (X-Api-Key header)
            api_password: Clari API password (X-Api-Password header)
        """
        self.api_key = api_key
        self.api_password = api_password
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "X-Api-Key": self.api_key,
                "X-Api-Password": self.api_password,
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def get_calls(self, page: int = 1, limit: int = 50) -> ClariCallsResponse:
        """
        Fetch paginated list of calls.

        Args:
            page: Page number (1-indexed)
            limit: Number of calls per page

        Returns:
            ClariCallsResponse with calls and pagination info

        Raises:
            httpx.HTTPStatusError: On API error
        """
        response = await self._call_with_retry(
            method="GET",
            endpoint="/calls",
            params={"page": page, "limit": limit},
        )

        calls = []
        for call_data in response.get("calls", []):
            participants_data = call_data.get("participants", [])
            from src.connectors.clari.schemas import ClariParticipant

            participants = [
                ClariParticipant(
                    name=p.get("name"),
                    email=p.get("email"),
                    role=p.get("role"),
                )
                for p in participants_data
            ]
            calls.append(
                ClariCall(
                    id=call_data.get("id", ""),
                    title=call_data.get("title"),
                    date=call_data.get("date"),
                    duration=call_data.get("duration"),
                    participants=participants,
                )
            )

        return ClariCallsResponse(
            calls=calls,
            total=response.get("total", 0),
            page=response.get("page", page),
            has_more=response.get("has_more", False),
        )

    async def get_call_details(self, call_id: str) -> ClariCallDetails:
        """
        Fetch full call details including transcript.

        Args:
            call_id: Clari call ID

        Returns:
            ClariCallDetails with call metadata and transcript entries

        Raises:
            httpx.HTTPStatusError: On API error
        """
        response = await self._call_with_retry(
            method="GET",
            endpoint="/call-details",
            params={"id": call_id},
        )

        # Parse call metadata
        call_data = response.get("call", {})
        participants_data = call_data.get("participants", [])
        from src.connectors.clari.schemas import ClariParticipant

        participants = [
            ClariParticipant(
                name=p.get("name"),
                email=p.get("email"),
                role=p.get("role"),
            )
            for p in participants_data
        ]

        call = ClariCall(
            id=call_data.get("id", call_id),
            title=call_data.get("title"),
            date=call_data.get("date"),
            duration=call_data.get("duration"),
            participants=participants,
        )

        # Parse transcript entries
        transcript_data = response.get("transcript", [])
        transcript = []
        for entry in transcript_data:
            try:
                transcript.append(
                    ClariTranscriptEntry(
                        speakerId=entry.get("speakerId", ""),
                        speakerName=entry.get("speakerName"),
                        start=entry.get("start", 0.0),
                        end=entry.get("end", 0.0),
                        text=entry.get("text", ""),
                    )
                )
            except Exception as e:
                logger.warning(f"[CLARI] Failed to parse transcript entry: {e}")
                continue

        return ClariCallDetails(call=call, transcript=transcript)

    async def _call_with_retry(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """
        Call Clari API with exponential backoff retry.

        Handles 429 rate limits using Retry-After header when available.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            params: Query parameters
            json: Request body

        Returns:
            Response JSON dict

        Raises:
            RuntimeError: If client not initialized via context manager
            httpx.HTTPStatusError: If all retries fail or non-429 error
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}{endpoint}"
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = await self._client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await self._client.post(url, params=params, json=json)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited — exponential backoff
                    wait_time = self.RETRY_DELAYS[
                        min(attempt, len(self.RETRY_DELAYS) - 1)
                    ]

                    # Honour Retry-After header if present
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after)

                    logger.warning(
                        f"[CLARI] Rate limited, waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(
                        f"[CLARI] API error {e.response.status_code}: {e.response.text}"
                    )
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[CLARI] Unexpected error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")
