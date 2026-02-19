"""Clari Copilot connector implementation."""

import logging

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorType,
    SyncResult,
)
from src.connectors.clari.client import ClariCopilotClient
from src.connectors.clari.transformer import ClariTransformer
from src.connectors.registry import connector
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@connector
class ClariConnector(BaseConnector):
    """
    Clari Copilot connector for syncing AE call recordings and transcripts.

    Authentication: API Key (X-Api-Key + X-Api-Password headers)
    API: https://rest-api.copilot.clari.com
    Pagination: Page-based (page number as cursor)
    Rate limits: Handled via Retry-After headers

    Configuration:
        config["api_key"]: Clari API key (required)
        config["api_password"]: Clari API password (required)

    Sync strategy:
        - Incremental: Uses sync_cursor (page number) to resume from last position
        - Full: Pages through all available calls (up to 30 days equivalent)

    Example:
        connector = ClariConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.CLARI,
            config={"api_key": "...", "api_password": "..."}
        )
        result = await connector.sync(instance)
    """

    connector_type = ConnectorType.CLARI
    display_name = "Clari Copilot"
    description = "Sync AE call recordings and transcripts from Clari Copilot"
    auth_type = AuthType.API_KEY
    supports_webhook = False

    def get_required_config_fields(self) -> list[str]:
        """Return required config field names.

        Returns:
            List containing "api_key" and "api_password"
        """
        return ["api_key", "api_password"]

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """
        Test connection by fetching 1 call to verify credentials work.

        Args:
            instance: Connector instance with API credentials

        Returns:
            True if connection successful
        """
        api_key = instance.config.get("api_key")
        api_password = instance.config.get("api_password")

        if not api_key or not api_password:
            logger.error("[CLARI] No API key or password provided")
            return False

        try:
            async with ClariCopilotClient(api_key, api_password) as client:
                response = await client.get_calls(page=1, limit=1)

            logger.info(
                f"[CLARI] Connection test successful: found {response.total} total calls"
            )
            return True

        except Exception as e:
            logger.exception(f"[CLARI] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform incremental sync from cursor.

        Uses sync_cursor as a page number string to resume from last position.
        When no cursor is present, starts from page 1.

        Args:
            instance: Connector instance with sync cursor

        Returns:
            SyncResult with items synced and new cursor
        """
        api_key = instance.config.get("api_key")
        api_password = instance.config.get("api_password")

        if not api_key or not api_password:
            return SyncResult(
                success=False,
                error_message="No API key or password configured",
            )

        # Parse cursor as page number, defaulting to page 1
        start_page = 1
        if instance.sync_cursor:
            try:
                start_page = int(instance.sync_cursor)
            except ValueError:
                logger.warning(
                    f"[CLARI] Invalid sync cursor: {instance.sync_cursor}, starting from page 1"
                )
                start_page = 1

        logger.info(f"[CLARI] Starting incremental sync from page {start_page}")

        return await self._sync_calls(
            instance=instance,
            api_key=api_key,
            api_password=api_password,
            start_page=start_page,
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform full sync fetching all available calls.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        api_key = instance.config.get("api_key")
        api_password = instance.config.get("api_password")

        if not api_key or not api_password:
            return SyncResult(
                success=False,
                error_message="No API key or password configured",
            )

        logger.info("[CLARI] Starting full sync from page 1")

        return await self._sync_calls(
            instance=instance,
            api_key=api_key,
            api_password=api_password,
            start_page=1,
        )

    async def _sync_calls(
        self,
        instance: ConnectorInstance,
        api_key: str,
        api_password: str,
        start_page: int = 1,
    ) -> SyncResult:
        """
        Internal method to page through all calls and sync each one.

        For each call: fetches full details + transcript, transforms to
        KnowledgeSource, deduplicates via content_hash, saves, and extracts
        knowledge entries.

        Args:
            instance: Connector instance
            api_key: Clari API key
            api_password: Clari API password
            start_page: Page number to start syncing from

        Returns:
            SyncResult
        """
        result = SyncResult(success=True)
        transformer = ClariTransformer(extractor=KnowledgeExtractor())

        try:
            from src.knowledge.service import KnowledgeIngestionService

            knowledge_service = KnowledgeIngestionService()

            async with ClariCopilotClient(api_key, api_password) as client:
                page = start_page
                last_page = start_page

                while True:
                    calls_response = await client.get_calls(page=page, limit=50)

                    if not calls_response.calls:
                        break

                    result.items_fetched += len(calls_response.calls)
                    last_page = page

                    for call in calls_response.calls:
                        try:
                            # Fetch full call details including transcript
                            call_details = await client.get_call_details(call.id)

                            # Skip calls with no transcript content
                            transcript_text = call_details.transcript_to_text()
                            if not transcript_text.strip():
                                logger.debug(
                                    f"[CLARI] Skipping call {call.id}: empty transcript"
                                )
                                result.items_skipped += 1
                                continue

                            # Transform to KnowledgeSource
                            source = transformer.call_to_source(call_details)

                            # Dedup via content_hash
                            if await self._is_duplicate(knowledge_service, source.content_hash):
                                logger.debug(
                                    f"[CLARI] Skipping duplicate call {call.id}"
                                )
                                result.items_skipped += 1
                                continue

                            # Save source to database
                            source.id = await knowledge_service._save_source(source)

                            # Extract knowledge
                            entries = await transformer.extract_knowledge(source)

                            # Save entries
                            if entries:
                                saved_count = await knowledge_service._save_entries(entries)
                                result.items_created += saved_count

                            result.items_extracted += 1

                        except Exception as e:
                            logger.exception(
                                f"[CLARI] Failed to process call {call.id}: {e}"
                            )
                            result.errors.append(
                                {
                                    "call_id": call.id,
                                    "error": str(e),
                                }
                            )
                            continue

                    # Check for more pages
                    if not calls_response.has_more:
                        break
                    page += 1

                # Store the next page as cursor so incremental sync can resume
                result.cursor_after = str(last_page + 1)

        except Exception as e:
            logger.exception(f"[CLARI] Sync failed: {e}")
            result.success = False
            result.error_message = str(e)

        logger.info(
            f"[CLARI] Sync complete: fetched={result.items_fetched}, "
            f"extracted={result.items_extracted}, created={result.items_created}, "
            f"skipped={result.items_skipped}, errors={len(result.errors)}"
        )

        return result

    async def _is_duplicate(self, knowledge_service, content_hash: str) -> bool:
        """Check if content has already been ingested.

        Args:
            knowledge_service: KnowledgeIngestionService instance
            content_hash: SHA256 hash of the content

        Returns:
            True if a matching record already exists
        """
        if not content_hash:
            return False

        try:
            response = (
                knowledge_service.supabase.table("knowledge_sources")
                .select("id")
                .eq("content_hash", content_hash)
                .limit(1)
                .execute()
            )
            return len(response.data) > 0
        except Exception:
            return False
