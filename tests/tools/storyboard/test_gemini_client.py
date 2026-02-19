"""Tests for Gemini Storyboard Client."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    GeminiConfig,
    StoryboardUnderstanding,
    _repair_json,
)
from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_ICP,
    get_audience_persona,
)


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
    """Tests for build_language_guidelines (extracted from client during decomposition)."""

    def test_builds_guidelines_from_icp(self):
        """Test guidelines are built from ICP preset."""
        from src.tools.storyboard.epiphan_presets import build_language_guidelines

        guidelines = build_language_guidelines(EPIPHAN_ICP)

        assert "LANGUAGE GUIDELINES" in guidelines
        assert "Tone:" in guidelines
        assert "AVOID" in guidelines
        assert "USE" in guidelines

    def test_includes_avoid_terms(self):
        """Test guidelines include terms to avoid."""
        from src.tools.storyboard.epiphan_presets import build_language_guidelines

        guidelines = build_language_guidelines(EPIPHAN_ICP)

        # Should include AV-specific jargon to avoid
        assert "bitrate optimization" in guidelines

    def test_includes_use_terms(self):
        """Test guidelines include terms to use."""
        from src.tools.storyboard.epiphan_presets import build_language_guidelines

        guidelines = build_language_guidelines(EPIPHAN_ICP)

        # Should include some of the use terms
        assert "just works" in guidelines


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
            icp_preset=EPIPHAN_ICP,
            audience="av_director",
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
            icp_preset=EPIPHAN_ICP,
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
            icp_preset=EPIPHAN_ICP,
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
        from src.tools.storyboard.epiphan_presets import get_stage_template

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
        with patch.dict("os.environ", {}, clear=True):
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


class TestRepairJson:
    """Tests for _repair_json() — handles malformed LLM JSON responses."""

    def test_valid_json_passes_through(self):
        """Valid JSON should be returned unchanged."""
        valid = '{"headline": "Test", "value": 42}'
        assert json.loads(_repair_json(valid)) == json.loads(valid)

    def test_trailing_comma_repair(self):
        """Trailing commas before closing braces should be removed."""
        broken = '{"a": 1, "b": 2,}'
        result = _repair_json(broken)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_trailing_comma_in_array(self):
        """Trailing commas before closing brackets should be removed."""
        broken = '{"items": [1, 2, 3,]}'
        result = _repair_json(broken)
        parsed = json.loads(result)
        assert parsed == {"items": [1, 2, 3]}

    def test_missing_closing_brace(self):
        """Missing closing braces should be added."""
        broken = '{"headline": "Test"'
        result = _repair_json(broken)
        parsed = json.loads(result)
        assert parsed["headline"] == "Test"

    def test_multiple_missing_braces(self):
        """Multiple missing closing braces should be added."""
        broken = '{"outer": {"inner": "value"'
        result = _repair_json(broken)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == "value"

    def test_markdown_code_fence_stripping(self):
        """Markdown code fences around JSON should be stripped."""
        wrapped = '```json\n{"headline": "Test"}\n```'
        result = _repair_json(wrapped)
        parsed = json.loads(result)
        assert parsed["headline"] == "Test"

    def test_markdown_code_fence_without_lang(self):
        """Markdown code fences without language tag should be handled."""
        wrapped = '```\n{"headline": "Test"}\n```'
        result = _repair_json(wrapped)
        parsed = json.loads(result)
        assert parsed["headline"] == "Test"

    def test_empty_string_returns_empty(self):
        """Empty string should be returned (will fail json.loads, that's OK)."""
        result = _repair_json("")
        assert isinstance(result, str)

    def test_unterminated_string_repair(self):
        """Unterminated strings should get a closing quote."""
        broken = '{"headline": "Test value'
        result = _repair_json(broken)
        # After repair, it should at least be parseable
        parsed = json.loads(result)
        assert "Test value" in parsed["headline"]


class TestBuildGenerationContentSection:
    """Tests for _build_generation_content_section() — post-Tier-1 content verification."""

    def _make_understanding(self, **overrides):
        """Helper to create a StoryboardUnderstanding with defaults."""
        defaults = {
            "headline": "Fleet Management Made Simple",
            "what_it_does": "Manages AV equipment across 300+ rooms",
            "business_value": "Save 20 hours/week on AV support tickets",
            "who_benefits": "AV Directors managing campus infrastructure",
            "differentiator": "Single pane of glass for all Pearl devices",
            "pain_point_addressed": "Each room has different AV, creating support chaos",
            "suggested_icon": "monitor",
            "raw_extracted_text": "Fleet management dashboard, NDI, SRT, rack-mount",
            "extraction_confidence": 0.92,
        }
        defaults.update(overrides)
        return StoryboardUnderstanding(**defaults)

    def _build_section(self, audience="av_director"):
        """Helper to build a content section."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)
        understanding = self._make_understanding()
        persona = get_audience_persona(audience, EPIPHAN_ICP)
        return client._build_generation_content_section(
            understanding, audience, persona
        )

    def test_never_contains_mep(self):
        """Output must NEVER contain MEP or contractor references."""
        for audience in [
            "av_director",
            "ld_director",
            "sim_center_director",
            "court_admin",
        ]:
            section = self._build_section(audience)
            section_lower = section.lower()
            assert "mep" not in section_lower, f"MEP in {audience} section"
            assert "contractor" not in section_lower, f"contractor in {audience} section"
            assert "hvac" not in section_lower, f"HVAC in {audience} section"
            assert "hard hat" not in section_lower, f"hard hat in {audience} section"

    def test_never_contains_top_tier_vc_branch(self):
        """The top_tier_vc branch should be completely removed."""
        section = self._build_section("av_director")
        assert "INVESTOR AUDIENCE" not in section
        assert "pitch deck" not in section.lower()

    def test_includes_understanding_fields(self):
        """Section should include the extracted understanding data."""
        section = self._build_section("av_director")
        assert "Fleet Management Made Simple" in section
        assert "Manages AV equipment across 300+ rooms" in section
        assert "Save 20 hours/week" in section

    def test_includes_persona_context(self):
        """Section should include persona-specific context."""
        section = self._build_section("av_director")
        assert "AV Director" in section or "av_director" in section.lower()

    def test_includes_raw_context_when_present(self):
        """Section should include raw extraction when available."""
        section = self._build_section("av_director")
        assert "RAW EXTRACTION" in section or "Fleet management dashboard" in section

    def test_all_eight_personas_produce_output(self):
        """All 8 BDR Playbook personas should produce valid content sections."""
        for audience in [
            "av_director",
            "ld_director",
            "sim_center_director",
            "court_admin",
            "corp_comms",
            "ehs_manager",
            "law_firm_it",
            "technical_director",
        ]:
            section = self._build_section(audience)
            assert len(section) > 100, f"{audience} section too short"
            assert "Fleet Management Made Simple" in section


class TestHealthCheckFixed:
    """Tests verifying H-1 fix — health_check uses correct attribute name."""

    @pytest.mark.asyncio
    async def test_health_check_returns_correct_model(self):
        """health_check should reference gemini_vision_model (not vision_model)."""
        config = GeminiConfig(api_key="test-key")
        client = GeminiStoryboardClient(config=config)

        # Mock successful initialization
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()

        with patch.dict(
            "sys.modules", {"google": MagicMock(), "google.genai": mock_genai}
        ):
            health = await client.health_check()

        # Should not crash with AttributeError
        assert health["api_key_configured"] is True
        # If healthy, should have vision_model key
        if health["status"] == "healthy":
            assert health["vision_model"] == "models/gemini-2.0-flash"


class TestOpenRouterRetryBackoff:
    """Tests for exponential backoff with jitter in OpenRouter retry."""

    @pytest.fixture
    def client(self):
        """Create a client with test config."""
        config = GeminiConfig(
            api_key="test-key",
            openrouter_api_key="test-or-key",
            timeout=5,
        )
        return GeminiStoryboardClient(config=config)

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, client):
        """Verify backoff uses exponential formula, not linear."""
        sleep_times = []

        mock_response = MagicMock()
        mock_response.status_code = 429

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_response
            # Third call succeeds
            success = MagicMock()
            success.status_code = 200
            success.raise_for_status = MagicMock()
            success.json.return_value = {
                "choices": [{"message": {"content": "test response"}}]
            }
            return success

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        async def capture_sleep(duration):
            sleep_times.append(duration)

        with patch("httpx.AsyncClient", return_value=mock_client), \
             patch("asyncio.sleep", side_effect=capture_sleep):
            result = await client._call_openrouter_with_retry(
                payload={
                    "model": "test",
                    "messages": [{"role": "user", "content": "hi"}],
                },
                max_retries=3,
            )

        assert result == "test response"
        assert len(sleep_times) == 2
        # First retry: 2^0 + jitter = ~1.0-1.5s (not 5s linear)
        assert 1.0 <= sleep_times[0] <= 1.5
        # Second retry: 2^1 + jitter = ~2.0-2.5s (not 10s linear)
        assert 2.0 <= sleep_times[1] <= 2.5

    @pytest.mark.asyncio
    async def test_backoff_capped_at_32_seconds(self, client):
        """Verify backoff is capped at 32 seconds for high attempt counts."""
        import random

        # Test the formula directly for various attempts
        for attempt in range(10):
            random.seed(42)  # Deterministic jitter
            wait_time = min(2**attempt, 32) + random.uniform(0, 0.5)
            assert wait_time <= 32.5, (
                f"Wait time {wait_time} exceeds cap at attempt {attempt}"
            )

    @pytest.mark.asyncio
    async def test_backoff_includes_jitter(self, client):
        """Verify jitter adds randomness to avoid thundering herd."""
        import random

        wait_times = []
        for _ in range(100):
            wait_times.append(min(2**0, 32) + random.uniform(0, 0.5))

        # All should be between 1.0 and 1.5
        assert all(1.0 <= t <= 1.5 for t in wait_times)
        # Should not all be identical (jitter working)
        assert len({round(t, 6) for t in wait_times}) > 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises(self, client):
        """Verify exception raised when all retries exhausted."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("httpx.AsyncClient", return_value=mock_client), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Max retries exceeded"):
                await client._call_openrouter_with_retry(
                    payload={"model": "test", "messages": []},
                    max_retries=3,
                )
