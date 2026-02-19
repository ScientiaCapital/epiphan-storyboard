"""Loom connector implementation."""

import hashlib
import logging

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorType,
    SyncResult,
)
from src.connectors.registry import connector
from src.knowledge.base import KnowledgeSource, SourceType

logger = logging.getLogger(__name__)


@connector
class LoomConnector(BaseConnector):
    """
    Loom connector for manual transcript uploads.

    Authentication: MANUAL (no API - user provides transcript)
    This is a manual connector - users paste transcripts directly.

    Configuration:
        No configuration required

    Usage:
        connector = LoomConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.LOOM,
            config={}
        )
        result = await connector.upload_transcript(
            instance=instance,
            video_url="https://loom.com/share/abc123",
            transcript="Full transcript text...",
            title="Product Demo"
        )
    """

    connector_type = ConnectorType.LOOM
    display_name = "Loom"
    description = "Upload Loom video transcripts for knowledge extraction"
    auth_type = AuthType.MANUAL
    supports_webhook = False

    def get_required_config_fields(self) -> list[str]:
        """Return required config field names.

        Returns:
            Empty list - no config needed for manual upload
        """
        return []

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """
        Always returns True - manual upload doesn't need connection test.

        Args:
            instance: Connector instance

        Returns:
            True (always successful)
        """
        logger.info("[LOOM] Connection test successful (manual upload)")
        return True

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Not applicable for manual connector.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with error message
        """
        return SyncResult(
            success=False,
            error_message="Use upload_transcript() for Loom - this is a manual connector",
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Not applicable for manual connector.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with error message
        """
        return SyncResult(
            success=False,
            error_message="Use upload_transcript() for Loom - this is a manual connector",
        )

    async def upload_transcript(
        self,
        instance: ConnectorInstance,
        video_url: str,
        transcript: str,
        title: str | None = None,
    ) -> SyncResult:
        """
        Process a Loom transcript manually uploaded by user.

        Args:
            instance: Connector instance
            video_url: Loom share URL (e.g., https://loom.com/share/abc123)
            transcript: Full transcript text
            title: Optional video title

        Returns:
            SyncResult with extraction stats
        """
        result = SyncResult(success=True)

        try:
            # Create source
            content_hash = hashlib.sha256(transcript[:1000].encode()).hexdigest()

            source = KnowledgeSource(
                source_type=SourceType.LOOM_TRANSCRIPT,
                external_url=video_url,
                source_title=title or "Loom Video",
                raw_content=transcript,
                content_hash=content_hash,
                org_id=instance.org_id,  # Multi-tenant isolation
            )

            # Check for duplicates
            from src.knowledge.service import KnowledgeIngestionService

            knowledge_service = KnowledgeIngestionService()

            if await self._is_duplicate(knowledge_service, content_hash):
                result.items_skipped = 1
                logger.info(f"[LOOM] Skipping duplicate transcript: {video_url}")
                return result

            # Save source with org_id for multi-tenant isolation
            source.id = await knowledge_service._save_source(source, org_id=instance.org_id)
            result.items_fetched = 1

            # Extract knowledge
            from src.knowledge.extraction import KnowledgeExtractor
            extractor = KnowledgeExtractor()
            extraction_result = await extractor.extract(
                source=source,
                additional_context="Loom video transcript - likely demo or walkthrough",
            )

            if extraction_result.error:
                result.success = False
                result.error_message = extraction_result.error
                result.errors.append({
                    "video_url": video_url,
                    "error": extraction_result.error,
                })
                return result

            # Save entries with org_id for multi-tenant isolation
            if extraction_result.entries:
                for entry in extraction_result.entries:
                    entry.org_id = instance.org_id
                saved_count = await knowledge_service._save_entries(extraction_result.entries)
                result.items_created = saved_count

            result.items_extracted = 1

            logger.info(
                f"[LOOM] Uploaded transcript: {video_url}, "
                f"extracted={result.items_extracted}, created={result.items_created}"
            )

        except Exception as e:
            logger.exception(f"[LOOM] Failed to upload transcript: {e}")
            result.success = False
            result.error_message = str(e)

        return result

    async def _is_duplicate(self, knowledge_service, content_hash: str) -> bool:
        """Check if content has already been ingested."""
        if not content_hash:
            return False

        try:
            response = knowledge_service.supabase.table("knowledge_sources") \
                .select("id") \
                .eq("content_hash", content_hash) \
                .limit(1) \
                .execute()
            return len(response.data) > 0
        except Exception:
            return False
