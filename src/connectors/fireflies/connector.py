"""Fireflies connector implementation."""

import logging

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    SyncResult,
)
from src.connectors.fireflies.client import FirefliesGraphQLClient
from src.connectors.fireflies.transformer import FirefliesTransformer
from src.connectors.registry import connector
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@connector
class FirefliesConnector(BaseConnector):
    """
    Fireflies.ai connector for syncing meeting transcripts and action items.

    Authentication: API Key (Bearer token)
    API: GraphQL (https://api.fireflies.ai/graphql)
    Pagination: Offset-based (limit + skip)

    Configuration:
        config["api_key"]: Fireflies API key (required)

    Sync strategy:
        - Incremental: Uses sync_cursor (integer offset) to fetch new transcripts
        - Full: Fetches all available transcripts (paginated)

    Example:
        connector = FirefliesConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.FIREFLIES,
            config={"api_key": "your-api-key"}
        )
        result = await connector.sync(instance)
    """

    connector_type = ConnectorType.FIREFLIES
    display_name = "Fireflies.ai"
    description = "Sync meeting transcripts and action items from Fireflies"
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
        Test connection by fetching 1 transcript.

        Args:
            instance: Connector instance with API key

        Returns:
            True if connection successful
        """
        api_key = instance.config.get("api_key")
        if not api_key:
            logger.error("[FIREFLIES] No API key provided")
            return False

        try:
            async with FirefliesGraphQLClient(api_key) as client:
                response = await client.get_transcripts(limit=1)

            logger.info(f"[FIREFLIES] Connection test successful: found {len(response.transcripts)} transcripts")
            return True

        except Exception as e:
            logger.exception(f"[FIREFLIES] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform incremental sync from cursor.

        Uses sync_cursor as integer offset for pagination.

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

        # Parse cursor as offset
        offset = 0
        if instance.sync_cursor:
            try:
                offset = int(instance.sync_cursor)
            except ValueError:
                logger.warning(f"[FIREFLIES] Invalid sync cursor: {instance.sync_cursor}, starting from 0")
                offset = 0

        logger.info(f"[FIREFLIES] Starting incremental sync from offset {offset}")

        return await self._sync_transcripts(
            instance=instance,
            api_key=api_key,
            skip=offset,
            limit=50,
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform full historical sync.

        Fetches all available transcripts with pagination.

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

        logger.info("[FIREFLIES] Starting full sync")

        return await self._sync_transcripts(
            instance=instance,
            api_key=api_key,
            skip=0,
            limit=50,
            full_sync=True,
        )

    async def _sync_transcripts(
        self,
        instance: ConnectorInstance,
        api_key: str,
        skip: int,
        limit: int,
        full_sync: bool = False,
    ) -> SyncResult:
        """
        Internal method to sync transcripts.

        Args:
            instance: Connector instance
            api_key: Fireflies API key
            skip: Offset for pagination
            limit: Number of transcripts per page
            full_sync: Whether to paginate through all transcripts

        Returns:
            SyncResult
        """
        result = SyncResult(success=True)
        transformer = FirefliesTransformer(extractor=KnowledgeExtractor())

        try:
            async with FirefliesGraphQLClient(api_key) as client:
                current_skip = skip
                has_more = True

                while has_more:
                    response = await client.get_transcripts(limit=limit, skip=current_skip)

                    if not response.transcripts:
                        has_more = False
                        break

                    result.items_fetched += len(response.transcripts)

                    # Process each transcript
                    from src.knowledge.service import KnowledgeIngestionService

                    knowledge_service = KnowledgeIngestionService()

                    for transcript in response.transcripts:
                        try:
                            # Transform to source
                            source = transformer.transcript_to_source(transcript)

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
                            logger.exception(f"[FIREFLIES] Failed to process transcript {transcript.id}: {e}")
                            result.errors.append({
                                "transcript_id": transcript.id,
                                "error": str(e),
                            })
                            continue

                    # Update for next iteration
                    current_skip += len(response.transcripts)

                    # For incremental sync, only fetch one batch
                    if not full_sync:
                        has_more = False

                # Update cursor to new offset
                result.cursor_after = str(current_skip)

        except Exception as e:
            logger.exception(f"[FIREFLIES] Sync failed: {e}")
            result.success = False
            result.error_message = str(e)

        logger.info(
            f"[FIREFLIES] Sync complete: fetched={result.items_fetched}, "
            f"extracted={result.items_extracted}, created={result.items_created}, "
            f"skipped={result.items_skipped}, errors={len(result.errors)}"
        )

        return result
