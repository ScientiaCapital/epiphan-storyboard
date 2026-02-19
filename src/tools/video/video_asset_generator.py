"""
Video Asset Generator Tool for Demo Pipeline.

Thin orchestration layer that converts SceneTemplates into the format
expected by BatchVideoGeneratorTool, delegates generation, and maps
results back to VideoAsset objects.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.video.demo_pipeline_schemas import (
    DemoSceneType,
    VideoAsset,
    VideoAssetBatchResult,
)
from src.tools.video.video_generator import BatchVideoGeneratorTool

logger = logging.getLogger(__name__)


class VideoAssetGeneratorTool(BaseTool):
    """Generate video assets from scene templates.

    Converts SceneTemplate objects to BatchVideoGeneratorTool input format,
    delegates to the existing batch generator, and maps results back
    to VideoAsset objects with scene metadata.
    """

    def __init__(self) -> None:
        self._batch_generator = BatchVideoGeneratorTool()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="video_asset_generator",
            description=(
                "Generate video assets from scene templates. Converts scene prompts "
                "to video clips using BatchVideoGeneratorTool. Returns VideoAssetBatchResult."
            ),
            category=ToolCategory.DATA,
            requires_approval=True,
            parameters={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "SceneTemplate dicts from scene extraction",
                        "items": {"type": "object"},
                    },
                    "provider": {
                        "type": "string",
                        "description": "Video generation provider",
                        "enum": ["kling", "hailuo", "runway", "pika", "luma"],
                        "default": "kling",
                    },
                    "style": {
                        "type": "string",
                        "description": "Visual style for all scenes",
                        "default": "professional",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "9:16", "1:1"],
                        "default": "16:9",
                    },
                },
                "required": ["scenes"],
            },
        )

    async def run(self, arguments: dict) -> ToolResult:
        """Execute video asset generation from scene templates."""
        start_time = perf_counter()

        raw_scenes = arguments.get("scenes", [])
        if not raw_scenes:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="No scenes provided",
                execution_time_ms=0,
            )

        provider = arguments.get("provider", "kling")
        style = arguments.get("style", "professional")
        aspect_ratio = arguments.get("aspect_ratio", "16:9")

        try:
            # Convert SceneTemplate dicts to BatchVideoGeneratorTool format
            batch_scenes = self._convert_to_batch_format(raw_scenes)

            # Delegate to BatchVideoGeneratorTool
            batch_result = await self._batch_generator.run(
                {
                    "scenes": batch_scenes,
                    "provider": provider,
                    "style": style,
                    "aspect_ratio": aspect_ratio,
                }
            )

            if not batch_result.success:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=batch_result.error or "Batch video generation failed",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Map batch results back to VideoAsset objects
            batch_data = batch_result.result or {}
            asset_result = self._map_to_video_assets(raw_scenes, batch_data, provider)

            execution_time_ms = int((perf_counter() - start_time) * 1000)

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=asset_result.model_dump(),
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"[VIDEO_ASSET_GENERATOR] Failed: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Video asset generation failed: {e}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _convert_to_batch_format(
        self, scenes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert SceneTemplate dicts to BatchVideoGeneratorTool input format.

        BatchVideoGeneratorTool expects:
        [{"name": "intro", "prompt": "...", "duration_seconds": 5}, ...]
        """
        batch_scenes = []
        for scene in scenes:
            batch_scenes.append(
                {
                    "name": scene.get("scene_type", "unknown"),
                    "prompt": scene.get("video_prompt", ""),
                    "duration_seconds": scene.get("duration_seconds", 5),
                }
            )
        return batch_scenes

    def _map_to_video_assets(
        self,
        original_scenes: list[dict[str, Any]],
        batch_data: dict[str, Any],
        provider: str,
    ) -> VideoAssetBatchResult:
        """Map BatchVideoGeneratorTool results back to VideoAsset objects."""
        batch_scene_results = batch_data.get("scenes", [])
        assets: list[VideoAsset] = []
        total_cost = 0.0
        success_count = 0

        for i, original in enumerate(original_scenes):
            # Match by index — batch results preserve order
            batch_scene = batch_scene_results[i] if i < len(batch_scene_results) else {}

            scene_type_str = original.get("scene_type", "intro")
            try:
                scene_type = DemoSceneType(scene_type_str)
            except ValueError:
                scene_type = DemoSceneType.INTRO

            is_success = batch_scene.get("success", False)
            cost = batch_scene.get("estimated_cost_usd", 0.0)

            if is_success:
                success_count += 1
                total_cost += cost

            assets.append(
                VideoAsset(
                    scene_type=scene_type,
                    scene_name=batch_scene.get("scene_name", scene_type_str),
                    video_url=batch_scene.get("video_url"),
                    duration_seconds=original.get("duration_seconds", 5),
                    provider=provider,
                    estimated_cost_usd=cost,
                    success=is_success,
                    error=batch_scene.get("error"),
                )
            )

        return VideoAssetBatchResult(
            assets=assets,
            total_scenes=len(original_scenes),
            successful_scenes=success_count,
            failed_scenes=len(original_scenes) - success_count,
            total_estimated_cost_usd=round(total_cost, 4),
            provider=provider,
        )
