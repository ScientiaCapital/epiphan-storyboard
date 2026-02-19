"""Tests for Notion transformer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.notion.schemas import (
    NotionBlock,
    NotionDatabase,
    NotionPage,
    NotionParent,
    NotionRichText,
)
from src.connectors.notion.transformer import NotionTransformer
from src.knowledge.base import KnowledgeEntry, KnowledgeType


@pytest.fixture
def transformer():
    """Create transformer instance."""
    return NotionTransformer()


@pytest.fixture
def sample_page():
    """Create sample Notion page."""
    return NotionPage(
        id="page-123",
        created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        parent=NotionParent(type="workspace"),
        properties={
            "title": {
                "type": "title",
                "title": [{"plain_text": "Product Roadmap Q4"}],
            }
        },
        url="https://notion.so/page-123",
    )


@pytest.fixture
def sample_blocks():
    """Create sample blocks."""
    return [
        NotionBlock(
            id="block-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            type="heading_1",
            heading_1={
                "rich_text": [
                    {"type": "text", "plain_text": "New Features"}
                ]
            },
        ),
        NotionBlock(
            id="block-2",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            type="paragraph",
            paragraph={
                "rich_text": [
                    {"type": "text", "plain_text": "AI-powered search across all documents"}
                ]
            },
        ),
        NotionBlock(
            id="block-3",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            type="bulleted_list_item",
            bulleted_list_item={
                "rich_text": [
                    {"type": "text", "plain_text": "Real-time collaboration"}
                ]
            },
        ),
    ]


@pytest.fixture
def sample_database():
    """Create sample Notion database."""
    return NotionDatabase(
        id="db-456",
        created_time=datetime(2025, 11, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        title=[
            NotionRichText(
                type="text",
                text={"content": "Customer Feedback"},
                plain_text="Customer Feedback",
            )
        ],
        description=[
            NotionRichText(
                type="text",
                text={"content": "Feedback from customer calls"},
                plain_text="Feedback from customer calls",
            )
        ],
        parent=NotionParent(type="workspace"),
        properties={},
        url="https://notion.so/db-456",
    )


@pytest.fixture
def sample_db_pages():
    """Create sample database pages."""
    return [
        NotionPage(
            id="page-1",
            created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="database_id", database_id="db-456"),
            properties={
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Need better search"}],
                },
                "Feedback": {
                    "type": "rich_text",
                    "rich_text": [
                        {"plain_text": "Current search is too slow and misses results"}
                    ],
                },
                "Priority": {
                    "type": "select",
                    "select": {"name": "High"},
                },
            },
            url="https://notion.so/page-1",
        ),
        NotionPage(
            id="page-2",
            created_time=datetime(2025, 12, 2, tzinfo=timezone.utc),
            last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
            parent=NotionParent(type="database_id", database_id="db-456"),
            properties={
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Export to PDF feature"}],
                },
                "Feedback": {
                    "type": "rich_text",
                    "rich_text": [{"plain_text": "Would love to export pages to PDF"}],
                },
            },
            url="https://notion.so/page-2",
        ),
    ]


@pytest.mark.asyncio
async def test_transform_page_roadmap(transformer, sample_page, sample_blocks):
    """Test transforming a roadmap page."""
    # Mock the extractor
    mock_entries = [
        KnowledgeEntry(
            knowledge_type=KnowledgeType.FEATURE,
            content="AI-powered search across all documents",
            confidence_score=0.9,
        ),
        KnowledgeEntry(
            knowledge_type=KnowledgeType.FEATURE,
            content="Real-time collaboration",
            confidence_score=0.9,
        ),
    ]

    with patch.object(
        transformer.extractor,
        "extract",
        new=AsyncMock(
            return_value=MagicMock(entries=mock_entries)
        ),
    ):
        source, entries = await transformer.transform_page(
            page=sample_page,
            blocks=sample_blocks,
            org_id="test-org",
        )

    # Verify source
    assert source.external_id == "page-123"
    assert source.external_url == "https://notion.so/page-123"
    assert "Product Roadmap Q4" in source.source_title

    # Verify content
    assert "Page: Product Roadmap Q4" in source.raw_content
    assert "# New Features" in source.raw_content
    assert "AI-powered search across all documents" in source.raw_content
    assert "- Real-time collaboration" in source.raw_content

    # Verify entries
    assert len(entries) == 2
    assert all(e.knowledge_type == KnowledgeType.FEATURE for e in entries)


@pytest.mark.asyncio
async def test_transform_database(transformer, sample_database, sample_db_pages):
    """Test transforming a database."""
    # Mock the extractor
    mock_entries = [
        KnowledgeEntry(
            knowledge_type=KnowledgeType.PAIN_POINT,
            content="Current search is too slow and misses results",
            confidence_score=0.9,
        ),
        KnowledgeEntry(
            knowledge_type=KnowledgeType.FEATURE,
            content="Export to PDF feature",
            confidence_score=0.85,
        ),
    ]

    with patch.object(
        transformer.extractor,
        "extract",
        new=AsyncMock(
            return_value=MagicMock(entries=mock_entries)
        ),
    ):
        source, entries = await transformer.transform_database(
            database=sample_database,
            pages=sample_db_pages,
            org_id="test-org",
        )

    # Verify source
    assert source.external_id == "db-456"
    assert source.external_url == "https://notion.so/db-456"
    assert "Customer Feedback" in source.source_title

    # Verify content
    assert "Database: Customer Feedback" in source.raw_content
    assert "Description: Feedback from customer calls" in source.raw_content
    assert "1. Need better search" in source.raw_content
    assert "2. Export to PDF feature" in source.raw_content
    assert "Feedback: Current search is too slow and misses results" in source.raw_content
    assert "Priority: High" in source.raw_content

    # Verify entries
    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT
    assert entries[1].knowledge_type == KnowledgeType.FEATURE


def test_page_to_text_formatting(transformer, sample_page, sample_blocks):
    """Test page to text conversion with various block types."""
    text = transformer._page_to_text(sample_page, sample_blocks)

    # Check basic structure
    assert "Page: Product Roadmap Q4" in text
    assert "Created: 2025-12-01" in text

    # Check heading formatting
    assert "\n# New Features" in text

    # Check paragraph
    assert "AI-powered search across all documents" in text

    # Check bulleted list
    assert "- Real-time collaboration" in text


def test_database_to_text_properties(transformer, sample_database, sample_db_pages):
    """Test database to text conversion with property values."""
    text = transformer._database_to_text(sample_database, sample_db_pages)

    # Check basic structure
    assert "Database: Customer Feedback" in text
    assert "Description: Feedback from customer calls" in text

    # Check pages listed
    assert "1. Need better search" in text
    assert "2. Export to PDF feature" in text

    # Check property values
    assert "Feedback: Current search is too slow and misses results" in text
    assert "Priority: High" in text


def test_block_get_text_content():
    """Test extracting text from different block types."""
    # Paragraph
    block = NotionBlock(
        id="b1",
        created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        type="paragraph",
        paragraph={"rich_text": [{"plain_text": "Test paragraph"}]},
    )
    assert block.get_text_content() == "Test paragraph"

    # To-do
    block = NotionBlock(
        id="b2",
        created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        type="to_do",
        to_do={"rich_text": [{"plain_text": "Complete task"}]},
    )
    assert block.get_text_content() == "Complete task"

    # Empty block
    block = NotionBlock(
        id="b3",
        created_time=datetime(2025, 12, 1, tzinfo=timezone.utc),
        last_edited_time=datetime(2025, 12, 9, tzinfo=timezone.utc),
        type="divider",
    )
    assert block.get_text_content() == ""
