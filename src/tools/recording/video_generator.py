"""
RunwayVideoGeneratorTool - AI Video Generation
===============================================

BaseTool wrapper for Runway Gen-3 Alpha video generation.
Supports text-to-video and image-to-video.

NO OpenAI - Runway API only.
"""

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.recording.config import RunwayConfig
from src.tools.recording.runway_client import RunwayClient

logger = logging.getLogger(__name__)


class RunwayVideoGeneratorTool(BaseTool):
    """
    Generate videos from text or images using Runway Gen-3 Alpha.

    Supports:
    - Text-to-video: Generate video from text prompt
    - Image-to-video: Animate a static image

    Example:
        tool = RunwayVideoGeneratorTool()

        # Text-to-video
        result = await tool.run({
            "prompt": "A futuristic city at sunset",
            "duration": 5,
        })

        # Image-to-video
        result = await tool.run({
            "prompt": "Camera slowly zooms in",
            "image": "base64encodeddata",
            "duration": 5,
        })
    """

    def __init__(
        self,
        runway_client: RunwayClient | None = None,
        config: RunwayConfig | None = None,
    ):
        """
        Initialize RunwayVideoGeneratorTool.

        Args:
            runway_client: Optional pre-configured client
            config: Optional configuration (uses env vars if not provided)
        """
        self._client = runway_client
        self._config = config

    def _get_client(self) -> RunwayClient:
        """Lazy initialization of Runway client."""
        if self._client is None:
            self._client = RunwayClient(config=self._config)
        return self._client

    @property
    def definition(self) -> ToolDefinition:
        """Tool definition for LLM function calling."""
        return ToolDefinition(
            name="runway_video_generator",
            description=(
                "Generate AI videos from text prompts or images using Runway Gen-3 Alpha. "
                "Creates 5-10 second video clips with cinematic quality. "
                "Supports text-to-video (describe scene) or image-to-video (animate image). "
                "Perfect for marketing videos, product demos, and creative content."
            ),
            category=ToolCategory.WEB,
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of desired video (required)",
                    },
                    "image": {
                        "type": "string",
                        "description": "Base64-encoded image to animate (optional, enables image-to-video)",
                    },
                    "duration": {
                        "type": "integer",
                        "enum": [5, 10],
                        "description": "Video duration in seconds (5 or 10)",
                        "default": 5,
                    },
                    "model": {
                        "type": "string",
                        "enum": ["gen3a_turbo", "gen3a"],
                        "description": "Model to use (turbo is faster, gen3a is higher quality)",
                        "default": "gen3a_turbo",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "9:16", "1:1"],
                        "description": "Video aspect ratio",
                        "default": "16:9",
                    },
                    "wait_for_completion": {
                        "type": "boolean",
                        "description": "Wait for video to complete (default: true)",
                        "default": True,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Custom output path for video file (optional)",
                    },
                },
                "required": ["prompt"],
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute video generation.

        Args:
            arguments: Tool arguments containing:
                - prompt: Required. Text description of desired video.
                - image: Optional. Base64 image for image-to-video.
                - duration: Optional. Video length (5 or 10 seconds).
                - model: Optional. Model to use.
                - aspect_ratio: Optional. Video aspect ratio.
                - wait_for_completion: Optional. Wait for completion (default true).
                - output_path: Optional. Custom output path.

        Returns:
            ToolResult with:
            - task_id: Runway task ID
            - status: Generation status
            - video_path: Path to video (if wait_for_completion=true)
            - progress: Progress percentage
        """
        start_time = perf_counter()

        # Validate required parameters
        prompt = arguments.get("prompt")
        if not prompt:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="Missing required 'prompt' parameter",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        if not prompt.strip():
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="'prompt' cannot be empty",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        # Extract parameters
        image = arguments.get("image")
        duration = arguments.get("duration", 5)
        model = arguments.get("model", "gen3a_turbo")
        aspect_ratio = arguments.get("aspect_ratio", "16:9")
        wait_for_completion = arguments.get("wait_for_completion", True)
        output_path = arguments.get("output_path")

        try:
            client = self._get_client()

            # Start generation
            if image:
                # Image-to-video
                logger.info(f"[RUNWAY_TOOL] Starting image-to-video generation")
                task = await client.generate_from_image(
                    image_data=image,
                    prompt=prompt,
                    duration=duration,
                    model=model,
                )
            else:
                # Text-to-video
                logger.info(f"[RUNWAY_TOOL] Starting text-to-video generation")
                task = await client.generate_from_text(
                    prompt=prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    model=model,
                )

            task_id = task["id"]
            status = task.get("status", "PENDING")

            # If not waiting, return immediately
            if not wait_for_completion:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=True,
                    result={
                        "task_id": task_id,
                        "status": status,
                        "message": "Generation started. Use task_id to poll status.",
                    },
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Wait for completion
            logger.info(f"[RUNWAY_TOOL] Waiting for task {task_id} to complete")
            final_status = await client.wait_for_completion(task_id)

            # Download video
            if output_path:
                download_path = Path(output_path)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_dir = tempfile.gettempdir()
                download_path = Path(temp_dir) / f"runway_{task_id}_{timestamp}.mp4"

            video_path = await client.download_video(task_id, download_path)

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result={
                    "task_id": task_id,
                    "status": "SUCCEEDED",
                    "video_path": video_path,
                    "duration_sec": duration,
                    "model": model,
                },
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        except ValueError as e:
            # Configuration errors (missing API key, etc.)
            logger.error(f"[RUNWAY_TOOL] Validation error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        except RuntimeError as e:
            # Generation failures
            logger.error(f"[RUNWAY_TOOL] Generation error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Generation failed: {e}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        except TimeoutError as e:
            # Timeout waiting for completion
            logger.error(f"[RUNWAY_TOOL] Timeout error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Timeout: {e}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        except Exception as e:
            # Unexpected errors
            logger.error(f"[RUNWAY_TOOL] Unexpected error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Error: {e}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
