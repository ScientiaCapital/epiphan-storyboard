"""
Screen Recording Module for Conductor-AI
=========================================

Cloud browser recording with Browserbase + Playwright.
Video generation with Runway Gen-3 Alpha.

NO OpenAI - Browserbase + Playwright + Runway only.
"""

from src.tools.recording.schemas import (
    ActionType,
    AuthConfig,
    AuthType,
    RecordingAction,
    RecordingConfig,
    RecordingResult,
    TimingEvent,
)
from src.tools.recording.config import (
    BrowserbaseConfig,
    RunwayConfig,
)
from src.tools.recording.browserbase import BrowserbaseClient
from src.tools.recording.runway_client import RunwayClient
from src.tools.recording.screen_capture import ScreenRecorderTool
from src.tools.recording.video_generator import RunwayVideoGeneratorTool

__all__ = [
    # Schemas
    "ActionType",
    "AuthConfig",
    "AuthType",
    "RecordingAction",
    "RecordingConfig",
    "RecordingResult",
    "TimingEvent",
    # Config
    "BrowserbaseConfig",
    "RunwayConfig",
    # Clients
    "BrowserbaseClient",
    "RunwayClient",
    # Tools (BaseTool implementations)
    "ScreenRecorderTool",
    "RunwayVideoGeneratorTool",
]
