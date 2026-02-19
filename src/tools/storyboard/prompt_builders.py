"""
Storyboard Prompt Builders
===========================

Dynamic prompt construction functions for the storyboard pipeline.
These pull from KnowledgeCache and merge runtime data to build
the actual prompt strings sent to LLMs.

Separated from gemini_client.py (orchestration) and prompts.py (static data).
"""

import uuid
from datetime import datetime
from typing import Any

from src.tools.storyboard import prompts

# ── Knowledge-enriched builders ──────────────────────────────────────────────


def build_language_guidelines(
    icp_preset: dict[str, Any], audience: str = "av_director"
) -> str:
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
- AVOID these words/phrases: {", ".join(avoid[:15])}
- USE these words/phrases: {", ".join(use[:15])}
- Write for someone with no technical background
- Focus on benefits, not features"""


def build_knowledge_context(audience: str) -> str:
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
            sections.append(
                f"CUSTOMER PAIN POINTS (from real calls): {'; '.join(ctx['pain_points'])}"
            )
        if ctx["features"]:
            sections.append(
                f"PRODUCT FEATURES TO REFERENCE: {', '.join(ctx['features'])}"
            )
        if ctx["metrics"]:
            sections.append(f"PROOF POINTS TO USE: {'; '.join(ctx['metrics'])}")
        if ctx.get("quotes"):
            sections.append(f"CUSTOMER QUOTES: {'; '.join(ctx['quotes'])}")

        return "\n".join(sections)
    except Exception:
        return ""  # Graceful degradation


def build_language_guidelines_minimal(audience: str) -> str:
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


# ── Extraction prompt templates ──────────────────────────────────────────────


def build_extraction_prompt(
    content_type: str,
    *,
    audience: str = "av_director",
    content: str | None = None,
    file_name: str | None = None,
    context: str | None = None,
    supplementary_context: str | None = None,
    num_images: int = 1,
) -> str:
    """
    Build the extraction prompt for any content type.

    Args:
        content_type: "code", "transcript", "image", or "images"
        audience: Target audience persona
        content: Text content (code source or transcript text)
        file_name: Optional file name (code only)
        context: Optional context string (transcript only)
        supplementary_context: Optional text to combine with images
        num_images: Number of images (images only)

    Returns:
        Complete prompt string ready to send to an LLM
    """
    knowledge_context = build_knowledge_context(audience)
    language_guidelines = build_language_guidelines_minimal(audience)
    value_angle_instruction = prompts.get_value_angle_instruction(audience)
    request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

    if content_type == "code":
        return _build_code_prompt(
            content=content or "",
            audience=audience,
            file_name=file_name,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
        )
    elif content_type == "transcript":
        return _build_transcript_prompt(
            content=content or "",
            audience=audience,
            context=context,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
        )
    elif content_type == "image":
        return _build_image_prompt(
            audience=audience,
            supplementary_context=supplementary_context,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
        )
    elif content_type == "images":
        return _build_multi_image_prompt(
            audience=audience,
            supplementary_context=supplementary_context,
            num_images=num_images,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
        )
    else:
        raise ValueError(f"Unknown content_type: {content_type}")


def _build_code_prompt(
    content: str,
    audience: str,
    file_name: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
) -> str:
    return f"""Analyze this code and extract business value.
REQUEST_ID: {request_id}

{f"File: {file_name}" if file_name else ""}

CODE:
```
{content[:8000]}
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


def _build_transcript_prompt(
    content: str,
    audience: str,
    context: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
) -> str:
    return f"""Extract key insights from this content.
REQUEST_ID: {request_id}

{f"CONTEXT: {context}" if context else ""}

CONTENT:
{content[:32000]}

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


def _build_image_prompt(
    audience: str,
    supplementary_context: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
) -> str:
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

    return f"""{context_section}{"CRITICAL: You have TWO primary inputs above:" if has_text else ""}
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


def _build_multi_image_prompt(
    audience: str,
    supplementary_context: str | None,
    num_images: int,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
) -> str:
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

    return f"""{context_section}{"CRITICAL: You have MULTIPLE primary inputs:" if has_text else ""}
{"1. TEXT TRANSCRIPT (above) - contains key conversation/description content" if has_text else ""}
{"2. IMAGES (below) - contain visual/structural information" if has_text else ""}
{"Extract from ALL sources and MERGE insights. Text and images are equally important." if has_text else ""}

{"Analyze BOTH the text above AND these " + str(num_images) + " images. Extract ALL content from ALL sources." if has_text else f"Analyze these {num_images} images and extract ALL content."}
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
