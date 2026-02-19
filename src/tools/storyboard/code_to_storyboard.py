"""
CodeToStoryboardTool - The Hero
================================

Transforms code files into beautiful one-page PNG storyboards.

Two-stage pipeline:
1. UNDERSTAND (Gemini Vision) - Read code, extract business value
2. GENERATE (Gemini Image Gen) - Create beautiful PNG storyboard

Supports any programming language (.py, .js, .ts, .go, .rs, etc.)
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
    sanitize_content,
    AudiencePersona,
    StoryboardStage,
)

logger = logging.getLogger(__name__)


class CodeToStoryboardTool(BaseTool):
    """
    Transform code files into beautiful one-page PNG storyboards.

    The hero tool of the storyboard pipeline. Takes any code file and produces
    an executive-ready visual that BDRs can attach to cold outreach emails.

    Features:
    - Language-agnostic (Python, JavaScript, TypeScript, Go, Rust, etc.)
    - Automatic IP sanitization (no technical details leaked)
    - ICP-optimized language (MEP+energy contractors)
    - Stage-aware visuals (preview/demo/shipped)
    - Audience targeting (business_owner/c_suite/btl_champion)

    Example:
        tool = CodeToStoryboardTool()
        result = await tool.run({
            "file_content": "def calculate_roi(): ...",
            "file_name": "calculator.py",
            "icp_preset": "coperniq_mep",
            "stage": "preview",
            "audience": "c_suite",
        })
        # result.result["storyboard_png"] = base64 PNG image
    """

    MODEL_ID = "gemini-2.0-flash"  # For understanding stage
    IMAGE_MODEL_ID = "gemini-2.0-flash-preview-image-generation"  # For generation stage
    DEFAULT_TIMEOUT = 90  # seconds

    def __init__(self, gemini_client: GeminiStoryboardClient | None = None):
        """
        Initialize CodeToStoryboardTool.

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
            name="code_to_storyboard",
            description=(
                "Transform code files into beautiful one-page PNG storyboards. "
                "Takes any programming language code and produces an executive-ready "
                "visual showing business value, benefits, and differentiators. "
                "Perfect for BDR cold outreach to contractors. "
                "Automatically sanitizes technical details and IP."
            ),
            category=ToolCategory.DATA,
            parameters={
                "type": "object",
                "properties": {
                    "file_content": {
                        "type": "string",
                        "description": "The source code content to analyze",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the code file (alternative to file_content)",
                    },
                    "file_name": {
                        "type": "string",
                        "description": "Name of the file for context (e.g., 'main.py')",
                    },
                    "icp_preset": {
                        "type": "string",
                        "description": "ICP preset to use (default: coperniq_mep)",
                        "default": "coperniq_mep",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["preview", "demo", "shipped"],
                        "description": "Storyboard stage for BDR cadence",
                        "default": "preview",
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
                },
                "required": [],  # Either file_content or file_path required
            },
            requires_approval=False,
        )

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the code-to-storyboard pipeline.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with:
            - storyboard_png: Base64-encoded PNG image
            - understanding: Extracted business insights
            - stage: The stage used
            - audience: The audience targeted
        """
        start_time = perf_counter()

        try:
            # Get code content
            file_content = arguments.get("file_content")
            file_path = arguments.get("file_path")
            file_name = arguments.get("file_name", "unknown")

            if not file_content and not file_path:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error="Either file_content or file_path is required",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Read from file path if needed
            if not file_content and file_path:
                if not os.path.exists(file_path):
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        error=f"File not found: {file_path}",
                        execution_time_ms=int((perf_counter() - start_time) * 1000),
                    )
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                if not file_name or file_name == "unknown":
                    file_name = os.path.basename(file_path)

            # Get configuration
            icp_preset_name = arguments.get("icp_preset", "coperniq_mep")
            stage = arguments.get("stage", "preview")
            audience = arguments.get("audience", "c_suite")
            custom_headline = arguments.get("custom_headline")

            try:
                icp_preset = get_icp_preset(icp_preset_name)
            except ValueError as e:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=str(e),
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Pre-sanitize code content
            sanitized_content = sanitize_content(file_content)

            # Stage 1: Understand the code
            logger.info(f"[CODE_STORYBOARD] Stage 1: Understanding {file_name}")
            understanding = await self.gemini_client.understand_code(
                code_content=sanitized_content,
                icp_preset=icp_preset,
                audience=audience,
                file_name=file_name,
            )

            # Apply custom headline if provided
            if custom_headline:
                understanding.headline = custom_headline

            # Stage 2: Generate the storyboard
            logger.info(f"[CODE_STORYBOARD] Stage 2: Generating storyboard")
            png_bytes = await self.gemini_client.generate_storyboard(
                understanding=understanding,
                stage=stage,
                icp_preset=icp_preset,
            )

            # Encode as base64
            png_base64 = base64.b64encode(png_bytes).decode("utf-8")

            execution_time_ms = int((perf_counter() - start_time) * 1000)
            logger.info(f"[CODE_STORYBOARD] Complete in {execution_time_ms}ms")

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
                    "stage": stage,
                    "audience": audience,
                    "icp_preset": icp_preset_name,
                    "file_name": file_name,
                },
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"[CODE_STORYBOARD] Error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
