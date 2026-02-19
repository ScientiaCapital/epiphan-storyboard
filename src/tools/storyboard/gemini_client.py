"""
Storyboard Client
==================

Multi-model client for understanding (vision) and image generation.
Implements the two-stage pipeline:
1. UNDERSTAND - Analyze code/images, extract business value (Gemini or Qwen via OpenRouter)
2. GENERATE - Create beautiful PNG storyboards (Gemini only)

Vision model options:
- gemini: Gemini 2.0 Flash (default)
- qwen: Qwen 2.5 VL 72B via OpenRouter (better for complex documents)

NO OpenAI - Gemini + Chinese VLMs only.
"""

import asyncio
import base64
import json
import logging
import os
import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from src.tools.storyboard import prompt_builders, prompts

logger = logging.getLogger(__name__)


def _repair_json(json_str: str) -> str:
    """
    Attempt to repair truncated or malformed JSON.

    Common issues from LLM responses:
    - Unterminated strings
    - Missing closing braces
    - Trailing commas
    """

    # Remove markdown code blocks
    if json_str.startswith("```"):
        parts = json_str.split("```")
        if len(parts) >= 2:
            json_str = parts[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        json_str = json_str.strip()

    # Try parsing as-is first
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass

    # Fix unterminated strings by closing them
    # Count quotes to see if we have an odd number (unterminated)
    quote_count = json_str.count('"') - json_str.count('\\"')
    if quote_count % 2 == 1:
        json_str = json_str + '"'

    # Add missing closing braces
    open_braces = json_str.count("{") - json_str.count("}")
    if open_braces > 0:
        json_str = json_str + "}" * open_braces

    # Remove trailing commas before closing braces
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    return json_str


def _safe_parse_understanding(
    response_text: str,
    source: str = "unknown",
) -> "StoryboardUnderstanding":
    """
    Safely parse LLM response to StoryboardUnderstanding.

    Returns error state instead of raising on parse failure.
    """
    try:
        json_str = _repair_json(response_text.strip())
        data = json.loads(json_str)
        return StoryboardUnderstanding(**data)
    except json.JSONDecodeError as e:
        logger.error(f"[UNDERSTAND] Failed to parse {source} response: {e}")
        logger.error(
            f"[UNDERSTAND] Raw response was: {response_text[:500] if response_text else 'None'}"
        )
        return StoryboardUnderstanding(
            headline="EXTRACTION FAILED - Check Input",
            tagline="Could not extract content",
            what_it_does="The AI returned malformed data. Try again or use a different input.",
            business_value="Unable to determine - extraction failed",
            who_benefits="Unable to determine - extraction failed",
            differentiator="Unable to determine - extraction failed",
            pain_point_addressed="Unable to determine - extraction failed",
            suggested_icon="alert-triangle",
            raw_extracted_text=f"PARSE ERROR ({source}): {str(e)[:200]}",
            extraction_confidence=0.0,
        )
    except Exception as e:
        logger.error(f"[UNDERSTAND] Unexpected error parsing {source}: {e}")
        return StoryboardUnderstanding(
            headline="EXTRACTION FAILED - Unexpected Error",
            tagline="Something went wrong",
            what_it_does=f"Error: {str(e)[:100]}",
            business_value="Unable to determine",
            who_benefits="Unable to determine",
            differentiator="Unable to determine",
            pain_point_addressed="Unable to determine",
            suggested_icon="alert-triangle",
            raw_extracted_text=f"ERROR ({source}): {str(e)[:300]}",
            extraction_confidence=0.0,
        )


# Vision model options for understanding (images)
VisionModel = Literal["gemini", "qwen"]

# Text model options for understanding (code/transcripts)
TextModel = Literal["gemini", "deepseek"]


class StoryboardUnderstanding(BaseModel):
    """Extracted understanding from code/roadmap analysis."""

    headline: str = Field(
        ..., description="Catchy, benefit-focused headline (8 words max)"
    )
    tagline: str = Field(
        default="",
        description="Dynamic tagline specific to content and persona (10 words max)",
    )
    what_it_does: str = Field(
        ..., description="Plain English description (2 sentences max)"
    )
    business_value: str = Field(
        ..., description="Quantified benefit (hours saved, % improvement)"
    )
    who_benefits: str = Field(..., description="Target persona description")
    differentiator: str = Field(..., description="What makes this special (1 sentence)")
    pain_point_addressed: str = Field(..., description="The problem this solves")
    suggested_icon: str = Field(
        default="clipboard-check", description="Icon suggestion for visual"
    )
    # DEBUG/VERIFICATION fields - for CEO/CTO to verify extraction is correct
    raw_extracted_text: str = Field(
        default="",
        description="Verbatim text/features extracted from input (for debugging/verification)",
    )
    extraction_confidence: float = Field(
        default=1.0, description="Confidence score 0-1. Below 0.7 = flag for review"
    )


@dataclass
class GeminiConfig:
    """Configuration for storyboard client."""

    api_key: str | None = None  # Google API key for Gemini
    openrouter_api_key: str | None = None  # OpenRouter API key for Qwen/DeepSeek

    # ==========================================================================
    # INTELLIGENT MODEL ROUTING
    # ==========================================================================
    # Stage 1 (EXTRACT): Primary models for initial extraction
    vision_provider: VisionModel = (
        "qwen"  # For images (default: qwen for better doc understanding)
    )
    text_provider: TextModel = (
        "deepseek"  # For text/transcripts (default: deepseek for best reasoning)
    )

    # Stage 2 (REFINE): Enable multi-model refinement for low-confidence extractions
    enable_refinement: bool = (
        True  # If True, low-confidence extractions get refined by alternate model
    )
    refinement_threshold: float = 0.75  # Confidence below this triggers refinement pass

    # Model identifiers
    gemini_vision_model: str = (
        "models/gemini-2.0-flash"  # Gemini vision model (fallback)
    )
    qwen_model: str = (
        "qwen/qwen2.5-vl-72b-instruct"  # Qwen 2.5 VL 72B - vision + doc understanding
    )
    deepseek_model: str = "deepseek/deepseek-chat"  # DeepSeek V3 - fast, excellent for structured extraction

    # Stage 3 (GENERATE): Image generation (Gemini only - no alternatives)
    image_model: str = (
        "models/gemini-3-pro-image-preview"  # Nano Banana - FREE during preview
    )

    timeout: int = 90
    max_retries: int = 3

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.openrouter_api_key is None:
            self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")


class GeminiStoryboardClient:
    """
    Client for Gemini Vision + Image Generation.

    Three-stage intelligent pipeline:
    1. EXTRACT - Primary model extracts (DeepSeek for text, Qwen for images)
    2. REFINE - If confidence < threshold, alternate model validates/improves
    3. GENERATE - Gemini creates the image (only model that can generate)

    Model Routing Intelligence:
    - DeepSeek R1-0528: Reasoning model, excels at structured extraction from text
    - Qwen 2.5 VL 72B: Vision model, excels at OCR and visual understanding
    - Gemini 3 Pro: Image generation (no alternatives available)

    Example:
        client = GeminiStoryboardClient()

        # Stage 1 + 2: Extract → Refine (automatic model routing)
        understanding = await client.understand_code(
            code_content="def calculate_roi(): ...",
            icp_preset=EPIPHAN_ICP,
            audience="av_director",
        )

        # Stage 3: Generate
        png_bytes = await client.generate_storyboard(
            understanding=understanding,
            stage="preview",
        )
    """

    def __init__(self, config: GeminiConfig | None = None):
        """
        Initialize Gemini client.

        Args:
            config: Optional GeminiConfig (uses env vars if not provided)
        """
        self.config = config or GeminiConfig()
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        """Lazy initialization of Gemini client."""
        if self._initialized:
            return

        if not self.config.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        try:
            from google import genai

            self._client = genai.Client(api_key=self.config.api_key)
            self._initialized = True
            logger.info("[GEMINI] Client initialized successfully")
        except ImportError:
            raise ImportError(
                "google-genai package not installed. "
                "Install with: pip install google-genai"
            )

    async def _call_openrouter_with_retry(
        self,
        payload: dict,
        max_retries: int = 3,
    ) -> str:
        """
        Call OpenRouter API with retry logic for rate limits.

        Args:
            payload: Request payload
            max_retries: Number of retries on rate limit

        Returns:
            Model response text
        """

        if not self.config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        headers = {
            "Authorization": f"Bearer {self.config.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://www.epiphan.com",
            "X-Title": "Epiphan Storyboard Generator",
        }

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                        logger.warning(
                            f"[OPENROUTER] Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"[OPENROUTER] Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                raise

        raise Exception("Max retries exceeded for OpenRouter API")

    async def _call_qwen_vision(
        self,
        prompt: str,
        image_data: bytes | None = None,
        images_data: list[bytes] | None = None,
    ) -> str:
        """
        Call Qwen VL via OpenRouter for vision understanding.

        Args:
            prompt: Text prompt for the model
            image_data: Single image bytes (optional)
            images_data: Multiple image bytes (optional)

        Returns:
            Model response text
        """
        # Build message content
        content = []

        # Add images if provided
        if images_data:
            for img_bytes in images_data[:3]:  # Max 3 images
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    }
                )
        elif image_data:
            img_b64 = base64.b64encode(image_data).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )

        # Add text prompt
        content.append({"type": "text", "text": prompt})

        payload = {
            "model": self.config.qwen_model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4096,
            "temperature": 0.5,  # Higher for creative extraction
        }

        logger.info(f"[QWEN] Calling {self.config.qwen_model} via OpenRouter")
        result = await self._call_openrouter_with_retry(payload)
        logger.info(f"[QWEN] Response received ({len(result)} chars)")
        return result

    async def _call_deepseek(
        self,
        prompt: str,
    ) -> str:
        """
        Call DeepSeek R1 via OpenRouter for text understanding (code/transcripts).

        Args:
            prompt: Text prompt for the model

        Returns:
            Model response text
        """
        payload = {
            "model": self.config.deepseek_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.5,  # Higher for creative extraction
        }

        logger.info(f"[DEEPSEEK] Calling {self.config.deepseek_model} via OpenRouter")
        result = await self._call_openrouter_with_retry(payload)
        logger.info(f"[DEEPSEEK] Response received ({len(result)} chars)")
        return result

    async def _refine_extraction(
        self,
        initial: StoryboardUnderstanding,
        original_content: str,
        content_type: str = "text",
        audience: str = "av_director",
    ) -> StoryboardUnderstanding:
        """
        Stage 2 (REFINE): Use alternate model to validate/improve low-confidence extraction.

        Intelligent routing:
        - If initial extraction used DeepSeek → refine with Qwen (adds vision/structure insight)
        - If initial extraction used Qwen → refine with DeepSeek (adds reasoning depth)

        Args:
            initial: Initial extraction result
            original_content: Original input (code or image description)
            content_type: "text" or "image" to determine which alternate model to use
            audience: Target audience for refinement context

        Returns:
            Refined StoryboardUnderstanding (or original if refinement disabled/unnecessary)
        """
        # Skip refinement if disabled or confidence is high enough
        if not self.config.enable_refinement:
            return initial
        if initial.extraction_confidence >= self.config.refinement_threshold:
            logger.info(
                f"[REFINE] Skipping - confidence {initial.extraction_confidence:.2f} >= threshold {self.config.refinement_threshold}"
            )
            return initial

        logger.info(
            f"[REFINE] Low confidence {initial.extraction_confidence:.2f} - triggering refinement pass"
        )

        # Build refinement prompt with initial extraction context
        refinement_prompt = f"""You are refining an initial extraction that had low confidence ({initial.extraction_confidence:.2f}).

INITIAL EXTRACTION (may be incomplete or inaccurate):
- Headline: "{initial.headline}"
- Tagline: "{initial.tagline}"
- What it does: "{initial.what_it_does}"
- Business value: "{initial.business_value}"
- Pain point: "{initial.pain_point_addressed}"
- Raw extracted: "{initial.raw_extracted_text[:500] if initial.raw_extracted_text else "None"}"

ORIGINAL CONTENT TO RE-ANALYZE:
{original_content[:6000]}

YOUR TASK: Improve and validate this extraction.
- If the initial extraction missed key details, add them
- If the initial extraction was wrong, correct it
- If the initial extraction was too generic, make it specific
- Increase confidence score ONLY if you found concrete details

TARGET AUDIENCE: {audience}

Return ONLY valid JSON matching this exact structure:
{{
    "raw_extracted_text": "...",
    "extraction_confidence": 0.9,
    "headline": "...",
    "tagline": "...",
    "what_it_does": "...",
    "business_value": "...",
    "who_benefits": "...",
    "differentiator": "...",
    "pain_point_addressed": "...",
    "suggested_icon": "..."
}}"""

        try:
            # Route to alternate model based on content type
            if content_type == "text":
                # Text was initially processed by DeepSeek, refine with... DeepSeek again (no vision alt for text)
                # Actually for text, we can try Gemini as alternate
                self._ensure_client()
                logger.info("[REFINE] Using Gemini as alternate for text refinement")
                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=refinement_prompt,
                )
                response_text = response.text
            else:
                # Image was initially processed by Qwen, refine with DeepSeek for reasoning
                logger.info(
                    "[REFINE] Using DeepSeek as alternate for image refinement (reasoning pass)"
                )
                response_text = await self._call_deepseek(refinement_prompt)

            # Parse refined result
            refined = _safe_parse_understanding(response_text, source="refinement")

            # Only use refinement if it actually improved confidence
            if refined.extraction_confidence > initial.extraction_confidence:
                logger.info(
                    f"[REFINE] Improved: {initial.extraction_confidence:.2f} → {refined.extraction_confidence:.2f}"
                )
                return refined
            else:
                logger.info(
                    f"[REFINE] No improvement ({refined.extraction_confidence:.2f}), keeping initial"
                )
                return initial

        except Exception as e:
            logger.warning(
                f"[REFINE] Refinement failed ({e}), keeping initial extraction"
            )
            return initial

    async def _understand(
        self,
        content_type: str,
        *,
        content: str | None = None,
        image_data: bytes | None = None,
        images_data: list[bytes] | None = None,
        audience: str = "av_director",
        file_name: str | None = None,
        context: str | None = None,
        supplementary_context: str | None = None,
    ) -> StoryboardUnderstanding:
        """
        Unified understanding engine for all content types.

        Routes to the appropriate model (text or vision) and handles:
        1. Prompt construction via prompt_builders
        2. Model routing (DeepSeek/Gemini for text, Qwen/Gemini for vision)
        3. Safe JSON parsing via _safe_parse_understanding
        4. Optional refinement pass for low-confidence extractions

        Args:
            content_type: "code", "transcript", "image", or "images"
            content: Text content (code or transcript)
            image_data: Single image bytes (for "image" type)
            images_data: Multiple image bytes (for "images" type)
            audience: Target audience persona
            file_name: Optional file name (code only)
            context: Optional context string (transcript only)
            supplementary_context: Optional text to combine with images
        """
        num_images = len(images_data) if images_data else 1

        # Build prompt via prompt_builders
        prompt = prompt_builders.build_extraction_prompt(
            content_type,
            audience=audience,
            content=content,
            file_name=file_name,
            context=context,
            supplementary_context=supplementary_context,
            num_images=num_images,
        )

        is_vision = content_type in ("image", "images")
        source_label = "multi-image" if content_type == "images" else content_type

        try:
            if is_vision:
                # Vision path: Qwen VL or Gemini vision
                if self.config.vision_provider == "qwen":
                    logger.info(
                        f"[UNDERSTAND] Using Qwen VL ({self.config.qwen_model}) for {source_label} understanding"
                    )
                    response_text = await self._call_qwen_vision(
                        prompt,
                        image_data=image_data,
                        images_data=images_data,
                    )
                else:
                    self._ensure_client()
                    logger.info(
                        f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for {source_label} understanding"
                    )
                    from google.genai import types

                    if images_data:
                        content_parts = [
                            types.Part.from_bytes(data=img, mime_type="image/png")
                            for img in images_data
                        ]
                        content_parts.append(prompt)
                    else:
                        content_parts = [
                            types.Part.from_bytes(
                                data=image_data, mime_type="image/png"
                            ),
                            prompt,
                        ]

                    response = self._client.models.generate_content(
                        model=self.config.gemini_vision_model,
                        contents=content_parts,
                    )
                    response_text = response.text
            else:
                # Text path: DeepSeek or Gemini text
                if self.config.text_provider == "deepseek":
                    logger.info(
                        f"[UNDERSTAND] Using DeepSeek ({self.config.deepseek_model}) for {source_label} understanding"
                    )
                    response_text = await self._call_deepseek(prompt)
                else:
                    self._ensure_client()
                    logger.info(
                        f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for {source_label} understanding"
                    )
                    response = self._client.models.generate_content(
                        model=self.config.gemini_vision_model,
                        contents=prompt,
                    )
                    response_text = response.text

            # Parse with safe fallback (consistent for all content types)
            initial_result = _safe_parse_understanding(
                response_text, source=source_label
            )
            if initial_result.extraction_confidence > 0:
                logger.info(
                    f"[UNDERSTAND] Successfully extracted insights from {source_label}"
                )

            # Stage 2 (REFINE): If low confidence, run through alternate model
            if is_vision:
                # For images, pass raw_extracted_text since we can't re-send the image
                refine_content = f"[{source_label.upper()} DESCRIPTION FROM QWEN VL]\n{initial_result.raw_extracted_text}"
                refine_type = "image"
            else:
                refine_content = content or ""
                refine_type = "text"

            return await self._refine_extraction(
                initial=initial_result,
                original_content=refine_content,
                content_type=refine_type,
                audience=audience,
            )

        except Exception as e:
            logger.error(f"[UNDERSTAND] {source_label} understanding failed: {e}")
            if not is_vision:
                raise
            return _safe_parse_understanding(
                "", source=f"{source_label}-error: {str(e)[:100]}"
            )

    # ── Public thin wrappers (preserve original signatures) ──────────────

    async def understand_code(
        self,
        code_content: str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "av_director",
        file_name: str | None = None,
    ) -> StoryboardUnderstanding:
        """Stage 1: Analyze code and extract business value."""
        return await self._understand(
            "code",
            content=code_content,
            audience=audience,
            file_name=file_name,
        )

    async def understand_transcript(
        self,
        transcript: str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "av_director",
        context: str | None = None,
    ) -> StoryboardUnderstanding:
        """Stage 1: Extract insights from transcript."""
        return await self._understand(
            "transcript",
            content=transcript,
            audience=audience,
            context=context,
        )

    async def understand_image(
        self,
        image_data: bytes | str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "av_director",
        sanitize_ip: bool = True,
        supplementary_context: str | None = None,
    ) -> StoryboardUnderstanding:
        """Stage 1: Analyze image and extract business value."""
        # Handle base64 string input
        if isinstance(image_data, str):
            if image_data.startswith("data:"):
                image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data

        return await self._understand(
            "image",
            image_data=image_bytes,
            audience=audience,
            supplementary_context=supplementary_context,
        )

    async def understand_multiple_images(
        self,
        images_data: list[bytes],
        icp_preset: dict[str, Any] | None = None,
        audience: str = "av_director",
        sanitize_ip: bool = True,
        supplementary_context: str | None = None,
    ) -> StoryboardUnderstanding:
        """Stage 1: Analyze multiple images and extract combined business value."""
        if len(images_data) > 3:
            logger.warning(f"Received {len(images_data)} images, using first 3 only")
            images_data = images_data[:3]

        return await self._understand(
            "images",
            images_data=images_data,
            audience=audience,
            supplementary_context=supplementary_context,
        )

    def _build_generation_content_section(
        self,
        understanding: StoryboardUnderstanding,
        audience: str,
        persona: dict,
    ) -> str:
        """Build audience-specific content section for image generation prompt."""
        knowledge_context = prompt_builders.build_knowledge_context(audience)
        persona_context = prompts.get_persona_generation_context(audience, persona)

        # Customer-focused storyboard (all 8 BDR Playbook personas)
        raw_context = ""
        if understanding.raw_extracted_text:
            raw_context = f"""
RAW EXTRACTION (for context):
{understanding.raw_extracted_text[:500]}
"""

        return f"""CONTENT TO DISPLAY:

{persona_context}

EXTRACTED DATA (organize visually - create your own section headers based on the content):
• {understanding.headline}
• {understanding.what_it_does}
• {understanding.business_value}
• {understanding.differentiator}
• {understanding.pain_point_addressed}

{raw_context}

{knowledge_context if knowledge_context else ""}

VISUAL DESIGN FREEDOM:
- Create section headers based on WHAT the content is about (field/domain names like "Scheduling", "Invoicing", "Crew Management")
- NOT generic labels like "Value Proposition" or "Key Benefit"
- Let icons and visuals communicate - minimize text
- Trust that executives understand visual hierarchy without explicit labels

INDUSTRY GUARDRAILS (CRITICAL - NEVER VIOLATE):
- This is for AV/IT professionals in education, corporate, healthcare, government, and live events
- NEVER mention unrelated industries (no construction, no retail, no agriculture)
- Icons must be AV/IT relevant: cameras, video encoders, displays, lecture halls, meeting rooms, live streams
- The target audience manages video capture, streaming, and recording infrastructure

PROFESSIONAL QUALITY (LinkedIn-ready):
- Must look like it came from a top-tier design agency
- Clean, modern, minimal - no clip art or amateur elements
- Every pixel must be intentional and polished
- Text must be 100% legible at thumbnail size
- Would you put this in front of a university AV director? If not, redo it.

NEVER output generic copy. ALWAYS use specifics from the extraction."""

    async def generate_storyboard(
        self,
        understanding: StoryboardUnderstanding,
        stage: str = "preview",
        audience: str = "av_director",
        output_format: str = "infographic",
        visual_style: str = "polished",
        artist_style: str | None = None,
        icp_preset: dict[str, Any] | None = None,
        custom_style: dict[str, Any] | None = None,
    ) -> bytes:
        """
        Stage 2: Generate beautiful PNG storyboard.

        Uses Gemini Image Generation to create a professional one-page
        executive storyboard ready for email attachment.

        Args:
            understanding: StoryboardUnderstanding from Stage 1
            stage: "preview", "demo", or "shipped" (affects visual style)
            audience: Target audience persona (8 BDR Playbook personas)
            output_format: "infographic" (horizontal 16:9) or "storyboard" (vertical, detailed)
            visual_style: "clean", "polished", "photo_realistic", or "minimalist"
            icp_preset: Optional ICP preset for visual style
            custom_style: Optional custom style overrides

        Returns:
            PNG image bytes
        """
        self._ensure_client()

        from src.tools.storyboard.epiphan_presets import (
            EPIPHAN_ICP,
            get_audience_persona,
            get_stage_template,
        )

        if icp_preset is None:
            icp_preset = EPIPHAN_ICP

        stage_template = get_stage_template(stage)
        visual_style_config = icp_preset.get("visual_style", {})
        persona = get_audience_persona(audience, icp_preset)

        # Add uniqueness to avoid cached/repetitive outputs
        unique_seed = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        # Build audience-specific content section
        content_section = self._build_generation_content_section(
            understanding,
            audience,
            persona,
        )

        # Use extracted tagline - NEVER fall back to canned brand tagline
        # If no tagline extracted, use the headline instead (which is always unique to input)
        dynamic_tagline = (
            understanding.tagline if understanding.tagline else understanding.headline
        )

        # Build the image generation prompt
        prompt = f"""Create a UNIQUE professional one-page executive storyboard infographic.

ANTI-CANNED-COPY RULE (CRITICAL):
- DO NOT use generic marketing phrases like "streamline operations", "get paid faster", "one platform"
- BANNED METAPHORS (NEVER USE): "Frankenstack", "Goldilocks", "Goldilocks Zone", "perfect fit", "daily grind", "fighting fires"
- Every word must come from the EXTRACTED DATA below - nothing else
- If you find yourself writing generic copy, STOP and use the specific extracted content instead
- The headline MUST be "{understanding.headline}" - do not change it
- The tagline/subtitle MUST come from the extracted content, not invented metaphors

GENERATION SEED: {unique_seed} (use this to create variation in layout and icons)

THEME: "{dynamic_tagline}"

{content_section}

VISUAL REQUIREMENTS:
- Style: {stage_template.get("visual_style", "Modern professional")}
- Color scheme: Professional brand palette (MUST USE THESE EXACT COLORS):
  - Primary (CTAs/headers): {visual_style_config.get("primary_color", "#1D2B51")} (dark navy)
  - Accent (highlights/emphasis): {visual_style_config.get("accent_color", "#8CBE3F")} (lime green)
  - Text: {visual_style_config.get("text_color", "#202329")} (dark gray)
  - Background: {visual_style_config.get("hero_bg", "#f6f7f9")} (light gray)
- NO badges, ribbons, or "demo/preview/coming soon" labels - keep it clean and professional
- Include simple icons representing the content (AV/IT/education metaphors)
- Large, readable text (executive-friendly)

TEXT ACCURACY REQUIREMENTS (CRITICAL - DO NOT IGNORE):
- ONLY use the EXACT text provided in the content section above - DO NOT invent or modify words
- Every single word must be spelled correctly - double-check spelling
- Use LARGE fonts (minimum 18pt equivalent) - small text gets garbled
- If you cannot render text clearly, use fewer words or icons instead
- NEVER include random letters or gibberish text
- Keep descriptions SHORT (under 15 words per section) to ensure clarity

{prompts.get_format_layout_instructions(output_format)}

{prompts.get_visual_style_instructions(visual_style)}

{prompts.get_artist_style_instructions(artist_style) if artist_style else ""}

DESIGN PRINCIPLES:
- {visual_style_config.get("aesthetic", "Modern, professional, navy/lime-green palette. Corporate but approachable.")}
- Light gray backgrounds with clean white sections
- Icons should be simple and metaphorical (cameras, displays, charts)
- Ready to share in presentations, emails, LinkedIn, or Slack
- CRITICAL: Use navy/lime-green color palette as specified above
- NO promotional badges or ribbons - this is executive content, not a sales flyer

{prompts.get_format_output_instructions(output_format)}"""

        try:
            from google.genai import types

            # Log key content being sent for debugging
            logger.info(
                f"[GEMINI-IMG] Generating image for audience={audience}, seed={unique_seed}"
            )
            logger.info(f"[GEMINI-IMG] Headline: {understanding.headline}")

            # Use temperature to avoid cached responses
            temperature = 0.9 + random.uniform(0, 0.1)  # 0.9-1.0

            response = self._client.models.generate_content(
                model=self.config.image_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=temperature,
                    seed=random.randint(1, 1000000),  # Random seed for cache busting
                ),
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

            raise ValueError("No image generated in response")

        except Exception as e:
            logger.error(f"[GEMINI] Image generation failed: {e}")
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check if Gemini client is properly configured.

        Returns:
            Health status dictionary
        """
        try:
            self._ensure_client()
            return {
                "status": "healthy",
                "vision_model": self.config.gemini_vision_model,
                "image_model": self.config.image_model,
                "api_key_configured": bool(self.config.api_key),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.config.api_key),
            }
