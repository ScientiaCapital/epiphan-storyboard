"""
Close CRM Ingestion Pipeline.

Fetches calls and notes from Close CRM API and extracts knowledge.

Close CRM API Docs: https://developer.close.com/

Required env vars:
- CLOSE_API_KEY: Close CRM API key

Usage:
    ingester = CloseCRMIngester()
    results = await ingester.ingest_recent_calls(days_back=7)
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx

from src.knowledge.base import (
    ExtractionResult,
    KnowledgeSource,
    SourceType,
)
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@dataclass
class CloseCRMConfig:
    """Configuration for Close CRM ingestion."""

    api_key: str = ""
    base_url: str = "https://api.close.com/api/v1"

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("CLOSE_API_KEY", "")


class CloseCRMIngester:
    """
    Ingests calls and notes from Close CRM.
    """

    def __init__(
        self,
        config: Optional[CloseCRMConfig] = None,
        extractor: Optional[KnowledgeExtractor] = None,
        supabase_client=None,
    ):
        self.config = config or CloseCRMConfig()
        self.extractor = extractor or KnowledgeExtractor()
        self.supabase = supabase_client  # Optional Supabase client for persistence

    async def ingest_recent_calls(
        self,
        days_back: int = 7,
        limit: int = 100,
        extract: bool = True,
    ) -> list[ExtractionResult]:
        """
        Ingest recent calls from Close CRM.

        Args:
            days_back: How many days back to fetch
            limit: Maximum number of calls to fetch
            extract: Whether to run knowledge extraction

        Returns:
            List of extraction results
        """
        if not self.config.api_key:
            raise ValueError("CLOSE_API_KEY not configured")

        # Calculate date range
        since_date = datetime.utcnow() - timedelta(days=days_back)
        date_str = since_date.strftime("%Y-%m-%d")

        logger.info(f"Fetching Close CRM calls since {date_str}")

        # Fetch calls from Close CRM
        calls = await self._fetch_calls(since_date=date_str, limit=limit)
        logger.info(f"Fetched {len(calls)} calls from Close CRM")

        results = []
        for call in calls:
            try:
                # Create source record
                source = self._call_to_source(call)

                # Check for duplicates
                if await self._is_duplicate(source.content_hash):
                    logger.debug(f"Skipping duplicate call: {source.external_id}")
                    continue

                # Save source to database
                if self.supabase:
                    source.id = await self._save_source(source)

                # Extract knowledge
                if extract and source.raw_content:
                    result = await self.extractor.extract(
                        source=source,
                        additional_context=f"Close CRM call with {', '.join(source.participant_names or [])}",
                    )

                    # Save extracted knowledge
                    if self.supabase and result.entries:
                        await self._save_knowledge_entries(result.entries)

                    results.append(result)

            except Exception as e:
                logger.exception(f"Failed to process call {call.get('id')}: {e}")

        return results

    async def ingest_recent_notes(
        self,
        days_back: int = 7,
        limit: int = 100,
        extract: bool = True,
    ) -> list[ExtractionResult]:
        """
        Ingest recent notes from Close CRM.

        Args:
            days_back: How many days back to fetch
            limit: Maximum number of notes to fetch
            extract: Whether to run knowledge extraction

        Returns:
            List of extraction results
        """
        if not self.config.api_key:
            raise ValueError("CLOSE_API_KEY not configured")

        since_date = datetime.utcnow() - timedelta(days=days_back)
        date_str = since_date.strftime("%Y-%m-%d")

        logger.info(f"Fetching Close CRM notes since {date_str}")

        # Fetch notes from Close CRM
        notes = await self._fetch_notes(since_date=date_str, limit=limit)
        logger.info(f"Fetched {len(notes)} notes from Close CRM")

        results = []
        for note in notes:
            try:
                source = self._note_to_source(note)

                if await self._is_duplicate(source.content_hash):
                    logger.debug(f"Skipping duplicate note: {source.external_id}")
                    continue

                if self.supabase:
                    source.id = await self._save_source(source)

                if extract and source.raw_content:
                    result = await self.extractor.extract(
                        source=source,
                        additional_context="Close CRM note/call summary",
                    )

                    if self.supabase and result.entries:
                        await self._save_knowledge_entries(result.entries)

                    results.append(result)

            except Exception as e:
                logger.exception(f"Failed to process note {note.get('id')}: {e}")

        return results

    async def _fetch_calls(self, since_date: str, limit: int = 100) -> list[dict]:
        """Fetch calls from Close CRM API."""
        calls = []
        skip = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(calls) < limit:
                response = await client.get(
                    f"{self.config.base_url}/activity/call/",
                    params={
                        "date_created__gte": since_date,
                        "_limit": min(100, limit - len(calls)),
                        "_skip": skip,
                    },
                    auth=(self.config.api_key, ""),
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

        return calls[:limit]

    async def _fetch_notes(self, since_date: str, limit: int = 100) -> list[dict]:
        """Fetch notes from Close CRM API."""
        notes = []
        skip = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(notes) < limit:
                response = await client.get(
                    f"{self.config.base_url}/activity/note/",
                    params={
                        "date_created__gte": since_date,
                        "_limit": min(100, limit - len(notes)),
                        "_skip": skip,
                    },
                    auth=(self.config.api_key, ""),
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

        return notes[:limit]

    def _call_to_source(self, call: dict) -> KnowledgeSource:
        """Convert Close CRM call to KnowledgeSource."""
        # Extract transcript or note text
        # Close stores call recordings and may have transcripts
        transcript = call.get("note", "") or call.get("recording_url", "")

        # Get participant info
        participants = []
        if call.get("user_name"):
            participants.append(call["user_name"])
        if call.get("contact_name"):
            participants.append(call["contact_name"])

        # Create content hash for deduplication
        content_hash = hashlib.sha256(
            f"{call.get('id', '')}:{transcript[:500]}".encode()
        ).hexdigest()

        return KnowledgeSource(
            source_type=SourceType.CLOSE_CRM_CALL,
            external_id=call.get("id"),
            source_title=f"Call with {call.get('contact_name', 'Unknown')}",
            source_date=datetime.fromisoformat(
                call.get("date_created", "").replace("Z", "+00:00")
            ) if call.get("date_created") else None,
            duration_seconds=call.get("duration"),
            participant_names=participants,
            raw_content=transcript,
            content_hash=content_hash,
        )

    def _note_to_source(self, note: dict) -> KnowledgeSource:
        """Convert Close CRM note to KnowledgeSource."""
        content = note.get("note", "")

        content_hash = hashlib.sha256(
            f"{note.get('id', '')}:{content[:500]}".encode()
        ).hexdigest()

        participants = []
        if note.get("user_name"):
            participants.append(note["user_name"])
        if note.get("contact_name"):
            participants.append(note["contact_name"])

        return KnowledgeSource(
            source_type=SourceType.CLOSE_CRM_NOTE,
            external_id=note.get("id"),
            source_title=f"Note: {content[:50]}...",
            source_date=datetime.fromisoformat(
                note.get("date_created", "").replace("Z", "+00:00")
            ) if note.get("date_created") else None,
            participant_names=participants,
            raw_content=content,
            content_hash=content_hash,
        )

    async def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content has already been ingested."""
        if not self.supabase or not content_hash:
            return False

        try:
            response = self.supabase.table("knowledge_sources") \
                .select("id") \
                .eq("content_hash", content_hash) \
                .limit(1) \
                .execute()
            return len(response.data) > 0
        except Exception:
            return False

    async def _save_source(self, source: KnowledgeSource) -> UUID:
        """Save source to Supabase."""
        data = {
            "source_type": source.source_type.value,
            "external_id": source.external_id,
            "external_url": source.external_url,
            "source_title": source.source_title,
            "source_date": source.source_date.isoformat() if source.source_date else None,
            "duration_seconds": source.duration_seconds,
            "participant_names": source.participant_names,
            "raw_content": source.raw_content,
            "content_hash": source.content_hash,
            "extraction_status": "completed" if source.raw_content else "pending",
        }

        response = self.supabase.table("knowledge_sources").insert(data).execute()
        return UUID(response.data[0]["id"])

    async def _save_knowledge_entries(self, entries: list) -> int:
        """Save knowledge entries to Supabase."""
        if not entries:
            return 0

        data = [entry.to_dict() for entry in entries]

        response = self.supabase.table("coperniq_knowledge").insert(data).execute()
        return len(response.data)
