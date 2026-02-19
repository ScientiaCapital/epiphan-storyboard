"""
Scene Extractor Tool for Demo Video Pipeline.

Converts StoryboardUnderstanding business insights into 6 scene prompts
suitable for AI video generation (Kling AI, HaiLuo, etc.).

Uses DeepSeek V3 via OpenRouter (same pattern as VideoScriptGeneratorTool).
"""

from __future__ import annotations

import json
import logging
import os
from time import perf_counter
from typing import Any

import aiohttp

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_PRODUCTS,
    EPIPHAN_VERTICALS,
    get_audience_persona,
)
from src.tools.video.demo_pipeline_schemas import (
    MVP_CLIP_DURATION_SECONDS,
    SCENE_TIMING_DEFAULTS,
    DemoSceneType,
    SceneExtractionResult,
    SceneTemplate,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Prompt Template
# ============================================================================

SCENE_EXTRACTION_SYSTEM_PROMPT = """\
You are an expert video marketing director for Epiphan Video, specializing in \
creating compelling product demo videos for AV/IT professionals.

Your task: Convert business insights about a product/feature into 6 concrete \
video scene descriptions that can be used to generate AI video clips.

Each scene must have a detailed `video_prompt` suitable for AI video generation \
(Kling AI). Video prompts should describe VISUAL scenes — camera angles, settings, \
people, screens, equipment, lighting — NOT abstract concepts.

CRITICAL RULES for video_prompt:
- Describe what the CAMERA SEES, not abstract ideas
- Include: setting, lighting, camera movement, subjects, equipment
- Reference Epiphan hardware by name when showing product
- Keep prompts 2-3 sentences, visually concrete
- Professional corporate/institutional style

Scene structure (6 scenes):
1. INTRO: Hook the viewer — show the problem environment
2. PAIN_POINT: Dramatize the specific pain — frustrated user or broken workflow
3. SOLUTION: Show the Epiphan product solving the problem
4. DIFFERENTIATION: Highlight what makes this unique vs alternatives
5. RESULTS: Show measurable outcomes — dashboards, happy users, metrics
6. CTA: Call to action — schedule a demo, visit website
"""

SCENE_EXTRACTION_USER_TEMPLATE = """\
Generate 6 video scenes for this Epiphan Video demo:

## Business Context
- Headline: {headline}
- Pain Point: {pain_point}
- Business Value: {business_value}
- What It Does: {what_it_does}
- Who Benefits: {who_benefits}
- Differentiator: {differentiator}

## Target Audience
- Persona: {persona_name} ({persona_title})
- Vertical: {vertical_name}
- Use Cases: {use_cases}

## Product Focus
- Product: {product_name} ({product_price})
- Key Specs: {product_specs}
- Best For: {product_best_for}

## Vertical Pain Points
{vertical_pain_points}

Return JSON with exactly 6 scenes:
```json
{{
  "scenes": [
    {{
      "scene_type": "intro|pain_point|solution|differentiation|results|cta",
      "video_prompt": "Detailed visual description for AI video generation...",
      "talking_points": ["Point 1", "Point 2"],
      "visual_description": "Brief description of what viewer sees"
    }}
  ]
}}
```
"""


class SceneExtractorTool(BaseTool):
    """Extract 6 video scene prompts from StoryboardUnderstanding.

    Converts business insights (headline, pain_point, business_value, etc.)
    into concrete video generation prompts using DeepSeek V3 via OpenRouter.

    Input: StoryboardUnderstanding dict + persona + vertical + product_focus
    Output: SceneExtractionResult with 6 SceneTemplate objects
    """

    MODEL_ID = "deepseek/deepseek-chat-v3"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 60

    def __init__(self) -> None:
        self._api_key = os.getenv("OPENROUTER_API_KEY")

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="scene_extractor",
            description=(
                "Extract 6 video scene prompts from storyboard understanding. "
                "Converts business insights into concrete AI video generation prompts "
                "using persona, vertical, and product context from Epiphan presets."
            ),
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "understanding": {
                        "type": "object",
                        "description": "StoryboardUnderstanding dict with headline, pain_point, business_value, etc.",
                    },
                    "persona": {
                        "type": "string",
                        "description": "Target audience persona (e.g., 'av_director')",
                        "default": "av_director",
                    },
                    "vertical": {
                        "type": "string",
                        "description": "Target vertical (e.g., 'higher_ed')",
                        "default": "higher_ed",
                    },
                    "product_focus": {
                        "type": "string",
                        "description": "Product to feature (e.g., 'pearl_mini')",
                        "default": "pearl_mini",
                    },
                },
                "required": ["understanding"],
            },
        )

    async def run(self, arguments: dict) -> ToolResult:
        """Execute scene extraction from storyboard understanding."""
        start_time = perf_counter()

        understanding = arguments.get("understanding", {})
        if not understanding:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error="understanding dict is required",
                execution_time_ms=0,
            )

        persona_key = arguments.get("persona", "av_director")
        vertical_key = arguments.get("vertical", "higher_ed")
        product_key = arguments.get("product_focus", "pearl_mini")

        try:
            # Resolve persona, vertical, and product context
            persona_data = self._resolve_persona(persona_key)
            vertical_data = self._resolve_vertical(vertical_key)
            product_data = self._resolve_product(product_key)

            # Build prompt
            prompt = self._build_prompt(
                understanding, persona_data, vertical_data, product_data
            )

            # Call LLM
            raw_response = await self._call_llm(prompt)

            # Parse response into SceneTemplates
            scenes = self._parse_scenes(raw_response)

            extraction_time_ms = int((perf_counter() - start_time) * 1000)

            result = SceneExtractionResult(
                scenes=scenes,
                persona=persona_key,
                vertical=vertical_key,
                product_focus=product_key,
                model_used=self.MODEL_ID,
                extraction_time_ms=extraction_time_ms,
            )

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result.model_dump(),
                execution_time_ms=extraction_time_ms,
            )

        except Exception as e:
            logger.error(f"[SCENE_EXTRACTOR] Failed: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                error=f"Scene extraction failed: {e}",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

    # ========================================================================
    # Internal helpers
    # ========================================================================

    def _resolve_persona(self, persona_key: str) -> dict[str, Any]:
        """Resolve persona context from epiphan_presets."""
        try:
            return get_audience_persona(persona_key)
        except (ValueError, KeyError):
            logger.warning(
                f"[SCENE_EXTRACTOR] Unknown persona '{persona_key}', using av_director"
            )
            return get_audience_persona("av_director")

    def _resolve_vertical(self, vertical_key: str) -> dict[str, Any]:
        """Resolve vertical context from epiphan_presets."""
        if vertical_key in EPIPHAN_VERTICALS:
            return EPIPHAN_VERTICALS[vertical_key]
        logger.warning(
            f"[SCENE_EXTRACTOR] Unknown vertical '{vertical_key}', using higher_ed"
        )
        return EPIPHAN_VERTICALS["higher_ed"]

    def _resolve_product(self, product_key: str) -> dict[str, Any]:
        """Resolve product context from epiphan_presets."""
        if product_key in EPIPHAN_PRODUCTS:
            return EPIPHAN_PRODUCTS[product_key]
        logger.warning(
            f"[SCENE_EXTRACTOR] Unknown product '{product_key}', using pearl_mini"
        )
        return EPIPHAN_PRODUCTS["pearl_mini"]

    def _build_prompt(
        self,
        understanding: dict[str, Any],
        persona_data: dict[str, Any],
        vertical_data: dict[str, Any],
        product_data: dict[str, Any],
    ) -> str:
        """Build the user prompt for scene extraction."""
        vertical_pain_points = "\n".join(
            f"- {pp}" for pp in vertical_data.get("pain_points", [])
        )

        return SCENE_EXTRACTION_USER_TEMPLATE.format(
            headline=understanding.get("headline", "Untitled"),
            pain_point=understanding.get("pain_point_addressed", "Unknown pain point"),
            business_value=understanding.get("business_value", "Improved efficiency"),
            what_it_does=understanding.get("what_it_does", ""),
            who_benefits=understanding.get("who_benefits", ""),
            differentiator=understanding.get("differentiator", ""),
            persona_name=persona_data.get(
                "name", persona_data.get("persona", "AV Director")
            ),
            persona_title=persona_data.get("title", ""),
            vertical_name=vertical_data.get("name", "Higher Education"),
            use_cases=", ".join(vertical_data.get("use_cases", [])),
            product_name=product_data.get("name", "Pearl Mini"),
            product_price=product_data.get("price", ""),
            product_specs=", ".join(product_data.get("key_specs", [])),
            product_best_for=", ".join(product_data.get("best_for", [])),
            vertical_pain_points=vertical_pain_points,
        )

    async def _call_llm(self, user_prompt: str) -> str:
        """Call DeepSeek V3 via OpenRouter and return raw response text."""
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://epiphan.video",
            "X-Title": "Epiphan Demo Pipeline",
        }

        payload = {
            "model": self.MODEL_ID,
            "messages": [
                {"role": "system", "content": SCENE_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT),
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    raise RuntimeError(
                        f"OpenRouter API error {response.status}: {body[:500]}"
                    )

                data = await response.json()
                content: str = data["choices"][0]["message"]["content"]
                return content

    def _parse_scenes(self, raw_response: str) -> list[SceneTemplate]:
        """Parse LLM response JSON into SceneTemplate objects."""
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e

        raw_scenes = parsed.get("scenes", [])
        if not raw_scenes:
            raise ValueError("LLM response contained no scenes")

        scene_order = list(DemoSceneType)
        templates: list[SceneTemplate] = []

        for i, raw_scene in enumerate(raw_scenes[:6]):
            # Determine scene type from response or use positional default
            scene_type_str = raw_scene.get("scene_type", "")
            try:
                scene_type = DemoSceneType(scene_type_str)
            except ValueError:
                scene_type = (
                    scene_order[i] if i < len(scene_order) else DemoSceneType.INTRO
                )

            timing = SCENE_TIMING_DEFAULTS.get(
                scene_type,
                {"start": 0, "end": 15, "duration": 15},
            )

            templates.append(
                SceneTemplate(
                    scene_type=scene_type,
                    video_prompt=raw_scene.get("video_prompt", f"Scene {i + 1}"),
                    talking_points=raw_scene.get("talking_points", []),
                    duration_seconds=MVP_CLIP_DURATION_SECONDS,
                    start_time=timing["start"],
                    end_time=timing["end"],
                    visual_description=raw_scene.get("visual_description", ""),
                )
            )

        return templates
