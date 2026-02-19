"""
RoadmapToStoryboardTool
========================

Transforms Miro/roadmap screenshots into sanitized "Coming Soon" teasers.

Two-stage pipeline:
1. UNDERSTAND + SANITIZE (Gemini Vision) - Analyze image, extract themes, strip IP
2. GENERATE (Gemini Image Gen) - Create beautiful PNG teaser

Extra aggressive sanitization for CTO roadmaps (lots of IP).
Target audience: MEP+energy contractors ($5M+ ICP)

NO OpenAI - Gemini only.
"""

import os
import base64
import logging
from time import perf_counter
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.storyboard.gemini_client import GeminiStoryboardClient, StoryboardUnderstanding
from src.tools.storyboard.coperniq_presets import (
    COPERNIQ_ICP,
    get_icp_preset,
    get_audience_persona,
    AudiencePersona,
    StoryboardStage,
)

logger = logging.getLogger(__name__)


class RoadmapToStoryboardTool(BaseTool):
    """
    Transform Miro/roadmap screenshots into sanitized "Coming Soon" teasers.

    Takes CTO roadmaps, Miro boards, or planning screenshots and produces
    exciting teasers that build anticipation without exposing IP.

    Features:
    - Extra IP sanitization (roadmaps often contain sensitive info)
    - "Coming Soon" teaser format (builds excitement)
    - Supports image bytes or base64 input
    - ICP-optimized language (MEP+energy contractors)
    - Stage-aware visuals (preview focus)

    Example:
        tool = RoadmapToStoryboardTool()
        result = await tool.run({
            "image_data": base64_screenshot,
            "icp_preset": "coperniq_mep",
            "audience": "c_suite",
        })
        # result.result["storyboard_png"] = base64 PNG teaser
    """

    MODEL_ID = "gemini-2.0-flash"  # For understanding stage
    IMAGE_MODEL_ID = "gemini-2.0-flash-preview-image-generation"  # For generation stage
    DEFAULT_TIMEOUT = 90  # seconds

    def __init__(self, gemini_client: GeminiStoryboardClient | None = None):
        """
        Initialize RoadmapToStoryboardTool.

        Args:
            gemini_client: Optional pre-configured Gemini client
        """
        self._gemini_client = gemini_client

    @property
    def gemini_client(self) -> GeminiStoryboardClient:
        """Lazy initialization of Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = GeminiStoryboardClient()
        return self._gemini_client

    @property
    def definition(self) -> ToolDefinition:
        """Tool definition for LLM function calling."""
        return ToolDefinition(
            name="roadmap_to_storyboard",
            description=(
                "Transform Miro/roadmap screenshots into sanitized 'Coming Soon' teasers. "
                "Takes CTO roadmaps or planning boards and produces exciting visual teasers "
                "that build anticipation without exposing IP or sensitive details. "
                "Perfect for BDR outreach to generate interest in upcoming features."
            ),
            category=ToolCategory.DATA,
            parameters={
                "type": "object",
                "properties": {
                    "image_data": {
                        "type": "string",
                        "description": "Base64-encoded image data or data URL",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Path to image file (alternative to image_data)",
                    },
                    "icp_preset": {
                        "type": "string",
                        "description": "ICP preset to use (default: coperniq_mep)",
                        "default": "coperniq_mep",
                    },
                    "audience": {
                        "type": "string",
                        "enum": ["business_owner", "c_suite", "btl_champion"],
                        "description": "Target audience persona",
                        "default": "c_suite",
                    },
                    "custom_headline": {
                        "type": "string",
                        "description": "Optional custom headline override",
                    },
                    "sanitize_ip": {
                        "type": "boolean",
                        "description": "Apply extra IP sanitization (default: true)",
                        "default": True,
                    },
                },
                "required": [],  # Either image_data or image_path required
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the roadmap-to-storyboard pipeline.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with:
            - storyboard_png: Base64-encoded PNG teaser image
            - understanding: Extracted themes (sanitized)
            - audience: The audience targeted
        """
        start_time = perf_counter()

        try:
            # Get image data
            image_data = arguments.get("image_data")
            image_path = arguments.get("image_path")

            if not image_data and not image_path:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error="Either image_data or image_path is required",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Read from file path if needed
            if not image_data and image_path:
                if not os.path.exists(image_path):
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        error=f"Image file not found: {image_path}",
                        execution_time_ms=int((perf_counter() - start_time) * 1000),
                    )
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                image_data = base64.b64encode(image_bytes).decode("utf-8")

            # Get configuration
            icp_preset_name = arguments.get("icp_preset", "coperniq_mep")
            audience = arguments.get("audience", "c_suite")
            custom_headline = arguments.get("custom_headline")
            sanitize_ip = arguments.get("sanitize_ip", True)

            try:
                icp_preset = get_icp_preset(icp_preset_name)
            except ValueError as e:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=str(e),
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Stage 1: Understand and sanitize the roadmap
            logger.info("[ROADMAP_STORYBOARD] Stage 1: Understanding and sanitizing roadmap")
            understanding = await self.gemini_client.understand_image(
                image_data=image_data,
                icp_preset=icp_preset,
                audience=audience,
                sanitize_ip=sanitize_ip,
            )

            # Apply custom headline if provided
            if custom_headline:
                understanding.headline = custom_headline

            # Stage 2: Generate the teaser storyboard
            # Roadmaps always use "preview" stage (Coming Soon)
            logger.info("[ROADMAP_STORYBOARD] Stage 2: Generating teaser storyboard")
            png_bytes = await self.gemini_client.generate_storyboard(
                understanding=understanding,
                stage="preview",  # Always preview for roadmaps
                icp_preset=icp_preset,
            )

            # Encode as base64
            png_base64 = base64.b64encode(png_bytes).decode("utf-8")

            execution_time_ms = int((perf_counter() - start_time) * 1000)
            logger.info(f"[ROADMAP_STORYBOARD] Complete in {execution_time_ms}ms")

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result={
                    "storyboard_png": png_base64,
                    "understanding": {
                        "headline": understanding.headline,
                        "what_it_does": understanding.what_it_does,
                        "business_value": understanding.business_value,
                        "who_benefits": understanding.who_benefits,
                        "differentiator": understanding.differentiator,
                        "pain_point_addressed": understanding.pain_point_addressed,
                        "suggested_icon": understanding.suggested_icon,
                    },
                    "stage": "preview",  # Always preview
                    "audience": audience,
                    "icp_preset": icp_preset_name,
                    "is_teaser": True,
                    "ip_sanitized": sanitize_ip,
                },
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"[ROADMAP_STORYBOARD] Error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
