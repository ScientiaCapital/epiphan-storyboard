"""Tests for LinearGraphQLClient."""

import pytest
import respx
from httpx import Response

from src.connectors.linear.client import LinearGraphQLClient
from src.connectors.linear.schemas import LinearIssue, LinearProject


@pytest.fixture
def linear_client():
    """Create Linear client with test token."""
    return LinearGraphQLClient(access_token="test-token-123")


@pytest.mark.asyncio
@respx.mock
async def test_get_viewer(linear_client):
    """Test getting authenticated user info."""
    mock_response = {
        "data": {
            "viewer": {
                "id": "user-123",
                "name": "Test User",
                "email": "test@example.com",
            }
        }
    }

    respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(200, json=mock_response)
    )

    viewer = await linear_client.get_viewer()

    assert viewer["id"] == "user-123"
    assert viewer["name"] == "Test User"
    assert viewer["email"] == "test@example.com"


@pytest.mark.asyncio
@respx.mock
async def test_get_issues_success(linear_client):
    """Test fetching issues with pagination."""
    mock_response = {
        "data": {
            "issues": {
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor-abc123",
                },
                "nodes": [
                    {
                        "id": "issue-1",
                        "identifier": "ENG-123",
                        "title": "Fix login bug",
                        "description": "Users can't log in with SSO",
                        "state": {"id": "state-1", "name": "In Progress", "type": "started"},
                        "priority": 3,
                        "labels": {"nodes": [{"id": "label-1", "name": "bug", "color": "#ff0000"}]},
                        "project": {
                            "id": "proj-1",
                            "name": "Q4 Sprint",
                            "description": None,
                            "state": "started",
                            "url": "https://linear.app/proj-1",
                            "createdAt": "2025-12-01T00:00:00Z",
                            "updatedAt": "2025-12-09T00:00:00Z",
                        },
                        "assignee": {"id": "user-1", "name": "Alice", "email": "alice@example.com"},
                        "creator": {"id": "user-2", "name": "Bob", "email": "bob@example.com"},
                        "url": "https://linear.app/issue-1",
                        "createdAt": "2025-12-01T00:00:00Z",
                        "updatedAt": "2025-12-09T00:00:00Z",
                        "comments": {
                            "nodes": [
                                {
                                    "id": "comment-1",
                                    "body": "I'll look into this",
                                    "user": {"id": "user-1", "name": "Alice"},
                                    "createdAt": "2025-12-02T00:00:00Z",
                                    "updatedAt": "2025-12-02T00:00:00Z",
                                }
                            ]
                        },
                    }
                ],
            }
        }
    }

    respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(200, json=mock_response)
    )

    issues, cursor = await linear_client.get_issues(limit=50)

    assert len(issues) == 1
    assert cursor == "cursor-abc123"

    issue = issues[0]
    assert isinstance(issue, LinearIssue)
    assert issue.identifier == "ENG-123"
    assert issue.title == "Fix login bug"
    assert issue.description == "Users can't log in with SSO"
    assert issue.priority == 3
    assert len(issue.labels) == 1
    assert issue.labels[0].name == "bug"
    assert len(issue.comments) == 1
    assert issue.comments[0].body == "I'll look into this"


@pytest.mark.asyncio
@respx.mock
async def test_get_issues_with_cursor(linear_client):
    """Test pagination with cursor."""
    mock_response = {
        "data": {
            "issues": {
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
                "nodes": [],
            }
        }
    }

    route = respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(200, json=mock_response)
    )

    issues, cursor = await linear_client.get_issues(cursor="prev-cursor", limit=50)

    assert len(issues) == 0
    assert cursor is None

    # Verify cursor was sent in request
    assert route.called
    request_json = route.calls[0].request.content
    assert b"prev-cursor" in request_json


@pytest.mark.asyncio
@respx.mock
async def test_get_projects(linear_client):
    """Test fetching projects."""
    mock_response = {
        "data": {
            "projects": {
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
                "nodes": [
                    {
                        "id": "proj-1",
                        "name": "Product Launch",
                        "description": "Launch new feature",
                        "state": "started",
                        "url": "https://linear.app/proj-1",
                        "createdAt": "2025-11-01T00:00:00Z",
                        "updatedAt": "2025-12-09T00:00:00Z",
                    }
                ],
            }
        }
    }

    respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(200, json=mock_response)
    )

    projects, cursor = await linear_client.get_projects()

    assert len(projects) == 1
    assert cursor is None

    project = projects[0]
    assert isinstance(project, LinearProject)
    assert project.name == "Product Launch"
    assert project.description == "Launch new feature"
    assert project.state == "started"


@pytest.mark.asyncio
@respx.mock
async def test_graphql_errors(linear_client):
    """Test handling of GraphQL errors."""
    mock_response = {
        "errors": [
            {"message": "Authentication required"},
            {"message": "Invalid query"},
        ]
    }

    respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(200, json=mock_response)
    )

    with pytest.raises(ValueError) as exc_info:
        await linear_client.get_viewer()

    assert "Authentication required" in str(exc_info.value)
    assert "Invalid query" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_http_errors(linear_client):
    """Test handling of HTTP errors."""
    respx.post("https://api.linear.app/graphql").mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )

    with pytest.raises(Exception):  # httpx.HTTPStatusError
        await linear_client.get_viewer()
