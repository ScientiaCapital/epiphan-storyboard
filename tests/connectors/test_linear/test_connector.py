"""Integration tests for Linear connector."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.base import ConnectorInstance, ConnectorType, OAuthTokens
from src.connectors.linear.connector import LinearConnector
from src.connectors.linear.schemas import (
    LinearIssue,
    LinearProject,
    LinearState,
    LinearUser,
)


@pytest.fixture
def connector():
    """Create Linear connector."""
    return LinearConnector()


@pytest.fixture
def connector_instance():
    """Create connector instance with OAuth tokens."""
    return ConnectorInstance(
        id="instance-123",
        org_id="test-org",
        connector_type=ConnectorType.LINEAR,
        oauth_tokens=OAuthTokens(access_token="test-token-123"),
        config={
            "sync_issues": True,
            "sync_projects": True,
            "page_size": 50,
        },
    )


@pytest.mark.asyncio
async def test_test_connection_success(connector, connector_instance):
    """Test successful connection test."""
    mock_viewer = {"id": "user-123", "name": "Test User", "email": "test@example.com"}

    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.get_viewer = AsyncMock(return_value=mock_viewer)

        result = await connector.test_connection(connector_instance)

    assert result is True


@pytest.mark.asyncio
async def test_test_connection_failure(connector, connector_instance):
    """Test failed connection test."""
    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.get_viewer = AsyncMock(side_effect=Exception("Unauthorized"))

        result = await connector.test_connection(connector_instance)

    assert result is False


@pytest.mark.asyncio
async def test_test_connection_no_tokens(connector):
    """Test connection test without OAuth tokens."""
    instance = ConnectorInstance(
        id="instance-123",
        org_id="test-org",
        connector_type=ConnectorType.LINEAR,
        oauth_tokens=None,
    )

    result = await connector.test_connection(instance)

    assert result is False


@pytest.mark.asyncio
async def test_sync_issues_and_projects(connector, connector_instance):
    """Test syncing issues and projects."""
    # Mock issues
    mock_issues = [
        LinearIssue(
            id="issue-1",
            identifier="ENG-123",
            title="Fix bug",
            description="Bug description",
            state=LinearState(id="s1", name="Done", type="completed"),
            priority=2,
            labels=[],
            comments=[],
            creator=LinearUser(id="u1", name="Alice"),
            url="https://linear.app/issue-1",
            createdAt=datetime(2025, 12, 1, tzinfo=timezone.utc),
            updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
        )
    ]

    # Mock projects
    mock_projects = [
        LinearProject(
            id="proj-1",
            name="Q4 Sprint",
            description="Sprint goals",
            state="started",
            url="https://linear.app/proj-1",
            createdAt=datetime(2025, 11, 1, tzinfo=timezone.utc),
            updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
        )
    ]

    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient, \
         patch.object(connector.transformer, "transform_issue", new=AsyncMock(
             return_value=(MagicMock(), [MagicMock()])
         )), \
         patch.object(connector.transformer, "transform_project", new=AsyncMock(
             return_value=(MagicMock(), [MagicMock()])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=1, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.get_issues = AsyncMock(return_value=(mock_issues, "cursor-123"))
        mock_client.get_projects = AsyncMock(return_value=(mock_projects, None))

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 2  # 1 issue + 1 project
    assert result.items_extracted == 2
    assert result.items_created == 2
    assert "cursor-123" in result.cursor_after


@pytest.mark.asyncio
async def test_sync_with_cursor(connector, connector_instance):
    """Test incremental sync with cursor."""
    # Set existing cursor
    connector_instance.sync_cursor = "issues:prev-cursor|projects:proj-cursor"

    mock_issues = []
    mock_projects = []

    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.get_issues = AsyncMock(return_value=(mock_issues, None))
        mock_client.get_projects = AsyncMock(return_value=(mock_projects, None))

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 0
    assert result.cursor_after is None  # No more data

    # Verify cursors were passed
    mock_client.get_issues.assert_called_once()
    call_kwargs = mock_client.get_issues.call_args.kwargs
    assert call_kwargs["cursor"] == "prev-cursor"


@pytest.mark.asyncio
async def test_sync_issues_only(connector, connector_instance):
    """Test syncing only issues."""
    connector_instance.config["sync_issues"] = True
    connector_instance.config["sync_projects"] = False

    mock_issues = [
        LinearIssue(
            id="issue-1",
            identifier="ENG-123",
            title="Test",
            description=None,
            state=None,
            priority=0,
            labels=[],
            comments=[],
            url="https://linear.app/issue-1",
            createdAt=datetime(2025, 12, 1, tzinfo=timezone.utc),
            updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
        )
    ]

    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient, \
         patch.object(connector.transformer, "transform_issue", new=AsyncMock(
             return_value=(MagicMock(), [])
         )), \
         patch.object(connector.knowledge_service, "ingest_source", new=AsyncMock(
             return_value=MagicMock(items_created=0, items_skipped=0)
         )):

        mock_client = MockClient.return_value
        mock_client.get_issues = AsyncMock(return_value=(mock_issues, None))

        result = await connector.sync(connector_instance)

    assert result.success is True
    assert result.items_fetched == 1

    # Verify get_projects was not called
    mock_client.get_projects.assert_not_called()


@pytest.mark.asyncio
async def test_full_sync(connector, connector_instance):
    """Test full sync clears cursor."""
    connector_instance.sync_cursor = "issues:old-cursor"
    connector_instance.last_sync_at = datetime(2025, 12, 1, tzinfo=timezone.utc)

    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.get_issues = AsyncMock(return_value=([], None))
        mock_client.get_projects = AsyncMock(return_value=([], None))

        result = await connector.full_sync(connector_instance)

    assert result.success is True

    # Verify get_issues was called without updated_after
    call_kwargs = mock_client.get_issues.call_args.kwargs
    assert call_kwargs["updated_after"] is None


@pytest.mark.asyncio
async def test_sync_error_handling(connector, connector_instance):
    """Test sync error handling."""
    with patch("src.connectors.linear.connector.LinearGraphQLClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.get_issues = AsyncMock(side_effect=Exception("API error"))

        result = await connector.sync(connector_instance)

    assert result.success is False
    assert "API error" in result.error_message


def test_get_oauth_config(connector):
    """Test OAuth config retrieval."""
    import os

    # Set environment variables
    os.environ["LINEAR_CLIENT_ID"] = "test-client-id"
    os.environ["LINEAR_CLIENT_SECRET"] = "test-client-secret"

    config = connector.get_oauth_config()

    assert config is not None
    assert config.client_id == "test-client-id"
    assert config.client_secret == "test-client-secret"
    assert config.authorize_url == "https://linear.app/oauth/authorize"
    assert config.token_url == "https://api.linear.app/oauth/token"
    assert "read" in config.scopes

    # Cleanup
    del os.environ["LINEAR_CLIENT_ID"]
    del os.environ["LINEAR_CLIENT_SECRET"]


def test_connector_metadata(connector):
    """Test connector metadata."""
    assert connector.connector_type == ConnectorType.LINEAR
    assert connector.display_name == "Linear"
    assert connector.auth_type.value == "oauth2"
    assert connector.supports_webhook is True

    metadata = connector.to_dict()
    assert metadata["type"] == "linear"
    assert metadata["display_name"] == "Linear"
    assert metadata["supports_webhook"] is True
