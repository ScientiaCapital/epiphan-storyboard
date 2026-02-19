"""Close CRM connector implementation."""

import logging
from datetime import datetime, timedelta, timezone

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorType,
    SyncResult,
)
from src.connectors.close.client import CloseCRMClient
from src.connectors.close.transformer import CloseTransformer
from src.connectors.registry import connector
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@connector
class CloseConnector(BaseConnector):
    """
    Close CRM connector for syncing calls and notes.

    Authentication: API Key (Basic auth with API key as username, empty password)
    API: REST (https://api.close.com/api/v1/)
    Pagination: Offset-based (_limit + _skip)

    Configuration:
        config["api_key"]: Close CRM API key (required)

    Sync strategy:
        - Incremental: Uses sync_cursor (ISO date) to fetch items created after cursor
        - Full: Fetches last 30 days of calls and notes

    Example:
        connector = CloseConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.CLOSE,
            config={"api_key": "your-api-key"}
        )
        result = await connector.sync(instance)
    """

    connector_type = ConnectorType.CLOSE
    display_name = "Close CRM"
    description = "Sync calls, notes, and activities from Close CRM"
    auth_type = AuthType.API_KEY
    supports_webhook = False

    def get_required_config_fields(self) -> list[str]:
        """Return required config field names.

        Returns:
            List containing "api_key"
        """
        return ["api_key"]

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """
        Test connection by fetching current user (GET /api/v1/me/).

        Args:
            instance: Connector instance with API key

        Returns:
            True if connection successful
        """
        api_key = instance.config.get("api_key")
        if not api_key:
            logger.error("[CLOSE] No API key provided")
            return False

        try:
            async with CloseCRMClient(api_key) as client:
                result = await client.test_connection()

            logger.info(f"[CLOSE] Connection test {'successful' if result else 'failed'}")
            return result

        except Exception as e:
            logger.exception(f"[CLOSE] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform incremental sync from cursor.

        Uses sync_cursor as ISO date (YYYY-MM-DD) for date_created__gte filter.

        Args:
            instance: Connector instance with sync cursor

        Returns:
            SyncResult with items synced and new cursor
        """
        api_key = instance.config.get("api_key")
        if not api_key:
            return SyncResult(
                success=False,
                error_message="No API key configured",
            )

        # Parse cursor as date or default to last 7 days
        since_date = None
        if instance.sync_cursor:
            since_date = instance.sync_cursor
        else:
            since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"[CLOSE] Starting incremental sync from {since_date}")

        return await self._sync_data(
            instance=instance,
            api_key=api_key,
            since_date=since_date,
            limit=100,
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform full historical sync.

        Fetches last 30 days of calls and notes.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        api_key = instance.config.get("api_key")
        if not api_key:
            return SyncResult(
                success=False,
                error_message="No API key configured",
            )

        # Fetch last 30 days
        since_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        logger.info(f"[CLOSE] Starting full sync from {since_date}")

        return await self._sync_data(
            instance=instance,
            api_key=api_key,
            since_date=since_date,
            limit=500,
        )

    async def _sync_data(
        self,
        instance: ConnectorInstance,
        api_key: str,
        since_date: str,
        limit: int,
    ) -> SyncResult:
        """
        Internal method to sync calls and notes.

        Args:
            instance: Connector instance
            api_key: Close CRM API key
            since_date: ISO date string to sync from
            limit: Max items per type

        Returns:
            SyncResult
        """
        result = SyncResult(success=True)
        transformer = CloseTransformer(extractor=KnowledgeExtractor())

        try:
            async with CloseCRMClient(api_key) as client:
                # Sync calls
                calls = await client.get_calls(since_date=since_date, limit=limit)
                result.items_fetched += len(calls)

                await self._process_calls(calls, transformer, result)

                # Sync notes
                notes = await client.get_notes(since_date=since_date, limit=limit)
                result.items_fetched += len(notes)

                await self._process_notes(notes, transformer, result)

                # Update cursor to current time
                result.cursor_after = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        except Exception as e:
            logger.exception(f"[CLOSE] Sync failed: {e}")
            result.success = False
            result.error_message = str(e)

        logger.info(
            f"[CLOSE] Sync complete: fetched={result.items_fetched}, "
            f"extracted={result.items_extracted}, created={result.items_created}, "
            f"skipped={result.items_skipped}, errors={len(result.errors)}"
        )

        return result

    async def _process_calls(
        self,
        calls: list[dict],
        transformer: CloseTransformer,
        result: SyncResult,
    ) -> None:
        """Process calls and extract knowledge."""
        from src.knowledge.service import KnowledgeIngestionService

        knowledge_service = KnowledgeIngestionService()

        for call in calls:
            try:
                # Transform to source
                source = transformer.call_to_source(call)

                # Check for duplicates
                if await self._is_duplicate(knowledge_service, source.content_hash):
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
                logger.exception(f"[CLOSE] Failed to process call {call.get('id')}: {e}")
                result.errors.append({
                    "call_id": call.get("id"),
                    "error": str(e),
                })

    async def _process_notes(
        self,
        notes: list[dict],
        transformer: CloseTransformer,
        result: SyncResult,
    ) -> None:
        """Process notes and extract knowledge."""
        from src.knowledge.service import KnowledgeIngestionService

        knowledge_service = KnowledgeIngestionService()

        for note in notes:
            try:
                # Transform to source
                source = transformer.note_to_source(note)

                # Check for duplicates
                if await self._is_duplicate(knowledge_service, source.content_hash):
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
                logger.exception(f"[CLOSE] Failed to process note {note.get('id')}: {e}")
                result.errors.append({
                    "note_id": note.get("id"),
                    "error": str(e),
                })

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
