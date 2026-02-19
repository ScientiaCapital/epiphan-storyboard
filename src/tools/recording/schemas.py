"""
Pydantic schemas for the screen recording module.

Defines data models for:
- Authentication (OAuth, cookies, headers, basic)
- Browser actions (navigate, click, type, scroll, wait, screenshot, hover)
- Recording metadata (timing events, results)
- Configuration (resolution, FPS, timing)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuthType(str, Enum):
    """Authentication types for target applications."""

    NONE = "none"
    OAUTH = "oauth"
    COOKIES = "cookies"
    HEADERS = "headers"
    BASIC = "basic"


class AuthConfig(BaseModel):
    """
    Configuration for authenticating to the target application.

    Supports multiple auth methods:
    - NONE: No authentication
    - OAUTH: OAuth provider (google, github, etc.)
    - COOKIES: Session cookies
    - HEADERS: Custom headers (e.g., Authorization)
    - BASIC: Username/password
    """

    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    provider: str | None = Field(
        default=None,
        description="OAuth provider: google, github, etc.",
    )
    cookies: dict[str, str] | None = Field(
        default=None,
        description="Cookie key-value pairs",
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="Custom headers (e.g., Authorization)",
    )
    username: str | None = Field(
        default=None,
        description="Basic auth username",
    )
    password: str | None = Field(
        default=None,
        description="Basic auth password",
    )
    cookie_domain: str | None = Field(
        default=None,
        description="Domain for cookies (e.g., '.example.com'). Extracted from target_url if not set.",
    )


class ActionType(str, Enum):
    """Supported browser actions for recording."""

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    HOVER = "hover"


class RecordingAction(BaseModel):
    """
    Single browser action to execute during recording.

    Examples:
        # Navigate to URL
        RecordingAction(action=ActionType.NAVIGATE, target="https://example.com")

        # Click button
        RecordingAction(action=ActionType.CLICK, target="button.submit")

        # Type text
        RecordingAction(action=ActionType.TYPE, target="input[name='email']", value="test@example.com")

        # Wait 2 seconds
        RecordingAction(action=ActionType.WAIT, delay_ms=2000)
    """

    action: ActionType = Field(..., description="Type of browser action")
    target: str | None = Field(
        default=None,
        description="CSS selector or URL (for navigate)",
    )
    value: str | None = Field(
        default=None,
        description="Text to type or scroll amount",
    )
    delay_ms: int = Field(
        default=500,
        ge=0,
        description="Delay after action in milliseconds",
    )


class TimingEvent(BaseModel):
    """
    Timestamp event captured during recording.

    Used to synchronize video with narration TTS.
    """

    step: int = Field(..., ge=0, description="Step number in sequence")
    action: ActionType = Field(..., description="Type of action performed")
    target: str | None = Field(default=None, description="CSS selector or URL")
    timestamp_ms: int = Field(..., ge=0, description="Milliseconds since recording start")
    screenshot_path: str | None = Field(
        default=None,
        description="Path to screenshot taken at this step",
    )


class RecordingResult(BaseModel):
    """
    Result from a completed screen recording session.

    Contains:
    - Video file path
    - Timing events for TTS sync
    - Screenshots for thumbnails
    - Duration and resolution metadata
    """

    video_path: str = Field(..., description="Path to recorded video file")
    timing_events: list[TimingEvent] = Field(
        default_factory=list,
        description="Timing events for TTS synchronization",
    )
    screenshots: list[str] = Field(
        default_factory=list,
        description="Paths to captured screenshots",
    )
    duration_ms: int = Field(..., ge=0, description="Total recording duration in milliseconds")
    resolution: dict[str, int] = Field(
        ...,
        description="Video resolution (width, height)",
    )


class RecordingConfig(BaseModel):
    """
    Configuration for screen recording.

    Default settings optimized for web app recordings:
    - 1920x1080 @ 30fps (full HD)
    - 500ms delay between actions (natural pace)
    - 50ms typing speed (fast but readable)
    - 3 minute max duration
    """

    resolution: dict[str, int] = Field(
        default={"width": 1920, "height": 1080},
        description="Video resolution",
    )
    fps: int = Field(default=30, ge=1, le=60, description="Frames per second")
    action_delay_ms: int = Field(
        default=500,
        ge=0,
        description="Default delay after each action",
    )
    typing_speed_ms: int = Field(
        default=50,
        ge=0,
        description="Delay between keystrokes when typing",
    )
    scroll_duration_ms: int = Field(
        default=800,
        ge=0,
        description="Duration for smooth scrolling",
    )
    click_highlight_ms: int = Field(
        default=300,
        ge=0,
        description="Duration to highlight click location",
    )
    max_duration_sec: int = Field(
        default=180,
        ge=1,
        description="Maximum recording duration in seconds",
    )
