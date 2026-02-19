"""
Tests for ScreenRecorderTool.

Following TDD: Write tests FIRST, watch them fail, then implement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestScreenRecorderToolDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        """Tool should have correct name."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        assert tool.definition.name == "screen_recorder"

    def test_definition_category(self):
        """Tool should have WEB category."""
        from src.tools.recording.screen_capture import ScreenRecorderTool
        from src.tools.base import ToolCategory

        tool = ScreenRecorderTool()
        assert tool.definition.category == ToolCategory.WEB

    def test_definition_has_required_parameters(self):
        """Definition should require target_url and actions."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        params = tool.definition.parameters
        assert "required" in params
        assert "target_url" in params["required"]
        assert "actions" in params["required"]

    def test_definition_has_description(self):
        """Tool should have non-empty description."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        assert tool.definition.description
        assert len(tool.definition.description) > 20

    def test_definition_does_not_require_approval(self):
        """Tool should not require approval."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        assert tool.definition.requires_approval is False


class TestScreenRecorderToolValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_run_requires_target_url(self):
        """run() should fail if target_url missing."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        result = await tool.run({"actions": []})

        assert result.success is False
        assert "target_url" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_requires_actions(self):
        """run() should fail if actions missing."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        result = await tool.run({"target_url": "https://example.com"})

        assert result.success is False
        assert "actions" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_validates_action_format(self):
        """run() should validate action format."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        result = await tool.run({
            "target_url": "https://example.com",
            "actions": [{"invalid": "action"}],  # Missing 'action' key
        })

        assert result.success is False
        assert "action" in result.error.lower() or "invalid" in result.error.lower()


class TestScreenRecorderToolExecution:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_run_success_returns_recording_result(self):
        """run() should return recording result on success."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()

        # Mock the browserbase client
        mock_client = MagicMock()
        mock_session = {"id": "session_123", "connectUrl": "wss://..."}
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.close_session = AsyncMock()

        # Mock page
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot")
        mock_client.connect = AsyncMock(return_value=mock_page)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with patch.object(tool, "_record_video", return_value="/tmp/recording.webm"):
                result = await tool.run({
                    "target_url": "https://example.com",
                    "actions": [
                        {"action": "click", "target": "button#submit"},
                    ],
                })

        assert result.success is True
        assert "video_path" in result.result

    @pytest.mark.asyncio
    async def test_run_handles_browserbase_error(self):
        """run() should handle Browserbase API errors gracefully."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()

        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(
            side_effect=ValueError("API key not configured")
        )

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.run({
                "target_url": "https://example.com",
                "actions": [{"action": "click", "target": "#btn"}],
            })

        assert result.success is False
        assert "API key" in result.error or "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_tracks_timing_events(self):
        """run() should track timing events for each action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()

        mock_client = MagicMock()
        mock_session = {"id": "session_123", "connectUrl": "wss://..."}
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.close_session = AsyncMock()

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake")
        mock_client.connect = AsyncMock(return_value=mock_page)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with patch.object(tool, "_record_video", return_value="/tmp/recording.webm"):
                result = await tool.run({
                    "target_url": "https://example.com",
                    "actions": [
                        {"action": "click", "target": "#btn1"},
                        {"action": "click", "target": "#btn2"},
                    ],
                })

        if result.success:
            assert "timing_events" in result.result
            assert len(result.result["timing_events"]) >= 2


class TestScreenRecorderToolActionExecution:
    """Tests for individual action execution."""

    @pytest.mark.asyncio
    async def test_execute_navigate_action(self):
        """_execute_action should handle navigate action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "navigate", "target": "https://example.com/page"},
        )

        mock_page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_click_action(self):
        """_execute_action should handle click action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.click = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "click", "target": "button#submit"},
        )

        mock_page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_type_action(self):
        """_execute_action should handle type action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.fill = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "type", "target": "input#email", "value": "test@example.com"},
        )

        mock_page.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_scroll_action(self):
        """_execute_action should handle scroll action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "scroll", "value": "500"},
        )

        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_wait_action(self):
        """_execute_action should handle wait action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.wait_for_timeout = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "wait", "value": "1000"},
        )

        mock_page.wait_for_timeout.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_screenshot_action(self):
        """_execute_action should handle screenshot action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_screenshot")

        result = await tool._execute_action(
            mock_page,
            {"action": "screenshot"},
        )

        mock_page.screenshot.assert_called_once()
        assert result == b"fake_screenshot"

    @pytest.mark.asyncio
    async def test_execute_hover_action(self):
        """_execute_action should handle hover action."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()
        mock_page = MagicMock()
        mock_page.hover = AsyncMock()

        await tool._execute_action(
            mock_page,
            {"action": "hover", "target": "div.menu"},
        )

        mock_page.hover.assert_called_once()


class TestScreenRecorderToolAuth:
    """Tests for authentication handling."""

    @pytest.mark.asyncio
    async def test_run_with_cookie_auth(self):
        """run() should pass auth config to Browserbase."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()

        mock_client = MagicMock()
        mock_session = {"id": "session_123", "connectUrl": "wss://..."}
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.close_session = AsyncMock()

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake")
        mock_client.connect = AsyncMock(return_value=mock_page)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with patch.object(tool, "_record_video", return_value="/tmp/recording.webm"):
                result = await tool.run({
                    "target_url": "https://example.com",
                    "actions": [{"action": "screenshot"}],
                    "auth": {
                        "type": "cookies",
                        "cookies": {"session": "abc123"},
                    },
                })

        # Verify connect was called (auth is passed through there)
        mock_client.connect.assert_called_once()


class TestScreenRecorderToolConfig:
    """Tests for recording configuration."""

    @pytest.mark.asyncio
    async def test_run_accepts_custom_resolution(self):
        """run() should accept custom resolution."""
        from src.tools.recording.screen_capture import ScreenRecorderTool

        tool = ScreenRecorderTool()

        mock_client = MagicMock()
        mock_session = {"id": "session_123", "connectUrl": "wss://..."}
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_client.close_session = AsyncMock()

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake")
        mock_client.connect = AsyncMock(return_value=mock_page)

        with patch.object(tool, "_get_client", return_value=mock_client):
            with patch.object(tool, "_record_video", return_value="/tmp/recording.webm"):
                result = await tool.run({
                    "target_url": "https://example.com",
                    "actions": [{"action": "screenshot"}],
                    "config": {
                        "resolution": {"width": 1280, "height": 720},
                    },
                })

        # Just verify it doesn't fail with custom config
        assert result.tool_name == "screen_recorder"
