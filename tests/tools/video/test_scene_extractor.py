"""Tests for SceneExtractorTool."""

import json

import pytest
from unittest.mock import AsyncMock, patch

from src.tools.video.scene_extractor import SceneExtractorTool
from src.tools.base import ToolCategory, BaseTool
from src.tools.video.demo_pipeline_schemas import DemoSceneType, SceneTemplate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_UNDERSTANDING = {
    "headline": "Automate Lecture Capture Across 300 Rooms",
    "pain_point_addressed": "Faculty refuse to use complex AV gear",
    "business_value": "90% adoption rate with one-button recording",
    "what_it_does": "Records, streams, and encodes lectures automatically",
    "who_benefits": "AV directors managing campus-wide deployments",
    "differentiator": "Hardware encoding with centralized cloud management",
}

SAMPLE_LLM_RESPONSE = json.dumps(
    {
        "scenes": [
            {
                "scene_type": "intro",
                "video_prompt": "Professional office with a wide establishing shot of a university campus lecture hall, soft natural lighting.",
                "talking_points": ["Universities need scalable AV"],
                "visual_description": "An expansive lecture hall with students",
            },
            {
                "scene_type": "pain_point",
                "video_prompt": "Close-up of a frustrated professor struggling with tangled cables and a blinking AV rack in a dimly lit room.",
                "talking_points": ["Faculty avoid complex AV setups"],
                "visual_description": "A professor fumbling with wires at a podium",
            },
            {
                "scene_type": "solution",
                "video_prompt": "Medium shot of a Pearl Mini mounted in a sleek AV rack, green status LEDs glowing, camera panning smoothly.",
                "talking_points": ["One-button recording with Pearl Mini"],
                "visual_description": "Pearl Mini device in a tidy rack",
            },
            {
                "scene_type": "differentiation",
                "video_prompt": "Split-screen comparison showing hardware encoding performance versus software alternatives on a monitor.",
                "talking_points": ["Hardware encoding beats software solutions"],
                "visual_description": "Side-by-side performance comparison on screen",
            },
            {
                "scene_type": "results",
                "video_prompt": "Dashboard screen showing 90% adoption metrics, camera slowly zooming in on green success indicators.",
                "talking_points": ["90% faculty adoption achieved"],
                "visual_description": "Analytics dashboard with success metrics",
            },
            {
                "scene_type": "cta",
                "video_prompt": "Professional presenter gesturing toward an Epiphan Video logo on a large screen, warm studio lighting.",
                "talking_points": ["Schedule your demo today"],
                "visual_description": "Presenter with Epiphan branding",
            },
        ]
    }
)


class TestSceneExtractorDefinition:
    def test_definition_name(self):
        tool = SceneExtractorTool()
        assert tool.definition.name == "scene_extractor"

    def test_definition_category(self):
        tool = SceneExtractorTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_inherits_from_base_tool(self):
        tool = SceneExtractorTool()
        assert isinstance(tool, BaseTool)

    def test_requires_approval_is_false(self):
        tool = SceneExtractorTool()
        assert tool.definition.requires_approval is False


class TestSceneExtractorResolvers:
    def test_resolve_persona_valid_key(self):
        tool = SceneExtractorTool()
        result = tool._resolve_persona("av_director")
        assert isinstance(result, dict)

    def test_resolve_persona_invalid_key_falls_back(self):
        tool = SceneExtractorTool()
        result = tool._resolve_persona("nonexistent_persona_xyz")
        expected = tool._resolve_persona("av_director")
        assert result == expected

    def test_resolve_vertical_valid_key(self):
        tool = SceneExtractorTool()
        result = tool._resolve_vertical("higher_ed")
        assert isinstance(result, dict)
        assert "name" in result

    def test_resolve_vertical_invalid_key_falls_back(self):
        tool = SceneExtractorTool()
        result = tool._resolve_vertical("nonexistent_vertical_xyz")
        expected = tool._resolve_vertical("higher_ed")
        assert result == expected

    def test_resolve_product_valid_key(self):
        tool = SceneExtractorTool()
        result = tool._resolve_product("pearl_mini")
        assert isinstance(result, dict)
        assert "name" in result

    def test_resolve_product_invalid_key_falls_back(self):
        tool = SceneExtractorTool()
        result = tool._resolve_product("nonexistent_product_xyz")
        expected = tool._resolve_product("pearl_mini")
        assert result == expected


class TestSceneExtractorPromptBuild:
    def test_build_prompt_contains_headline(self):
        tool = SceneExtractorTool()
        persona_data = tool._resolve_persona("av_director")
        vertical_data = tool._resolve_vertical("higher_ed")
        product_data = tool._resolve_product("pearl_mini")
        prompt = tool._build_prompt(
            SAMPLE_UNDERSTANDING, persona_data, vertical_data, product_data
        )
        assert SAMPLE_UNDERSTANDING["headline"] in prompt

    def test_build_prompt_contains_product_name(self):
        tool = SceneExtractorTool()
        persona_data = tool._resolve_persona("av_director")
        vertical_data = tool._resolve_vertical("higher_ed")
        product_data = tool._resolve_product("pearl_mini")
        prompt = tool._build_prompt(
            SAMPLE_UNDERSTANDING, persona_data, vertical_data, product_data
        )
        assert "Pearl Mini" in prompt

    def test_build_prompt_contains_vertical_pain_points(self):
        tool = SceneExtractorTool()
        persona_data = tool._resolve_persona("av_director")
        vertical_data = tool._resolve_vertical("higher_ed")
        product_data = tool._resolve_product("pearl_mini")
        prompt = tool._build_prompt(
            SAMPLE_UNDERSTANDING, persona_data, vertical_data, product_data
        )
        for pain_point in vertical_data.get("pain_points", []):
            assert pain_point in prompt


class TestSceneExtractorParsing:
    def test_parse_scenes_valid_json_returns_list(self):
        tool = SceneExtractorTool()
        scenes = tool._parse_scenes(SAMPLE_LLM_RESPONSE)
        assert isinstance(scenes, list)
        assert all(isinstance(s, SceneTemplate) for s in scenes)

    def test_parse_scenes_returns_six_with_correct_types(self):
        tool = SceneExtractorTool()
        scenes = tool._parse_scenes(SAMPLE_LLM_RESPONSE)
        assert len(scenes) == 6
        expected_types = [
            DemoSceneType.INTRO,
            DemoSceneType.PAIN_POINT,
            DemoSceneType.SOLUTION,
            DemoSceneType.DIFFERENTIATION,
            DemoSceneType.RESULTS,
            DemoSceneType.CTA,
        ]
        actual_types = [s.scene_type for s in scenes]
        assert actual_types == expected_types

    def test_parse_scenes_invalid_json_raises_value_error(self):
        tool = SceneExtractorTool()
        with pytest.raises(ValueError, match="Failed to parse"):
            tool._parse_scenes("this is not valid json {{{")

    def test_parse_scenes_empty_scenes_raises_value_error(self):
        tool = SceneExtractorTool()
        with pytest.raises(ValueError, match="no scenes"):
            tool._parse_scenes(json.dumps({"scenes": []}))


class TestSceneExtractorRun:
    @pytest.mark.asyncio
    async def test_run_empty_understanding_returns_error(self):
        tool = SceneExtractorTool()
        result = await tool.run({"understanding": {}})
        assert result.success is False
        assert "understanding" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_with_mocked_llm_returns_success(self):
        tool = SceneExtractorTool()
        tool._call_llm = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)
        result = await tool.run(
            {
                "understanding": SAMPLE_UNDERSTANDING,
                "persona": "av_director",
                "vertical": "higher_ed",
                "product_focus": "pearl_mini",
            }
        )
        assert result.success is True
        assert result.result is not None
        assert "scenes" in result.result
        assert len(result.result["scenes"]) == 6
        tool._call_llm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_with_llm_error_returns_failed(self):
        tool = SceneExtractorTool()
        tool._call_llm = AsyncMock(side_effect=RuntimeError("API timeout"))
        result = await tool.run(
            {
                "understanding": SAMPLE_UNDERSTANDING,
                "persona": "av_director",
                "vertical": "higher_ed",
                "product_focus": "pearl_mini",
            }
        )
        assert result.success is False
        assert "API timeout" in result.error
