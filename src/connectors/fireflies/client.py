"""Fireflies GraphQL API Client."""

import asyncio
import logging

import httpx

from src.connectors.fireflies.schemas import (
    FirefliesActionItem,
    FirefliesKeyword,
    FirefliesSentence,
    FirefliesTranscript,
    FirefliesTranscriptsResponse,
    FirefliesUser,
)

logger = logging.getLogger(__name__)


class FirefliesGraphQLClient:
    """
    Async client for Fireflies GraphQL API.

    Handles:
    - GraphQL queries for transcripts
    - Pagination
    - Exponential backoff retry
    - Rate limit handling

    Example:
        async with FirefliesGraphQLClient(api_key="...") as client:
            transcripts = await client.get_transcripts(limit=50)
    """

    ENDPOINT = "https://api.fireflies.ai/graphql"
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 10, 15]  # seconds

    def __init__(self, api_key: str):
        """
        Initialize Fireflies GraphQL client.

        Args:
            api_key: Fireflies API key (Bearer token)
        """
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def get_transcripts(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> FirefliesTranscriptsResponse:
        """
        Fetch transcripts with pagination.

        Args:
            limit: Number of transcripts to fetch (max 50)
            skip: Number of transcripts to skip (for pagination)

        Returns:
            FirefliesTranscriptsResponse with transcripts

        Raises:
            httpx.HTTPStatusError: On API error
        """
        query = """
        query Transcripts($limit: Int, $skip: Int) {
            transcripts(limit: $limit, skip: $skip) {
                id
                title
                date
                duration
                meeting_url
                video_url
                organizer {
                    user_id
                    name
                    email
                }
                participants {
                    displayName
                }
                sentences {
                    text
                    speaker_name
                    speaker_id
                    start_time
                    end_time
                }
                action_items {
                    text
                    assignee
                }
                keywords {
                    text
                    score
                }
                summary {
                    overview
                    action_items
                    outline
                }
            }
        }
        """

        variables = {
            "limit": limit,
            "skip": skip,
        }

        response = await self._call_graphql_with_retry(query, variables)

        # Parse response
        transcripts_data = response.get("data", {}).get("transcripts", [])
        transcripts = []

        for t_data in transcripts_data:
            try:
                # Parse sentences
                sentences = [
                    FirefliesSentence(
                        text=s.get("text", ""),
                        speaker_name=s.get("speaker_name"),
                        speaker_id=s.get("speaker_id"),
                        start_time=s.get("start_time"),
                        end_time=s.get("end_time"),
                    )
                    for s in t_data.get("sentences", [])
                ]

                # Parse action items
                action_items = [
                    FirefliesActionItem(
                        text=a.get("text", ""),
                        assignee=a.get("assignee"),
                    )
                    for a in t_data.get("action_items", [])
                ]

                # Parse keywords
                keywords = [
                    FirefliesKeyword(
                        text=k.get("text", ""),
                        score=k.get("score"),
                    )
                    for k in t_data.get("keywords", [])
                ]

                # Parse participants
                participants = [
                    p.get("displayName", "Unknown")
                    for p in t_data.get("participants", [])
                    if p.get("displayName")
                ]

                # Parse organizer
                organizer = None
                org_data = t_data.get("organizer")
                if org_data:
                    organizer = FirefliesUser(
                        user_id=org_data.get("user_id", ""),
                        name=org_data.get("name"),
                        email=org_data.get("email"),
                    )

                transcript = FirefliesTranscript(
                    id=t_data.get("id", ""),
                    title=t_data.get("title"),
                    date=t_data.get("date"),
                    duration=t_data.get("duration"),
                    meeting_url=t_data.get("meeting_url"),
                    video_url=t_data.get("video_url"),
                    organizer=organizer,
                    participants=participants,
                    sentences=sentences,
                    action_items=action_items,
                    keywords=keywords,
                    summary=t_data.get("summary"),
                )
                transcripts.append(transcript)

            except Exception as e:
                logger.warning(f"Failed to parse transcript: {e}")
                continue

        return FirefliesTranscriptsResponse(transcripts=transcripts)

    async def _call_graphql_with_retry(
        self,
        query: str,
        variables: dict | None = None,
    ) -> dict:
        """
        Call Fireflies GraphQL API with exponential backoff retry.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response JSON

        Raises:
            httpx.HTTPStatusError: If all retries fail
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        payload = {
            "query": query,
            "variables": variables or {},
        }

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.post(self.ENDPOINT, json=payload)
                response.raise_for_status()

                data = response.json()

                # Check for GraphQL errors
                if "errors" in data:
                    errors = data["errors"]
                    error_messages = [e.get("message", str(e)) for e in errors]
                    raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")

                return data

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = self.RETRY_DELAYS[
                        min(attempt, len(self.RETRY_DELAYS) - 1)
                    ]

                    # Check for Retry-After header (capped at 60s)
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = min(int(retry_after), 60)

                    logger.warning(
                        f"[FIREFLIES] Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Other HTTP error - don't retry
                    logger.error(
                        f"[FIREFLIES] API error {e.response.status_code}: {e.response.text}"
                    )
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[FIREFLIES] Unexpected error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")
