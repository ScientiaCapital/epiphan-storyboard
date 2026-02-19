"""Tests for VideoTemplateManagerTool."""

import pytest
from unittest.mock import patch, AsyncMock

from src.tools.video.video_template_manager import (
    VideoTemplateManagerTool,
    Industry,
    SceneType,
    INDUSTRY_PRESETS,
)
from src.tools.base import ToolCategory, BaseTool


class TestVideoTemplateManagerDefinition:
    """Tests for tool definition."""

    def test_definition_name(self):
        tool = VideoTemplateManagerTool()
        assert tool.definition.name == "video_template_manager"

    def test_definition_category(self):
        tool = VideoTemplateManagerTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_definition_has_parameters(self):
        tool = VideoTemplateManagerTool()
        params = tool.definition.parameters
        assert params["type"] == "object"
        assert "operation" in params["properties"]

    def test_inherits_from_base_tool(self):
        tool = VideoTemplateManagerTool()
        assert isinstance(tool, BaseTool)


class TestIndustryEnums:
    """Tests for Industry enum."""

    def test_solar_industry(self):
        assert Industry.SOLAR.value == "solar"

    def test_hvac_industry(self):
        assert Industry.HVAC.value == "hvac"

    def test_electrical_industry(self):
        assert Industry.ELECTRICAL.value == "electrical"

    def test_roofing_industry(self):
        assert Industry.ROOFING.value == "roofing"

    def test_mep_industry(self):
        assert Industry.MEP.value == "mep"

    def test_general_contractor_industry(self):
        assert Industry.GENERAL_CONTRACTOR.value == "general_contractor"


class TestSceneTypeEnums:
    """Tests for SceneType enum."""

    def test_intro_scene(self):
        assert SceneType.INTRO_SCENE.value == "intro_scene"

    def test_problem_scene(self):
        assert SceneType.PROBLEM_SCENE.value == "problem_scene"

    def test_solution_scene(self):
        assert SceneType.SOLUTION_SCENE.value == "solution_scene"

    def test_differentiation_scene(self):
        assert SceneType.DIFFERENTIATION_SCENE.value == "differentiation_scene"

    def test_results_scene(self):
        assert SceneType.RESULTS_SCENE.value == "results_scene"

    def test_cta_scene(self):
        assert SceneType.CTA_SCENE.value == "cta_scene"


class TestIndustryPresets:
    """Tests for industry presets."""

    def test_solar_preset_exists(self):
        assert Industry.SOLAR in INDUSTRY_PRESETS

    def test_hvac_preset_exists(self):
        assert Industry.HVAC in INDUSTRY_PRESETS

    def test_presets_have_pain_points(self):
        for industry, preset in INDUSTRY_PRESETS.items():
            assert "pain_points" in preset, f"{industry} missing pain_points"
            assert len(preset["pain_points"]) > 0

    def test_presets_have_key_features(self):
        for industry, preset in INDUSTRY_PRESETS.items():
            assert "key_features" in preset, f"{industry} missing key_features"

    def test_presets_have_roi_metrics(self):
        for industry, preset in INDUSTRY_PRESETS.items():
            assert "roi_metrics" in preset, f"{industry} missing roi_metrics"


class TestVideoTemplateManagerRun:
    """Tests for VideoTemplateManagerTool execution."""

    @pytest.mark.asyncio
    async def test_list_templates_operation(self):
        """Test listing available templates."""
        tool = VideoTemplateManagerTool()
        result = await tool.run({
            "operation": "list_templates",
        })

        assert result.success is True
        assert "templates" in result.result or "industries" in result.result

    @pytest.mark.asyncio
    async def test_customize_template_for_industry(self):
        """Test customizing template for specific industry."""
        tool = VideoTemplateManagerTool()
        result = await tool.run({
            "operation": "customize_template",
            "industry": "solar",
            "product_name": "SolarMax CRM",
            "prospect_segment": "residential installers",
        })

        # customize_template returns success with template_id and template
        assert result.success is True
        assert "template_id" in result.result
        assert "template" in result.result

    @pytest.mark.asyncio
    async def test_get_template_after_creation(self):
        """Test getting template after it was created."""
        tool = VideoTemplateManagerTool()

        # First create a template
        create_result = await tool.run({
            "operation": "customize_template",
            "industry": "hvac",
            "product_name": "TestCRM",
            "prospect_segment": "contractors",
        })
        assert create_result.success is True
        template_id = create_result.result["template_id"]

        # Now retrieve it
        get_result = await tool.run({
            "operation": "get_template",
            "template_id": template_id,
        })

        assert get_result.success is True
        assert "template" in get_result.result

    @pytest.mark.asyncio
    async def test_invalid_operation(self):
        """Test error for invalid operation."""
        tool = VideoTemplateManagerTool()
        result = await tool.run({
            "operation": "invalid_operation",
        })

        assert result.success is False

    @pytest.mark.asyncio
    async def test_missing_operation(self):
        """Test error when operation is missing."""
        tool = VideoTemplateManagerTool()
        result = await tool.run({})

        assert result.success is False


class TestTemplateBuilding:
    """Tests for template building functionality."""

    def test_model_id_is_deepseek(self):
        """Default model should be DeepSeek."""
        tool = VideoTemplateManagerTool()
        assert "deepseek" in tool.MODEL_ID.lower()

    def test_default_timeout(self):
        """Default timeout should be reasonable."""
        tool = VideoTemplateManagerTool()
        assert tool.DEFAULT_TIMEOUT >= 30
        assert tool.DEFAULT_TIMEOUT <= 120
