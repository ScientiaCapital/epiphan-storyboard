"""
Knowledge Ingestion Service - Main orchestrator.

Coordinates ingestion from all sources and provides a unified API.
"""

import logging
import os
from dataclasses import dataclass

from src.knowledge.base import (
    ExtractionResult,
    KnowledgeEntry,
    KnowledgeType,
)
from src.knowledge.close_crm import CloseCRMIngester
from src.knowledge.extraction import KnowledgeExtractor
try:
    from supabase import Client, create_client
except ImportError:
    Client = None  # type: ignore[assignment,misc]
    create_client = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for Knowledge Ingestion Service."""

    supabase_url: str = ""
    supabase_key: str = ""

    def __post_init__(self):
        if not self.supabase_url:
            self.supabase_url = os.getenv("SUPABASE_URL", "")
        if not self.supabase_key:
            self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")


class KnowledgeIngestionService:
    """
    Main service for knowledge ingestion and retrieval.

    Usage:
        service = KnowledgeIngestionService()

        # Ingest from Close CRM
        await service.ingest_close_crm(days_back=7)

        # Ingest from Loom transcript
        await service.ingest_loom_transcript(url="...", transcript="...")

        # Ingest from Miro screenshot
        await service.ingest_miro_board(image_data=b"...")

        # Query knowledge for storyboard
        knowledge = await service.get_knowledge_for_storyboard(
            audience="c_suite",
            industry="solar"
        )
    """

    def __init__(self, config: ServiceConfig | None = None):
        self.config = config or ServiceConfig()
        self._supabase: Client | None = None
        self._extractor: KnowledgeExtractor | None = None

    @property
    def supabase(self) -> Client:
        """Lazy initialization of Supabase client."""
        if self._supabase is None:
            if not self.config.supabase_url or not self.config.supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
            self._supabase = create_client(
                self.config.supabase_url,
                self.config.supabase_key,
            )
        return self._supabase

    @property
    def extractor(self) -> KnowledgeExtractor:
        """Lazy initialization of extractor."""
        if self._extractor is None:
            self._extractor = KnowledgeExtractor()
        return self._extractor

    # =========================================================================
    # INGESTION METHODS
    # =========================================================================

    async def ingest_close_crm(
        self,
        days_back: int = 7,
        limit: int = 100,
        include_calls: bool = True,
        include_notes: bool = True,
    ) -> dict:
        """
        Ingest recent data from Close CRM.

        Args:
            days_back: How many days back to fetch
            limit: Max items per type
            include_calls: Whether to ingest calls
            include_notes: Whether to ingest notes

        Returns:
            Summary of ingestion results
        """
        ingester = CloseCRMIngester(
            extractor=self.extractor,
            supabase_client=self.supabase,
        )

        results = {
            "calls": [],
            "notes": [],
            "total_extracted": 0,
            "errors": [],
        }

        if include_calls:
            try:
                call_results = await ingester.ingest_recent_calls(
                    days_back=days_back,
                    limit=limit,
                )
                results["calls"] = call_results
                results["total_extracted"] += sum(
                    r.items_extracted for r in call_results
                )
            except Exception as e:
                logger.exception(f"Failed to ingest calls: {e}")
                results["errors"].append(f"Calls: {str(e)}")

        if include_notes:
            try:
                note_results = await ingester.ingest_recent_notes(
                    days_back=days_back,
                    limit=limit,
                )
                results["notes"] = note_results
                results["total_extracted"] += sum(
                    r.items_extracted for r in note_results
                )
            except Exception as e:
                logger.exception(f"Failed to ingest notes: {e}")
                results["errors"].append(f"Notes: {str(e)}")

        logger.info(
            f"Close CRM ingestion complete: {results['total_extracted']} items extracted"
        )
        return results

    async def ingest_loom_transcript(
        self,
        video_url: str,
        transcript: str,
        title: str | None = None,
    ) -> ExtractionResult:
        """
        Ingest a Loom video transcript.

        Args:
            video_url: Loom share URL
            transcript: Full transcript text
            title: Optional video title

        Returns:
            ExtractionResult with extracted knowledge
        """
        import hashlib

        from src.knowledge.base import KnowledgeSource, SourceType

        source = KnowledgeSource(
            source_type=SourceType.LOOM_TRANSCRIPT,
            external_url=video_url,
            source_title=title or "Loom Video",
            raw_content=transcript,
            content_hash=hashlib.sha256(transcript[:1000].encode()).hexdigest(),
        )

        # Save source
        source.id = await self._save_source(source)

        # Extract knowledge
        result = await self.extractor.extract(
            source=source,
            additional_context="Loom video transcript - likely demo or walkthrough",
        )

        # Save entries
        if result.entries:
            await self._save_entries(result.entries)

        return result

    async def ingest_miro_board(
        self,
        image_data: bytes,
        board_url: str | None = None,
        title: str | None = None,
    ) -> ExtractionResult:
        """
        Ingest a Miro board screenshot.

        Uses vision model to understand the board content,
        then extracts knowledge from the understanding.

        Args:
            image_data: PNG/JPEG screenshot bytes
            board_url: Optional Miro board URL
            title: Optional board title

        Returns:
            ExtractionResult with extracted knowledge
        """
        import hashlib

        from src.knowledge.base import KnowledgeSource, SourceType
        from src.tools.storyboard.gemini_client import GeminiStoryboardClient

        # First, use vision model to understand the board
        gemini = GeminiStoryboardClient()
        understanding = await gemini.understand_image(
            image_data=image_data,
            icp_preset=None,  # Raw extraction, no ICP filtering
        )

        # Create source with vision model output as content
        vision_output = f"""
MIRO BOARD ANALYSIS:
Headline: {understanding.headline}
Tagline: {understanding.tagline}
What It Does: {understanding.what_it_does}
Business Value: {understanding.business_value}
Who Benefits: {understanding.who_benefits}
Differentiator: {understanding.differentiator}
Pain Point: {understanding.pain_point_addressed}
Raw Extracted: {understanding.raw_extracted_text}
"""

        source = KnowledgeSource(
            source_type=SourceType.MIRO_BOARD,
            external_url=board_url,
            source_title=title or "Miro Board",
            raw_content=vision_output,
            content_hash=hashlib.sha256(image_data[:1000]).hexdigest(),
        )

        # Save source
        source.id = await self._save_source(source)

        # Extract knowledge from vision output
        result = await self.extractor.extract(
            source=source,
            additional_context="Miro board screenshot - likely roadmap, workflow, or feature diagram",
        )

        if result.entries:
            await self._save_entries(result.entries)

        return result

    async def ingest_code(
        self,
        code_content: str,
        file_path: str | None = None,
        author: str | None = None,
    ) -> ExtractionResult:
        """
        Ingest engineer code to extract feature information.

        Args:
            code_content: The code content
            file_path: Optional file path
            author: Optional author name

        Returns:
            ExtractionResult with extracted knowledge
        """
        import hashlib

        from src.knowledge.base import KnowledgeSource, SourceType

        source = KnowledgeSource(
            source_type=SourceType.ENGINEER_CODE,
            file_path=file_path,
            source_title=file_path or "Code Snippet",
            participant_names=[author] if author else [],
            raw_content=code_content,
            content_hash=hashlib.sha256(code_content[:1000].encode()).hexdigest(),
        )

        source.id = await self._save_source(source)

        result = await self.extractor.extract(
            source=source,
            additional_context="Engineer code - extract feature names and capabilities",
        )

        if result.entries:
            await self._save_entries(result.entries)

        return result

    async def ingest_source(
        self,
        source,
        entries: list[KnowledgeEntry],
        org_id: str,
    ) -> ExtractionResult:
        """
        Generic method to ingest a knowledge source with extracted entries.

        Used by connectors (Linear, Notion, etc.) to store knowledge.

        Args:
            source: KnowledgeSource object
            entries: List of extracted KnowledgeEntry objects
            org_id: Organization ID for multi-tenant isolation

        Returns:
            ExtractionResult with ingestion stats
        """
        try:
            # Set org_id on source for multi-tenant isolation
            source.org_id = org_id

            # Save source with org_id
            source_id = await self._save_source(source, org_id=org_id)

            # Update source_id and org_id in entries
            for entry in entries:
                entry.source_id = source_id
                entry.org_id = org_id

            # Save entries (org_id included via to_dict())
            created_count = await self._save_entries(entries)

            logger.info(
                f"Ingested source {source.source_title} for org {org_id}: "
                f"{len(entries)} extracted, {created_count} created"
            )

            return ExtractionResult(
                source_id=source_id,
                items_extracted=len(entries),
                items_created=created_count,
                items_skipped=0,
                entries=entries,
                execution_time_ms=0,
            )

        except Exception as e:
            logger.exception(f"Failed to ingest source: {e}")
            return ExtractionResult(
                source_id=source.id,
                error=str(e),
                execution_time_ms=0,
            )

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    async def get_knowledge_for_storyboard(
        self,
        audience: str = "c_suite",
        industry: str | None = None,
        knowledge_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[KnowledgeEntry]:
        """
        Get relevant knowledge for storyboard generation.

        Args:
            audience: Target audience (c_suite, business_owner, etc.)
            industry: Target industry (solar, hvac, etc.)
            knowledge_types: Types to include (default: pain_point, metric, approved_term, feature)
            limit: Max entries to return

        Returns:
            List of KnowledgeEntry objects
        """
        if knowledge_types is None:
            knowledge_types = ["pain_point", "metric", "approved_term", "feature"]

        # Build query
        query = (
            self.supabase.table("knowledge")
            .select("*")
            .in_("knowledge_type", knowledge_types)
            .gte("confidence_score", 0.7)
            .order("usage_count", desc=True)
            .order("confidence_score", desc=True)
            .limit(limit)
        )

        # Add audience filter if applicable
        # Note: PostgreSQL array contains syntax
        if audience:
            query = query.or_(f"audience.cs.{{{audience}}},audience.eq.{{}}")

        if industry:
            query = query.or_(f"industries.cs.{{{industry}}},industries.eq.{{}}")

        response = query.execute()

        entries = []
        for row in response.data:
            entry = KnowledgeEntry(
                knowledge_type=KnowledgeType(row["knowledge_type"]),
                content=row["content"],
                context=row.get("context"),
                verbatim=row.get("verbatim", False),
                confidence_score=row.get("confidence_score", 0.8),
                audience=row.get("audience", []),
                industries=row.get("industries", []),
                product_areas=row.get("product_areas", []),
                speaker_name=row.get("speaker_name"),
                speaker_role=row.get("speaker_role"),
                company_name=row.get("company_name"),
            )
            entries.append(entry)

        return entries

    async def get_banned_terms(self) -> list[str]:
        """Get all banned terms from knowledge base."""
        response = (
            self.supabase.table("knowledge")
            .select("content")
            .eq("knowledge_type", "banned_term")
            .execute()
        )

        return [row["content"] for row in response.data]

    async def get_approved_terms(self, audience: str | None = None) -> list[str]:
        """Get approved terms, optionally filtered by audience."""
        query = (
            self.supabase.table("knowledge")
            .select("content, audience")
            .eq("knowledge_type", "approved_term")
        )

        response = query.execute()

        if audience:
            return [
                row["content"]
                for row in response.data
                if not row.get("audience") or audience in row.get("audience", [])
            ]
        return [row["content"] for row in response.data]

    async def search_knowledge(
        self,
        query: str,
        knowledge_types: list[str] | None = None,
        limit: int = 20,
    ) -> list[KnowledgeEntry]:
        """
        Full-text search across knowledge base.

        Args:
            query: Search query
            knowledge_types: Optional filter by types
            limit: Max results

        Returns:
            List of matching KnowledgeEntry objects
        """
        # Use the database function for full-text search
        response = self.supabase.rpc(
            "search_knowledge",
            {
                "search_query": query,
                "knowledge_types": knowledge_types,
                "min_confidence": 0.5,
                "max_results": limit,
            },
        ).execute()

        entries = []
        for row in response.data:
            entry = KnowledgeEntry(
                knowledge_type=KnowledgeType(row["knowledge_type"]),
                content=row["content"],
                context=row.get("context"),
                confidence_score=row.get("confidence_score", 0.8),
            )
            entries.append(entry)

        return entries

    async def increment_usage(self, entry_id: str) -> None:
        """Increment usage count for a knowledge entry (for learning)."""
        self.supabase.rpc("increment_usage_count", {"entry_id": entry_id}).execute()

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _save_source(self, source, org_id: str | None = None) -> str:
        """Save source to database.

        Args:
            source: KnowledgeSource object
            org_id: Organization ID for multi-tenant isolation
        """
        data = {
            "source_type": source.source_type.value,
            "external_id": source.external_id,
            "external_url": source.external_url,
            "file_path": source.file_path,
            "source_title": source.source_title,
            "source_date": source.source_date.isoformat()
            if source.source_date
            else None,
            "duration_seconds": source.duration_seconds,
            "participant_names": source.participant_names,
            "raw_content": source.raw_content,
            "content_hash": source.content_hash,
            "extraction_status": "completed",
        }

        # Include org_id for multi-tenant isolation
        effective_org_id = org_id or getattr(source, "org_id", None)
        if effective_org_id:
            data["org_id"] = effective_org_id

        response = self.supabase.table("knowledge_sources").insert(data).execute()
        return response.data[0]["id"]

    async def _save_entries(self, entries: list[KnowledgeEntry]) -> int:
        """Save knowledge entries to database."""
        if not entries:
            return 0

        data = [entry.to_dict() for entry in entries]
        response = self.supabase.table("knowledge").insert(data).execute()
        return len(response.data)
