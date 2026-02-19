"""
Configuration dataclasses for recording module.

Provides configuration for:
- BrowserbaseConfig: Cloud browser settings
- RunwayConfig: Video generation settings
"""

import os
from dataclasses import dataclass, field


@dataclass
class BrowserbaseConfig:
    """
    Configuration for Browserbase client.

    Reads API credentials from environment variables if not provided explicitly.

    Environment Variables:
        BROWSERBASE_API_KEY: API key for Browserbase
        BROWSERBASE_PROJECT_ID: Project ID for Browserbase

    Example:
        # From environment
        config = BrowserbaseConfig()

        # Explicit values (override env)
        config = BrowserbaseConfig(api_key="key", project_id="proj")
    """

    api_key: str | None = None
    project_id: str | None = None
    base_url: str = "https://www.browserbase.com/v1"
    timeout: int = 120
    max_retries: int = 3

    def __post_init__(self):
        """Load from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.getenv("BROWSERBASE_API_KEY")
        if self.project_id is None:
            self.project_id = os.getenv("BROWSERBASE_PROJECT_ID")


@dataclass
class RunwayConfig:
    """
    Configuration for Runway API client.

    Reads API credentials from environment variables if not provided explicitly.

    Environment Variables:
        RUNWAY_API_KEY: API key for Runway

    Supported Models:
        - gen3a_turbo: Fast text/image-to-video (5-10s clips)
        - gen3a: Higher quality (longer generation time)

    Example:
        # From environment
        config = RunwayConfig()

        # Explicit values
        config = RunwayConfig(api_key="key", default_model="gen3a")
    """

    api_key: str | None = None
    base_url: str = "https://api.runwayml.com/v1"
    timeout: int = 120
    max_retries: int = 3
    default_model: str = "gen3a_turbo"
    default_duration: int = 5  # seconds
    default_aspect_ratio: str = "16:9"

    def __post_init__(self):
        """Load from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.getenv("RUNWAY_API_KEY")
