"""Tests for NotionAPIClient."""

import pytest
import respx
from httpx import Response

from src.connectors.notion.client import NotionAPIClient
from src.connectors.notion.schemas import (
    NotionBlock,
    NotionDatabase,
    NotionPage,
)


@pytest.fixture
def notion_client():
    """Create Notion client with test token."""
    return NotionAPIClient(access_token="test-token-123")


@pytest.mark.asyncio
@respx.mock
async def test_search_pages(notion_client):
    """Test searching for pages."""
    mock_response = {
        "object": "list",
        "results": [
            {
                "object": "page",
                "id": "page-123",
                "created_time": "2025-12-01T00:00:00Z",
                "last_edited_time": "2025-12-09T00:00:00Z",
                "parent": {"type": "workspace"},
                "archived": False,
                "properties": {
                    "title": {
                        "type": "title",
                        "title": [{"plain_text": "Product Roadmap"}],
                    }
                },
                "url": "https://notion.so/page-123",
            }
        ],
        "next_cursor": "cursor-abc",
        "has_more": True,
    }

    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(200, json=mock_response)
    )

    results, cursor = await notion_client.search(query="roadmap", filter_type="page")

    assert len(results) == 1
    assert cursor == "cursor-abc"

    page = results[0]
    assert isinstance(page, NotionPage)
    assert page.id == "page-123"
    assert page.get_title() == "Product Roadmap"


@pytest.mark.asyncio
@respx.mock
async def test_search_databases(notion_client):
    """Test searching for databases."""
    mock_response = {
        "object": "list",
        "results": [
            {
                "object": "database",
                "id": "db-456",
                "created_time": "2025-11-01T00:00:00Z",
                "last_edited_time": "2025-12-09T00:00:00Z",
                "title": [{"type": "text", "plain_text": "Feature Requests"}],
                "description": [{"type": "text", "plain_text": "Customer feature requests"}],
                "parent": {"type": "workspace"},
                "properties": {},
                "url": "https://notion.so/db-456",
                "archived": False,
            }
        ],
        "next_cursor": None,
        "has_more": False,
    }

    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(200, json=mock_response)
    )

    results, cursor = await notion_client.search(filter_type="database")

    assert len(results) == 1
    assert cursor is None

    database = results[0]
    assert isinstance(database, NotionDatabase)
    assert database.id == "db-456"
    assert database.get_title() == "Feature Requests"
    assert database.get_description() == "Customer feature requests"


@pytest.mark.asyncio
@respx.mock
async def test_get_page(notion_client):
    """Test getting a page by ID."""
    mock_response = {
        "object": "page",
        "id": "page-123",
        "created_time": "2025-12-01T00:00:00Z",
        "last_edited_time": "2025-12-09T00:00:00Z",
        "parent": {"type": "database_id", "database_id": "db-456"},
        "archived": False,
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Test Page"}],
            }
        },
        "url": "https://notion.so/page-123",
    }

    respx.get("https://api.notion.com/v1/pages/page123").mock(
        return_value=Response(200, json=mock_response)
    )

    page = await notion_client.get_page("page-123")

    assert page.id == "page-123"
    assert page.get_title() == "Test Page"


@pytest.mark.asyncio
@respx.mock
async def test_get_blocks(notion_client):
    """Test getting blocks from a page."""
    mock_response = {
        "object": "list",
        "results": [
            {
                "object": "block",
                "id": "block-1",
                "parent": {"type": "page_id", "page_id": "page-123"},
                "created_time": "2025-12-01T00:00:00Z",
                "last_edited_time": "2025-12-09T00:00:00Z",
                "has_children": False,
                "archived": False,
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "plain_text": "This is a paragraph"}
                    ]
                },
            },
            {
                "object": "block",
                "id": "block-2",
                "parent": {"type": "page_id", "page_id": "page-123"},
                "created_time": "2025-12-01T00:00:00Z",
                "last_edited_time": "2025-12-09T00:00:00Z",
                "has_children": False,
                "archived": False,
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {"type": "text", "plain_text": "Important Heading"}
                    ]
                },
            },
        ],
        "next_cursor": None,
        "has_more": False,
    }

    respx.get("https://api.notion.com/v1/blocks/page123/children").mock(
        return_value=Response(200, json=mock_response)
    )

    blocks, cursor = await notion_client.get_blocks("page-123")

    assert len(blocks) == 2
    assert cursor is None

    block1 = blocks[0]
    assert isinstance(block1, NotionBlock)
    assert block1.type == "paragraph"
    assert block1.get_text_content() == "This is a paragraph"

    block2 = blocks[1]
    assert block2.type == "heading_1"
    assert block2.get_text_content() == "Important Heading"


@pytest.mark.asyncio
@respx.mock
async def test_query_database(notion_client):
    """Test querying database pages."""
    mock_response = {
        "object": "list",
        "results": [
            {
                "object": "page",
                "id": "page-1",
                "created_time": "2025-12-01T00:00:00Z",
                "last_edited_time": "2025-12-09T00:00:00Z",
                "parent": {"type": "database_id", "database_id": "db-456"},
                "archived": False,
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Row 1"}],
                    },
                    "Status": {
                        "type": "select",
                        "select": {"name": "Done"},
                    },
                },
                "url": "https://notion.so/page-1",
            }
        ],
        "next_cursor": None,
        "has_more": False,
    }

    respx.post("https://api.notion.com/v1/databases/db456/query").mock(
        return_value=Response(200, json=mock_response)
    )

    pages, cursor = await notion_client.query_database("db-456")

    assert len(pages) == 1
    assert cursor is None

    page = pages[0]
    assert isinstance(page, NotionPage)
    assert page.get_title() == "Row 1"


@pytest.mark.asyncio
@respx.mock
async def test_normalize_id(notion_client):
    """Test ID normalization."""
    # Test with hyphens
    normalized = notion_client._normalize_id("12345678-1234-1234-1234-123456789abc")
    assert normalized == "12345678123412341234123456789abc"

    # Test without hyphens
    normalized = notion_client._normalize_id("12345678123412341234123456789abc")
    assert normalized == "12345678123412341234123456789abc"


@pytest.mark.asyncio
@respx.mock
async def test_http_error(notion_client):
    """Test handling of HTTP errors."""
    respx.post("https://api.notion.com/v1/search").mock(
        return_value=Response(401, json={"message": "Unauthorized"})
    )

    with pytest.raises(Exception):  # httpx.HTTPStatusError
        await notion_client.search()
