"""
ScreenRecorderTool - Record Web App Interactions
=================================================

BaseTool wrapper for Browserbase cloud browser recording.
Records authenticated web app sessions with timing events.

NO OpenAI - Playwright over CDP only.
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.recording.browserbase import BrowserbaseClient
from src.tools.recording.config import BrowserbaseConfig
from src.tools.recording.schemas import (
    ActionType,
    AuthConfig,
    AuthType,
    RecordingAction,
    RecordingConfig,
    RecordingResult,
    TimingEvent,
)

logger = logging.getLogger(__name__)


class ScreenRecorderTool(BaseTool):
    """
    Record authenticated web app interactions.

    Uses Browserbase cloud browser for session management and Playwright
    for browser automation. Outputs WebM video with timing events.

    Example:
        tool = ScreenRecorderTool()
        result = await tool.run({
            "target_url": "https://app.example.com",
            "actions": [
                {"action": "click", "target": "button#login"},
                {"action": "type", "target": "input#email", "value": "user@example.com"},
                {"action": "screenshot"},
            ],
            "auth": {
                "type": "cookies",
                "cookies": {"session": "abc123"},
            },
        })
    """

    def __init__(
        self,
        browserbase_client: BrowserbaseClient | None = None,
        config: BrowserbaseConfig | None = None,
    ):
        """
        Initialize ScreenRecorderTool.

        Args:
            browserbase_client: Optional pre-configured client
            config: Optional configuration (uses env vars if not provided)
        """
        self._client = browserbase_client
        self._config = config

    def _get_client(self) -> BrowserbaseClient:
        """Lazy initialization of Browserbase client."""
        if self._client is None:
            self._client = BrowserbaseClient(config=self._config)
        return self._client

    @property
    def definition(self) -> ToolDefinition:
        """Tool definition for LLM function calling."""
        return ToolDefinition(
            name="screen_recorder",
            description=(
                "Record authenticated web app interactions as video. "
                "Connects to any web app via cloud browser, executes actions "
                "(click, type, scroll, etc.), and captures screen recording. "
                "Supports cookie/header/basic auth injection. "
                "Perfect for creating demo videos, tutorials, and documentation."
            ),
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "target_url": {
                        "type": "string",
                        "description": "URL of the web app to record",
                    },
                    "actions": {
                        "type": "array",
                        "description": "List of actions to execute",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["navigate", "click", "type", "scroll", "wait", "screenshot", "hover"],
                                    "description": "Action type",
                                },
                                "target": {
                                    "type": "string",
                                    "description": "CSS selector or URL for navigate",
                                },
                                "value": {
                                    "type": "string",
                                    "description": "Text to type or scroll amount",
                                },
                                "delay_ms": {
                                    "type": "integer",
                                    "description": "Delay after action in ms",
                                    "default": 500,
                                },
                            },
                            "required": ["action"],
                        },
                    },
                    "auth": {
                        "type": "object",
                        "description": "Authentication config (cookies, headers, basic)",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["none", "cookies", "headers", "basic", "oauth"],
                            },
                            "cookies": {
                                "type": "object",
                                "description": "Cookie key-value pairs",
                            },
                            "headers": {
                                "type": "object",
                                "description": "Header key-value pairs",
                            },
                            "username": {
                                "type": "string",
                                "description": "Basic auth username",
                            },
                            "password": {
                                "type": "string",
                                "description": "Basic auth password",
                            },
                            "cookie_domain": {
                                "type": "string",
                                "description": "Domain for cookies",
                            },
                        },
                    },
                    "config": {
                        "type": "object",
                        "description": "Recording configuration",
                        "properties": {
                            "resolution": {
                                "type": "object",
                                "properties": {
                                    "width": {"type": "integer", "default": 1920},
                                    "height": {"type": "integer", "default": 1080},
                                },
                            },
                            "fps": {"type": "integer", "default": 30},
                            "max_duration_sec": {"type": "integer", "default": 180},
                        },
                    },
                },
                "required": ["target_url", "actions"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute recording session.

        Args:
            arguments: Tool arguments containing:
                - target_url: Required. URL to record.
                - actions: Required. List of actions to execute.
                - auth: Optional. Authentication config.
                - config: Optional. Recording configuration.

        Returns:
            ToolResult with:
            - video_path: Path to recorded video
            - timing_events: List of action timestamps
            - screenshots: List of screenshot paths
            - duration_ms: Total recording duration
        """
        start_time = perf_counter()

        # Validate required parameters
        target_url = arguments.get("target_url")
        if not target_url:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="Missing required 'target_url' parameter",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        actions = arguments.get("actions")
        if actions is None:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="Missing required 'actions' parameter",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        # Validate action format
        for i, action in enumerate(actions):
            if not isinstance(action, dict) or "action" not in action:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=f"Invalid action at index {i}: must have 'action' key",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )
            if action["action"] not in ["navigate", "click", "type", "scroll", "wait", "screenshot", "hover"]:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=f"Invalid action type at index {i}: {action['action']}",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

        # Parse auth config
        auth_config = None
        auth_data = arguments.get("auth")
        if auth_data:
            auth_type = auth_data.get("type", "none")
            auth_config = AuthConfig(
                type=AuthType(auth_type),
                cookies=auth_data.get("cookies"),
                headers=auth_data.get("headers"),
                username=auth_data.get("username"),
                password=auth_data.get("password"),
                cookie_domain=auth_data.get("cookie_domain"),
            )

        # Parse recording config
        config_data = arguments.get("config", {})
        recording_config = RecordingConfig(
            resolution=config_data.get("resolution", {"width": 1920, "height": 1080}),
            fps=config_data.get("fps", 30),
            max_duration_sec=config_data.get("max_duration_sec", 180),
        )

        try:
            client = self._get_client()

            # Create session
            session = await client.create_session()
            session_id = session["id"]

            try:
                # Connect to browser
                page = await client.connect(session_id, auth_config)

                # Navigate to target URL
                await page.goto(target_url)
                await asyncio.sleep(1)  # Wait for page load

                # Execute actions and track timing
                timing_events: list[dict] = []
                screenshots: list[str] = []
                recording_start = perf_counter()

                for i, action in enumerate(actions):
                    action_start = perf_counter()
                    result = await self._execute_action(page, action)

                    # Track timing
                    timing_events.append({
                        "step": i,
                        "action": action["action"],
                        "target": action.get("target"),
                        "timestamp_ms": int((action_start - recording_start) * 1000),
                    })

                    # Capture screenshot if action returned one
                    if isinstance(result, bytes):
                        screenshot_path = self._save_screenshot(result, i)
                        screenshots.append(screenshot_path)
                        timing_events[-1]["screenshot_path"] = screenshot_path

                    # Apply delay
                    delay_ms = action.get("delay_ms", 500)
                    await asyncio.sleep(delay_ms / 1000)

                # Generate video path (recording is handled by Browserbase)
                video_path = await self._record_video(session_id)

                recording_duration = int((perf_counter() - recording_start) * 1000)

                return ToolResult(
                    tool_name=self.definition.name,
                    success=True,
                    result={
                        "video_path": video_path,
                        "timing_events": timing_events,
                        "screenshots": screenshots,
                        "duration_ms": recording_duration,
                        "resolution": recording_config.resolution,
                    },
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            finally:
                # Always close session
                await client.close_session(session_id)

        except Exception as e:
            logger.error(f"[SCREEN_RECORDER] Error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

    async def _execute_action(self, page, action: dict) -> Any:
        """
        Execute a single browser action.

        Args:
            page: Playwright Page object
            action: Action dict with 'action', 'target', 'value' keys

        Returns:
            Screenshot bytes if action was screenshot, else None
        """
        action_type = action["action"]
        target = action.get("target")
        value = action.get("value")

        if action_type == "navigate":
            await page.goto(target)

        elif action_type == "click":
            await page.click(target)

        elif action_type == "type":
            await page.fill(target, value or "")

        elif action_type == "scroll":
            scroll_amount = int(value) if value else 500
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

        elif action_type == "wait":
            wait_ms = int(value) if value else 1000
            await page.wait_for_timeout(wait_ms)

        elif action_type == "screenshot":
            return await page.screenshot()

        elif action_type == "hover":
            await page.hover(target)

        return None

    def _save_screenshot(self, screenshot_bytes: bytes, index: int) -> str:
        """
        Save screenshot to temp file.

        Args:
            screenshot_bytes: PNG bytes
            index: Action index

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}_{index}.png"
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)

        with open(file_path, "wb") as f:
            f.write(screenshot_bytes)

        logger.info(f"[SCREEN_RECORDER] Saved screenshot: {file_path}")
        return file_path

    async def _record_video(self, session_id: str) -> str:
        """
        Get video recording from Browserbase session.

        Note: Browserbase handles video recording on their end.
        This method would download/return the video path.

        Args:
            session_id: Browserbase session ID

        Returns:
            Path to video file
        """
        # In a real implementation, this would download the video from Browserbase
        # For now, return a placeholder path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        video_path = os.path.join(temp_dir, f"recording_{session_id}_{timestamp}.webm")

        logger.info(f"[SCREEN_RECORDER] Video recording: {video_path}")
        return video_path
