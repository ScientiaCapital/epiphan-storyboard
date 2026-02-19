"""Tests for VideoSchedulerTool."""

import pytest
from datetime import time
from zoneinfo import ZoneInfo

from src.tools.video.video_scheduler import VideoSchedulerTool
from src.tools.base import ToolCategory, BaseTool


class TestVideoSchedulerDefinition:
    """Tests for VideoSchedulerTool definition."""

    def test_definition_name(self):
        tool = VideoSchedulerTool()
        assert tool.definition.name == "video_scheduler"

    def test_definition_category(self):
        tool = VideoSchedulerTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_parameters(self):
        tool = VideoSchedulerTool()
        params = tool.definition.parameters
        assert params["type"] == "object"

    def test_inherits_from_base_tool(self):
        tool = VideoSchedulerTool()
        assert isinstance(tool, BaseTool)


class TestDayScoring:
    """Tests for day-of-week scoring."""

    def test_tuesday_high_score(self):
        """Tuesday should have high engagement score."""
        tool = VideoSchedulerTool()
        assert tool.DAY_SCORES[1]["score"] >= 0.8  # Tuesday = index 1

    def test_wednesday_high_score(self):
        """Wednesday should have high engagement score."""
        tool = VideoSchedulerTool()
        assert tool.DAY_SCORES[2]["score"] >= 0.8  # Wednesday = index 2

    def test_saturday_low_score(self):
        """Saturday should have low engagement score."""
        tool = VideoSchedulerTool()
        assert tool.DAY_SCORES[5]["score"] <= 0.5  # Saturday = index 5

    def test_sunday_low_score(self):
        """Sunday should have low engagement score."""
        tool = VideoSchedulerTool()
        assert tool.DAY_SCORES[6]["score"] <= 0.5  # Sunday = index 6

    def test_all_days_have_names(self):
        """All days should have name attribute."""
        tool = VideoSchedulerTool()
        for day_idx in range(7):
            assert "name" in tool.DAY_SCORES[day_idx]

    def test_get_top_days_excludes_weekends(self):
        """Top days should not include weekends."""
        tool = VideoSchedulerTool()
        top_days = tool._get_top_days()
        # 5 = Saturday, 6 = Sunday
        assert 5 not in top_days
        assert 6 not in top_days


class TestRoleLevelAdjustments:
    """Tests for role-based scheduling adjustments."""

    def test_c_level_adjustments_exist(self):
        """C-level role should have adjustments."""
        tool = VideoSchedulerTool()
        assert "c-level" in tool.ROLE_ADJUSTMENTS

    def test_vp_adjustments_exist(self):
        """VP role should have adjustments."""
        tool = VideoSchedulerTool()
        assert "vp" in tool.ROLE_ADJUSTMENTS

    def test_director_adjustments_exist(self):
        """Director role should have adjustments."""
        tool = VideoSchedulerTool()
        assert "director" in tool.ROLE_ADJUSTMENTS

    def test_manager_adjustments_exist(self):
        """Manager role should have adjustments."""
        tool = VideoSchedulerTool()
        assert "manager" in tool.ROLE_ADJUSTMENTS


class TestTimezoneHandling:
    """Tests for timezone validation."""

    def test_default_timezone(self):
        """Default timezone should be America/New_York."""
        tool = VideoSchedulerTool()
        assert tool.DEFAULT_TIMEZONE == "America/New_York"

    @pytest.mark.asyncio
    async def test_valid_timezone_accepted(self):
        """Valid timezone should be accepted."""
        tool = VideoSchedulerTool()
        result = await tool.run({
            "prospect_timezone": "America/Los_Angeles",
            "industry": "solar",
        })
        # Should not fail on timezone validation
        # May fail on other reasons (no LLM key), but timezone should be valid
        if not result.success:
            assert "timezone" not in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_timezone_rejected(self):
        """Invalid timezone should be rejected."""
        tool = VideoSchedulerTool()
        result = await tool.run({
            "prospect_timezone": "Invalid/Timezone",
            "industry": "solar",
        })
        assert result.success is False
        assert "timezone" in result.error.lower()


class TestVideoSchedulerRun:
    """Tests for VideoSchedulerTool execution."""

    @pytest.mark.asyncio
    async def test_returns_optimal_times(self):
        """Test that run returns optimal send times."""
        tool = VideoSchedulerTool()
        result = await tool.run({
            "prospect_timezone": "America/New_York",
            "industry": "solar",
            "role_level": "manager",
            "use_llm": False,  # Skip LLM for faster test
        })

        assert result.success is True
        assert "top_3_windows" in result.result

    @pytest.mark.asyncio
    async def test_returns_reasoning(self):
        """Test that run returns reasoning."""
        tool = VideoSchedulerTool()
        result = await tool.run({
            "prospect_timezone": "America/New_York",
            "industry": "hvac",
            "role_level": "director",
            "use_llm": False,
        })

        assert result.success is True
        assert "reasoning" in result.result

    @pytest.mark.asyncio
    async def test_returns_avoid_times(self):
        """Test that run returns times to avoid."""
        tool = VideoSchedulerTool()
        result = await tool.run({
            "prospect_timezone": "America/Chicago",
            "industry": "electrical",
            "use_llm": False,
        })

        assert result.success is True
        assert "avoid_times" in result.result
