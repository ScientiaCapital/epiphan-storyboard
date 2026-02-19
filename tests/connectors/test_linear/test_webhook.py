"""Tests for Linear webhook handler."""

import hashlib
import hmac
import json

import pytest

from src.connectors.linear.webhook import LinearWebhookHandler


@pytest.fixture
def webhook_handler():
    """Create webhook handler with test secret."""
    return LinearWebhookHandler(signing_secret="test-secret-123")


def test_verify_signature_valid(webhook_handler):
    """Test signature verification with valid signature."""
    payload = b'{"type": "Issue", "action": "create"}'

    # Generate valid signature
    signature = hmac.new(
        b"test-secret-123",
        payload,
        hashlib.sha256,
    ).hexdigest()

    assert webhook_handler.verify_signature(payload, signature) is True


def test_verify_signature_invalid(webhook_handler):
    """Test signature verification with invalid signature."""
    payload = b'{"type": "Issue", "action": "create"}'
    invalid_signature = "wrong-signature-12345"

    assert webhook_handler.verify_signature(payload, invalid_signature) is False


def test_verify_signature_tampered_payload(webhook_handler):
    """Test signature verification with tampered payload."""
    original_payload = b'{"type": "Issue", "action": "create"}'
    tampered_payload = b'{"type": "Issue", "action": "delete"}'

    # Signature is for original payload
    signature = hmac.new(
        b"test-secret-123",
        original_payload,
        hashlib.sha256,
    ).hexdigest()

    # Should fail with tampered payload
    assert webhook_handler.verify_signature(tampered_payload, signature) is False


@pytest.mark.asyncio
async def test_handle_issue_create_event(webhook_handler):
    """Test handling issue create event."""
    event = {
        "type": "Issue",
        "action": "create",
        "data": {
            "id": "issue-123",
            "identifier": "ENG-456",
            "title": "New bug report",
        },
        "url": "https://linear.app/issue-123",
        "createdAt": "2025-12-09T12:00:00Z",
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is True
    assert result["action"] == "issue_created"
    assert result["issue_id"] == "issue-123"


@pytest.mark.asyncio
async def test_handle_issue_update_event(webhook_handler):
    """Test handling issue update event."""
    event = {
        "type": "Issue",
        "action": "update",
        "data": {
            "id": "issue-123",
            "identifier": "ENG-456",
            "title": "Updated bug report",
        },
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is True
    assert result["action"] == "issue_updated"
    assert result["issue_id"] == "issue-123"


@pytest.mark.asyncio
async def test_handle_issue_delete_event(webhook_handler):
    """Test handling issue delete event."""
    event = {
        "type": "Issue",
        "action": "remove",
        "data": {
            "id": "issue-123",
            "identifier": "ENG-456",
        },
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is True
    assert result["action"] == "issue_deleted"
    assert result["issue_id"] == "issue-123"


@pytest.mark.asyncio
async def test_handle_comment_create_event(webhook_handler):
    """Test handling comment create event."""
    event = {
        "type": "Comment",
        "action": "create",
        "data": {
            "id": "comment-789",
            "issueId": "issue-123",
            "body": "This is a comment",
        },
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is True
    assert result["action"] == "comment_created"
    assert result["comment_id"] == "comment-789"


@pytest.mark.asyncio
async def test_handle_project_create_event(webhook_handler):
    """Test handling project create event."""
    event = {
        "type": "Project",
        "action": "create",
        "data": {
            "id": "project-456",
            "name": "Q1 Roadmap",
        },
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is True
    assert result["action"] == "project_created"
    assert result["project_id"] == "project-456"


@pytest.mark.asyncio
async def test_handle_unknown_event_type(webhook_handler):
    """Test handling unknown event type."""
    event = {
        "type": "UnknownType",
        "action": "create",
        "data": {},
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is False
    assert "Unknown event type" in result["error"]


@pytest.mark.asyncio
async def test_handle_unknown_action(webhook_handler):
    """Test handling unknown action."""
    event = {
        "type": "Issue",
        "action": "unknown_action",
        "data": {
            "id": "issue-123",
        },
    }

    result = await webhook_handler.handle_event(event)

    assert result["success"] is False
    assert "Unknown action" in result["error"]
