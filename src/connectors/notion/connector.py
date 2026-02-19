"""Notion connector implementation."""

import logging
from datetime import datetime, timezone

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorStatus,
    ConnectorType,
    OAuthConfig,
    SyncResult,
)
from src.connectors.notion.client import NotionAPIClient
from src.connectors.notion.transformer import NotionTransformer
from src.connectors.registry import connector
from src.knowledge.service import KnowledgeIngestionService

logger = logging.getLogger(__name__)


@connector
class NotionConnector(BaseConnector):
    """Notion connector for syncing pages, databases, and wiki content.

    Capabilities:
    - OAuth 2.0 authentication (public integrations)
    - Incremental sync via cursor pagination
    - Extracts: features, use_cases, pain_points, approved_terms from pages/databases

    Config fields:
    - sync_pages: bool (default True) - Sync pages
    - sync_databases: bool (default True) - Sync databases
    - sync_blocks: bool (default True) - Sync page content blocks
    - page_size: int (default 100) - Items per page
    - database_ids: list[str] (optional) - Specific databases to sync
    """

    connector_type = ConnectorType.NOTION
    display_name = "Notion"
    description = "Sync pages, databases, and wiki content from Notion"
    auth_type = AuthType.OAUTH2
    supports_webhook = False  # Notion doesn't support webhooks as of 2025

    def __init__(self):
        self.transformer = NotionTransformer()
        self.knowledge_service = KnowledgeIngestionService()

    def get_oauth_config(self) -> OAuthConfig | None:
        """Return OAuth config for Notion.

        Requires:
        - NOTION_CLIENT_ID environment variable
        - NOTION_CLIENT_SECRET environment variable
        """
        import os

        client_id = os.getenv("NOTION_CLIENT_ID", "")
        client_secret = os.getenv("NOTION_CLIENT_SECRET", "")
        redirect_uri = os.getenv("NOTION_REDIRECT_URI", "")

        if not client_id or not client_secret:
            logger.warning("NOTION_CLIENT_ID or NOTION_CLIENT_SECRET not configured")
            return None

        return OAuthConfig(
            authorize_url="https://api.notion.com/v1/oauth/authorize",
            token_url="https://api.notion.com/v1/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[],  # Notion doesn't use scopes in OAuth
            redirect_uri=redirect_uri if redirect_uri else None,
        )

    def get_required_config_fields(self) -> list[str]:
        """No required config fields - all are optional."""
        return []

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """Verify Notion API credentials are valid.

        Args:
            instance: Connector instance with OAuth tokens

        Returns:
            True if connection successful
        """
        if not instance.oauth_tokens:
            logger.error("[NOTION] No OAuth tokens configured")
            return False

        try:
            client = NotionAPIClient(instance.oauth_tokens.access_token)

            # Test connection by searching (empty query returns accessible content)
            results, _ = await client.search(query="", page_size=1)

            logger.info(f"[NOTION] Connected successfully (found {len(results)} items)")
            return True

        except Exception as e:
            logger.error(f"[NOTION] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform incremental sync from cursor.

        Syncs:
        1. Pages (if enabled)
        2. Databases and their rows (if enabled)
        3. Page blocks (content) if sync_blocks is enabled

        Args:
            instance: Connector instance with sync cursor

        Returns:
            SyncResult with items synced and new cursor
        """
        if not instance.oauth_tokens:
            return SyncResult(
                success=False,
                error_message="No OAuth tokens configured",
            )

        try:
            client = NotionAPIClient(instance.oauth_tokens.access_token)

            # Get config
            sync_pages = instance.config.get("sync_pages", True)
            sync_databases = instance.config.get("sync_databases", True)
            sync_blocks = instance.config.get("sync_blocks", True)
            page_size = instance.config.get("page_size", 100)
            database_ids = instance.config.get("database_ids", [])

            items_fetched = 0
            items_extracted = 0
            items_created = 0
            items_skipped = 0
            errors = []

            # Parse cursor (format: "pages:{cursor}|databases:{cursor}")
            pages_cursor = None
            databases_cursor = None

            if instance.sync_cursor:
                parts = instance.sync_cursor.split("|")
                for part in parts:
                    if part.startswith("pages:"):
                        pages_cursor = part.replace("pages:", "") or None
                    elif part.startswith("databases:"):
                        databases_cursor = part.replace("databases:", "") or None

            # Sync pages
            if sync_pages:
                logger.info(f"[NOTION] Syncing pages from cursor: {pages_cursor}")

                pages, next_pages_cursor = await client.search(
                    query="",
                    filter_type="page",
                    cursor=pages_cursor,
                    page_size=page_size,
                )

                items_fetched += len(pages)

                for page in pages:
                    try:
                        # Fetch page blocks if enabled
                        blocks = []
                        if sync_blocks:
                            blocks = await client.get_all_blocks(page.id)

                        source, entries = await self.transformer.transform_page(
                            page=page,
                            blocks=blocks,
                            org_id=instance.org_id,
                        )

                        items_extracted += len(entries)

                        # Store in knowledge base
                        result = await self.knowledge_service.ingest_source(
                            source=source,
                            entries=entries,
                            org_id=instance.org_id,
                        )

                        items_created += result.items_created
                        items_skipped += result.items_skipped

                    except Exception as e:
                        logger.error(f"[NOTION] Failed to process page {page.id}: {e}")
                        errors.append({"page_id": page.id, "error": str(e)})

                pages_cursor = next_pages_cursor

            # Sync databases
            if sync_databases:
                logger.info(f"[NOTION] Syncing databases from cursor: {databases_cursor}")

                # If specific database IDs are configured, sync those
                if database_ids:
                    for db_id in database_ids:
                        try:
                            database = await client.get_database(db_id)
                            items_fetched += 1

                            # Query all pages in database
                            all_db_pages = []
                            db_cursor = None
                            while True:
                                db_pages, db_cursor = await client.query_database(
                                    database_id=db_id,
                                    cursor=db_cursor,
                                    page_size=page_size,
                                )
                                all_db_pages.extend(db_pages)
                                if not db_cursor:
                                    break

                            source, entries = await self.transformer.transform_database(
                                database=database,
                                pages=all_db_pages,
                                org_id=instance.org_id,
                            )

                            items_extracted += len(entries)

                            # Store in knowledge base
                            result = await self.knowledge_service.ingest_source(
                                source=source,
                                entries=entries,
                                org_id=instance.org_id,
                            )

                            items_created += result.items_created
                            items_skipped += result.items_skipped

                        except Exception as e:
                            logger.error(f"[NOTION] Failed to process database {db_id}: {e}")
                            errors.append({"database_id": db_id, "error": str(e)})

                else:
                    # Discover databases via search
                    databases, next_databases_cursor = await client.search(
                        query="",
                        filter_type="database",
                        cursor=databases_cursor,
                        page_size=page_size,
                    )

                    items_fetched += len(databases)

                    for database in databases:
                        try:
                            # Query all pages in database
                            all_db_pages = []
                            db_cursor = None
                            while True:
                                db_pages, db_cursor = await client.query_database(
                                    database_id=database.id,
                                    cursor=db_cursor,
                                    page_size=page_size,
                                )
                                all_db_pages.extend(db_pages)
                                if not db_cursor:
                                    break

                            source, entries = await self.transformer.transform_database(
                                database=database,
                                pages=all_db_pages,
                                org_id=instance.org_id,
                            )

                            items_extracted += len(entries)

                            # Store in knowledge base
                            result = await self.knowledge_service.ingest_source(
                                source=source,
                                entries=entries,
                                org_id=instance.org_id,
                            )

                            items_created += result.items_created
                            items_skipped += result.items_skipped

                        except Exception as e:
                            logger.error(f"[NOTION] Failed to process database {database.id}: {e}")
                            errors.append({"database_id": database.id, "error": str(e)})

                    databases_cursor = next_databases_cursor

            # Build new cursor
            cursor_parts = []
            if pages_cursor:
                cursor_parts.append(f"pages:{pages_cursor}")
            if databases_cursor:
                cursor_parts.append(f"databases:{databases_cursor}")

            new_cursor = "|".join(cursor_parts) if cursor_parts else None

            logger.info(
                f"[NOTION] Sync complete: {items_fetched} fetched, "
                f"{items_extracted} extracted, {items_created} created, "
                f"{items_skipped} skipped"
            )

            return SyncResult(
                success=True,
                items_fetched=items_fetched,
                items_extracted=items_extracted,
                items_created=items_created,
                items_skipped=items_skipped,
                cursor_after=new_cursor,
                errors=errors,
            )

        except Exception as e:
            logger.exception(f"[NOTION] Sync failed: {e}")
            return SyncResult(
                success=False,
                error_message=str(e),
            )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform full historical sync.

        Same as incremental sync but starts from the beginning.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        # Clear cursor to start from beginning
        instance.sync_cursor = None

        result = await self.sync(instance)
        return result
