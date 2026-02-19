"""
Video Generator Tool
====================

AI-powered video generation using multiple providers:
- Kling AI (Kuaishou) - Best value Chinese model
- HaiLuo AI (MiniMax) - Fast Chinese generation
- Runway Gen-3 - High quality Western option
- Pika Labs - Quick iterations
- Luma Dream Machine - Realistic motion

Cost comparison (per 5-second clip):
- Kling: ~$0.02-0.05
- HaiLuo: ~$0.03-0.08
- Runway: ~$0.25-0.50
- Pika: ~$0.10-0.20

Workflow integration:
1. VideoScriptGeneratorTool -> generates script
2. VideoTemplateManagerTool -> creates scene breakdown
3. VideoGeneratorTool -> generates actual video clips
4. Combine clips for full personalized demo
"""

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import Any

import aiohttp
from pydantic import BaseModel, Field

from src.sdk.security.ssrf import SSRFError, validate_url
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class VideoProvider(str, Enum):
    """Supported video generation providers."""
    KLING = "kling"           # Kuaishou - Best value
    HAILUO = "hailuo"         # MiniMax - Fast
    RUNWAY = "runway"         # Gen-3 Alpha - High quality
    PIKA = "pika"             # Quick iterations
    LUMA = "luma"             # Dream Machine - Realistic
    MINIMAX = "minimax"       # Alias for HaiLuo


class VideoAspectRatio(str, Enum):
    """Common aspect ratios for video generation."""
    LANDSCAPE_16_9 = "16:9"   # Standard widescreen (1920x1080)
    PORTRAIT_9_16 = "9:16"    # Vertical/mobile (1080x1920)
    SQUARE_1_1 = "1:1"        # Social media square
    CINEMATIC_21_9 = "21:9"   # Ultra-wide cinematic


class VideoStyle(str, Enum):
    """Video generation styles."""
    REALISTIC = "realistic"
    CINEMATIC = "cinematic"
    PROFESSIONAL = "professional"
    ANIMATED = "animated"
    DOCUMENTARY = "documentary"


@dataclass
class ProviderConfig:
    """Configuration for a video provider."""
    name: str
    api_base: str
    env_key: str
    cost_per_second: float
    max_duration: int
    supports_image_to_video: bool
    supports_text_to_video: bool
    quality_tier: str  # budget, standard, premium


# Provider configurations
PROVIDER_CONFIGS = {
    VideoProvider.KLING: ProviderConfig(
        name="Kling AI",
        api_base="https://api.klingai.com/v1",
        env_key="KLING_API_KEY",
        cost_per_second=0.01,
        max_duration=10,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="budget",
    ),
    VideoProvider.HAILUO: ProviderConfig(
        name="HaiLuo AI (MiniMax)",
        api_base="https://api.minimaxi.chat/v1",
        env_key="MINIMAX_API_KEY",
        cost_per_second=0.015,
        max_duration=6,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="budget",
    ),
    VideoProvider.MINIMAX: ProviderConfig(
        name="MiniMax Video",
        api_base="https://api.minimaxi.chat/v1",
        env_key="MINIMAX_API_KEY",
        cost_per_second=0.015,
        max_duration=6,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="budget",
    ),
    VideoProvider.RUNWAY: ProviderConfig(
        name="Runway Gen-3",
        api_base="https://api.runwayml.com/v1",
        env_key="RUNWAY_API_KEY",
        cost_per_second=0.05,
        max_duration=10,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="premium",
    ),
    VideoProvider.PIKA: ProviderConfig(
        name="Pika Labs",
        api_base="https://api.pika.art/v1",
        env_key="PIKA_API_KEY",
        cost_per_second=0.025,
        max_duration=4,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="standard",
    ),
    VideoProvider.LUMA: ProviderConfig(
        name="Luma Dream Machine",
        api_base="https://api.lumalabs.ai/v1",
        env_key="LUMA_API_KEY",
        cost_per_second=0.04,
        max_duration=5,
        supports_image_to_video=True,
        supports_text_to_video=True,
        quality_tier="premium",
    ),
}


class VideoGenerationRequest(BaseModel):
    """Input schema for video generation."""

    prompt: str = Field(
        ...,
        description="Text prompt describing the video to generate",
        min_length=10,
        max_length=2000,
    )
    provider: VideoProvider = Field(
        default=VideoProvider.KLING,
        description="Video generation provider (kling, hailuo, runway, pika, luma)",
    )
    duration_seconds: int = Field(
        default=5,
        description="Video duration in seconds",
        ge=1,
        le=10,
    )
    aspect_ratio: VideoAspectRatio = Field(
        default=VideoAspectRatio.LANDSCAPE_16_9,
        description="Video aspect ratio",
    )
    style: VideoStyle = Field(
        default=VideoStyle.PROFESSIONAL,
        description="Visual style for the video",
    )
    reference_image_url: str | None = Field(
        default=None,
        description="URL of reference image for image-to-video generation",
    )
    negative_prompt: str | None = Field(
        default=None,
        description="What to avoid in the generated video",
    )
    seed: int | None = Field(
        default=None,
        description="Random seed for reproducibility",
    )


class VideoGenerationResult(BaseModel):
    """Output schema for video generation."""

    video_url: str = Field(..., description="URL to download/stream the generated video")
    thumbnail_url: str | None = Field(None, description="Video thumbnail URL")
    duration_seconds: float = Field(..., description="Actual video duration")
    resolution: str = Field(..., description="Video resolution (e.g., 1920x1080)")
    provider: str = Field(..., description="Provider used for generation")
    generation_id: str = Field(..., description="Unique ID for this generation")
    estimated_cost_usd: float = Field(..., description="Estimated cost in USD")
    generation_time_seconds: float = Field(..., description="Time taken to generate")
    status: str = Field(..., description="Generation status (completed, processing, failed)")


class VideoGeneratorTool(BaseTool):
    """
    AI video generation tool supporting multiple providers.

    Generates video clips from text prompts or reference images using:
    - Kling AI (Best value - Chinese)
    - HaiLuo/MiniMax (Fast - Chinese)
    - Runway Gen-3 (High quality - Western)
    - Pika Labs (Quick iterations)
    - Luma Dream Machine (Realistic motion)

    Perfect for generating:
    - Personalized prospect intro clips
    - Product demo b-roll
    - Industry-specific visuals
    - Social proof testimonial videos

    Cost optimization: Defaults to Kling AI at ~$0.01/second,
    10-50x cheaper than Runway while maintaining quality.
    """

    # Polling configuration for async generation
    MAX_POLL_ATTEMPTS = 60
    POLL_INTERVAL_SECONDS = 5

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for video_generator."""
        return ToolDefinition(
            name="video_generator",
            description=(
                "Generate AI videos from text prompts or reference images. "
                "Supports Kling (cheapest), HaiLuo, Runway (highest quality), Pika, Luma. "
                "Use for personalized prospect videos, product demos, and b-roll generation."
            ),
            category=ToolCategory.DATA,
            requires_approval=True,  # Video generation can be expensive
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Detailed text prompt describing the video. "
                            "Be specific about: scene, action, camera movement, lighting, style. "
                            "Example: 'Professional businessman in modern office, smiling while "
                            "looking at laptop screen, soft natural lighting, slow camera push-in'"
                        ),
                        "minLength": 10,
                        "maxLength": 2000,
                    },
                    "provider": {
                        "type": "string",
                        "description": "Video generation provider",
                        "enum": ["kling", "hailuo", "minimax", "runway", "pika", "luma"],
                        "default": "kling",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Video duration (1-10 seconds)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Video aspect ratio",
                        "enum": ["16:9", "9:16", "1:1", "21:9"],
                        "default": "16:9",
                    },
                    "style": {
                        "type": "string",
                        "description": "Visual style",
                        "enum": ["realistic", "cinematic", "professional", "animated", "documentary"],
                        "default": "professional",
                    },
                    "reference_image_url": {
                        "type": "string",
                        "description": "URL of reference image for image-to-video (optional)",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What to avoid in the video (optional)",
                    },
                },
                "required": ["prompt"],
            },
        )

    def _get_api_key(self, provider: VideoProvider) -> str | None:
        """Get API key for the specified provider."""
        config = PROVIDER_CONFIGS.get(provider)
        if not config:
            return None
        return os.getenv(config.env_key)

    def _select_best_provider(self, prefer_quality: bool = False) -> VideoProvider:
        """
        Select the best available provider based on API key availability.

        Args:
            prefer_quality: If True, prefer higher quality providers

        Returns:
            Best available provider
        """
        # Priority order: cost-optimized by default
        priority_order = [
            VideoProvider.KLING,
            VideoProvider.HAILUO,
            VideoProvider.PIKA,
            VideoProvider.LUMA,
            VideoProvider.RUNWAY,
        ]

        if prefer_quality:
            # Quality-first order
            priority_order = [
                VideoProvider.RUNWAY,
                VideoProvider.LUMA,
                VideoProvider.PIKA,
                VideoProvider.KLING,
                VideoProvider.HAILUO,
            ]

        for provider in priority_order:
            if self._get_api_key(provider):
                return provider

        # Default to Kling even without key (will fail gracefully)
        return VideoProvider.KLING

    async def _generate_with_kling(
        self,
        session: aiohttp.ClientSession,
        request: VideoGenerationRequest,
        api_key: str,
    ) -> dict[str, Any]:
        """Generate video using Kling AI API."""
        config = PROVIDER_CONFIGS[VideoProvider.KLING]

        # Kling API payload
        payload = {
            "model": "kling-v1",
            "prompt": request.prompt,
            "duration": request.duration_seconds,
            "aspect_ratio": request.aspect_ratio.value,
            "style": request.style.value,
        }

        if request.reference_image_url:
            payload["image_url"] = request.reference_image_url
            payload["mode"] = "image_to_video"
        else:
            payload["mode"] = "text_to_video"

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        if request.seed:
            payload["seed"] = request.seed

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Submit generation request
        async with session.post(
            f"{config.api_base}/videos/generations",
            json=payload,
            headers=headers,
        ) as response:
            if response.status != 200 and response.status != 201:
                error_text = await response.text()
                raise ValueError(f"Kling API error: {response.status} - {error_text}")

            result = await response.json()
            generation_id = result.get("id") or result.get("generation_id")

        # Poll for completion
        return await self._poll_for_completion(
            session, config, api_key, generation_id, request
        )

    async def _generate_with_hailuo(
        self,
        session: aiohttp.ClientSession,
        request: VideoGenerationRequest,
        api_key: str,
    ) -> dict[str, Any]:
        """Generate video using HaiLuo/MiniMax API."""
        config = PROVIDER_CONFIGS[VideoProvider.HAILUO]

        payload = {
            "model": "video-01",
            "prompt": request.prompt,
        }

        if request.reference_image_url:
            payload["first_frame_image"] = request.reference_image_url

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(
            f"{config.api_base}/video_generation",
            json=payload,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"HaiLuo API error: {response.status} - {error_text}")

            result = await response.json()
            task_id = result.get("task_id")

        # Poll for completion
        return await self._poll_hailuo_completion(
            session, config, api_key, task_id, request
        )

    async def _generate_with_runway(
        self,
        session: aiohttp.ClientSession,
        request: VideoGenerationRequest,
        api_key: str,
    ) -> dict[str, Any]:
        """Generate video using Runway Gen-3 API."""
        config = PROVIDER_CONFIGS[VideoProvider.RUNWAY]

        payload = {
            "promptText": request.prompt,
            "model": "gen3a_turbo",
            "duration": request.duration_seconds,
            "ratio": request.aspect_ratio.value.replace(":", "_"),
        }

        if request.reference_image_url:
            payload["promptImage"] = request.reference_image_url

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

        async with session.post(
            f"{config.api_base}/image_to_video",
            json=payload,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Runway API error: {response.status} - {error_text}")

            result = await response.json()
            task_id = result.get("id")

        return await self._poll_runway_completion(
            session, config, api_key, task_id, request
        )

    async def _generate_with_pika(
        self,
        session: aiohttp.ClientSession,
        request: VideoGenerationRequest,
        api_key: str,
    ) -> dict[str, Any]:
        """Generate video using Pika Labs API."""
        config = PROVIDER_CONFIGS[VideoProvider.PIKA]

        payload = {
            "prompt": request.prompt,
            "style": request.style.value,
            "aspectRatio": request.aspect_ratio.value,
        }

        if request.reference_image_url:
            payload["image"] = request.reference_image_url

        if request.negative_prompt:
            payload["negativePrompt"] = request.negative_prompt

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(
            f"{config.api_base}/generate",
            json=payload,
            headers=headers,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise ValueError(f"Pika API error: {response.status} - {error_text}")

            result = await response.json()
            return self._format_result(result, request, VideoProvider.PIKA)

    async def _generate_with_luma(
        self,
        session: aiohttp.ClientSession,
        request: VideoGenerationRequest,
        api_key: str,
    ) -> dict[str, Any]:
        """Generate video using Luma Dream Machine API."""
        config = PROVIDER_CONFIGS[VideoProvider.LUMA]

        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio.value,
            "loop": False,
        }

        if request.reference_image_url:
            payload["keyframes"] = {
                "frame0": {
                    "type": "image",
                    "url": request.reference_image_url,
                }
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(
            f"{config.api_base}/generations",
            json=payload,
            headers=headers,
        ) as response:
            if response.status != 200 and response.status != 201:
                error_text = await response.text()
                raise ValueError(f"Luma API error: {response.status} - {error_text}")

            result = await response.json()
            generation_id = result.get("id")

        return await self._poll_luma_completion(
            session, config, api_key, generation_id, request
        )

    async def _poll_for_completion(
        self,
        session: aiohttp.ClientSession,
        config: ProviderConfig,
        api_key: str,
        generation_id: str,
        request: VideoGenerationRequest,
    ) -> dict[str, Any]:
        """Generic polling for video generation completion."""
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        for _ in range(self.MAX_POLL_ATTEMPTS):
            async with session.get(
                f"{config.api_base}/videos/generations/{generation_id}",
                headers=headers,
            ) as response:
                if response.status != 200:
                    await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                    continue

                result = await response.json()
                status = result.get("status", "").lower()

                if status in ("completed", "succeeded", "done"):
                    return self._format_result(result, request, VideoProvider.KLING)
                elif status in ("failed", "error"):
                    raise ValueError(f"Generation failed: {result.get('error', 'Unknown error')}")

                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        raise TimeoutError("Video generation timed out after maximum polling attempts")

    async def _poll_hailuo_completion(
        self,
        session: aiohttp.ClientSession,
        config: ProviderConfig,
        api_key: str,
        task_id: str,
        request: VideoGenerationRequest,
    ) -> dict[str, Any]:
        """Poll HaiLuo/MiniMax for completion."""
        headers = {"Authorization": f"Bearer {api_key}"}

        for _ in range(self.MAX_POLL_ATTEMPTS):
            async with session.get(
                f"{config.api_base}/query/video_generation",
                params={"task_id": task_id},
                headers=headers,
            ) as response:
                if response.status != 200:
                    await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                    continue

                result = await response.json()
                status = result.get("status", "")

                if status == "Success":
                    return self._format_result(result, request, VideoProvider.HAILUO)
                elif status == "Fail":
                    raise ValueError(f"Generation failed: {result.get('error', 'Unknown')}")

                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        raise TimeoutError("HaiLuo generation timed out")

    async def _poll_runway_completion(
        self,
        session: aiohttp.ClientSession,
        config: ProviderConfig,
        api_key: str,
        task_id: str,
        request: VideoGenerationRequest,
    ) -> dict[str, Any]:
        """Poll Runway for completion."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
        }

        for _ in range(self.MAX_POLL_ATTEMPTS):
            async with session.get(
                f"{config.api_base}/tasks/{task_id}",
                headers=headers,
            ) as response:
                if response.status != 200:
                    await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                    continue

                result = await response.json()
                status = result.get("status", "")

                if status == "SUCCEEDED":
                    return self._format_result(result, request, VideoProvider.RUNWAY)
                elif status == "FAILED":
                    raise ValueError(f"Runway generation failed: {result.get('failure')}")

                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        raise TimeoutError("Runway generation timed out")

    async def _poll_luma_completion(
        self,
        session: aiohttp.ClientSession,
        config: ProviderConfig,
        api_key: str,
        generation_id: str,
        request: VideoGenerationRequest,
    ) -> dict[str, Any]:
        """Poll Luma for completion."""
        headers = {"Authorization": f"Bearer {api_key}"}

        for _ in range(self.MAX_POLL_ATTEMPTS):
            async with session.get(
                f"{config.api_base}/generations/{generation_id}",
                headers=headers,
            ) as response:
                if response.status != 200:
                    await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                    continue

                result = await response.json()
                state = result.get("state", "")

                if state == "completed":
                    return self._format_result(result, request, VideoProvider.LUMA)
                elif state == "failed":
                    raise ValueError(f"Luma generation failed: {result.get('failure_reason')}")

                await asyncio.sleep(self.POLL_INTERVAL_SECONDS)

        raise TimeoutError("Luma generation timed out")

    def _format_result(
        self,
        api_result: dict[str, Any],
        request: VideoGenerationRequest,
        provider: VideoProvider,
    ) -> dict[str, Any]:
        """Format API result into standard output structure."""
        config = PROVIDER_CONFIGS[provider]

        # Extract video URL based on provider response structure
        video_url = (
            api_result.get("video_url") or
            api_result.get("output", [{}])[0].get("url") if isinstance(api_result.get("output"), list) else None or
            api_result.get("assets", {}).get("video") or
            api_result.get("file_id") or
            api_result.get("video", {}).get("url") or
            ""
        )

        # Handle nested video URL structures
        if not video_url and "video" in api_result:
            if isinstance(api_result["video"], str):
                video_url = api_result["video"]
            elif isinstance(api_result["video"], dict):
                video_url = api_result["video"].get("url", "")

        # Calculate resolution from aspect ratio
        aspect_map = {
            "16:9": "1920x1080",
            "9:16": "1080x1920",
            "1:1": "1080x1080",
            "21:9": "2560x1080",
        }
        resolution = aspect_map.get(request.aspect_ratio.value, "1920x1080")

        estimated_cost = config.cost_per_second * request.duration_seconds

        return {
            "video_url": video_url,
            "thumbnail_url": api_result.get("thumbnail") or api_result.get("thumbnail_url"),
            "duration_seconds": request.duration_seconds,
            "resolution": resolution,
            "provider": config.name,
            "generation_id": api_result.get("id") or api_result.get("task_id") or "unknown",
            "estimated_cost_usd": round(estimated_cost, 4),
            "status": "completed",
        }

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute video generation.

        Args:
            arguments: Tool arguments including prompt, provider, duration, etc.

        Returns:
            ToolResult with video URL and metadata or error
        """
        start_time = perf_counter()

        # Parse arguments
        try:
            prompt = arguments.get("prompt")
            if not prompt:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error="Prompt is required",
                    execution_time_ms=0,
                )

            provider_str = arguments.get("provider", "kling").lower()
            try:
                provider = VideoProvider(provider_str)
            except ValueError:
                provider = VideoProvider.KLING

            duration = min(arguments.get("duration_seconds", 5), 10)

            aspect_str = arguments.get("aspect_ratio", "16:9")
            try:
                aspect_ratio = VideoAspectRatio(aspect_str)
            except ValueError:
                aspect_ratio = VideoAspectRatio.LANDSCAPE_16_9

            style_str = arguments.get("style", "professional").lower()
            try:
                style = VideoStyle(style_str)
            except ValueError:
                style = VideoStyle.PROFESSIONAL

            request = VideoGenerationRequest(
                prompt=prompt,
                provider=provider,
                duration_seconds=duration,
                aspect_ratio=aspect_ratio,
                style=style,
                reference_image_url=arguments.get("reference_image_url"),
                negative_prompt=arguments.get("negative_prompt"),
                seed=arguments.get("seed"),
            )

            # SSRF validation for reference_image_url
            if request.reference_image_url:
                try:
                    validate_url(request.reference_image_url)
                except SSRFError as e:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        error=f"Invalid reference_image_url (SSRF blocked): {str(e)}",
                        execution_time_ms=0,
                    )

        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Invalid arguments: {str(e)}",
                execution_time_ms=0,
            )

        # Get API key for selected provider
        api_key = self._get_api_key(provider)

        if not api_key:
            # Try to find any available provider
            fallback_provider = self._select_best_provider()
            api_key = self._get_api_key(fallback_provider)

            if not api_key:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    error=(
                        f"No API key found for {provider.value} or any fallback provider. "
                        f"Set one of: KLING_API_KEY, MINIMAX_API_KEY, RUNWAY_API_KEY, "
                        f"PIKA_API_KEY, LUMA_API_KEY"
                    ),
                    execution_time_ms=0,
                )

            provider = fallback_provider
            request.provider = provider

        # Generate video
        try:
            timeout = aiohttp.ClientTimeout(total=600)  # 10 min timeout for generation
            async with aiohttp.ClientSession(timeout=timeout) as session:

                if provider == VideoProvider.KLING:
                    result = await self._generate_with_kling(session, request, api_key)
                elif provider in (VideoProvider.HAILUO, VideoProvider.MINIMAX):
                    result = await self._generate_with_hailuo(session, request, api_key)
                elif provider == VideoProvider.RUNWAY:
                    result = await self._generate_with_runway(session, request, api_key)
                elif provider == VideoProvider.PIKA:
                    result = await self._generate_with_pika(session, request, api_key)
                elif provider == VideoProvider.LUMA:
                    result = await self._generate_with_luma(session, request, api_key)
                else:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        error=f"Unsupported provider: {provider.value}",
                        execution_time_ms=0,
                    )

            end_time = perf_counter()
            generation_time = end_time - start_time
            result["generation_time_seconds"] = round(generation_time, 2)

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result,
                execution_time_ms=int(generation_time * 1000),
            )

        except TimeoutError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
        except aiohttp.ClientError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"HTTP error: {str(e)}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Video generation failed: {str(e)}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )


class BatchVideoGeneratorTool(BaseTool):
    """
    Generate multiple video clips in batch for scene-by-scene demos.

    Perfect for:
    - Multi-scene product demos (from VideoTemplateManagerTool output)
    - A/B testing different video styles
    - Generating clips for each section of a sales video

    Uses parallel generation for efficiency.
    """

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for batch_video_generator."""
        return ToolDefinition(
            name="batch_video_generator",
            description=(
                "Generate multiple video clips in batch. Perfect for multi-scene demos. "
                "Accepts array of prompts, generates in parallel, returns all video URLs."
            ),
            category=ToolCategory.DATA,
            requires_approval=True,
            parameters={
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "Array of scene prompts to generate",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Scene name/ID"},
                                "prompt": {"type": "string", "description": "Video prompt"},
                                "duration_seconds": {"type": "integer", "default": 5},
                            },
                            "required": ["name", "prompt"],
                        },
                    },
                    "provider": {
                        "type": "string",
                        "description": "Video provider for all scenes",
                        "enum": ["kling", "hailuo", "runway", "pika", "luma"],
                        "default": "kling",
                    },
                    "style": {
                        "type": "string",
                        "description": "Consistent style across all scenes",
                        "enum": ["realistic", "cinematic", "professional", "animated"],
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
        """
        Execute batch video generation.

        Args:
            arguments: Contains scenes array and shared settings

        Returns:
            ToolResult with array of generated video results
        """
        start_time = perf_counter()

        scenes = arguments.get("scenes", [])
        if not scenes:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="No scenes provided",
                execution_time_ms=0,
            )

        provider = arguments.get("provider", "kling")
        style = arguments.get("style", "professional")
        aspect_ratio = arguments.get("aspect_ratio", "16:9")

        # Create individual generator
        generator = VideoGeneratorTool()

        # Generate all scenes in parallel
        tasks = []
        for scene in scenes:
            task_args = {
                "prompt": scene.get("prompt", ""),
                "provider": provider,
                "duration_seconds": scene.get("duration_seconds", 5),
                "style": style,
                "aspect_ratio": aspect_ratio,
            }
            tasks.append(generator.run(task_args))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Format batch results
        batch_results = []
        total_cost = 0.0
        success_count = 0

        for i, (scene, result) in enumerate(zip(scenes, results, strict=True)):
            if isinstance(result, Exception):
                batch_results.append({
                    "scene_name": scene.get("name", f"scene_{i}"),
                    "success": False,
                    "error": str(result),
                })
            elif isinstance(result, ToolResult):
                result_data = result.result or {}
                if result.success:
                    success_count += 1
                    total_cost += result_data.get("estimated_cost_usd", 0)

                batch_results.append({
                    "scene_name": scene.get("name", f"scene_{i}"),
                    "success": result.success,
                    "video_url": result_data.get("video_url") if result.success else None,
                    "error": result.error if not result.success else None,
                    "estimated_cost_usd": result_data.get("estimated_cost_usd", 0) if result.success else 0,
                })

        end_time = perf_counter()

        return ToolResult(
            tool_name=self.definition.name,
            success=success_count > 0,
            result={
                "scenes": batch_results,
                "total_scenes": len(scenes),
                "successful_scenes": success_count,
                "failed_scenes": len(scenes) - success_count,
                "total_estimated_cost_usd": round(total_cost, 4),
                "provider": provider,
            },
            execution_time_ms=int((end_time - start_time) * 1000),
        )
