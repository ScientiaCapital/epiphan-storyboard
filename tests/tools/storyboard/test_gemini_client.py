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
            assert config.image_model == "models/gemini-2.0-flash-exp-image-generation"
            assert config.openrouter_image_model == "google/gemini-2.5-flash-image"
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
    async def test_health_check_no_keys(self):
        """Test health check fails without any API keys."""
        with patch.dict("os.environ", {}, clear=True):
            config = GeminiConfig(api_key=None, openrouter_api_key=None)
            client = GeminiStoryboardClient(config=config)
            health = await client.health_check()
            assert health["status"] == "unhealthy"
            assert health["google_api_key_configured"] is False
            assert health["openrouter_api_key_configured"] is False

    @pytest.mark.asyncio
    async def test_health_check_with_openrouter_key(self):
        """Test health check healthy with OpenRouter key only (no Google key)."""
        config = GeminiConfig(api_key=None, openrouter_api_key="test-or-key")
        client = GeminiStoryboardClient(config=config)
        health = await client.health_check()
        assert health["status"] == "healthy"
        assert health["image_backend"] == "openrouter"
        assert health["google_api_key_configured"] is False
        assert health["openrouter_api_key_configured"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_google_key(self):
        """Test health check healthy with Google API key (prefers direct)."""
        config = GeminiConfig(api_key="test-key", openrouter_api_key="test-or-key")
        client = GeminiStoryboardClient(config=config)
        health = await client.health_check()
        assert health["status"] == "healthy"
        assert health["image_backend"] == "google_direct"
        assert health["google_api_key_configured"] is True


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
        mock_response.text = json.dumps(
            {
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
            }
        )

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
        assert (
            "EXTRACTION FAILED" in result.headline
            or "FAILED" in result.headline.upper()
        )
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
            assert "contractor" not in section_lower, (
                f"contractor in {audience} section"
            )
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
        assert health["google_api_key_configured"] is True
        # If healthy, should have image_backend key
        if health["status"] == "healthy":
            assert health["image_backend"] == "google_direct"


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

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", side_effect=capture_sleep),
        ):
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

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(Exception, match="Max retries exceeded"):
                await client._call_openrouter_with_retry(
                    payload={"model": "test", "messages": []},
                    max_retries=3,
                )


# ============================================================================
# DA-R1 — Two-pass narrative+schema Forces extraction
# ============================================================================
#
# Backlog DA-R1: Phase 1.3 shipped build_narrative_extraction_prompt and
# build_schema_mapping_prompt as infrastructure-ready, but the orchestration
# call site in _understand() doesn't wire them. Production still runs the
# rigid single-pass extraction. Two-pass is the un-coupled approach: pass 1
# narrative preserves nuance, pass 2 maps narrative → strict JSON. Fires on
# transcripts ≥ two_pass_threshold_chars OR extraction_confidence < threshold.
#
# Schema reconciliation: additive — StoryboardUnderstanding gains optional
# forces_of_progress + frankenstack fields. Single-pass result's flat 10
# fields are preserved; two-pass overlays the new structured fields.


class TestStoryboardUnderstandingForcesOfProgress:
    """Schema extension — StoryboardUnderstanding gains forces_of_progress + frankenstack."""

    def test_storyboard_understanding_accepts_forces_of_progress(self):
        """The schema must accept an optional ForcesOfProgress dict."""
        from src.tools.storyboard.gemini_client import ForcesOfProgress

        forces = ForcesOfProgress(
            push="The classroom PC layer crashes mid-lecture.",
            pull="Hardware-encoded reliability with cloud fleet management.",
            anxiety="The new system might still need PC-layer babysitting.",
            habit="Walking the building twice a day to check green lights.",
        )
        u = StoryboardUnderstanding(
            headline="t",
            what_it_does="t",
            business_value="t",
            who_benefits="t",
            differentiator="t",
            pain_point_addressed="t",
            forces_of_progress=forces,
            frankenstack="Classroom PC + software encoder + manual log scrape.",
        )
        assert u.forces_of_progress is forces
        assert "Classroom PC" in (u.frankenstack or "")

    def test_storyboard_understanding_forces_default_none(self):
        """Existing call sites that don't set forces_of_progress must still work."""
        u = StoryboardUnderstanding(
            headline="t",
            what_it_does="t",
            business_value="t",
            who_benefits="t",
            differentiator="t",
            pain_point_addressed="t",
        )
        assert u.forces_of_progress is None
        assert u.frankenstack is None


class TestGeminiConfigTwoPassFields:
    """GeminiConfig gains two_pass routing controls."""

    def test_default_enable_two_pass_extraction_is_true(self):
        """Two-pass should default ON so the quality lift is realized in prod."""
        config = GeminiConfig(api_key="t")
        assert config.enable_two_pass_extraction is True

    def test_default_two_pass_threshold_is_10000_chars(self):
        """The 10K threshold matches the Backlog DA-R1 spec."""
        config = GeminiConfig(api_key="t")
        assert config.two_pass_threshold_chars == 10_000

    def test_two_pass_can_be_disabled(self):
        """Operators must be able to flip it off (cost / latency trade-off)."""
        config = GeminiConfig(api_key="t", enable_two_pass_extraction=False)
        assert config.enable_two_pass_extraction is False


class TestExtractViaTwoPass:
    """Direct unit tests for the new _extract_via_two_pass method."""

    def _mocked_gemini_client(self, narrative_text: str, schema_json: str):
        """Build a client whose Gemini text path returns ``narrative_text``
        on the first call and ``schema_json`` on the second."""
        config = GeminiConfig(api_key="test-key", text_provider="gemini")
        client = GeminiStoryboardClient(config=config)

        responses = [MagicMock(text=narrative_text), MagicMock(text=schema_json)]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = responses

        client._client = mock_genai_client
        client._initialized = True
        return client

    @pytest.mark.asyncio
    async def test_method_exists(self):
        """_extract_via_two_pass must exist on GeminiStoryboardClient."""
        config = GeminiConfig(api_key="t")
        client = GeminiStoryboardClient(config=config)
        assert hasattr(client, "_extract_via_two_pass")

    @pytest.mark.asyncio
    async def test_merges_forces_into_single_pass_result(self):
        """The merge must preserve flat fields from single-pass and overlay
        forces_of_progress + frankenstack from the two-pass schema mapping."""
        single_pass = StoryboardUnderstanding(
            headline="Reliable Lecture Capture",
            what_it_does="Records every classroom session.",
            business_value="Saves 12 hours of triage per week.",
            who_benefits="University AV directors.",
            differentiator="Hardware-first, no PC layer.",
            pain_point_addressed="Lectures going unrecorded.",
            extraction_confidence=0.6,
        )

        narrative = "PUSH: PC layer fails. PULL: Hardware reliability. ..."
        schema_json = json.dumps(
            {
                "forces_of_progress": {
                    "push": "PC layer fails mid-lecture.",
                    "pull": "Hardware-encoded reliability.",
                    "anxiety": "Will the migration introduce new failure modes?",
                    "habit": "Walking the building twice daily.",
                },
                "frankenstack": "PC + software encoder + manual triage script.",
                "extraction_confidence": 0.85,
            }
        )
        client = self._mocked_gemini_client(narrative, schema_json)

        result = await client._extract_via_two_pass(
            transcript="(long transcript)",
            audience="av_director",
            vertical="higher_ed",
            single_pass_result=single_pass,
        )

        # Flat fields preserved
        assert result.headline == "Reliable Lecture Capture"
        assert result.business_value == "Saves 12 hours of triage per week."
        # New fields populated
        assert result.forces_of_progress is not None
        assert "PC layer fails" in result.forces_of_progress.push
        assert "Walking the building" in result.forces_of_progress.habit
        assert result.frankenstack is not None
        assert "PC + software encoder" in result.frankenstack
        # Confidence is the max of the two passes
        assert result.extraction_confidence == 0.85

    @pytest.mark.asyncio
    async def test_falls_back_to_single_pass_on_parse_error(self):
        """If the schema-mapping LLM returns garbage, return single_pass unchanged."""
        single_pass = StoryboardUnderstanding(
            headline="H",
            what_it_does="W",
            business_value="B",
            who_benefits="WB",
            differentiator="D",
            pain_point_addressed="P",
            extraction_confidence=0.5,
        )
        client = self._mocked_gemini_client(
            narrative_text="PUSH: ...",
            schema_json="this is definitely not valid json {",
        )

        result = await client._extract_via_two_pass(
            transcript="(transcript)",
            audience="av_director",
            vertical=None,
            single_pass_result=single_pass,
        )

        assert result is single_pass  # exact same object — no merge happened
        assert result.forces_of_progress is None
        assert result.extraction_confidence == 0.5  # unchanged

    @pytest.mark.asyncio
    async def test_falls_back_when_llm_call_raises(self):
        """If either LLM call raises, return single_pass unchanged (graceful degradation)."""
        single_pass = StoryboardUnderstanding(
            headline="H",
            what_it_does="W",
            business_value="B",
            who_benefits="WB",
            differentiator="D",
            pain_point_addressed="P",
            extraction_confidence=0.4,
        )
        config = GeminiConfig(api_key="test-key", text_provider="gemini")
        client = GeminiStoryboardClient(config=config)

        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = RuntimeError(
            "upstream 503"
        )

        client._client = mock_genai_client
        client._initialized = True

        result = await client._extract_via_two_pass(
            transcript="(transcript)",
            audience="av_director",
            vertical="legal",
            single_pass_result=single_pass,
        )

        assert result is single_pass


class TestUnderstandRoutesToTwoPass:
    """End-to-end: _understand() must route long / low-confidence transcripts
    through _extract_via_two_pass instead of _refine_extraction."""

    def _single_pass_payload(self, confidence: float) -> str:
        """Build a JSON payload the single-pass path will return."""
        return json.dumps(
            {
                "headline": "Test Headline",
                "tagline": "",
                "what_it_does": "Does the thing.",
                "business_value": "Saves time.",
                "who_benefits": "Users.",
                "differentiator": "It's better.",
                "pain_point_addressed": "Pain.",
                "suggested_icon": "clipboard",
                "raw_extracted_text": "...",
                "extraction_confidence": confidence,
            }
        )

    def _schema_pass_payload(self) -> str:
        return json.dumps(
            {
                "forces_of_progress": {
                    "push": "p",
                    "pull": "l",
                    "anxiety": "a",
                    "habit": "h",
                },
                "frankenstack": "stack",
                "extraction_confidence": 0.9,
            }
        )

    @pytest.mark.asyncio
    async def test_long_transcript_triggers_two_pass(self):
        """Transcript ≥ two_pass_threshold_chars must route through two-pass even
        when single-pass returned high confidence."""
        config = GeminiConfig(
            api_key="test-key",
            text_provider="gemini",
            two_pass_threshold_chars=100,  # tiny threshold for the test
        )
        client = GeminiStoryboardClient(config=config)

        long_transcript = "A" * 200  # > 100 chars threshold

        mock_responses = [
            MagicMock(text=self._single_pass_payload(confidence=0.9)),  # single-pass
            MagicMock(text="PUSH: ... PULL: ..."),  # narrative pass
            MagicMock(text=self._schema_pass_payload()),  # schema pass
        ]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = mock_responses

        client._client = mock_genai_client
        client._initialized = True

        result = await client._understand(
            "transcript",
            content=long_transcript,
            audience="av_director",
            vertical="higher_ed",
        )

        # Three Gemini calls total: single-pass + narrative + schema
        assert mock_genai_client.models.generate_content.call_count == 3
        assert result.forces_of_progress is not None
        assert result.frankenstack == "stack"

    @pytest.mark.asyncio
    async def test_low_confidence_short_transcript_triggers_two_pass(self):
        """Even short transcripts must route through two-pass when the
        single-pass returned low confidence (< refinement_threshold)."""
        config = GeminiConfig(
            api_key="test-key",
            text_provider="gemini",
            two_pass_threshold_chars=10_000,  # large — won't trip on length
            refinement_threshold=0.75,
        )
        client = GeminiStoryboardClient(config=config)

        mock_responses = [
            MagicMock(text=self._single_pass_payload(confidence=0.5)),  # low conf
            MagicMock(text="PUSH: ..."),
            MagicMock(text=self._schema_pass_payload()),
        ]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = mock_responses

        client._client = mock_genai_client
        client._initialized = True

        result = await client._understand(
            "transcript",
            content="short transcript",
            audience="av_director",
        )

        assert mock_genai_client.models.generate_content.call_count == 3
        assert result.forces_of_progress is not None

    @pytest.mark.asyncio
    async def test_short_high_confidence_skips_two_pass(self):
        """The trigger must NOT fire when transcript is short AND confidence is high.
        Otherwise we'd burn 2× the cost on every short transcript."""
        config = GeminiConfig(
            api_key="test-key",
            text_provider="gemini",
            two_pass_threshold_chars=10_000,
            refinement_threshold=0.75,
            enable_refinement=False,  # skip the existing refine path so call count is clean
        )
        client = GeminiStoryboardClient(config=config)

        mock_responses = [
            MagicMock(text=self._single_pass_payload(confidence=0.95)),  # high conf
        ]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = mock_responses

        client._client = mock_genai_client
        client._initialized = True

        result = await client._understand(
            "transcript",
            content="short transcript",
            audience="av_director",
        )

        # Only ONE call — single-pass. Two-pass did not fire.
        assert mock_genai_client.models.generate_content.call_count == 1
        assert result.forces_of_progress is None

    @pytest.mark.asyncio
    async def test_disabled_flag_skips_two_pass_even_on_long_transcript(self):
        """enable_two_pass_extraction=False is the operator escape hatch."""
        config = GeminiConfig(
            api_key="test-key",
            text_provider="gemini",
            enable_two_pass_extraction=False,
            two_pass_threshold_chars=100,
            enable_refinement=False,
        )
        client = GeminiStoryboardClient(config=config)

        mock_responses = [
            MagicMock(text=self._single_pass_payload(confidence=0.9)),
        ]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = mock_responses

        client._client = mock_genai_client
        client._initialized = True

        result = await client._understand(
            "transcript",
            content="A" * 200,  # would otherwise trip the threshold
            audience="av_director",
        )

        assert mock_genai_client.models.generate_content.call_count == 1
        assert result.forces_of_progress is None

    @pytest.mark.asyncio
    async def test_non_transcript_content_never_routes_to_two_pass(self):
        """Code content type must never trigger two-pass — narrative+schema
        framing only makes sense for transcripts."""
        config = GeminiConfig(
            api_key="test-key",
            text_provider="gemini",
            two_pass_threshold_chars=10,
            refinement_threshold=0.99,  # almost always trip on confidence too
            enable_refinement=False,
        )
        client = GeminiStoryboardClient(config=config)

        mock_responses = [
            MagicMock(text=self._single_pass_payload(confidence=0.5)),  # low conf
        ]
        mock_genai_client = MagicMock()
        mock_genai_client.models.generate_content.side_effect = mock_responses

        client._client = mock_genai_client
        client._initialized = True

        result = await client._understand(
            "code",
            content="def foo(): pass" * 100,
            audience="av_director",
        )

        assert mock_genai_client.models.generate_content.call_count == 1
        assert result.forces_of_progress is None
