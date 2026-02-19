"""Google Docs connector implementation."""

import logging
import os
from datetime import UTC, datetime

from src.connectors.base import (
    AuthType,
    BaseConnector,
    ConnectorInstance,
    ConnectorType,
    OAuthConfig,
    SyncResult,
)
from src.connectors.google_docs.client import GoogleDocsAPIClient
from src.connectors.google_docs.transformer import GoogleDocsTransformer
from src.connectors.registry import connector
from src.knowledge.service import KnowledgeIngestionService

logger = logging.getLogger(__name__)


@connector
class GoogleDocsConnector(BaseConnector):
    """Google Docs connector for syncing documents and content.

    Capabilities:
    - OAuth 2.0 authentication
    - Incremental sync via modifiedTime cursor
    - Extracts: features, use_cases, approved_terms, documentation, pain_points

    Config fields:
    - page_size: int (default 100) - Documents per page
    - sync_shared_with_me: bool (default False) - Include shared docs
    """

    connector_type = ConnectorType.GOOGLE_DOCS
    display_name = "Google Docs"
    description = "Sync documents and content from Google Docs"
    auth_type = AuthType.OAUTH2
    supports_webhook = False  # Google Docs doesn't support webhooks directly

    def __init__(self):
        self.transformer = GoogleDocsTransformer()
        self.knowledge_service = KnowledgeIngestionService()

    def get_oauth_config(self) -> OAuthConfig | None:
        """Return OAuth config for Google Docs.

        Requires:
        - GOOGLE_CLIENT_ID environment variable
        - GOOGLE_CLIENT_SECRET environment variable
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")

        if not client_id or not client_secret:
            logger.warning("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured")
            return None

        return OAuthConfig(
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                "https://www.googleapis.com/auth/documents.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
            redirect_uri=redirect_uri if redirect_uri else None,
        )

    def get_required_config_fields(self) -> list[str]:
        """No required config fields - all are optional."""
        return []

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """Verify Google Docs API credentials are valid.

        Args:
            instance: Connector instance with OAuth tokens

        Returns:
            True if connection successful
        """
        if not instance.oauth_tokens:
            logger.error("[GOOGLE_DOCS] No OAuth tokens configured")
            return False

        try:
            client = GoogleDocsAPIClient(instance.oauth_tokens.access_token)

            # Test connection by listing documents (limit 1)
            files, _ = await client.list_documents(page_size=1)

            logger.info(
                f"[GOOGLE_DOCS] Connected successfully (found {len(files)} documents)"
            )
            return True

        except Exception as e:
            logger.error(f"[GOOGLE_DOCS] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform incremental sync from cursor.

        Syncs:
        1. List documents modified since cursor (modifiedTime)
        2. Fetch full document content
        3. Extract plain text
        4. Transform to knowledge entries via LLM

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
            client = GoogleDocsAPIClient(instance.oauth_tokens.access_token)

            # Get config
            page_size = instance.config.get("page_size", 100)

            items_fetched = 0
            items_extracted = 0
            items_created = 0
            items_skipped = 0
            errors = []

            # Parse cursor (format: "modified_after:{timestamp}|page_token:{token}")
            modified_after = None
            page_token = None

            if instance.sync_cursor:
                parts = instance.sync_cursor.split("|")
                for part in parts:
                    if part.startswith("modified_after:"):
                        modified_after = part.replace("modified_after:", "") or None
                    elif part.startswith("page_token:"):
                        page_token = part.replace("page_token:", "") or None

            # If no cursor, default to documents from last 7 days
            if not modified_after:
                from datetime import timedelta

                cutoff = datetime.now(UTC) - timedelta(days=7)
                modified_after = cutoff.isoformat()

            logger.info(
                f"[GOOGLE_DOCS] Syncing documents modified after {modified_after} "
                f"(page_token: {page_token})"
            )

            # List documents
            files, next_page_token = await client.list_documents(
                page_token=page_token,
                page_size=page_size,
                modified_after=modified_after,
            )

            items_fetched += len(files)

            # Process each document
            for drive_file in files:
                try:
                    # Fetch full document content
                    document = await client.get_document(drive_file.id)

                    # Extract plain text
                    plain_text = client.extract_text_from_body(
                        document.body.model_dump()
                    )

                    if not plain_text.strip():
                        logger.warning(
                            f"[GOOGLE_DOCS] Document {drive_file.id} has no text content, skipping"
                        )
                        items_skipped += 1
                        continue

                    # Transform to knowledge entries
                    source, entries = await self.transformer.transform_document(
                        document=document,
                        drive_file=drive_file,
                        plain_text=plain_text,
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
                    logger.error(
                        f"[GOOGLE_DOCS] Failed to process document {drive_file.id}: {e}"
                    )
                    errors.append({"document_id": drive_file.id, "error": str(e)})

            # Build new cursor
            cursor_parts = []
            if modified_after:
                cursor_parts.append(f"modified_after:{modified_after}")
            if next_page_token:
                cursor_parts.append(f"page_token:{next_page_token}")

            new_cursor = "|".join(cursor_parts) if cursor_parts else None

            # If we finished this page, update modified_after to now for next sync
            if not next_page_token and modified_after:
                now = datetime.now(UTC).isoformat()
                new_cursor = f"modified_after:{now}"

            logger.info(
                f"[GOOGLE_DOCS] Sync complete: {items_fetched} fetched, "
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
            logger.exception(f"[GOOGLE_DOCS] Sync failed: {e}")
            return SyncResult(
                success=False,
                error_message=str(e),
            )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform full historical sync.

        Syncs all documents (no modified_after filter).

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        # Clear cursor to start from beginning (no time filter)
        instance.sync_cursor = None

        # Full sync gets ALL documents (no modified_after filter)
        if not instance.oauth_tokens:
            return SyncResult(
                success=False,
                error_message="No OAuth tokens configured",
            )

        try:
            client = GoogleDocsAPIClient(instance.oauth_tokens.access_token)

            # Get config
            page_size = instance.config.get("page_size", 100)

            items_fetched = 0
            items_extracted = 0
            items_created = 0
            items_skipped = 0
            errors = []

            logger.info("[GOOGLE_DOCS] Starting full sync (all documents)")

            # Paginate through ALL documents
            page_token = None
            while True:
                files, next_page_token = await client.list_documents(
                    page_token=page_token,
                    page_size=page_size,
                    modified_after=None,  # No time filter for full sync
                )

                items_fetched += len(files)

                # Process each document
                for drive_file in files:
                    try:
                        # Fetch full document content
                        document = await client.get_document(drive_file.id)

                        # Extract plain text
                        plain_text = client.extract_text_from_body(
                            document.body.model_dump()
                        )

                        if not plain_text.strip():
                            logger.warning(
                                f"[GOOGLE_DOCS] Document {drive_file.id} has no text content, skipping"
                            )
                            items_skipped += 1
                            continue

                        # Transform to knowledge entries
                        source, entries = await self.transformer.transform_document(
                            document=document,
                            drive_file=drive_file,
                            plain_text=plain_text,
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
                        logger.error(
                            f"[GOOGLE_DOCS] Failed to process document {drive_file.id}: {e}"
                        )
                        errors.append({"document_id": drive_file.id, "error": str(e)})

                # Check for next page
                if not next_page_token:
                    break
                page_token = next_page_token

            # Set cursor to current time for future incremental syncs
            now = datetime.now(UTC).isoformat()
            new_cursor = f"modified_after:{now}"

            logger.info(
                f"[GOOGLE_DOCS] Full sync complete: {items_fetched} fetched, "
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
            logger.exception(f"[GOOGLE_DOCS] Full sync failed: {e}")
            return SyncResult(
                success=False,
                error_message=str(e),
            )
