"""Miro connector implementation."""

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
class MiroConnector(BaseConnector):
    """
    Miro connector for manual board screenshot uploads.

    Authentication: MANUAL (no API - user provides screenshot)
    This is a manual connector - users upload Miro board screenshots.

    Configuration:
        No configuration required

    Usage:
        connector = MiroConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.MIRO,
            config={}
        )
        result = await connector.upload_screenshot(
            instance=instance,
            image_data=image_bytes,
            board_url="https://miro.com/app/board/abc",
            title="Product Roadmap"
        )
    """

    connector_type = ConnectorType.MIRO
    display_name = "Miro"
    description = "Upload Miro board screenshots for knowledge extraction"
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
        logger.info("[MIRO] Connection test successful (manual upload)")
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
            error_message="Use upload_screenshot() for Miro - this is a manual connector",
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
            error_message="Use upload_screenshot() for Miro - this is a manual connector",
        )

    async def upload_screenshot(
        self,
        instance: ConnectorInstance,
        image_data: bytes,
        board_url: str | None = None,
        title: str | None = None,
    ) -> SyncResult:
        """
        Process a Miro screenshot manually uploaded by user.

        Uses Gemini vision model to understand the board content,
        then extracts knowledge from the understanding.

        Args:
            instance: Connector instance
            image_data: PNG/JPEG screenshot bytes
            board_url: Optional Miro board URL
            title: Optional board title

        Returns:
            SyncResult with extraction stats
        """
        result = SyncResult(success=True)

        try:
            # Use Gemini vision to understand the board
            from src.tools.storyboard.gemini_client import GeminiStoryboardClient

            gemini = GeminiStoryboardClient()
            understanding = await gemini.understand_image(
                image_data=image_data,
                icp_preset=None,  # Raw extraction, no ICP filtering
            )

            # Create vision output text
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

            # Create source
            content_hash = hashlib.sha256(image_data[:1000]).hexdigest()

            source = KnowledgeSource(
                source_type=SourceType.MIRO_BOARD,
                external_url=board_url,
                source_title=title or "Miro Board",
                raw_content=vision_output,
                content_hash=content_hash,
                org_id=instance.org_id,  # Multi-tenant isolation
            )

            # Check for duplicates
            from src.knowledge.service import KnowledgeIngestionService

            knowledge_service = KnowledgeIngestionService()

            if await self._is_duplicate(knowledge_service, content_hash):
                result.items_skipped = 1
                logger.info(f"[MIRO] Skipping duplicate board: {board_url}")
                return result

            # Save source with org_id for multi-tenant isolation
            source.id = await knowledge_service._save_source(source, org_id=instance.org_id)
            result.items_fetched = 1

            # Extract knowledge from vision output
            from src.knowledge.extraction import KnowledgeExtractor
            extractor = KnowledgeExtractor()
            extraction_result = await extractor.extract(
                source=source,
                additional_context="Miro board screenshot - likely roadmap, workflow, or feature diagram",
            )

            if extraction_result.error:
                result.success = False
                result.error_message = extraction_result.error
                result.errors.append({
                    "board_url": board_url,
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
                f"[MIRO] Uploaded screenshot: {board_url or 'no-url'}, "
                f"extracted={result.items_extracted}, created={result.items_created}"
            )

        except Exception as e:
            logger.exception(f"[MIRO] Failed to upload screenshot: {e}")
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
