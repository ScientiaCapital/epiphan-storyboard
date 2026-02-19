"""Linear connector implementation."""

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
from src.connectors.linear.client import LinearGraphQLClient
from src.connectors.linear.transformer import LinearTransformer
from src.connectors.registry import connector
from src.knowledge.service import KnowledgeIngestionService

logger = logging.getLogger(__name__)


@connector
class LinearConnector(BaseConnector):
    """Linear connector for syncing issues, comments, and projects.

    Capabilities:
    - OAuth 2.0 authentication
    - Incremental sync via cursor pagination
    - Real-time updates via webhooks
    - Extracts: features, pain points, use cases from issues and projects

    Config fields:
    - sync_issues: bool (default True) - Sync issues
    - sync_projects: bool (default True) - Sync projects
    - page_size: int (default 50) - Items per page
    """

    connector_type = ConnectorType.LINEAR
    display_name = "Linear"
    description = "Sync issues, comments, and projects from Linear"
    auth_type = AuthType.OAUTH2
    supports_webhook = True

    def __init__(self):
        self.transformer = LinearTransformer()
        self.knowledge_service = KnowledgeIngestionService()

    def get_oauth_config(self) -> OAuthConfig | None:
        """Return OAuth config for Linear.

        Requires:
        - LINEAR_CLIENT_ID environment variable
        - LINEAR_CLIENT_SECRET environment variable
        """
        import os

        client_id = os.getenv("LINEAR_CLIENT_ID", "")
        client_secret = os.getenv("LINEAR_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            logger.warning("LINEAR_CLIENT_ID or LINEAR_CLIENT_SECRET not configured")
            return None

        return OAuthConfig(
            authorize_url="https://linear.app/oauth/authorize",
            token_url="https://api.linear.app/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["read", "write"],  # read for data, write for webhooks
        )

    def get_required_config_fields(self) -> list[str]:
        """No required config fields - all are optional."""
        return []

    async def test_connection(self, instance: ConnectorInstance) -> bool:
        """Verify Linear API credentials are valid.

        Args:
            instance: Connector instance with OAuth tokens

        Returns:
            True if connection successful
        """
        if not instance.oauth_tokens:
            logger.error("[LINEAR] No OAuth tokens configured")
            return False

        try:
            client = LinearGraphQLClient(instance.oauth_tokens.access_token)
            viewer = await client.get_viewer()

            logger.info(f"[LINEAR] Connected as {viewer.get('name')} ({viewer.get('email')})")
            return True

        except Exception as e:
            logger.error(f"[LINEAR] Connection test failed: {e}")
            return False

    async def sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform incremental sync from cursor.

        Syncs:
        1. Issues updated since last sync
        2. Projects (if enabled in config)

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
            client = LinearGraphQLClient(instance.oauth_tokens.access_token)

            # Get config
            sync_issues = instance.config.get("sync_issues", True)
            sync_projects = instance.config.get("sync_projects", True)
            page_size = instance.config.get("page_size", 50)

            items_fetched = 0
            items_extracted = 0
            items_created = 0
            items_skipped = 0
            errors = []

            # Parse cursor (format: "issues:{cursor}|projects:{cursor}")
            issue_cursor = None
            project_cursor = None

            if instance.sync_cursor:
                parts = instance.sync_cursor.split("|")
                for part in parts:
                    if part.startswith("issues:"):
                        issue_cursor = part.replace("issues:", "") or None
                    elif part.startswith("projects:"):
                        project_cursor = part.replace("projects:", "") or None

            # Sync issues
            if sync_issues:
                logger.info(f"[LINEAR] Syncing issues from cursor: {issue_cursor}")

                # Only fetch issues updated since last sync
                updated_after = instance.last_sync_at

                issues, next_issue_cursor = await client.get_issues(
                    updated_after=updated_after,
                    cursor=issue_cursor,
                    limit=page_size,
                )

                items_fetched += len(issues)

                for issue in issues:
                    try:
                        source, entries = await self.transformer.transform_issue(
                            issue=issue,
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
                        logger.error(f"[LINEAR] Failed to process issue {issue.identifier}: {e}")
                        errors.append({"issue_id": issue.id, "error": str(e)})

                issue_cursor = next_issue_cursor

            # Sync projects
            if sync_projects:
                logger.info(f"[LINEAR] Syncing projects from cursor: {project_cursor}")

                projects, next_project_cursor = await client.get_projects(
                    cursor=project_cursor,
                    limit=page_size,
                )

                items_fetched += len(projects)

                for project in projects:
                    try:
                        source, entries = await self.transformer.transform_project(
                            project=project,
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
                        logger.error(f"[LINEAR] Failed to process project {project.name}: {e}")
                        errors.append({"project_id": project.id, "error": str(e)})

                project_cursor = next_project_cursor

            # Build new cursor
            cursor_parts = []
            if issue_cursor:
                cursor_parts.append(f"issues:{issue_cursor}")
            if project_cursor:
                cursor_parts.append(f"projects:{project_cursor}")

            new_cursor = "|".join(cursor_parts) if cursor_parts else None

            logger.info(
                f"[LINEAR] Sync complete: {items_fetched} fetched, "
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
            logger.exception(f"[LINEAR] Sync failed: {e}")
            return SyncResult(
                success=False,
                error_message=str(e),
            )

    async def full_sync(self, instance: ConnectorInstance) -> SyncResult:
        """Perform full historical sync.

        Same as incremental sync but without updated_after filter.

        Args:
            instance: Connector instance

        Returns:
            SyncResult with all items synced
        """
        # Save original last_sync_at
        original_last_sync = instance.last_sync_at

        # Clear last_sync_at to fetch all issues
        instance.last_sync_at = None
        instance.sync_cursor = None

        try:
            result = await self.sync(instance)
            return result

        finally:
            # Restore original last_sync_at
            instance.last_sync_at = original_last_sync
