"""Gong connector implementation."""

import logging
from datetime import datetime, timedelta, timezone

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    OAuthConfig,
    SyncResult,
)
from src.connectors.gong.client import GongAPIClient
from src.connectors.gong.schemas import GongCall
from src.connectors.gong.transformer import GongTransformer
from src.connectors.registry import connector
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


@connector
class GongConnector(BaseConnector):
    """
    Gong connector for syncing call transcripts and AI insights.

    Authentication: OAuth2 Bearer token
    API: https://api.gong.io/v2/
    Pagination: Cursor-based
    Rate limits: Handled via Retry-After headers

    Configuration:
        oauth_tokens.access_token: OAuth2 bearer token (required)

    Sync strategy:
        - Incremental: Uses sync_cursor (timestamp) to fetch new calls
        - Full: Fetches last 30 days of calls

    Example:
        connector = GongConnector()
        instance = ConnectorInstance.create_new(
            org_id="my-org",
            connector_type=ConnectorType.GONG,
            oauth_tokens=OAuthTokens(access_token="...")
        )
        result = await connector.sync(instance)
    """

    connector_type = ConnectorType.GONG
    display_name = "Gong"
    description = "Sync call transcripts and AI insights from Gong"
    auth_type = AuthType.OAUTH2
    supports_webhook = False

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """
        Test connection by fetching recent calls.

        Args:
            instance: Connector instance with OAuth tokens

        Returns:
            True if connection successful
        """
        if not instance.oauth_tokens or not instance.oauth_tokens.access_token:
            logger.error("[GONG] No OAuth access token provided")
            return False

        try:
            # Test by fetching calls from last 24 hours
            from_date = datetime.now(timezone.utc) - timedelta(days=1)

            async with GongAPIClient(instance.oauth_tokens.access_token) as client:
                response = await client.get_calls(from_date=from_date)

            logger.info(f"[GONG] Connection test successful: found {len(response.calls)} recent calls")
            return True

        except Exception as e:
            logger.exception(f"[GONG] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform incremental sync from cursor.

        Uses sync_cursor as ISO timestamp to fetch new calls since last sync.

        Args:
            instance: Connector instance with sync cursor

        Returns:
            SyncResult with items synced and new cursor
        """
        if not instance.oauth_tokens or not instance.oauth_tokens.access_token:
            return SyncResult(
                success=False,
                error_message="No OAuth access token configured",
            )

        # Parse cursor as timestamp
        if instance.sync_cursor:
            try:
                from_date = datetime.fromisoformat(instance.sync_cursor)
            except ValueError:
                logger.warning(f"[GONG] Invalid sync cursor: {instance.sync_cursor}, falling back to 7 days")
                from_date = datetime.now(timezone.utc) - timedelta(days=7)
        else:
            # First sync - get last 7 days
            from_date = datetime.now(timezone.utc) - timedelta(days=7)

        logger.info(f"[GONG] Starting incremental sync from {from_date.isoformat()}")

        return await self._sync_calls(
            instance=instance,
            from_date=from_date,
            to_date=datetime.now(timezone.utc),
        )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """
        Perform full historical sync (last 30 days).

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        if not instance.oauth_tokens or not instance.oauth_tokens.access_token:
            return SyncResult(
                success=False,
                error_message="No OAuth access token configured",
            )

        from_date = datetime.now(timezone.utc) - timedelta(days=30)
        logger.info(f"[GONG] Starting full sync from {from_date.isoformat()}")

        return await self._sync_calls(
            instance=instance,
            from_date=from_date,
            to_date=datetime.now(timezone.utc),
        )

    async def _sync_calls(
        self,
        instance: ConnectorInstance,
        from_date: datetime,
        to_date: datetime,
    ) -> SyncResult:
        """
        Internal method to sync calls in date range.

        Args:
            instance: Connector instance
            from_date: Start date
            to_date: End date

        Returns:
            SyncResult
        """
        result = SyncResult(success=True)
        transformer = GongTransformer(extractor=KnowledgeExtractor())

        try:
            async with GongAPIClient(instance.oauth_tokens.access_token) as client:
                # Paginate through all calls
                cursor = None
                all_call_ids = []

                while True:
                    response = await client.get_calls(
                        from_date=from_date,
                        to_date=to_date,
                        cursor=cursor,
                    )

                    # Extract call IDs from raw data
                    for call_data in response.calls:
                        metadata = call_data.get("metaData", {})
                        call_id = metadata.get("id")
                        if call_id:
                            all_call_ids.append((call_id, call_data))

                    result.items_fetched += len(response.calls)

                    # Check for more pages
                    if not response.cursor:
                        break
                    cursor = response.cursor

                logger.info(f"[GONG] Fetched {result.items_fetched} calls")

                # Fetch transcripts in batches
                call_ids = [cid for cid, _ in all_call_ids]
                transcripts = await client.get_transcripts(call_ids)

                # Build transcript map
                transcript_map = {t.call_id: t for t in transcripts}

                # Process each call
                from src.knowledge.service import KnowledgeIngestionService

                knowledge_service = KnowledgeIngestionService()

                for call_id, call_data in all_call_ids:
                    try:
                        # Parse call
                        call = GongCall.from_api_response(call_data)

                        # Get transcript
                        transcript = transcript_map.get(call_id)
                        if not transcript:
                            logger.warning(f"[GONG] No transcript for call {call_id}, skipping")
                            result.items_skipped += 1
                            continue

                        # Transform to source
                        source = transformer.call_to_source(call=call, transcript=transcript)

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
                        logger.exception(f"[GONG] Failed to process call {call_id}: {e}")
                        result.errors.append({
                            "call_id": call_id,
                            "error": str(e),
                        })
                        continue

                # Update cursor to current time
                result.cursor_after = to_date.isoformat()

        except Exception as e:
            logger.exception(f"[GONG] Sync failed: {e}")
            result.success = False
            result.error_message = str(e)

        logger.info(
            f"[GONG] Sync complete: fetched={result.items_fetched}, "
            f"extracted={result.items_extracted}, created={result.items_created}, "
            f"skipped={result.items_skipped}, errors={len(result.errors)}"
        )

        return result

    def get_oauth_config(self) -> OAuthConfig | None:
        """
        Return Gong OAuth configuration.

        Note: Gong OAuth requires company-specific setup.
        See: https://app.gong.io/settings/api/documentation

        Returns:
            OAuthConfig for Gong
        """
        import os

        # These would typically come from environment or config
        return OAuthConfig(
            authorize_url="https://app.gong.io/oauth2/authorize",
            token_url="https://app.gong.io/oauth2/generate-customer-token",
            client_id=os.getenv("GONG_CLIENT_ID", ""),
            client_secret=os.getenv("GONG_CLIENT_SECRET", ""),
            scopes=["api:calls:read:transcript"],
        )
