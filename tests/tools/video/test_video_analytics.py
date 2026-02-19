"""Tests for Loom analytics tools."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.video.video_analytics import (
    LoomViewTrackerTool,
    ViewerEnrichmentTool,
    LoomViewer,
    ViewAnalytics,
    EnrichedViewer,
)
from src.tools.base import ToolCategory, BaseTool


class TestLoomViewTrackerDefinition:
    """Tests for LoomViewTrackerTool definition."""

    def test_definition_name(self):
        tool = LoomViewTrackerTool()
        assert tool.definition.name == "loom_view_tracker"

    def test_definition_category(self):
        tool = LoomViewTrackerTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_parameters(self):
        tool = LoomViewTrackerTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "video_id" in params["properties"]

    def test_inherits_from_base_tool(self):
        tool = LoomViewTrackerTool()
        assert isinstance(tool, BaseTool)


class TestViewerEnrichmentDefinition:
    """Tests for ViewerEnrichmentTool definition."""

    def test_definition_name(self):
        tool = ViewerEnrichmentTool()
        assert tool.definition.name == "viewer_enrichment"

    def test_definition_category(self):
        tool = ViewerEnrichmentTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_inherits_from_base_tool(self):
        tool = ViewerEnrichmentTool()
        assert isinstance(tool, BaseTool)


class TestPydanticModels:
    """Tests for Pydantic data models."""

    def test_loom_viewer_model(self):
        """Test LoomViewer model creation."""
        viewer = LoomViewer(
            email="test@example.com",
            view_id="view-123",
            watch_duration_seconds=60,
            completion_rate=85.5,
            rewatch_count=2,
            first_viewed_at="2024-01-15T10:00:00Z",
            last_viewed_at="2024-01-15T10:01:00Z",
        )
        assert viewer.email == "test@example.com"
        assert viewer.completion_rate == 85.5
        assert viewer.rewatch_count == 2

    def test_loom_viewer_optional_email(self):
        """Test LoomViewer with no email."""
        viewer = LoomViewer(
            view_id="view-123",
            watch_duration_seconds=30,
            completion_rate=50.0,
            first_viewed_at="2024-01-15T10:00:00Z",
            last_viewed_at="2024-01-15T10:00:30Z",
        )
        assert viewer.email is None

    def test_enriched_viewer_model(self):
        """Test EnrichedViewer model creation."""
        viewer = EnrichedViewer(
            email="john@acme.com",
            full_name="John Doe",
            company="Acme Inc",
            title="VP Sales",
            industry="Technology",
            revenue=10000000,
            employee_count=500,
            linkedin_url="https://linkedin.com/in/johndoe",
            enrichment_source="apollo",
            engagement_score=85.0,
            is_hot_lead=True,
        )
        assert viewer.email == "john@acme.com"
        assert viewer.is_hot_lead is True
        assert viewer.engagement_score == 85.0

    def test_enriched_viewer_hot_lead_flag(self):
        """Test EnrichedViewer hot lead identification."""
        hot_viewer = EnrichedViewer(
            email="hot@example.com",
            enrichment_source="apollo",
            engagement_score=90.0,
            is_hot_lead=True,
        )
        assert hot_viewer.is_hot_lead is True

        cold_viewer = EnrichedViewer(
            email="cold@example.com",
            enrichment_source="apollo",
            engagement_score=30.0,
            is_hot_lead=False,
        )
        assert cold_viewer.is_hot_lead is False


class TestEngagementScoring:
    """Tests for engagement score calculation."""

    def test_engagement_score_range(self):
        """Test engagement score is in valid range."""
        viewer = EnrichedViewer(
            email="test@example.com",
            enrichment_source="apollo",
            engagement_score=75.5,
        )
        assert 0 <= viewer.engagement_score <= 100

    def test_completion_rate_range(self):
        """Test completion rate is in valid range."""
        viewer = LoomViewer(
            view_id="view-123",
            watch_duration_seconds=60,
            completion_rate=100.0,  # Max
            first_viewed_at="2024-01-15T10:00:00Z",
            last_viewed_at="2024-01-15T10:01:00Z",
        )
        assert viewer.completion_rate == 100.0


class TestLoomViewTrackerRun:
    """Tests for LoomViewTrackerTool execution."""

    @pytest.mark.asyncio
    async def test_missing_video_id(self):
        """Test error when video_id is missing."""
        tool = LoomViewTrackerTool()
        result = await tool.run({})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test error when Loom API key is missing."""
        tool = LoomViewTrackerTool()

        with patch.dict("os.environ", {}, clear=True):
            result = await tool.run({
                "video_id": "abc123",
            })

        assert result.success is False


class TestViewerEnrichmentRun:
    """Tests for ViewerEnrichmentTool execution."""

    @pytest.mark.asyncio
    async def test_missing_viewer_email(self):
        """Test error when viewer_email is missing."""
        tool = ViewerEnrichmentTool()
        result = await tool.run({})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_email_format(self):
        """Test error for invalid email format."""
        tool = ViewerEnrichmentTool()
        result = await tool.run({
            "viewer_email": "not-an-email",
        })
        assert result.success is False
