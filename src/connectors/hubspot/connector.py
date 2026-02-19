"""HubSpot CRM connector implementation."""

import logging
from datetime import UTC, datetime, timedelta

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorType,
    SyncResult,
)
from src.connectors.hubspot.client import HubSpotAPIClient
from src.connectors.hubspot.transformer import HubSpotTransformer
from src.connectors.registry import connector
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@connector
class HubSpotConnector(BaseConnector):
    """
    HubSpot CRM connector for syncing call transcripts from SalesMSG.

    Authentication: HubSpot Private App Token (stored as api_key)
    API: https://api.hubapi.com/crm/v3/objects/calls
    Pagination: Cursor-based (after param)

    Configuration:
        config["api_key"]: HubSpot Private App Token (required)

    Sync strategy:
        - Incremental: Uses sync_cursor (ISO timestamp) to fetch new calls since last sync
        - Full: Fetches last 30 days of calls

    Calls are only processed if they contain transcript text in hs_call_body
    (populated by the SalesMSG integration).

    Example:
        connector = HubSpotConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.HUBSPOT,
            config={"api_key": "pat-na1-..."}
        )
        result = await connector.sync(instance)
    """

    connector_type = ConnectorType.HUBSPOT
    display_name = "HubSpot"
    description = "Sync call transcripts from HubSpot CRM (SalesMSG)"
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
        Test connection by fetching 1 call to verify the token works.

        Args:
            instance: Connector instance with api_key in config

        Returns:
            True if connection successful
        """
        api_key = instance.config.get("api_key")
        if not api_key:
            logger.error("[HUBSPOT] No API key provided")
            return False

        try:
            async with HubSpotAPIClient(access_token=api_key) as client:
                await client.get_calls(limit=1)

            logger.info("[HUBSPOT] Connection test successful")
            return True

        except Exception as e:
            logger.exception(f"[HUBSPOT] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform incremental sync from cursor.

        Uses sync_cursor as ISO timestamp to fetch new calls since last sync.
        Defaults to 7 days if no cursor is set.

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

        # Parse cursor as ISO timestamp or default to last 7 days
        if instance.sync_cursor:
            from_date = instance.sync_cursor
        else:
            from_date = (datetime.now(UTC) - timedelta(days=7)).isoformat()

        to_date = datetime.now(UTC).isoformat()

        logger.info(f"[HUBSPOT] Starting incremental sync from {from_date}")

        return await self._sync_calls(
            instance=instance,
            api_key=api_key,
            from_date=from_date,
            to_date=to_date,
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform full historical sync (last 30 days).

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

        from_date = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        to_date = datetime.now(UTC).isoformat()

        logger.info(f"[HUBSPOT] Starting full sync from {from_date}")

        return await self._sync_calls(
            instance=instance,
            api_key=api_key,
            from_date=from_date,
            to_date=to_date,
        )

    async def _sync_calls(
        self,
        instance: ConnectorInstance,
        api_key: str,
        from_date: str,
        to_date: str,
    ) -> SyncResult:
        """
        Internal method to sync calls in a date range.

        Fetches calls via search_calls, skips any call without hs_call_body,
        and deduplicates via content_hash before saving.

        Args:
            instance: Connector instance
            api_key: HubSpot Private App Token
            from_date: ISO timestamp string for start of range
            to_date: ISO timestamp string for end of range

        Returns:
            SyncResult
        """
        result = SyncResult(success=True)
        transformer = HubSpotTransformer(extractor=KnowledgeExtractor())

        try:
            async with HubSpotAPIClient(access_token=api_key) as client:
                calls = await client.search_calls(
                    from_date=from_date,
                    to_date=to_date,
                )

            result.items_fetched = len(calls)
            logger.info(f"[HUBSPOT] Fetched {result.items_fetched} calls")

            from src.knowledge.service import KnowledgeIngestionService

            knowledge_service = KnowledgeIngestionService()

            for call in calls:
                try:
                    # Skip calls without transcript body
                    if not call.properties.hs_call_body:
                        logger.debug(
                            f"[HUBSPOT] Skipping call {call.id}: no hs_call_body"
                        )
                        result.items_skipped += 1
                        continue

                    # Transform to source
                    source = transformer.call_to_source(call)

                    # Dedup via content_hash
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
                    logger.exception(
                        f"[HUBSPOT] Failed to process call {call.id}: {e}"
                    )
                    result.errors.append(
                        {
                            "call_id": call.id,
                            "error": str(e),
                        }
                    )
                    continue

            # Update cursor to current time
            result.cursor_after = to_date

        except Exception as e:
            logger.exception(f"[HUBSPOT] Sync failed: {e}")
            result.success = False
            result.error_message = str(e)

        logger.info(
            f"[HUBSPOT] Sync complete: fetched={result.items_fetched}, "
            f"extracted={result.items_extracted}, created={result.items_created}, "
            f"skipped={result.items_skipped}, errors={len(result.errors)}"
        )

        return result

    async def _is_duplicate(self, knowledge_service, content_hash: str) -> bool:
        """Check if content has already been ingested."""
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
