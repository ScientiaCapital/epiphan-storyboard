"""Tests for Epiphan ICP presets and sanitization."""

import pytest
import re

from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_ICP,
    SANITIZE_RULES,
    AudiencePersona,
    StoryboardStage,
    STAGE_TEMPLATES,
    get_icp_preset,
    get_audience_persona,
    get_stage_template,
    sanitize_content,
    build_language_guidelines,
)


class TestEpiphanICPStructure:
    """Tests for Epiphan ICP configuration structure."""

    def test_icp_has_name(self):
        """ICP preset should have a name."""
        assert "name" in EPIPHAN_ICP
        assert EPIPHAN_ICP["name"] == "epiphan_av"

    def test_icp_has_target(self):
        """ICP should define target audience."""
        assert "target" in EPIPHAN_ICP
        assert "ATL decision-makers" in EPIPHAN_ICP["target"]

    def test_icp_has_characteristics(self):
        """ICP should have characteristics section."""
        assert "characteristics" in EPIPHAN_ICP
        chars = EPIPHAN_ICP["characteristics"]
        assert "verticals" in chars
        assert "style" in chars
        assert "pain_points" in chars

    def test_icp_has_audience_personas(self):
        """ICP should have all 11 personas (8 original + 3 Higher Ed executive)."""
        assert "audience_personas" in EPIPHAN_ICP
        personas = EPIPHAN_ICP["audience_personas"]
        # ATL personas (7 from BDR Playbook)
        assert AudiencePersona.AV_DIRECTOR in personas
        assert AudiencePersona.LD_DIRECTOR in personas
        assert AudiencePersona.SIM_CENTER_DIRECTOR in personas
        assert AudiencePersona.COURT_ADMIN in personas
        assert AudiencePersona.CORP_COMMS in personas
        assert AudiencePersona.EHS_MANAGER in personas
        assert AudiencePersona.LAW_FIRM_IT in personas
        # ATL personas (3 Higher Ed executive)
        assert AudiencePersona.PROVOST in personas
        assert AudiencePersona.UNIVERSITY_PRESIDENT in personas
        assert AudiencePersona.UNIVERSITY_FINANCE in personas
        # BTL persona (1 from BDR Playbook)
        assert AudiencePersona.TECHNICAL_DIRECTOR in personas
        assert len(personas) == 11

    def test_icp_has_language_style(self):
        """ICP should have language style guidelines."""
        assert "language_style" in EPIPHAN_ICP
        style = EPIPHAN_ICP["language_style"]
        assert "avoid" in style
        assert "use" in style
        assert len(style["avoid"]) > 0
        assert len(style["use"]) > 0

    def test_icp_has_tone(self):
        """ICP should define tone."""
        assert "tone" in EPIPHAN_ICP
        assert len(EPIPHAN_ICP["tone"]) > 0

    def test_icp_has_visual_style(self):
        """ICP should have visual style guidelines."""
        assert "visual_style" in EPIPHAN_ICP
        visual = EPIPHAN_ICP["visual_style"]
        assert "colors" in visual
        assert len(visual["colors"]) > 0


class TestLanguageStyleRules:
    """Tests for language style avoid/use rules."""

    def test_avoid_contains_technical_jargon(self):
        """Avoid list should contain technical jargon that confuses AV buyers."""
        avoid = EPIPHAN_ICP["language_style"]["avoid"]
        technical_terms = ["synergy", "paradigm", "holistic"]
        for term in technical_terms:
            assert term in avoid, f"'{term}' should be in avoid list"

    def test_avoid_contains_corporate_speak(self):
        """Avoid list should contain marketing fluff."""
        avoid = EPIPHAN_ICP["language_style"]["avoid"]
        corporate_terms = ["revolutionary", "disruptive", "game-changing"]
        for term in corporate_terms:
            assert term in avoid, f"'{term}' should be in avoid list"

    def test_use_contains_simple_language(self):
        """Use list should contain simple, benefit-focused language."""
        use = EPIPHAN_ICP["language_style"]["use"]
        simple_phrases = ["just works", "reliable every time"]
        for phrase in simple_phrases:
            assert phrase in use, f"'{phrase}' should be in use list"

    def test_no_openai_in_avoid_list(self):
        """OpenAI should not be explicitly mentioned (we just don't use it)."""
        avoid = EPIPHAN_ICP["language_style"]["avoid"]
        # We avoid "AI" as a term, but don't call out OpenAI specifically
        assert "OpenAI" not in avoid


class TestAudiencePersonas:
    """Tests for audience persona configurations."""

    def test_av_director_persona(self):
        """AV director persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.AV_DIRECTOR]
        assert persona["title"] == "AV Director"
        assert persona["persona_type"] == "ATL"
        assert "system reliability" in persona["cares_about"]
        assert "hooks" in persona

    def test_ld_director_persona(self):
        """L&D director persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.LD_DIRECTOR]
        assert persona["title"] == "L&D Director"
        assert persona["persona_type"] == "ATL"
        assert "training content quality" in persona["cares_about"]

    def test_sim_center_director_persona(self):
        """Sim center director persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.SIM_CENTER_DIRECTOR]
        assert persona["title"] == "Simulation Center Director"
        assert "HIPAA compliance" in persona["cares_about"]

    def test_court_admin_persona(self):
        """Court admin persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.COURT_ADMIN]
        assert persona["title"] == "Court Administrator"
        assert persona["persona_type"] == "ATL"
        assert "record integrity" in persona["cares_about"]

    def test_ehs_manager_persona(self):
        """EHS manager persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.EHS_MANAGER]
        assert "EHS" in persona["title"]
        assert "OSHA compliance" in persona["cares_about"]

    def test_provost_persona(self):
        """Provost persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.PROVOST]
        assert "Provost" in persona["title"]
        assert persona["persona_type"] == "ATL"
        assert "higher_ed" in persona["verticals"]
        assert "student outcomes" in persona["cares_about"]
        assert persona["value_angle"] == "ROI"

    def test_university_president_persona(self):
        """University president persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.UNIVERSITY_PRESIDENT]
        assert "President" in persona["title"]
        assert persona["persona_type"] == "ATL"
        assert "higher_ed" in persona["verticals"]
        assert "institutional reputation" in persona["cares_about"]
        assert persona["value_angle"] == "ROI"

    def test_university_finance_persona(self):
        """University finance persona should have required fields."""
        persona = EPIPHAN_ICP["audience_personas"][AudiencePersona.UNIVERSITY_FINANCE]
        assert "Finance" in persona["title"] or "CFO" in persona["title"]
        assert persona["persona_type"] == "ATL"
        assert "higher_ed" in persona["verticals"]
        assert "total cost of ownership" in persona["cares_about"]
        assert persona["value_angle"] == "ROI"

    def test_all_personas_have_required_fields(self):
        """Every persona should have the required fields."""
        required_fields = ["title", "persona_type", "cares_about", "tone", "hooks",
                          "voice_tone", "vocabulary", "forbidden_phrases", "default_visual_style"]
        for persona_key, persona in EPIPHAN_ICP["audience_personas"].items():
            for field in required_fields:
                assert field in persona, f"Persona {persona_key} missing '{field}'"


class TestSanitizeRules:
    """Tests for sanitization rule structure."""

    def test_has_remove_rules(self):
        """Sanitize rules should have remove section."""
        assert "remove" in SANITIZE_RULES
        assert len(SANITIZE_RULES["remove"]) > 0

    def test_has_keep_rules(self):
        """Sanitize rules should have keep section."""
        assert "keep" in SANITIZE_RULES
        assert len(SANITIZE_RULES["keep"]) > 0

    def test_has_transform_rules(self):
        """Sanitize rules should have transform section."""
        assert "transform" in SANITIZE_RULES
        assert len(SANITIZE_RULES["transform"]) > 0

    def test_remove_contains_code_internals(self):
        """Remove list should include code internals."""
        remove = SANITIZE_RULES["remove"]
        code_items = ["class names", "function names", "variable names"]
        for item in code_items:
            assert item in remove, f"'{item}' should be in remove list"

    def test_remove_contains_security_items(self):
        """Remove list should include security-sensitive items."""
        remove = SANITIZE_RULES["remove"]
        security_items = ["API keys", "passwords", "secrets"]
        for item in security_items:
            assert item in remove, f"'{item}' should be in remove list"

    def test_keep_contains_business_value(self):
        """Keep list should include business value items."""
        keep = SANITIZE_RULES["keep"]
        business_items = ["business outcome", "user benefit", "time saved"]
        for item in business_items:
            assert item in keep, f"'{item}' should be in keep list"


class TestStageTemplates:
    """Tests for stage template configurations."""

    def test_preview_stage_exists(self):
        """Preview stage template should exist."""
        assert StoryboardStage.PREVIEW in STAGE_TEMPLATES

    def test_demo_stage_exists(self):
        """Demo stage template should exist."""
        assert StoryboardStage.DEMO in STAGE_TEMPLATES

    def test_shipped_stage_exists(self):
        """Shipped stage template should exist."""
        assert StoryboardStage.SHIPPED in STAGE_TEMPLATES

    def test_stage_template_has_required_fields(self):
        """All stage templates should have required fields."""
        required_fields = ["header_prefix", "tone_modifier", "cta", "visual_style", "badge"]
        for stage, template in STAGE_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Stage {stage} missing '{field}'"

    def test_preview_stage_is_professional(self):
        """Preview stage should be professional (no badges for LinkedIn/email)."""
        template = STAGE_TEMPLATES[StoryboardStage.PREVIEW]
        # NOTE: Badge is now empty - we removed badges for cleaner marketing graphics
        assert template["badge"] == ""
        assert "header_prefix" in template


class TestGetICPPreset:
    """Tests for get_icp_preset function."""

    def test_get_epiphan_preset(self):
        """Should return Epiphan preset."""
        preset = get_icp_preset("epiphan_av")
        assert preset["name"] == "epiphan_av"

    def test_get_default_preset(self):
        """Default should be epiphan_av."""
        preset = get_icp_preset()
        assert preset["name"] == "epiphan_av"

    def test_invalid_preset_raises_error(self):
        """Invalid preset name should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_icp_preset("invalid_preset")
        assert "Unknown ICP preset" in str(exc_info.value)


class TestGetAudiencePersona:
    """Tests for get_audience_persona function."""

    def test_get_av_director_persona(self):
        """Should return AV director persona (default)."""
        persona = get_audience_persona(AudiencePersona.AV_DIRECTOR)
        assert persona["title"] == "AV Director"

    def test_get_persona_by_string(self):
        """Should accept string value."""
        persona = get_audience_persona("ld_director")
        assert "L&D Director" in persona["title"]

    def test_get_court_admin_persona(self):
        """Should return court admin persona."""
        persona = get_audience_persona(AudiencePersona.COURT_ADMIN)
        assert "Court Administrator" in persona["title"]

    def test_unknown_persona_falls_back_to_av_director(self):
        """Unknown persona string should fall back to AV Director."""
        persona = get_audience_persona("nonexistent_persona")
        assert persona["title"] == "AV Director"


class TestGetStageTemplate:
    """Tests for get_stage_template function."""

    def test_get_preview_template(self):
        """Should return preview template with no badge."""
        template = get_stage_template(StoryboardStage.PREVIEW)
        # NOTE: Badges removed for cleaner LinkedIn/email graphics
        assert template["badge"] == ""
        assert "header_prefix" in template

    def test_get_demo_template(self):
        """Should return demo template with no badge."""
        template = get_stage_template(StoryboardStage.DEMO)
        # NOTE: Badges removed for cleaner LinkedIn/email graphics
        assert template["badge"] == ""
        assert "visual_style" in template

    def test_get_template_by_string(self):
        """Should accept string value."""
        template = get_stage_template("shipped")
        # NOTE: Badges removed for cleaner LinkedIn/email graphics
        assert template["badge"] == ""
        assert "cta" in template


class TestSanitizeContent:
    """Tests for sanitize_content function."""

    def test_removes_import_statements(self):
        """Should remove Python import statements."""
        content = "import os\nfrom typing import Any\nprint('hello')"
        sanitized = sanitize_content(content)
        assert "import os" not in sanitized
        assert "from typing" not in sanitized

    def test_sanitizes_class_definitions(self):
        """Should sanitize class definitions."""
        content = "class MySecretClass:\n    pass"
        sanitized = sanitize_content(content)
        assert "MySecretClass" not in sanitized

    def test_sanitizes_function_definitions(self):
        """Should sanitize function definitions."""
        content = "def calculate_secret_algo(x):\n    return x"
        sanitized = sanitize_content(content)
        assert "calculate_secret_algo" not in sanitized

    def test_sanitizes_async_functions(self):
        """Should sanitize async function definitions."""
        content = "async def fetch_internal_data():\n    pass"
        sanitized = sanitize_content(content)
        assert "fetch_internal_data" not in sanitized

    def test_sanitizes_api_keys(self):
        """Should redact API keys."""
        content = 'API_KEY = "sk-secret123"\nSECRET_TOKEN = "abc"'
        sanitized = sanitize_content(content)
        assert "sk-secret123" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitizes_email_addresses(self):
        """Should redact email addresses."""
        content = "Contact: john@internal-company.com"
        sanitized = sanitize_content(content)
        assert "john@internal-company.com" not in sanitized
        assert "[email]" in sanitized

    def test_preserves_non_sensitive_content(self):
        """Should preserve non-sensitive content."""
        content = "This feature helps users save time."
        sanitized = sanitize_content(content)
        assert "save time" in sanitized


class TestBuildLanguageGuidelines:
    """Tests for build_language_guidelines function."""

    def test_includes_avoid_words(self):
        """Guidelines should include words to avoid."""
        guidelines = build_language_guidelines()
        assert "AVOID" in guidelines
        assert "bitrate optimization" in guidelines  # First AV jargon term is avoided

    def test_includes_use_words(self):
        """Guidelines should include words to use."""
        guidelines = build_language_guidelines()
        assert "USE" in guidelines
        assert "just works" in guidelines

    def test_includes_tone(self):
        """Guidelines should include tone."""
        guidelines = build_language_guidelines()
        assert "Tone" in guidelines

    def test_includes_5th_grader_rule(self):
        """Guidelines should mention 5th grader rule."""
        guidelines = build_language_guidelines()
        assert "5th grader" in guidelines


class TestAudiencePersonaEnum:
    """Tests for AudiencePersona enum."""

    def test_av_director_value(self):
        """AV director enum value (primary ATL)."""
        assert AudiencePersona.AV_DIRECTOR.value == "av_director"

    def test_all_11_personas_exist(self):
        """All 11 personas should be present in the enum (8 original + 3 Higher Ed executive)."""
        assert len(AudiencePersona) == 11
        expected = [
            "av_director", "ld_director", "sim_center_director", "court_admin",
            "corp_comms", "ehs_manager", "law_firm_it",
            "provost", "university_president", "university_finance",
            "technical_director",
        ]
        actual = [p.value for p in AudiencePersona]
        for val in expected:
            assert val in actual, f"Missing persona: {val}"

    def test_technical_director_value(self):
        """Technical director enum value (BTL)."""
        assert AudiencePersona.TECHNICAL_DIRECTOR.value == "technical_director"


class TestStoryboardStageEnum:
    """Tests for StoryboardStage enum."""

    def test_preview_value(self):
        """Preview stage enum value."""
        assert StoryboardStage.PREVIEW.value == "preview"

    def test_demo_value(self):
        """Demo stage enum value."""
        assert StoryboardStage.DEMO.value == "demo"

    def test_shipped_value(self):
        """Shipped stage enum value."""
        assert StoryboardStage.SHIPPED.value == "shipped"
