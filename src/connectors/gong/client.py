"""Gong API Client - REST API wrapper."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from src.connectors.gong.schemas import (
    GongCallsResponse,
    GongTranscript,
    GongTranscriptTopic,
)

logger = logging.getLogger(__name__)


class GongAPIClient:
    """
    Async client for Gong API v2.

    Handles:
    - Call listing with pagination
    - Transcript fetching
    - Exponential backoff retry
    - Rate limit handling

    Example:
        async with GongAPIClient(access_token="...") as client:
            calls = await client.get_calls(from_date=datetime.now() - timedelta(days=7))
            transcripts = await client.get_transcripts([call.id for call in calls])
    """

    BASE_URL = "https://api.gong.io/v2"
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 10, 15]  # seconds

    def __init__(self, access_token: str):
        """
        Initialize Gong API client.

        Args:
            access_token: OAuth2 bearer token
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
        from_date: datetime,
        to_date: datetime | None = None,
        cursor: str | None = None,
    ) -> GongCallsResponse:
        """
        Fetch calls within date range.

        Gong API uses ISO 8601 timestamps and cursor-based pagination.

        Args:
            from_date: Start date (inclusive)
            to_date: End date (inclusive), defaults to now
            cursor: Pagination cursor from previous response

        Returns:
            GongCallsResponse with calls and next cursor

        Raises:
            httpx.HTTPStatusError: On API error
        """
        if to_date is None:
            to_date = datetime.now(UTC)

        # Gong expects ISO 8601 format
        filter_payload = {
            "filter": {
                "fromDateTime": from_date.isoformat(),
                "toDateTime": to_date.isoformat(),
            }
        }

        if cursor:
            filter_payload["cursor"] = cursor

        response = await self._call_with_retry(
            method="POST",
            endpoint="/calls",
            json=filter_payload,
        )

        return GongCallsResponse.from_api_response(response)

    async def get_transcripts(self, call_ids: list[str]) -> list[GongTranscript]:
        """
        Fetch transcripts for specific calls.

        Gong limits to 100 call IDs per request.

        Args:
            call_ids: List of call IDs

        Returns:
            List of GongTranscript objects

        Raises:
            httpx.HTTPStatusError: On API error
        """
        if not call_ids:
            return []

        # Batch into groups of 100
        transcripts = []
        for i in range(0, len(call_ids), 100):
            batch = call_ids[i : i + 100]

            payload = {"filter": {"callIds": batch}}

            response = await self._call_with_retry(
                method="POST",
                endpoint="/calls/transcript",
                json=payload,
            )

            # Parse transcripts from response
            for transcript_data in response.get("callTranscripts", []):
                try:
                    # Build transcript from Gong structure
                    call_id = transcript_data.get("callId", "")
                    topics = []

                    for topic_data in transcript_data.get("transcript", []):
                        topic_name = topic_data.get("topic", "General")
                        sentences_data = topic_data.get("sentences", [])

                        # Parse sentences
                        from src.connectors.gong.schemas import GongTranscriptSentence

                        sentences = [
                            GongTranscriptSentence(
                                start=s.get("start", 0),
                                end=s.get("end", 0),
                                text=s.get("text", ""),
                                speakerId=s.get("speakerId", ""),
                            )
                            for s in sentences_data
                        ]

                        topics.append(
                            GongTranscriptTopic(
                                topicName=topic_name,
                                sentences=sentences,
                            )
                        )

                    transcript = GongTranscript(callId=call_id, topics=topics)
                    transcripts.append(transcript)

                except Exception as e:
                    logger.warning(f"Failed to parse transcript for call: {e}")
                    continue

        return transcripts

    async def _call_with_retry(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
    ) -> dict:
        """
        Call Gong API with exponential backoff retry.

        Follows pattern from browserbase_client.py

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            json: Request body

        Returns:
            Response JSON

        Raises:
            httpx.HTTPStatusError: If all retries fail
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.BASE_URL}{endpoint}"
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == "POST":
                    response = await self._client.post(url, json=json)
                elif method.upper() == "GET":
                    response = await self._client.get(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = self.RETRY_DELAYS[
                        min(attempt, len(self.RETRY_DELAYS) - 1)
                    ]

                    # Check for Retry-After header
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after)

                    logger.warning(
                        f"[GONG] Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Other HTTP error - don't retry
                    logger.error(
                        f"[GONG] API error {e.response.status_code}: {e.response.text}"
                    )
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[GONG] Unexpected error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")
