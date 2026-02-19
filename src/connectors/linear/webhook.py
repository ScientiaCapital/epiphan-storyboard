"""Linear webhook handler for real-time updates.

Docs: https://developers.linear.app/docs/graphql/webhooks
"""

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LinearWebhookHandler:
    """Handle Linear webhook events for real-time updates.

    Linear signs webhook payloads with HMAC-SHA256 using your webhook
    signing secret. The signature is in the "Linear-Signature" header.

    Events:
    - Issue: Issue created, updated, deleted
    - Comment: Comment created, updated, deleted
    - Project: Project created, updated, deleted
    """

    def __init__(self, signing_secret: str):
        """Initialize webhook handler.

        Args:
            signing_secret: Webhook signing secret from Linear settings
        """
        self.signing_secret = signing_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body bytes
            signature: Signature from "Linear-Signature" header

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            self.signing_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process webhook event and return result.

        Event structure:
        {
            "action": "create" | "update" | "remove",
            "type": "Issue" | "Comment" | "Project",
            "data": { ... entity data ... },
            "url": "https://linear.app/...",
            "createdAt": "2025-12-09T..."
        }

        Args:
            event: Webhook event data

        Returns:
            Result dict with "success" and optional "action" taken
        """
        event_type = event.get("type")
        action = event.get("action")
        data = event.get("data", {})

        logger.info(f"[LINEAR WEBHOOK] Received {action} {event_type}")

        if event_type == "Issue":
            return await self._handle_issue_event(action, data)
        elif event_type == "Comment":
            return await self._handle_comment_event(action, data)
        elif event_type == "Project":
            return await self._handle_project_event(action, data)
        else:
            logger.warning(f"[LINEAR WEBHOOK] Unknown event type: {event_type}")
            return {"success": False, "error": f"Unknown event type: {event_type}"}

    async def _handle_issue_event(
        self,
        action: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle issue webhook event.

        Args:
            action: "create", "update", or "remove"
            data: Issue data

        Returns:
            Result dict
        """
        issue_id = data.get("id")
        identifier = data.get("identifier")

        if action == "create":
            logger.info(f"[LINEAR WEBHOOK] New issue: {identifier}")
            # TODO: Trigger immediate sync of this issue
            return {"success": True, "action": "issue_created", "issue_id": issue_id}

        elif action == "update":
            logger.info(f"[LINEAR WEBHOOK] Updated issue: {identifier}")
            # TODO: Re-sync this specific issue
            return {"success": True, "action": "issue_updated", "issue_id": issue_id}

        elif action == "remove":
            logger.info(f"[LINEAR WEBHOOK] Deleted issue: {identifier}")
            # TODO: Soft-delete knowledge entries linked to this issue
            return {"success": True, "action": "issue_deleted", "issue_id": issue_id}

        return {"success": False, "error": f"Unknown action: {action}"}

    async def _handle_comment_event(
        self,
        action: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle comment webhook event.

        Args:
            action: "create", "update", or "remove"
            data: Comment data

        Returns:
            Result dict
        """
        comment_id = data.get("id")
        issue_id = data.get("issueId")

        if action == "create":
            logger.info(f"[LINEAR WEBHOOK] New comment on issue {issue_id}")
            # TODO: Re-extract knowledge from issue (may have new insights in comments)
            return {
                "success": True,
                "action": "comment_created",
                "comment_id": comment_id,
            }

        elif action == "update":
            logger.info(f"[LINEAR WEBHOOK] Updated comment {comment_id}")
            return {
                "success": True,
                "action": "comment_updated",
                "comment_id": comment_id,
            }

        elif action == "remove":
            logger.info(f"[LINEAR WEBHOOK] Deleted comment {comment_id}")
            return {
                "success": True,
                "action": "comment_deleted",
                "comment_id": comment_id,
            }

        return {"success": False, "error": f"Unknown action: {action}"}

    async def _handle_project_event(
        self,
        action: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle project webhook event.

        Args:
            action: "create", "update", or "remove"
            data: Project data

        Returns:
            Result dict
        """
        project_id = data.get("id")
        project_name = data.get("name")

        if action == "create":
            logger.info(f"[LINEAR WEBHOOK] New project: {project_name}")
            # TODO: Sync project and extract knowledge
            return {
                "success": True,
                "action": "project_created",
                "project_id": project_id,
            }

        elif action == "update":
            logger.info(f"[LINEAR WEBHOOK] Updated project: {project_name}")
            # TODO: Re-sync project
            return {
                "success": True,
                "action": "project_updated",
                "project_id": project_id,
            }

        elif action == "remove":
            logger.info(f"[LINEAR WEBHOOK] Deleted project: {project_name}")
            # TODO: Soft-delete knowledge entries linked to this project
            return {
                "success": True,
                "action": "project_deleted",
                "project_id": project_id,
            }

        return {"success": False, "error": f"Unknown action: {action}"}
