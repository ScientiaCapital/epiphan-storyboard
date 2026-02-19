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

import os
import json
import base64
import logging
import httpx
from typing import Any, Literal
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _repair_json(json_str: str) -> str:
    """
    Attempt to repair truncated or malformed JSON.

    Common issues from LLM responses:
    - Unterminated strings
    - Missing closing braces
    - Trailing commas
    """
    import re

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
    open_braces = json_str.count('{') - json_str.count('}')
    if open_braces > 0:
        json_str = json_str + '}' * open_braces

    # Remove trailing commas before closing braces
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

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
        logger.error(f"[UNDERSTAND] Raw response was: {response_text[:500] if response_text else 'None'}")
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

    headline: str = Field(..., description="Catchy, benefit-focused headline (8 words max)")
    tagline: str = Field(
        default="One platform for contractors who do it all",
        description="Dynamic tagline specific to content and persona (10 words max)"
    )
    what_it_does: str = Field(..., description="Plain English description (2 sentences max)")
    business_value: str = Field(..., description="Quantified benefit (hours saved, % improvement)")
    who_benefits: str = Field(..., description="Target persona description")
    differentiator: str = Field(..., description="What makes this special (1 sentence)")
    pain_point_addressed: str = Field(..., description="The problem this solves")
    suggested_icon: str = Field(default="clipboard-check", description="Icon suggestion for visual")
    # DEBUG/VERIFICATION fields - for CEO/CTO to verify extraction is correct
    raw_extracted_text: str = Field(
        default="",
        description="Verbatim text/features extracted from input (for debugging/verification)"
    )
    extraction_confidence: float = Field(
        default=1.0,
        description="Confidence score 0-1. Below 0.7 = flag for review"
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
    vision_provider: VisionModel = "qwen"  # For images (default: qwen for better doc understanding)
    text_provider: TextModel = "deepseek"  # For text/transcripts (default: deepseek for best reasoning)

    # Stage 2 (REFINE): Enable multi-model refinement for low-confidence extractions
    enable_refinement: bool = True  # If True, low-confidence extractions get refined by alternate model
    refinement_threshold: float = 0.75  # Confidence below this triggers refinement pass

    # Model identifiers
    gemini_vision_model: str = "models/gemini-2.0-flash"  # Gemini vision model (fallback)
    qwen_model: str = "qwen/qwen2.5-vl-72b-instruct"  # Qwen 2.5 VL 72B - vision + doc understanding
    deepseek_model: str = "deepseek/deepseek-chat"  # DeepSeek V3 - fast, excellent for structured extraction

    # Stage 3 (GENERATE): Image generation (Gemini only - no alternatives)
    image_model: str = "models/gemini-3-pro-image-preview"  # Nano Banana - FREE during preview

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
            icp_preset=COPERNIQ_ICP,
            audience="c_suite",
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
        import asyncio

        if not self.config.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        headers = {
            "Authorization": f"Bearer {self.config.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://coperniq.io",
            "X-Title": "Coperniq Storyboard Generator",
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
                        logger.warning(f"[OPENROUTER] Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
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
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                })
        elif image_data:
            img_b64 = base64.b64encode(image_data).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })

        # Add text prompt
        content.append({
            "type": "text",
            "text": prompt
        })

        payload = {
            "model": self.config.qwen_model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
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
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
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
        audience: str = "c_suite",
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
            logger.info(f"[REFINE] Skipping - confidence {initial.extraction_confidence:.2f} >= threshold {self.config.refinement_threshold}")
            return initial

        logger.info(f"[REFINE] Low confidence {initial.extraction_confidence:.2f} - triggering refinement pass")

        # Build refinement prompt with initial extraction context
        refinement_prompt = f"""You are refining an initial extraction that had low confidence ({initial.extraction_confidence:.2f}).

INITIAL EXTRACTION (may be incomplete or inaccurate):
- Headline: "{initial.headline}"
- Tagline: "{initial.tagline}"
- What it does: "{initial.what_it_does}"
- Business value: "{initial.business_value}"
- Pain point: "{initial.pain_point_addressed}"
- Raw extracted: "{initial.raw_extracted_text[:500] if initial.raw_extracted_text else 'None'}"

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
                logger.info(f"[REFINE] Using Gemini as alternate for text refinement")
                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=refinement_prompt,
                )
                response_text = response.text
            else:
                # Image was initially processed by Qwen, refine with DeepSeek for reasoning
                logger.info(f"[REFINE] Using DeepSeek as alternate for image refinement (reasoning pass)")
                response_text = await self._call_deepseek(refinement_prompt)

            # Parse refined result
            refined = _safe_parse_understanding(response_text, source="refinement")

            # Only use refinement if it actually improved confidence
            if refined.extraction_confidence > initial.extraction_confidence:
                logger.info(f"[REFINE] Improved: {initial.extraction_confidence:.2f} → {refined.extraction_confidence:.2f}")
                return refined
            else:
                logger.info(f"[REFINE] No improvement ({refined.extraction_confidence:.2f}), keeping initial")
                return initial

        except Exception as e:
            logger.warning(f"[REFINE] Refinement failed ({e}), keeping initial extraction")
            return initial

    async def understand_code(
        self,
        code_content: str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "c_suite",
        file_name: str | None = None,
    ) -> StoryboardUnderstanding:
        """
        Stage 1: Analyze code and extract business value.

        Minimal constraints - let the model find what matters.
        Zero hardcoded company/product info.

        Args:
            code_content: Source code as string
            icp_preset: Optional ICP config (ignored - kept for API compatibility)
            audience: Target audience persona
            file_name: Optional file name for context

        Returns:
            StoryboardUnderstanding with extracted insights
        """
        # Build dynamic context from knowledge cache only
        knowledge_context = self._build_knowledge_context(audience)
        language_guidelines = self._build_language_guidelines_minimal(audience)
        value_angle_instruction = self._get_value_angle_instruction(audience)

        # Cache-busting: unique identifier per request to prevent API caching
        import uuid
        from datetime import datetime
        request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        prompt = f"""Analyze this code and extract business value.
REQUEST_ID: {request_id}

{f"File: {file_name}" if file_name else ""}

CODE:
```
{code_content[:8000]}
```

TARGET AUDIENCE: {audience}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

EXTRACT:
- What does this code do (plain English)?
- Who benefits from this?
- What problem does it solve?
- What makes it special?

{value_angle_instruction}

CRITICAL RULES:
- NEVER include personal names - use roles/personas (e.g., "Operations Team" not "John")
- ALWAYS derive business value - infer from the problem being solved
- If value isn't explicit, INFER it

Return JSON:
{{
    "raw_extracted_text": "Key technical elements: classes, functions, logic",
    "extraction_confidence": 0.0-1.0,
    "headline": "Benefit-focused headline (8 words max)",
    "tagline": "Unique to THIS code (10 words max)",
    "what_it_does": "Plain English (2 sentences max)",
    "business_value": "ALWAYS provide value - quantified if possible, inferred if not",
    "who_benefits": "Role/persona titles ONLY - NO personal names",
    "differentiator": "What makes it special",
    "pain_point_addressed": "Problem solved",
    "suggested_icon": "Simple icon name"
}}"""

        try:
            # Route to DeepSeek or Gemini based on config
            if self.config.text_provider == "deepseek":
                logger.info(f"[UNDERSTAND] Using DeepSeek ({self.config.deepseek_model}) for code understanding")
                response_text = await self._call_deepseek(prompt)
            else:
                # Use Gemini
                self._ensure_client()
                logger.info(f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for code understanding")
                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=prompt,
                )
                response_text = response.text

            # Parse JSON response
            json_str = response_text.strip()
            # Handle markdown code blocks
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                json_str = json_str.strip()

            data = json.loads(json_str)
            initial_result = StoryboardUnderstanding(**data)

            # Stage 2 (REFINE): If low confidence, run through alternate model
            refined_result = await self._refine_extraction(
                initial=initial_result,
                original_content=code_content,
                content_type="text",
                audience=audience,
            )
            return refined_result

        except json.JSONDecodeError as e:
            logger.error(f"[UNDERSTAND] Failed to parse response: {e}")
            logger.error(f"[UNDERSTAND] Raw response was: {response_text[:500] if response_text else 'None'}")
            # DO NOT return generic fallback - that hides extraction failures
            # Instead, return with low confidence so user knows to check
            return StoryboardUnderstanding(
                headline="EXTRACTION FAILED - Check Input",
                tagline="Could not extract content from this code",
                what_it_does="The AI could not parse this input. Try a different code file or check formatting.",
                business_value="Unable to determine - extraction failed",
                who_benefits="Unable to determine - extraction failed",
                differentiator="Unable to determine - extraction failed",
                pain_point_addressed="Unable to determine - extraction failed",
                suggested_icon="alert-triangle",
                raw_extracted_text=f"PARSE ERROR: {str(e)[:200]}",
                extraction_confidence=0.0,  # Zero confidence = failed
            )
        except Exception as e:
            logger.error(f"[GEMINI] Understanding failed: {e}")
            raise

    async def understand_transcript(
        self,
        transcript: str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "c_suite",
        context: str | None = None,
    ) -> StoryboardUnderstanding:
        """
        Stage 1: Extract insights from transcript with minimal constraints.

        Let the model find what matters. Zero hardcoded company/product info.

        Args:
            transcript: Full transcript text (up to 32K chars)
            icp_preset: Optional ICP config (ignored - kept for API compatibility)
            audience: Target audience for tone/focus
            context: Optional context (e.g., "Sales call", "Demo")

        Returns:
            StoryboardUnderstanding with insights extracted FROM the transcript
        """
        # Build dynamic knowledge context (from cache, or empty)
        knowledge_context = self._build_knowledge_context(audience)
        language_guidelines = self._build_language_guidelines_minimal(audience)

        # Get value angle for this audience
        value_angle_instruction = self._get_value_angle_instruction(audience)

        # Cache-busting: unique identifier per request to prevent API caching
        import uuid
        from datetime import datetime
        request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        prompt = f"""Extract key insights from this content.
REQUEST_ID: {request_id}

{f"CONTEXT: {context}" if context else ""}

CONTENT:
{transcript[:32000]}

TARGET AUDIENCE: {audience}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

EXTRACTION PRIORITIES:
- Preserve EXACT quotes and specific numbers
- Note speaker ROLES (not personal names - generalize to "Field Tech", "Project Manager", "Operations Team")
- Find what would resonate with {audience}
- ALWAYS derive business value - infer it from context if not explicitly stated

{value_angle_instruction}

CRITICAL RULES:
- NEVER output "Not mentioned in transcript" - always derive/infer value
- NEVER include personal names - use titles/roles/personas instead (e.g., "Operations Team" not "John and Sarah")
- If value isn't explicit, INFER it from the problem being solved

Return JSON:
{{
    "raw_extracted_text": "Key quotes, numbers, specifics from content",
    "extraction_confidence": 0.0-1.0,
    "headline": "Punchy headline from content (8 words max)",
    "tagline": "Unique to this content (10 words max)",
    "what_it_does": "Plain English (2 sentences max)",
    "business_value": "ALWAYS provide value - quantified if possible, inferred if not",
    "who_benefits": "Role/persona titles ONLY (e.g., 'Field Crews', 'Operations Teams') - NO personal names",
    "differentiator": "What stands out",
    "pain_point_addressed": "Problem solved",
    "suggested_icon": "Simple icon name"
}}"""

        try:
            # Route to DeepSeek or Gemini based on config
            if self.config.text_provider == "deepseek":
                logger.info(f"[UNDERSTAND] Using DeepSeek ({self.config.deepseek_model}) for transcript understanding")
                response_text = await self._call_deepseek(prompt)
            else:
                # Use Gemini
                self._ensure_client()
                logger.info(f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for transcript understanding")
                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=prompt,
                )
                response_text = response.text

            # Parse JSON response with safe fallback
            initial_result = _safe_parse_understanding(response_text, source="transcript")
            if initial_result.extraction_confidence > 0:
                logger.info(f"[UNDERSTAND] Successfully extracted insights from transcript for {audience}")

            # Stage 2 (REFINE): If low confidence, run through alternate model
            refined_result = await self._refine_extraction(
                initial=initial_result,
                original_content=transcript,
                content_type="text",
                audience=audience,
            )
            return refined_result

        except Exception as e:
            logger.error(f"[GEMINI] Transcript understanding failed: {e}")
            return _safe_parse_understanding("", source=f"transcript-error: {str(e)[:100]}")

    def _get_persona_extraction_focus(self, audience: str, audience_info: dict) -> str:
        """Get persona-specific extraction instructions."""
        extractions = {
            "business_owner": """FOCUS FOR BUSINESS OWNER:
- What PROFIT or REVENUE impact was discussed?
- What TIME savings would they get back (family time, less nights/weekends)?
- What HEADACHES would disappear?
- Did they mention competitors or falling behind?""",

            "c_suite": """FOCUS FOR C-SUITE EXECUTIVE:
- What ROI or METRICS were mentioned?
- What SCALABILITY or GROWTH enablement was discussed?
- What DATA or VISIBILITY improvements?
- What COMPETITIVE advantages?""",

            "btl_champion": """FOCUS FOR OPERATIONS/PROJECT MANAGER:
- What DAILY FRUSTRATIONS would be eliminated?
- What COORDINATION problems were mentioned?
- What would their TEAM actually use?
- How does this reduce fire-fighting and chaos?""",

            "top_tier_vc": """FOCUS FOR VC/INVESTOR:
- What MARKET SIZE indicators were mentioned?
- What TRACTION or GROWTH metrics?
- What MOAT or defensibility?
- What makes this a CATEGORY-DEFINING opportunity?""",

            "field_crew": """FOCUS FOR FIELD CREW:
- What would make their JOB EASIER?
- What PAPERWORK or HASSLE would disappear?
- What TOOLS would they actually use on the job site?
- Keep it SIMPLE - 5th grade vocabulary.""",
        }
        return extractions.get(audience, extractions["c_suite"])

    async def understand_image(
        self,
        image_data: bytes | str,
        icp_preset: dict[str, Any] | None = None,
        audience: str = "c_suite",
        sanitize_ip: bool = True,
        supplementary_context: str | None = None,
    ) -> StoryboardUnderstanding:
        """
        Stage 1: Analyze image and extract business value.

        Minimal constraints - let the model find what matters.
        Zero hardcoded company/product info.

        Args:
            image_data: Image bytes or base64 string
            icp_preset: Optional ICP config (ignored - kept for API compatibility)
            audience: Target audience persona
            sanitize_ip: Whether to apply extra IP sanitization
            supplementary_context: Optional text context (transcript, notes) to combine with image

        Returns:
            StoryboardUnderstanding with extracted insights
        """
        # Handle base64 string input
        if isinstance(image_data, str):
            if image_data.startswith("data:"):
                # Remove data URL prefix
                image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data

        # Build dynamic context from knowledge cache only
        knowledge_context = self._build_knowledge_context(audience)
        language_guidelines = self._build_language_guidelines_minimal(audience)
        value_angle_instruction = self._get_value_angle_instruction(audience)

        # Cache-busting: unique identifier per request to prevent API caching
        import uuid
        from datetime import datetime
        request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        # Build text context section - TEXT IS A PRIMARY INPUT, NOT SECONDARY
        context_section = ""
        has_text = supplementary_context and supplementary_context.strip()
        if has_text:
            context_section = f"""=== PRIMARY INPUT #1: TEXT TRANSCRIPT ===
This text is a PRIMARY INPUT with EQUAL weight to the image below.
Extract insights from THIS TEXT FIRST, then synthesize with the image.

{supplementary_context[:16000]}
=== END TEXT INPUT ===

"""

        # When we have both text and image, start with text context so LLM processes it first
        prompt = f"""{context_section}{"CRITICAL: You have TWO primary inputs above:" if has_text else ""}
{"1. TEXT TRANSCRIPT (above) - contains key conversation/description content" if has_text else ""}
{"2. IMAGE (below) - contains visual/structural information" if has_text else ""}
{"Extract from BOTH sources and MERGE insights. Neither is more important." if has_text else ""}

{"Analyze BOTH the text above AND this image. Extract ALL content from BOTH sources." if has_text else "Analyze this image and extract ALL content."}
REQUEST_ID: {request_id}

{"PRIORITY: The text transcript likely contains the MAIN MESSAGE and TALKING POINTS. The image provides VISUAL CONTEXT. Combine them." if has_text else "CRITICAL: Extract the ACTUAL content from this image."}
Do NOT generate generic copy. Do NOT make things up.

TARGET AUDIENCE: {audience}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

EXTRACT:
- Every label, feature name, number visible
- Hierarchy/structure if present
- Timing, versions, phases if shown
- Workflow steps, connections, relationships

{value_angle_instruction}

CRITICAL RULES:
- NEVER output "Not mentioned in transcript/image" - always INFER from context
- NEVER include personal names - use roles/personas (e.g., "Project Managers" not "John")
- ALWAYS derive business value and problem solved - infer from what you see
- If something isn't explicit, INFER it from the context

Return JSON:
{{
    "raw_extracted_text": "Everything visible: labels, names, numbers",
    "extraction_confidence": 0.0-1.0,
    "headline": "Main theme from image (8 words max)",
    "tagline": "Unique to THIS content (10 words max)",
    "what_it_does": "Specific features/areas shown",
    "business_value": "INFER value from what this enables - never say 'not mentioned'",
    "who_benefits": "Role/persona titles ONLY - NO personal names",
    "differentiator": "What makes this special",
    "pain_point_addressed": "INFER the problem this solves - never say 'not mentioned'",
    "suggested_icon": "Icon representing content"
}}"""

        try:
            # Route to Qwen VL or Gemini based on config
            if self.config.vision_provider == "qwen":
                logger.info(f"[UNDERSTAND] Using Qwen VL ({self.config.qwen_model}) for image understanding")
                response_text = await self._call_qwen_vision(prompt, image_data=image_bytes)
            else:
                # Use Gemini
                self._ensure_client()
                logger.info(f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for image understanding")
                from google.genai import types

                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/png",
                )

                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=[image_part, prompt],
                )
                response_text = response.text

            # Parse JSON response with safe fallback
            initial_result = _safe_parse_understanding(response_text, source="image")
            if initial_result.extraction_confidence > 0:
                logger.info(f"[UNDERSTAND] Successfully extracted insights from image")

            # Stage 2 (REFINE): If low confidence, run through DeepSeek for reasoning pass
            # For images, we pass the raw_extracted_text as context since we can't re-send the image
            refined_result = await self._refine_extraction(
                initial=initial_result,
                original_content=f"[IMAGE DESCRIPTION FROM QWEN VL]\n{initial_result.raw_extracted_text}",
                content_type="image",
                audience=audience,
            )
            return refined_result

        except Exception as e:
            logger.error(f"[GEMINI] Image understanding failed: {e}")
            return _safe_parse_understanding("", source=f"image-error: {str(e)[:100]}")

    async def understand_multiple_images(
        self,
        images_data: list[bytes],
        icp_preset: dict[str, Any] | None = None,
        audience: str = "c_suite",
        sanitize_ip: bool = True,
        supplementary_context: str | None = None,
    ) -> StoryboardUnderstanding:
        """
        Stage 1: Analyze multiple images and extract combined business value.

        Minimal constraints - let the model find what matters.
        Zero hardcoded company/product info.

        Args:
            images_data: List of image bytes (up to 3 images)
            icp_preset: Optional ICP config (ignored - kept for API compatibility)
            audience: Target audience persona
            sanitize_ip: Whether to apply extra IP sanitization
            supplementary_context: Optional text context (transcript, notes) to combine with images

        Returns:
            StoryboardUnderstanding with combined insights from all images
        """
        if len(images_data) > 3:
            logger.warning(f"Received {len(images_data)} images, using first 3 only")
            images_data = images_data[:3]

        # Build dynamic context from knowledge cache only
        knowledge_context = self._build_knowledge_context(audience)
        language_guidelines = self._build_language_guidelines_minimal(audience)
        value_angle_instruction = self._get_value_angle_instruction(audience)

        # Cache-busting: unique identifier per request to prevent API caching
        import uuid
        from datetime import datetime
        request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        # Build text context section - TEXT IS A PRIMARY INPUT, NOT SECONDARY
        context_section = ""
        has_text = supplementary_context and supplementary_context.strip()
        if has_text:
            context_section = f"""=== PRIMARY INPUT #1: TEXT TRANSCRIPT ===
This text is a PRIMARY INPUT with EQUAL weight to the images below.
Extract insights from THIS TEXT FIRST, then synthesize with the images.

{supplementary_context[:16000]}
=== END TEXT INPUT ===

"""

        # When we have both text and images, start with text context so LLM processes it first
        prompt = f"""{context_section}{"CRITICAL: You have MULTIPLE primary inputs:" if has_text else ""}
{"1. TEXT TRANSCRIPT (above) - contains key conversation/description content" if has_text else ""}
{"2. IMAGES (below) - contain visual/structural information" if has_text else ""}
{"Extract from ALL sources and MERGE insights. Text and images are equally important." if has_text else ""}

{"Analyze BOTH the text above AND these " + str(len(images_data)) + " images. Extract ALL content from ALL sources." if has_text else f"Analyze these {len(images_data)} images and extract ALL content."}
REQUEST_ID: {request_id}

{"PRIORITY: The text transcript likely contains the MAIN MESSAGE and TALKING POINTS. The images provide VISUAL CONTEXT. Combine them." if has_text else "CRITICAL: Extract ACTUAL content from each image."}
Do NOT generate generic copy. Do NOT make things up.

TARGET AUDIENCE: {audience}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

EXTRACT FROM EACH IMAGE:
- Every label, feature name, number visible
- Hierarchy/structure if present
- Timing, versions, phases if shown
- Workflow steps, connections, relationships

{value_angle_instruction}

Then SYNTHESIZE into unified message.

CRITICAL RULES:
- NEVER output "Not mentioned" - always INFER from context
- NEVER include personal names - use roles/personas
- ALWAYS derive business value and problem solved

Return JSON:
{{
    "raw_extracted_text": "IMAGE 1: [content]... IMAGE 2: [content]...",
    "extraction_confidence": 0.0-1.0,
    "headline": "Synthesized theme (8 words max)",
    "tagline": "Unique to THIS content (10 words max)",
    "what_it_does": "Specific features across images",
    "business_value": "Numbers from images if present",
    "who_benefits": "Who would use this",
    "differentiator": "What makes this special",
    "pain_point_addressed": "Problem solved",
    "suggested_icon": "Icon representing theme"
}}"""

        try:
            # Route to Qwen VL or Gemini based on config
            if self.config.vision_provider == "qwen":
                logger.info(f"[UNDERSTAND] Using Qwen VL ({self.config.qwen_model}) for {len(images_data)} images")
                response_text = await self._call_qwen_vision(prompt, images_data=images_data)
            else:
                # Use Gemini
                self._ensure_client()
                logger.info(f"[UNDERSTAND] Using Gemini ({self.config.gemini_vision_model}) for {len(images_data)} images")
                from google.genai import types

                # Create image parts for all images
                content_parts = []
                for i, img_bytes in enumerate(images_data):
                    image_part = types.Part.from_bytes(
                        data=img_bytes,
                        mime_type="image/png",
                    )
                    content_parts.append(image_part)

                # Add the prompt at the end
                content_parts.append(prompt)

                response = self._client.models.generate_content(
                    model=self.config.gemini_vision_model,
                    contents=content_parts,
                )
                response_text = response.text

            # Parse JSON response with safe fallback
            initial_result = _safe_parse_understanding(response_text, source="multi-image")
            if initial_result.extraction_confidence > 0:
                logger.info(f"[GEMINI] Successfully understood {len(images_data)} images together")

            # Stage 2 (REFINE): If low confidence, run through DeepSeek for reasoning pass
            refined_result = await self._refine_extraction(
                initial=initial_result,
                original_content=f"[MULTI-IMAGE DESCRIPTION FROM QWEN VL]\n{initial_result.raw_extracted_text}",
                content_type="image",
                audience=audience,
            )
            return refined_result

        except Exception as e:
            logger.error(f"[GEMINI] Multi-image understanding failed: {e}")
            return _safe_parse_understanding("", source=f"multi-image-error: {str(e)[:100]}")

    async def generate_storyboard(
        self,
        understanding: StoryboardUnderstanding,
        stage: str = "preview",
        audience: str = "c_suite",
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
            audience: Target audience (top_tier_vc uses different structure)
            output_format: "infographic" (horizontal 16:9) or "storyboard" (vertical, detailed)
            visual_style: "clean", "polished", "photo_realistic", or "minimalist"
            icp_preset: Optional ICP preset for visual style
            custom_style: Optional custom style overrides

        Returns:
            PNG image bytes
        """
        self._ensure_client()

        from src.tools.storyboard.coperniq_presets import (
            COPERNIQ_ICP,
            COPERNIQ_BRAND,
            get_stage_template,
            get_audience_persona,
        )

        if icp_preset is None:
            icp_preset = COPERNIQ_ICP

        import uuid
        from datetime import datetime

        stage_template = get_stage_template(stage)
        visual_style_config = icp_preset.get("visual_style", {})
        brand = COPERNIQ_BRAND
        persona = get_audience_persona(audience, icp_preset)

        # Add uniqueness to avoid cached/repetitive outputs
        unique_seed = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

        # Build audience-specific content structure
        # Get dynamic proof points from knowledge cache
        knowledge_context = self._build_knowledge_context(audience)

        # Build persona-specific generation context (value angle, what they care about)
        persona_context = self._build_persona_generation_context(audience, persona)

        if audience == "top_tier_vc":
            # VC/Investor storyboard - flexible investment thesis

            # Include raw extraction for richer context
            raw_context = ""
            if understanding.raw_extracted_text:
                raw_context = f"""
SOURCE MATERIAL (use to derive specific insights):
{understanding.raw_extracted_text[:600]}
"""

            content_section = f"""CONTENT FOR INVESTOR AUDIENCE:

{persona_context}

WHAT WE EXTRACTED:
- Core Insight: "{understanding.headline}"
- Problem Space: "{understanding.pain_point_addressed}"
- Solution: "{understanding.what_it_does}"
- Differentiator: "{understanding.differentiator}"
- Business Value: "{understanding.business_value}"
{raw_context}

{knowledge_context if knowledge_context else ""}

CREATIVE FREEDOM: Design the visual however best tells this story.
You choose the layout, sections, and flow. No rigid template required.
Make it visually compelling - this could end up in a pitch deck."""
        else:
            # Customer-focused storyboard (sales, internal, field crew)

            # Include raw extraction for context (if available)
            raw_context = ""
            if understanding.raw_extracted_text:
                raw_context = f"""
RAW EXTRACTION (for context):
{understanding.raw_extracted_text[:500]}
"""

            content_section = f"""CONTENT TO DISPLAY:

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
- This is for MEP contractors: ELECTRICAL, HVAC, PLUMBING, SOLAR, ENERGY contractors
- NEVER mention unrelated industries (no beef, no agriculture, no manufacturing, no retail)
- Icons must be construction/trades relevant: trucks, tools, clipboards, hard hats, wrenches, wire, pipes, solar panels
- If the input mentions an unrelated industry, IGNORE it and focus on MEP contractor context
- The target audience runs field service crews, does installations, handles permits, manages subcontractors

PROFESSIONAL QUALITY (LinkedIn-ready):
- Must look like it came from a top-tier design agency
- Clean, modern, minimal - no clip art or amateur elements
- Every pixel must be intentional and polished
- Text must be 100% legible at thumbnail size
- Would you put this in front of a $10M contractor? If not, redo it.

NEVER output generic copy. ALWAYS use specifics from the extraction."""

        # Use extracted tagline - NEVER fall back to canned brand tagline
        # If no tagline extracted, use the headline instead (which is always unique to input)
        dynamic_tagline = understanding.tagline if understanding.tagline else understanding.headline

        # Build the image generation prompt
        prompt = f"""Create a UNIQUE professional one-page executive storyboard infographic.

ANTI-CANNED-COPY RULE (CRITICAL):
- DO NOT use generic marketing phrases like "streamline operations", "get paid faster", "one platform"
- BANNED METAPHORS (NEVER USE): "Frankenstack", "Goldilocks", "Goldilocks Zone", "perfect fit", "daily grind", "fighting fires", "2026 Software"
- Every word must come from the EXTRACTED DATA below - nothing else
- If you find yourself writing generic copy, STOP and use the specific extracted content instead
- The headline MUST be "{understanding.headline}" - do not change it
- The tagline/subtitle MUST come from the extracted content, not invented metaphors

GENERATION SEED: {unique_seed} (use this to create variation in layout and icons)

THEME: "{dynamic_tagline}"

{content_section}

VISUAL REQUIREMENTS:
- Style: {stage_template.get('visual_style', 'Modern professional')}
- Color scheme: Professional teal/green palette (MUST USE THESE EXACT COLORS):
  - Primary (CTAs/headers): {visual_style_config.get('primary_color', '#23433E')} (dark teal/forest green)
  - Accent (highlights/emphasis): {visual_style_config.get('accent_color', '#2D9688')} (teal)
  - Text: {visual_style_config.get('text_color', '#333333')} (dark gray)
  - Background: {visual_style_config.get('hero_bg', '#DDEDEB')} (light mint/sage green)
- NO badges, ribbons, or "demo/preview/coming soon" labels - keep it clean and professional
- Include simple icons representing the content (construction/business metaphors)
- Large, readable text (executive-friendly)

TEXT ACCURACY REQUIREMENTS (CRITICAL - DO NOT IGNORE):
- ONLY use the EXACT text provided in the content section above - DO NOT invent or modify words
- Every single word must be spelled correctly - double-check spelling
- Use LARGE fonts (minimum 18pt equivalent) - small text gets garbled
- If you cannot render text clearly, use fewer words or icons instead
- NEVER include random letters or gibberish text
- Keep descriptions SHORT (under 15 words per section) to ensure clarity

{self._get_format_layout_instructions(output_format)}

{self._get_visual_style_instructions(visual_style)}

{self._get_artist_style_instructions(artist_style) if artist_style else ""}

DESIGN PRINCIPLES:
- {visual_style_config.get('aesthetic', 'Modern, professional, teal/green palette. Corporate but approachable.')}
- Light mint/sage backgrounds with clean white sections
- Icons should be simple and metaphorical (tools, buildings, charts)
- Ready to share in presentations, emails, LinkedIn, or Slack
- CRITICAL: Use teal/green color palette, NOT orange or blue
- NO promotional badges or ribbons - this is executive content, not a sales flyer

{self._get_format_output_instructions(output_format)}"""

        try:
            from google.genai import types
            import random

            # Log key content being sent for debugging
            logger.info(f"[GEMINI-IMG] Generating image for audience={audience}, seed={unique_seed}")
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

    def _build_language_guidelines(self, icp_preset: dict[str, Any], audience: str = "c_suite") -> str:
        """Build language guidelines string for prompts, enriched with knowledge."""
        # Get static defaults from preset
        avoid = icp_preset.get("language_style", {}).get("avoid", [])
        use = icp_preset.get("language_style", {}).get("use", [])
        tone = icp_preset.get("tone", "Friendly and professional")

        # Merge with dynamic knowledge from cache
        try:
            from src.knowledge.cache import KnowledgeCache
            cache = KnowledgeCache.get()
            if cache.is_loaded():
                knowledge = cache.get_language_guidelines(audience)
                # Knowledge terms take priority (fresher data from real conversations)
                avoid = list(set(knowledge["avoid"] + avoid))[:15]
                use = list(set(knowledge["use"] + use))[:15]
        except Exception:
            pass  # Graceful degradation - use static presets only

        return f"""LANGUAGE GUIDELINES:
- Tone: {tone}
- AVOID these words/phrases: {', '.join(avoid[:15])}
- USE these words/phrases: {', '.join(use[:15])}
- Write for someone with no technical background
- Focus on benefits, not features"""

    def _build_knowledge_context(self, audience: str) -> str:
        """Build knowledge context section for prompts."""
        try:
            from src.knowledge.cache import KnowledgeCache
            cache = KnowledgeCache.get()
            if not cache.is_loaded():
                return ""

            ctx = cache.get_context(audience)

            if not any([ctx["pain_points"], ctx["features"], ctx["metrics"]]):
                return ""

            sections = []
            if ctx["pain_points"]:
                sections.append(f"CUSTOMER PAIN POINTS (from real calls): {'; '.join(ctx['pain_points'])}")
            if ctx["features"]:
                sections.append(f"PRODUCT FEATURES TO REFERENCE: {', '.join(ctx['features'])}")
            if ctx["metrics"]:
                sections.append(f"PROOF POINTS TO USE: {'; '.join(ctx['metrics'])}")
            if ctx.get("quotes"):
                sections.append(f"CUSTOMER QUOTES: {'; '.join(ctx['quotes'])}")

            return "\n".join(sections)
        except Exception:
            return ""  # Graceful degradation

    def _get_value_angle_instruction(self, audience: str) -> str:
        """
        Get value angle framing instruction for extraction based on audience.

        This ensures the extraction phase knows HOW to frame value:
        - COI (Cost of Inaction): What they LOSE by not acting
        - ROI (Return on Investment): What they GAIN by acting
        - EASE: How much simpler their life becomes
        """
        value_angles = {
            "business_owner": """VALUE FRAMING: COI (Cost of Inaction) - AMPLIFIED

SPEAK TO THE FOUNDER'S WEIGHT:
- What are they BLEEDING every day they don't act?
- Cash walking out the door, jobs going sideways
- Sleepless nights wondering what fell through the cracks
- "Your competitors already figured this out"

VOCABULARY THAT HITS:
- "bleeding money", "my guys", "cash flow", "keeping the lights on"
- "I built this", "sleepless nights", "finally get control"
- "make payroll", "skin in the game"

FORBIDDEN (sounds corporate, not founder):
- "stakeholders", "enterprise solution", "synergize", "leverage"

EMOTIONAL CORE: Loss aversion. Fear of missing out. Founder anxiety meets pragmatic hope.
""",
            "c_suite": """VALUE FRAMING: ROI (Return on Investment) - AMPLIFIED

SPEAK BOARDROOM LANGUAGE:
- Every word must earn its place. Numbers speak louder than adjectives.
- X invested → Y returned. Payback in Z months.
- Show the math they can take to the board.

VOCABULARY THAT RESONATES:
- "margin improvement", "operational leverage", "unit economics"
- "payback period", "scale efficiently", "competitive moat"
- "data-driven", "visibility", "reduce overhead"

FORBIDDEN (sounds like marketing fluff):
- "game-changing", "revolutionary", "best-in-class", "paradigm shift"

EMOTIONAL CORE: Validation through data. Strategic advantage. Looking smart to the board.
""",
            "btl_champion": """VALUE FRAMING: COI (Cost of Inaction) - AMPLIFIED

THE DAILY REALITY:
- Every fire you're fighting today? There's a tool that prevents it
- Finally get the coordination problem under control
- Stop chasing updates and start getting ahead

VOCABULARY THAT RESONATES:
- "fires to put out", "chasing updates", "prove it works"
- "the team will actually use this", "less headaches"
- "one less thing", "finally under control", "save time"

FORBIDDEN (sounds like enterprise sales):
- "enterprise-grade", "holistic solution", "comprehensive platform"

EMOTIONAL CORE: Daily grind empathy. Practical solutions for real frustrations.
""",
            "top_tier_vc": """VALUE FRAMING: ROI (Return on Investment) - AMPLIFIED

PATTERN-MATCHING INVESTOR BRAIN:
- Show the moat. Prove the momentum. No fluff.
- Market timing, founder-market fit, category creation potential
- Unit economics that actually work

VOCABULARY THAT RESONATES:
- "defensible moat", "network effects", "land and expand"
- "negative churn", "CAC payback", "LTV/CAC ratio"
- "gross margin", "market timing", "founder-market fit"

FORBIDDEN (every pitch deck says this):
- "disruptive", "revolutionary", "game-changing", "Uber for X"

EMOTIONAL CORE: Fear of missing the next big thing. Pattern recognition. Return potential.
""",
            "field_crew": """VALUE FRAMING: EASE (Simplicity) - AMPLIFIED

BUDDY ON THE JOBSITE:
- No corporate BS. Just show me it works.
- Less hassle. Less paperwork. Get home on time.
- One tap. Done. Works even offline.

VOCABULARY THAT RESONATES:
- "get it done", "no BS", "works offline", "one tap"
- "no training needed", "my truck", "the job"
- "clock out on time", "just works"

FORBIDDEN (sounds like office people):
- "optimize", "leverage", "utilize", "streamline"
- "stakeholder", "implementation", "enterprise", "scalable"

EMOTIONAL CORE: Make my day easier. Keep it simple. Let me get home on time.
""",
        }
        return value_angles.get(audience, value_angles["c_suite"])

    def _build_language_guidelines_minimal(self, audience: str) -> str:
        """
        Build minimal language guidelines from knowledge cache only.

        Zero hardcoding - only uses dynamic data from knowledge cache.
        Returns empty string if cache not loaded or empty.
        """
        try:
            from src.knowledge.cache import KnowledgeCache
            cache = KnowledgeCache.get()
            if not cache.is_loaded():
                return ""

            knowledge = cache.get_language_guidelines(audience)
            avoid = knowledge.get("avoid", [])[:10]
            use = knowledge.get("use", [])[:10]

            if not avoid and not use:
                return ""

            parts = []
            if avoid:
                parts.append(f"AVOID: {', '.join(avoid)}")
            if use:
                parts.append(f"USE: {', '.join(use)}")

            return "\n".join(parts)
        except Exception:
            return ""  # Graceful degradation

    def _build_persona_generation_context(self, audience: str, persona: dict) -> str:
        """
        Build persona-specific context for image generation.

        CRITICAL: Only provides high-level GUIDANCE, not literal content.
        - Value angle (COI/ROI/EASE) tells HOW to frame
        - Visual style tells WHAT to design
        - Forbidden phrases are guardrails only
        - NO vocabulary or cares_about - these caused literal rendering

        The EXTRACTION phase already outputs persona-appropriate content.
        This method just guides the VISUAL treatment.
        """
        title = persona.get("title", audience)
        voice_tone = persona.get("voice_tone", "")
        forbidden = persona.get("forbidden_phrases", [])
        default_style = persona.get("default_visual_style", "polished")

        # Field Crew: Super simple, 5th grade vocabulary
        if audience == "field_crew":
            style = persona.get("infographic_style", {})
            language_rules = style.get('language_rules', ['Use 5th grade vocabulary'])[:3]
            return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: EASE - show how this makes the job easier (no ROI/savings talk)
VISUAL STYLE: {default_style} (hand-drawn, approachable, no corporate feel)
DESIGN: {style.get('design', 'Simple icons, big text, minimal words')}
LANGUAGE: {'; '.join(language_rules)}
AVOID WORDS: {', '.join(forbidden[:5])}"""

        # C-Suite: Data and numbers focus
        if audience == "c_suite":
            return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ROI - show the math, metrics, and return on investment
VISUAL STYLE: {default_style} (charts, graphs, numbers prominent)
DESIGN: Clean data visualization, McKinsey/BCG aesthetic, executive summary format
AVOID WORDS: {', '.join(forbidden[:5])}"""

        # Business Owner: Emotional pain→solution story
        if audience == "business_owner":
            return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI (Cost of Inaction) - emphasize what they LOSE by not acting
VISUAL STYLE: {default_style} (modern SaaS, Stripe/Linear quality)
DESIGN: Emotional hook, pain → solution narrative, relatable founder energy
AVOID WORDS: {', '.join(forbidden[:5])}"""

        # BTL Champion: Day-in-life practical benefits
        if audience == "btl_champion":
            return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: COI - the daily cost of not having this, reduce daily frustration
VISUAL STYLE: {default_style} (professional infographic, shareable internally)
DESIGN: Day-in-life scenarios, practical benefits, before/after comparison
AVOID WORDS: {', '.join(forbidden[:5])}"""

        # VC/Investor: Investment thesis format
        if audience == "top_tier_vc":
            return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: ROI - market opportunity, defensibility, return profile
VISUAL STYLE: {default_style} (bold, memorable pitch deck slide)
DESIGN: Investment thesis format, show the moat, prove momentum with data
AVOID WORDS: {', '.join(forbidden[:5])}, book a demo, contact sales, free trial"""

        # Default fallback
        return f"""FOR: {title}
VOICE: {voice_tone}
VALUE ANGLE: Show clear business value
VISUAL STYLE: {default_style}
DESIGN: Professional and polished"""

    def _get_format_layout_instructions(self, output_format: str) -> str:
        """Get layout instructions based on output format."""
        if output_format == "storyboard":
            return """LAYOUT (VERTICAL STORYBOARD):
- PORTRAIT orientation - tall, scrollable format
- Visual flow from TOP TO BOTTOM (vertical reading)
- Multiple sections stacked vertically
- Each section tells part of the story
- Good for detailed explanations and step-by-step narratives
- Think: LinkedIn article header or presentation slide deck feel"""
        else:  # infographic (default)
            return """LAYOUT (HORIZONTAL INFOGRAPHIC):
- LANDSCAPE orientation - wide, single-view format
- Visual flow from LEFT TO RIGHT (horizontal reading)
- Clean, scannable, executive-friendly
- Key points visible at a glance
- Good for quick value communication
- Think: LinkedIn post image or email header"""

    def _get_format_output_instructions(self, output_format: str) -> str:
        """Get output specifications based on format."""
        if output_format == "storyboard":
            return """OUTPUT:
- Single image, PORTRAIT 9:16 aspect ratio (vertical)
- 1080x1920 resolution (mobile/story format)
- PNG format"""
        else:  # infographic (default)
            return """OUTPUT:
- Single image, LANDSCAPE 16:9 aspect ratio (widescreen horizontal)
- 1920x1080 resolution (HD widescreen)
- PNG format"""

    def _get_visual_style_instructions(self, visual_style: str) -> str:
        """Get visual style instructions based on style preference."""
        styles = {
            "clean": """VISUAL STYLE: CLEAN
- Simple flat icons and shapes
- Minimal decoration, maximum clarity
- Bold typography, lots of whitespace
- No gradients or shadows
- Think: Apple keynote slides""",
            "polished": """VISUAL STYLE: POLISHED PROFESSIONAL
- Refined, corporate-quality graphics
- Subtle gradients and modern touches
- Professional iconography
- Balanced composition with visual hierarchy
- Think: McKinsey or BCG presentation""",
            "photo_realistic": """VISUAL STYLE: PHOTO-REALISTIC
- Include realistic imagery and photos
- High-quality stock photo aesthetic
- Blend photos with text overlays
- Modern editorial feel
- Think: LinkedIn featured image or magazine layout""",
            "minimalist": """VISUAL STYLE: MINIMALIST
- Extreme simplicity, sparse elements
- Maximum whitespace
- Only essential text and icons
- Single accent color usage
- Think: Japanese design or Dieter Rams""",
            # NEW STYLES FOR PERSONA RESONANCE
            "isometric": """VISUAL STYLE: ISOMETRIC 3D
- Clean 3D isometric icons and illustrations
- Soft shadows, subtle depth
- Modern SaaS aesthetic (Stripe, Linear, Notion)
- Precise geometric shapes
- Light, airy backgrounds with floating elements
- Think: Stripe's marketing illustrations""",
            "sketch": """VISUAL STYLE: HAND-DRAWN SKETCH
- Whiteboard/napkin sketch aesthetic
- Imperfect, hand-drawn lines
- Marker or pencil texture
- Casual, approachable feel
- Doodle-style icons
- Think: Quick sketch explaining an idea to a coworker""",
            "data_viz": """VISUAL STYLE: DATA VISUALIZATION
- Charts, graphs, and numbers prominent
- McKinsey/BCG consulting deck aesthetic
- Clean data tables and metrics
- Waterfall charts, bar graphs, trend lines
- Numbers are heroes, not supporting cast
- Think: Board presentation with hard data""",
            "bold": """VISUAL STYLE: BOLD GEOMETRIC
- Bauhaus-inspired strong shapes
- High contrast, vibrant colors
- Geometric patterns and forms
- Memorable, stand-out aesthetic
- Think: Pitch deck slide that demands attention""",
        }
        return styles.get(visual_style, styles["polished"])

    def _get_artist_style_instructions(self, artist_style: str | None) -> str:
        """Get artist style instructions for fun variations."""
        if not artist_style:
            return ""

        artists = {
            "salvador_dali": """ARTIST STYLE: SALVADOR DALI
- Surrealist elements and dreamlike quality
- Melting or distorted shapes (but keep text readable!)
- Unexpected juxtapositions
- Rich, warm colors with dramatic lighting
- Imaginative, thought-provoking visuals
- Think: The Persistence of Memory meets corporate presentation""",
            "monet": """ARTIST STYLE: CLAUDE MONET
- Impressionist brushstroke texture
- Soft, diffused lighting
- Pastel and natural color palette
- Dreamy, atmospheric quality
- Nature-inspired elements (water lilies, gardens)
- Think: Water Lilies meets executive summary""",
            "diego_rivera": """ARTIST STYLE: DIEGO RIVERA
- Bold muralist style
- Strong, blocky shapes and forms
- Workers and industry themes
- Rich earth tones and vibrant accents
- Social realism aesthetic
- Think: Detroit Industry Murals meets tech infographic""",
            "warhol": """ARTIST STYLE: ANDY WARHOL
- Pop art boldness
- High contrast, vibrant colors
- Repetition and pattern elements
- Commercial art aesthetic
- Bold outlines and flat colors
- Think: Campbell's Soup meets business presentation""",
            "van_gogh": """ARTIST STYLE: VAN GOGH
- Expressive brushstroke texture
- Swirling, dynamic movement
- Bold, emotional color choices
- Starry Night energy
- Intense yellows, blues, and greens
- Think: Starry Night meets executive dashboard""",
            "picasso": """ARTIST STYLE: PICASSO (CUBIST)
- Geometric, fragmented forms
- Multiple perspectives simultaneously
- Bold, angular shapes
- Strong black outlines
- Analytical cubism meets business graphics
- Think: Three Musicians meets corporate storyboard""",
            # NEW ARTIST STYLE
            "giger": """ARTIST STYLE: H.R. GIGER (BIOMECHANICAL)
- Dark, intricate biomechanical aesthetic
- Organic forms merged with mechanical elements
- Alien/xenomorph design language
- Textured, layered surfaces
- Haunting, otherworldly atmosphere
- Bold choice for disruption/transformation messaging
- Think: Alien movie meets tech transformation story""",
        }
        return artists.get(artist_style, "")

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
                "vision_model": self.config.vision_model,
                "image_model": self.config.image_model,
                "api_key_configured": bool(self.config.api_key),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.config.api_key),
            }