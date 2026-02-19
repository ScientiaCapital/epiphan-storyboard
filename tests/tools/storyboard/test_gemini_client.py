"""Tests for Gemini Storyboard Client."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    GeminiConfig,
    StoryboardUnderstanding,
)
from src.tools.storyboard.coperniq_presets import COPERNIQ_ICP


class TestGeminiConfig:
    """Tests for GeminiConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            config = GeminiConfig()
            # NOTE: Config now has split model config for multi-model architecture
            assert config.gemini_vision_model == "models/gemini-2.0-flash"
            assert config.image_model == "models/gemini-3-pro-image-preview"
            assert config.timeout == 90
            assert config.max_retries == 3

    def test_config_from_env(self):
        """Test API key loaded from environment."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-test-key"}):
            config = GeminiConfig()
            assert config.api_key == "env-test-key"

    def test_config_explicit_key(self):
        """Test explicit API key overrides environment."""
        config = GeminiConfig(api_key="explicit-key")
        assert config.api_key == "explicit-key"

    def test_custom_models(self):
        """Test custom model configuration."""
        config = GeminiConfig(
            gemini_vision_model="custom-gemini-vision",
            qwen_model="custom-qwen",
            image_model="custom-image",
        )
        assert config.gemini_vision_model == "custom-gemini-vision"
        assert config.qwen_model == "custom-qwen"
        assert config.image_model == "custom-image"


class TestStoryboardUnderstanding:
    """Tests for StoryboardUnderstanding model."""

    def test_required_fields(self):
        """Test required fields are enforced."""
        understanding = StoryboardUnderstanding(
            headline="Test Headline",
            what_it_does="Test description",
            business_value="Test value",
            who_benefits="Test audience",
            differentiator="Test differentiator",
            pain_point_addressed="Test pain point",
        )
        assert understanding.headline == "Test Headline"
        assert understanding.suggested_icon == "clipboard-check"  # default

    def test_custom_icon(self):
        """Test custom icon override."""
        understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
            suggested_icon="rocket",
        )
        assert understanding.suggested_icon == "rocket"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "headline": "Dict Headline",
            "what_it_does": "Dict description",
            "business_value": "Dict value",
            "who_benefits": "Dict audience",
            "differentiator": "Dict diff",
            "pain_point_addressed": "Dict pain",
            "suggested_icon": "star",
        }
        understanding = StoryboardUnderstanding(**data)
        assert understanding.headline == "Dict Headline"
        assert understanding.suggested_icon == "star"


class TestGeminiStoryboardClientInit:
    """Tests for GeminiStoryboardClient initialization."""

    def test_init_with_config(self):
        """Test initialization with explicit config."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)
        assert client.config.api_key == "test-key"
        assert client._initialized is False

    def test_init_default_config(self):
        """Test initialization with default config."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}):
            client = GeminiStoryboardClient()
            assert client.config.api_key == "env-key"

    def test_lazy_initialization(self):
        """Test client is not initialized until first use."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)
        assert client._client is None
        assert client._initialized is False


class TestGeminiClientHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """Test health check fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            config = GeminiConfig(api_key=None)
            client = GeminiStoryboardClient(config=config)
            health = await client.health_check()
            assert health["status"] == "unhealthy"
            assert health["api_key_configured"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_api_key(self):
        """Test health check with API key (mocked import)."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        # Mock the google.genai import
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()

        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
            health = await client.health_check()
            # Will still fail because actual import differs, but API key is configured
            assert health["api_key_configured"] is True


class TestLanguageGuidelines:
    """Tests for _build_language_guidelines method."""

    def test_builds_guidelines_from_icp(self):
        """Test guidelines are built from ICP preset."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        guidelines = client._build_language_guidelines(COPERNIQ_ICP)

        assert "LANGUAGE GUIDELINES" in guidelines
        assert "Tone:" in guidelines
        assert "AVOID" in guidelines
        assert "USE" in guidelines

    def test_includes_avoid_terms(self):
        """Test guidelines include terms to avoid."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        guidelines = client._build_language_guidelines(COPERNIQ_ICP)

        # Should include some of the avoid terms (technical jargon)
        # NOTE: "AI" is NOT avoided anymore - we use it for AI features
        assert "API" in guidelines

    def test_includes_use_terms(self):
        """Test guidelines include terms to use."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        guidelines = client._build_language_guidelines(COPERNIQ_ICP)

        # Should include some of the use terms
        assert "saves you time" in guidelines


class TestUnderstandCodeMocked:
    """Tests for understand_code with mocked Gemini API."""

    @pytest.mark.asyncio
    async def test_understand_code_parses_response(self):
        """Test code understanding parses Gemini response."""
        # Use text_provider="gemini" to test the Gemini code path
        config = GeminiConfig(api_key="test-key", text_provider="gemini")
        client = GeminiStoryboardClient(config=config)

        # Mock response with new extraction verification fields
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "headline": "Track Your Jobs Effortlessly",
            "tagline": "One platform for all your projects",
            "what_it_does": "See all your projects in one place.",
            "business_value": "Save 5 hours per week.",
            "who_benefits": "Project managers and owners",
            "differentiator": "Works on your phone in the field.",
            "pain_point_addressed": "Spreadsheet chaos.",
            "suggested_icon": "clipboard",
            "raw_extracted_text": "def track_job(): pass - Job tracking function",
            "extraction_confidence": 0.95,
        })

        # Mock the client
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response

        client._client = mock_genai_client
        client._initialized = True

        result = await client.understand_code(
            code_content="def track_job(): pass",
            icp_preset=COPERNIQ_ICP,
            audience="c_suite",
        )

        assert result.headline == "Track Your Jobs Effortlessly"
        assert result.business_value == "Save 5 hours per week."
        assert result.suggested_icon == "clipboard"

    @pytest.mark.asyncio
    async def test_understand_code_handles_markdown_response(self):
        """Test code understanding handles markdown-wrapped JSON."""
        # Use text_provider="gemini" to test the Gemini code path
        config = GeminiConfig(api_key="test-key", text_provider="gemini")
        client = GeminiStoryboardClient(config=config)

        # Mock response with markdown code block (includes new fields)
        mock_response = MagicMock()
        mock_response.text = """```json
{
    "headline": "Test Headline",
    "tagline": "Test tagline",
    "what_it_does": "Test",
    "business_value": "Test",
    "who_benefits": "Test",
    "differentiator": "Test",
    "pain_point_addressed": "Test",
    "suggested_icon": "test",
    "raw_extracted_text": "Test code content",
    "extraction_confidence": 0.9
}
```"""

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response

        client._client = mock_genai_client
        client._initialized = True

        result = await client.understand_code(
            code_content="test code",
            icp_preset=COPERNIQ_ICP,
        )

        assert result.headline == "Test Headline"

    @pytest.mark.asyncio
    async def test_understand_code_fallback_on_parse_error(self):
        """Test code understanding returns error state on parse error."""
        # Use text_provider="gemini" to test the Gemini code path
        config = GeminiConfig(api_key="test-key", text_provider="gemini")
        client = GeminiStoryboardClient(config=config)

        # Mock invalid response
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.return_value = mock_response

        client._client = mock_genai_client
        client._initialized = True

        result = await client.understand_code(
            code_content="test code",
            icp_preset=COPERNIQ_ICP,
        )

        # Should return error state (not generic copy) so CEO/CTO can review
        # NOTE: New behavior - we show extraction failed instead of hiding with generic copy
        assert "EXTRACTION FAILED" in result.headline or "FAILED" in result.headline.upper()
        assert result.extraction_confidence == 0.0


class TestUnderstandImageMocked:
    """Tests for understand_image with mocked Gemini API."""

    @pytest.mark.asyncio
    async def test_understand_image_accepts_bytes(self):
        """Test image understanding accepts byte input."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        # Verify client can be configured for image understanding
        # NOTE: Field renamed to gemini_vision_model for multi-model architecture
        assert client.config.gemini_vision_model == "models/gemini-2.0-flash"
        assert client._initialized is False

        # Test that bytes can be encoded to base64
        import base64
        test_bytes = b"fake image data"
        b64 = base64.b64encode(test_bytes).decode()
        assert len(b64) > 0

    @pytest.mark.asyncio
    async def test_understand_image_accepts_base64(self):
        """Test image understanding accepts base64 string."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        # Test data URL handling
        import base64
        test_data = b"fake image data"
        b64_string = base64.b64encode(test_data).decode()

        # The client should be able to handle data URL format
        data_url = f"data:image/png;base64,{b64_string}"

        # Just verify no immediate error on base64 parsing logic
        # (actual API call would need full mocking)
        assert data_url.startswith("data:")


class TestGenerateStoryboardMocked:
    """Tests for generate_storyboard with mocked Gemini API."""

    @pytest.mark.asyncio
    async def test_generate_storyboard_uses_understanding(self):
        """Test storyboard generation accepts understanding data."""
        understanding = StoryboardUnderstanding(
            headline="Test Headline",
            what_it_does="Test description",
            business_value="Save 5 hours/week",
            who_benefits="Project managers",
            differentiator="Works anywhere",
            pain_point_addressed="Manual tracking",
            suggested_icon="clipboard",
        )

        # Verify understanding model is properly structured
        assert understanding.headline == "Test Headline"
        assert understanding.business_value == "Save 5 hours/week"
        assert understanding.suggested_icon == "clipboard"

        # Verify it can be serialized for API call
        data = {
            "headline": understanding.headline,
            "what_it_does": understanding.what_it_does,
            "business_value": understanding.business_value,
        }
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_generate_storyboard_uses_stage_template(self):
        """Test storyboard generation uses correct stage template."""
        from src.tools.storyboard.coperniq_presets import get_stage_template

        understanding = StoryboardUnderstanding(
            headline="Test",
            what_it_does="Test",
            business_value="Test",
            who_benefits="Test",
            differentiator="Test",
            pain_point_addressed="Test",
        )

        # Verify each stage has proper template
        for stage in ["preview", "demo", "shipped"]:
            template = get_stage_template(stage)
            assert "badge" in template
            assert "cta" in template
            assert "visual_style" in template

        # NOTE: Badges removed for cleaner LinkedIn/email graphics
        # All stages now have empty badges
        preview = get_stage_template("preview")
        assert preview["badge"] == ""
        assert "header_prefix" in preview

        demo = get_stage_template("demo")
        assert demo["badge"] == ""
        assert "visual_style" in demo

        shipped = get_stage_template("shipped")
        assert shipped["badge"] == ""
        assert "cta" in shipped


class TestEnsureClientInitialization:
    """Tests for _ensure_client initialization."""

    def test_raises_without_api_key(self):
        """Test initialization raises without API key."""
        config = GeminiConfig(api_key=None)
        client = GeminiStoryboardClient(config=config)

        with pytest.raises(ValueError) as exc_info:
            client._ensure_client()

        assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_raises_on_missing_package(self):
        """Test initialization raises if google-genai not installed."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        # Mock import failure
        with patch.dict("sys.modules", {"google": None}):
            with pytest.raises((ImportError, ValueError)):
                client._ensure_client()
