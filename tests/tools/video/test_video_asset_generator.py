"""Tests for VideoAssetGeneratorTool."""

import pytest
from unittest.mock import AsyncMock, patch

from src.tools.video.video_asset_generator import VideoAssetGeneratorTool
from src.tools.base import ToolCategory, BaseTool, ToolResult
from src.tools.video.demo_pipeline_schemas import (
    DemoSceneType,
    VideoAsset,
    VideoAssetBatchResult,
)


class TestVideoAssetGeneratorDefinition:
    def test_definition_name(self):
        tool = VideoAssetGeneratorTool()
        assert tool.definition.name == "video_asset_generator"

    def test_definition_category(self):
        tool = VideoAssetGeneratorTool()
        assert tool.definition.category == ToolCategory.DATA

    def test_inherits_from_base_tool(self):
        tool = VideoAssetGeneratorTool()
        assert isinstance(tool, BaseTool)

    def test_requires_approval_is_true(self):
        tool = VideoAssetGeneratorTool()
        assert tool.definition.requires_approval is True


class TestConvertToBatchFormat:
    def test_converts_scene_dicts_correctly(self):
        tool = VideoAssetGeneratorTool()
        scenes = [
            {
                "scene_type": "intro",
                "video_prompt": "Professional conference room",
                "duration_seconds": 5,
            },
            {
                "scene_type": "pain_point",
                "video_prompt": "Frustrated IT admin",
                "duration_seconds": 10,
            },
        ]
        result = tool._convert_to_batch_format(scenes)
        assert len(result) == 2
        assert result[0]["name"] == "intro"
        assert result[0]["prompt"] == "Professional conference room"
        assert result[0]["duration_seconds"] == 5
        assert result[1]["name"] == "pain_point"
        assert result[1]["prompt"] == "Frustrated IT admin"
        assert result[1]["duration_seconds"] == 10

    def test_empty_list_returns_empty_list(self):
        tool = VideoAssetGeneratorTool()
        result = tool._convert_to_batch_format([])
        assert result == []

    def test_uses_defaults_for_missing_fields(self):
        tool = VideoAssetGeneratorTool()
        scenes = [{}]
        result = tool._convert_to_batch_format(scenes)
        assert len(result) == 1
        assert result[0]["name"] == "unknown"
        assert result[0]["prompt"] == ""
        assert result[0]["duration_seconds"] == 5


class TestMapToVideoAssets:
    def test_maps_batch_results_to_video_assets(self):
        tool = VideoAssetGeneratorTool()
        original_scenes = [
            {
                "scene_type": "intro",
                "video_prompt": "Conference room",
                "duration_seconds": 5,
            },
        ]
        batch_data = {
            "scenes": [
                {
                    "scene_name": "intro",
                    "success": True,
                    "video_url": "https://example.com/intro.mp4",
                    "estimated_cost_usd": 0.05,
                },
            ],
        }
        result = tool._map_to_video_assets(original_scenes, batch_data, "kling")
        assert isinstance(result, VideoAssetBatchResult)
        assert len(result.assets) == 1
        asset = result.assets[0]
        assert isinstance(asset, VideoAsset)
        assert asset.scene_type == DemoSceneType.INTRO
        assert asset.scene_name == "intro"
        assert asset.video_url == "https://example.com/intro.mp4"
        assert asset.success is True
        assert asset.provider == "kling"

    def test_handles_mixed_success_failure(self):
        tool = VideoAssetGeneratorTool()
        original_scenes = [
            {"scene_type": "intro", "duration_seconds": 5},
            {"scene_type": "pain_point", "duration_seconds": 5},
        ]
        batch_data = {
            "scenes": [
                {
                    "scene_name": "intro",
                    "success": True,
                    "video_url": "https://example.com/intro.mp4",
                    "estimated_cost_usd": 0.05,
                },
                {
                    "scene_name": "pain_point",
                    "success": False,
                    "video_url": None,
                    "estimated_cost_usd": 0.0,
                    "error": "Generation timed out",
                },
            ],
        }
        result = tool._map_to_video_assets(original_scenes, batch_data, "kling")
        assert result.successful_scenes == 1
        assert result.failed_scenes == 1
        assert result.assets[0].success is True
        assert result.assets[1].success is False
        assert result.assets[1].error == "Generation timed out"

    def test_calculates_totals_correctly(self):
        tool = VideoAssetGeneratorTool()
        original_scenes = [
            {"scene_type": "intro", "duration_seconds": 5},
            {"scene_type": "solution", "duration_seconds": 5},
        ]
        batch_data = {
            "scenes": [
                {
                    "scene_name": "intro",
                    "success": True,
                    "video_url": "https://example.com/intro.mp4",
                    "estimated_cost_usd": 0.05,
                },
                {
                    "scene_name": "solution",
                    "success": True,
                    "video_url": "https://example.com/solution.mp4",
                    "estimated_cost_usd": 0.07,
                },
            ],
        }
        result = tool._map_to_video_assets(original_scenes, batch_data, "kling")
        assert result.total_scenes == 2
        assert result.successful_scenes == 2
        assert result.failed_scenes == 0
        assert result.total_estimated_cost_usd == 0.12
        assert result.provider == "kling"


class TestVideoAssetGeneratorRun:
    @pytest.mark.asyncio
    async def test_run_with_no_scenes_returns_error(self):
        tool = VideoAssetGeneratorTool()
        result = await tool.run({"scenes": []})
        assert result.success is False
        assert result.error == "No scenes provided"
        assert result.tool_name == "video_asset_generator"

    @pytest.mark.asyncio
    async def test_run_with_mocked_batch_generator_returns_success(self):
        tool = VideoAssetGeneratorTool()
        mock_batch_result = ToolResult(
            tool_name="batch_video_generator",
            success=True,
            result={
                "scenes": [
                    {
                        "scene_name": "intro",
                        "success": True,
                        "video_url": "https://example.com/intro.mp4",
                        "estimated_cost_usd": 0.05,
                    },
                    {
                        "scene_name": "pain_point",
                        "success": True,
                        "video_url": "https://example.com/pain.mp4",
                        "estimated_cost_usd": 0.05,
                    },
                ],
                "total_scenes": 2,
                "successful_scenes": 2,
                "failed_scenes": 0,
                "total_estimated_cost_usd": 0.10,
                "provider": "kling",
            },
            execution_time_ms=500,
        )
        tool._batch_generator.run = AsyncMock(return_value=mock_batch_result)

        input_scenes = [
            {
                "scene_type": "intro",
                "video_prompt": "Professional conference room with large display...",
                "duration_seconds": 5,
            },
            {
                "scene_type": "pain_point",
                "video_prompt": "Frustrated IT admin managing multiple AV systems...",
                "duration_seconds": 5,
            },
        ]
        result = await tool.run({"scenes": input_scenes})
        assert result.success is True
        assert result.tool_name == "video_asset_generator"
        assert result.result is not None
        assert result.result["total_scenes"] == 2
        assert result.result["successful_scenes"] == 2
        assert result.result["failed_scenes"] == 0
        assert result.result["total_estimated_cost_usd"] == 0.10
        assert result.result["provider"] == "kling"
        assert len(result.result["assets"]) == 2
