"""
Tests for recording module schemas.

Following TDD: Write tests FIRST, watch them fail, then implement.
"""

import pytest
from pydantic import ValidationError


class TestAuthType:
    """Tests for AuthType enum."""

    def test_auth_type_has_none(self):
        """AuthType should have NONE option."""
        from src.tools.recording.schemas import AuthType

        assert AuthType.NONE == "none"

    def test_auth_type_has_oauth(self):
        """AuthType should have OAUTH option."""
        from src.tools.recording.schemas import AuthType

        assert AuthType.OAUTH == "oauth"

    def test_auth_type_has_cookies(self):
        """AuthType should have COOKIES option."""
        from src.tools.recording.schemas import AuthType

        assert AuthType.COOKIES == "cookies"

    def test_auth_type_has_headers(self):
        """AuthType should have HEADERS option."""
        from src.tools.recording.schemas import AuthType

        assert AuthType.HEADERS == "headers"

    def test_auth_type_has_basic(self):
        """AuthType should have BASIC option."""
        from src.tools.recording.schemas import AuthType

        assert AuthType.BASIC == "basic"


class TestAuthConfig:
    """Tests for AuthConfig Pydantic model."""

    def test_auth_config_default_type_is_none(self):
        """AuthConfig should default to NONE type."""
        from src.tools.recording.schemas import AuthConfig, AuthType

        config = AuthConfig()
        assert config.type == AuthType.NONE

    def test_auth_config_with_cookies(self):
        """AuthConfig should accept cookies dict."""
        from src.tools.recording.schemas import AuthConfig, AuthType

        config = AuthConfig(
            type=AuthType.COOKIES,
            cookies={"session": "abc123", "token": "xyz"},
        )
        assert config.type == AuthType.COOKIES
        assert config.cookies == {"session": "abc123", "token": "xyz"}

    def test_auth_config_with_headers(self):
        """AuthConfig should accept headers dict."""
        from src.tools.recording.schemas import AuthConfig, AuthType

        config = AuthConfig(
            type=AuthType.HEADERS,
            headers={"Authorization": "Bearer token123"},
        )
        assert config.type == AuthType.HEADERS
        assert config.headers == {"Authorization": "Bearer token123"}

    def test_auth_config_with_oauth(self):
        """AuthConfig should accept OAuth provider."""
        from src.tools.recording.schemas import AuthConfig, AuthType

        config = AuthConfig(
            type=AuthType.OAUTH,
            provider="google",
        )
        assert config.type == AuthType.OAUTH
        assert config.provider == "google"

    def test_auth_config_with_basic_auth(self):
        """AuthConfig should accept basic auth credentials."""
        from src.tools.recording.schemas import AuthConfig, AuthType

        config = AuthConfig(
            type=AuthType.BASIC,
            username="user",
            password="pass",
        )
        assert config.type == AuthType.BASIC
        assert config.username == "user"
        assert config.password == "pass"


class TestActionType:
    """Tests for ActionType enum."""

    def test_action_type_has_navigate(self):
        """ActionType should have NAVIGATE option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.NAVIGATE == "navigate"

    def test_action_type_has_click(self):
        """ActionType should have CLICK option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.CLICK == "click"

    def test_action_type_has_type(self):
        """ActionType should have TYPE option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.TYPE == "type"

    def test_action_type_has_scroll(self):
        """ActionType should have SCROLL option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.SCROLL == "scroll"

    def test_action_type_has_wait(self):
        """ActionType should have WAIT option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.WAIT == "wait"

    def test_action_type_has_screenshot(self):
        """ActionType should have SCREENSHOT option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.SCREENSHOT == "screenshot"

    def test_action_type_has_hover(self):
        """ActionType should have HOVER option."""
        from src.tools.recording.schemas import ActionType

        assert ActionType.HOVER == "hover"


class TestRecordingAction:
    """Tests for RecordingAction Pydantic model."""

    def test_recording_action_requires_action_type(self):
        """RecordingAction should require action type."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(action=ActionType.CLICK, target="button.submit")
        assert action.action == ActionType.CLICK

    def test_recording_action_target_optional(self):
        """RecordingAction target should be optional."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(action=ActionType.WAIT)
        assert action.target is None

    def test_recording_action_value_optional(self):
        """RecordingAction value should be optional."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(action=ActionType.TYPE, target="input[name='email']")
        assert action.value is None

    def test_recording_action_with_value(self):
        """RecordingAction should accept value for type actions."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(
            action=ActionType.TYPE,
            target="input[name='email']",
            value="test@example.com",
        )
        assert action.value == "test@example.com"

    def test_recording_action_default_delay(self):
        """RecordingAction should have default delay of 500ms."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(action=ActionType.CLICK)
        assert action.delay_ms == 500

    def test_recording_action_custom_delay(self):
        """RecordingAction should accept custom delay."""
        from src.tools.recording.schemas import RecordingAction, ActionType

        action = RecordingAction(action=ActionType.WAIT, delay_ms=2000)
        assert action.delay_ms == 2000


class TestTimingEvent:
    """Tests for TimingEvent Pydantic model."""

    def test_timing_event_creation(self):
        """TimingEvent should capture step, action, timestamp."""
        from src.tools.recording.schemas import TimingEvent, ActionType

        event = TimingEvent(
            step=1,
            action=ActionType.CLICK,
            target="button.submit",
            timestamp_ms=1500,
            screenshot_path="/tmp/step_1.png",
        )
        assert event.step == 1
        assert event.action == ActionType.CLICK
        assert event.target == "button.submit"
        assert event.timestamp_ms == 1500
        assert event.screenshot_path == "/tmp/step_1.png"

    def test_timing_event_optional_screenshot(self):
        """TimingEvent screenshot_path should be optional."""
        from src.tools.recording.schemas import TimingEvent, ActionType

        event = TimingEvent(
            step=1,
            action=ActionType.NAVIGATE,
            target="https://example.com",
            timestamp_ms=0,
        )
        assert event.screenshot_path is None


class TestRecordingResult:
    """Tests for RecordingResult Pydantic model."""

    def test_recording_result_creation(self):
        """RecordingResult should contain video path and metadata."""
        from src.tools.recording.schemas import RecordingResult, TimingEvent, ActionType

        result = RecordingResult(
            video_path="/tmp/recording.webm",
            timing_events=[
                TimingEvent(step=1, action=ActionType.NAVIGATE, target="https://example.com", timestamp_ms=0),
            ],
            screenshots=["/tmp/step_1.png"],
            duration_ms=5000,
            resolution={"width": 1920, "height": 1080},
        )
        assert result.video_path == "/tmp/recording.webm"
        assert len(result.timing_events) == 1
        assert result.duration_ms == 5000
        assert result.resolution == {"width": 1920, "height": 1080}


class TestRecordingConfig:
    """Tests for RecordingConfig Pydantic model."""

    def test_recording_config_defaults(self):
        """RecordingConfig should have sensible defaults."""
        from src.tools.recording.schemas import RecordingConfig

        config = RecordingConfig()
        assert config.resolution == {"width": 1920, "height": 1080}
        assert config.fps == 30
        assert config.action_delay_ms == 500
        assert config.typing_speed_ms == 50
        assert config.scroll_duration_ms == 800
        assert config.click_highlight_ms == 300
        assert config.max_duration_sec == 180

    def test_recording_config_custom_resolution(self):
        """RecordingConfig should accept custom resolution."""
        from src.tools.recording.schemas import RecordingConfig

        config = RecordingConfig(resolution={"width": 1280, "height": 720})
        assert config.resolution == {"width": 1280, "height": 720}


class TestRunwayConfig:
    """Tests for RunwayConfig dataclass."""

    def test_runway_config_defaults(self):
        """RunwayConfig should have sensible defaults."""
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig()
        assert config.base_url == "https://api.runwayml.com/v1"
        assert config.timeout == 120
        assert config.max_retries == 3
        assert config.default_model == "gen3a_turbo"

    def test_runway_config_custom_model(self):
        """RunwayConfig should accept custom model."""
        from src.tools.recording.config import RunwayConfig

        config = RunwayConfig(default_model="gen3a")
        assert config.default_model == "gen3a"


class TestBrowserbaseConfig:
    """Tests for BrowserbaseConfig dataclass."""

    def test_browserbase_config_defaults(self):
        """BrowserbaseConfig should have sensible defaults."""
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig()
        assert config.base_url == "https://www.browserbase.com/v1"
        assert config.timeout == 120
        assert config.max_retries == 3

    def test_browserbase_config_reads_env(self, monkeypatch):
        """BrowserbaseConfig should read from environment variables."""
        from src.tools.recording.config import BrowserbaseConfig

        monkeypatch.setenv("BROWSERBASE_API_KEY", "test_key")
        monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "test_project")

        config = BrowserbaseConfig()
        assert config.api_key == "test_key"
        assert config.project_id == "test_project"

    def test_browserbase_config_explicit_values(self):
        """BrowserbaseConfig explicit values should override env."""
        from src.tools.recording.config import BrowserbaseConfig

        config = BrowserbaseConfig(api_key="explicit_key", project_id="explicit_project")
        assert config.api_key == "explicit_key"
        assert config.project_id == "explicit_project"
