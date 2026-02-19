"""Tests for Linear transformer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.linear.schemas import (
    LinearComment,
    LinearIssue,
    LinearLabel,
    LinearProject,
    LinearState,
    LinearUser,
)
from src.connectors.linear.transformer import LinearTransformer
from src.knowledge.base import KnowledgeEntry, KnowledgeType


@pytest.fixture
def transformer():
    """Create transformer instance."""
    return LinearTransformer()


@pytest.fixture
def sample_issue():
    """Create sample Linear issue."""
    return LinearIssue(
        id="issue-123",
        identifier="ENG-456",
        title="Fix authentication bug",
        description="Users unable to login via SSO",
        state=LinearState(id="state-1", name="In Progress", type="started"),
        priority=3,
        labels=[
            LinearLabel(id="label-1", name="bug", color="#ff0000"),
            LinearLabel(id="label-2", name="security", color="#00ff00"),
        ],
        project=LinearProject(
            id="proj-1",
            name="Security Sprint",
            description="Q4 security improvements",
            state="started",
            url="https://linear.app/proj-1",
            createdAt=datetime(2025, 11, 1, tzinfo=timezone.utc),
            updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
        ),
        creator=LinearUser(id="user-1", name="Alice"),
        assignee=LinearUser(id="user-2", name="Bob"),
        comments=[
            LinearComment(
                id="comment-1",
                body="This is blocking production",
                user=LinearUser(id="user-1", name="Alice"),
                createdAt=datetime(2025, 12, 2, tzinfo=timezone.utc),
                updatedAt=datetime(2025, 12, 2, tzinfo=timezone.utc),
            )
        ],
        url="https://linear.app/issue-123",
        createdAt=datetime(2025, 12, 1, tzinfo=timezone.utc),
        updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_project():
    """Create sample Linear project."""
    return LinearProject(
        id="proj-1",
        name="AI Feature Rollout",
        description="Implement AI assistant across all pages",
        state="started",
        url="https://linear.app/proj-1",
        createdAt=datetime(2025, 11, 1, tzinfo=timezone.utc),
        updatedAt=datetime(2025, 12, 9, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_transform_issue_bug_report(transformer, sample_issue):
    """Test transforming a bug report issue."""
    # Mock the extractor
    mock_entries = [
        KnowledgeEntry(
            knowledge_type=KnowledgeType.PAIN_POINT,
            content="Users unable to login via SSO",
            confidence_score=0.9,
        ),
        KnowledgeEntry(
            knowledge_type=KnowledgeType.QUOTE,
            content="This is blocking production",
            verbatim=True,
            confidence_score=0.95,
        ),
    ]

    with patch.object(
        transformer.extractor,
        "extract",
        new=AsyncMock(
            return_value=MagicMock(entries=mock_entries)
        ),
    ):
        source, entries = await transformer.transform_issue(
            issue=sample_issue,
            org_id="test-org",
        )

    # Verify source
    assert source.external_id == "issue-123"
    assert source.external_url == "https://linear.app/issue-123"
    assert "ENG-456" in source.source_title
    assert "Fix authentication bug" in source.source_title

    # Verify content
    assert "Issue: ENG-456" in source.raw_content
    assert "Title: Fix authentication bug" in source.raw_content
    assert "Description: Users unable to login via SSO" in source.raw_content
    assert "State: In Progress" in source.raw_content
    assert "Priority: High" in source.raw_content
    assert "Labels: bug, security" in source.raw_content
    assert "This is blocking production" in source.raw_content

    # Verify entries
    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.PAIN_POINT
    assert entries[1].knowledge_type == KnowledgeType.QUOTE


@pytest.mark.asyncio
async def test_transform_project(transformer, sample_project):
    """Test transforming a project."""
    # Mock the extractor
    mock_entries = [
        KnowledgeEntry(
            knowledge_type=KnowledgeType.FEATURE,
            content="AI assistant across all pages",
            confidence_score=0.9,
        ),
        KnowledgeEntry(
            knowledge_type=KnowledgeType.USE_CASE,
            content="Implement AI feature rollout",
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
        source, entries = await transformer.transform_project(
            project=sample_project,
            org_id="test-org",
        )

    # Verify source
    assert source.external_id == "proj-1"
    assert source.external_url == "https://linear.app/proj-1"
    assert "AI Feature Rollout" in source.source_title

    # Verify content
    assert "Project: AI Feature Rollout" in source.raw_content
    assert "State: started" in source.raw_content
    assert "Description: Implement AI assistant across all pages" in source.raw_content

    # Verify entries
    assert len(entries) == 2
    assert entries[0].knowledge_type == KnowledgeType.FEATURE
    assert entries[1].knowledge_type == KnowledgeType.USE_CASE


def test_issue_to_text(sample_issue):
    """Test converting issue to text."""
    text = sample_issue.to_text()

    assert "Issue: ENG-456" in text
    assert "Title: Fix authentication bug" in text
    assert "Description: Users unable to login via SSO" in text
    assert "State: In Progress (started)" in text
    assert "Priority: High" in text
    assert "Labels: bug, security" in text
    assert "Project: Security Sprint" in text
    assert "Created by: Alice" in text
    assert "Assigned to: Bob" in text
    assert "Comments:" in text
    assert "Alice: This is blocking production" in text
