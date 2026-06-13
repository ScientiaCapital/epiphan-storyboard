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
from src.tools.storyboard.problem_statements import get_problem_statements
from src.tools.storyboard.transcript_compactor import compact_transcript


def _truncate_with_marker(text: str, limit: int, *, unit: str = "chars") -> str:
    """Slice ``text`` to ``limit`` chars, appending a visible marker when cut.

    A bare ``text[:limit]`` slice can hand the model a code block that ends
    mid-function or a transcript cut mid-sentence, with no signal that content
    is missing — the model then treats the fragment as the whole. The marker
    tells the model its input was truncated so it doesn't over-conclude from a
    partial view.
    """
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n\n[… input truncated at {limit:,} {unit}; content above is partial …]"


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


# ── Phase 1.3 polish: ground-truth anchors + Frankenstack patterns ──────────


def build_problem_statement_anchor(
    vertical: str | None, persona: str | None, *, limit: int = 3
) -> str:
    """Return a `VERBATIM PAIN LANGUAGE` block to ground the LLM in real BDR text.

    The model is told to copy this phrasing into ``pain_point`` unless the
    transcript clearly contradicts it. This stops it drifting into generic AI
    fluff and routes it toward language the BDR team has validated reads in
    one breath.

    Returns an empty string when either ``vertical`` or ``persona`` is missing,
    or when no records match the combo. Never raises.
    """
    if not vertical or not persona:
        return ""
    try:
        statements = get_problem_statements(
            vertical=vertical, persona=persona, limit=limit
        )
    except Exception:
        return ""
    if not statements:
        return ""

    bullets = "\n".join(f'- "{ps.statement}"' for ps in statements)
    return (
        "VERBATIM PAIN LANGUAGE FROM PEERS — use this exact phrasing for the "
        "pain_point field unless the transcript clearly contradicts it. These "
        "are sales-validated openers proven to read in one breath:\n"
        f"{bullets}"
    )


# Shared CRITICAL RULES block: how to treat competitor products found in the
# source material. Interpolated into every extraction prompt. Regression
# guard: a Sony-focused source once produced an Epiphan-branded card with
# Sony positioned as the hero.
_COMPETITOR_RULES_BLOCK: str = """\
COMPETITOR HANDLING:
- The source may describe a COMPETITOR's product or workflow (Sony, Panasonic, Blackmagic, vMix, etc.)
- NEVER position the competitor as the solution. headline, tagline, what_it_does, business_value, and differentiator must sell EPIPHAN products only
- Treat the competitor's workflow as the CURRENT/'before' state: it belongs in pain_point_addressed, frankenstack, and forces_of_progress.push
- Avoid hype words: revolutionary, revolutionizes, game-changing, disruptive. No exclamation points."""


# Frankenstack patterns — implicit workaround language we want the LLM to
# detect. The current jtbd_instructions only lists explicit competitor names;
# this block adds the linguistic patterns that signal a workaround even when
# no vendor is named outright.
#
# IMPORTANT: We never frame an LMS / CMS / video-platform partner (Panopto,
# Kaltura, YuJa, Echo360, Canvas, Zoom, etc.) as "the broken thing." Those
# are partners. The Frankenstack is the **classroom-PC + software-encoder
# layer underneath** that fails to deliver into the LMS reliably. The fix
# is replacing the PC layer with a hardware encoder, not replacing the LMS.
_FRANKENSTACK_PATTERN_BLOCK: str = """\
FRANKENSTACK DETECTION (look for IMPLICIT workarounds, not just vendor names):
- Linguistic markers: "we had to", "we ended up", "we wound up using", "work
  around", "in addition to", "not designed for", "not built for", "instead
  of"
- Classic Frankenstack combos in the wild (the broken layer is the encoder
  / capture layer, NOT the LMS or conferencing partner):
    * A software encoder running on a classroom PC feeding the LMS — the PC
      crashes, the OS pushes an update, antivirus quarantines the agent;
      the LMS partner is fine, the PC layer is the failure point
    * vMix + ATEM + separate recorder — 3 boxes that should be 1
    * Bonded cellular + an external recorder + a software switcher — the
      transport works, the orchestration is duct-taped
    * A control system wired to capture gear that doesn't expose a clean
      API — control without capture (the integration gap, not the brand)
- LMS / CMS / conferencing platforms (Panopto, Kaltura, YuJa, Echo360,
  Canvas, Blackboard, Moodle, Zoom, Teams, WebEx) are PARTNERS. Pearl is
  designed to feed them cleanly. Frame the workaround as "the encoder /
  capture layer ahead of the LMS," not as the LMS itself.
- When you spot any of these, populate the ``frankenstack`` field with a
  concrete description of the workaround the prospect described, including
  the cost they're paying for it (time, headcount, reliability)."""


# ── Two-pass Forces extraction (Fix #2) ──────────────────────────────────────


def build_narrative_extraction_prompt(
    transcript: str,
    audience: str = "av_director",
    vertical: str | None = None,
) -> str:
    """Pass-1 prompt: free-text narrative for each Force of Progress.

    No JSON schema. The LLM is asked to describe each Force in 2-3 sentences
    of natural language. Pass-2 (``build_schema_mapping_prompt``) takes that
    narrative and re-prompts the LLM to map it onto the strict
    ``ForcesOfProgress`` Pydantic shape. Two cheap calls beat one rigid call
    because the rigid schema strips contextual nuance during extraction.

    Reuses ``compact_transcript`` so long calls don't blow the context window.
    """
    compacted = compact_transcript(transcript, target_chars=24_000)
    knowledge_context = build_knowledge_context(audience)
    anchor = build_problem_statement_anchor(vertical, audience)

    return f"""You are an expert sales discovery analyst. Read this call \
transcript and write a SHORT NARRATIVE describing each Force of Progress \
(JTBD framework) in plain prose. Do NOT return JSON. Do NOT use bullet \
points. Use 2-3 sentences per Force, written in natural conversational \
English, in the prospect's voice as much as possible.

TARGET AUDIENCE: {audience}

{anchor}

{knowledge_context}

{_FRANKENSTACK_PATTERN_BLOCK}

TRANSCRIPT (compacted, key moments first):
=== KEY MOMENTS ===
{compacted.key_moments}

=== FULL CONTEXT ===
{compacted.full_context}

WRITE THE NARRATIVE in this exact order, with these exact section headers:

PUSH (current pain driving change):
[2-3 sentences in the prospect's voice — what's broken today, what they hate]

PULL (new solution attraction):
[2-3 sentences — what they're being drawn toward, the new way they're considering]

ANXIETY (fear of switching):
[2-3 sentences — what scares them about changing vendors/systems/process]

HABIT (current comfort):
[2-3 sentences — what's familiar, what they'd lose, who'd need retraining]

FRANKENSTACK (current workarounds):
[2-3 sentences — the duct-tape stack they've assembled, including the
human cost (time, headcount, reliability)]
"""


def build_schema_mapping_prompt(narrative: str, audience: str = "av_director") -> str:
    """Pass-2 prompt: take pass-1 narrative and emit strict JSON.

    The narrative carries all the contextual nuance the rigid JSON pass would
    have stripped; this pass just normalizes it to the schema the rest of the
    pipeline expects.
    """
    return f"""You will receive a free-text narrative describing a sales \
prospect's Forces of Progress (JTBD framework). Your job is to map it to a \
strict JSON schema, preserving every quantified detail and named vendor.

TARGET AUDIENCE: {audience}

NARRATIVE:
\"\"\"
{narrative}
\"\"\"

Return JSON with this exact shape — do not invent fields, do not omit fields:

{{
    "forces_of_progress": {{
        "push": "1-2 sentences from the PUSH section",
        "pull": "1-2 sentences from the PULL section",
        "anxiety": "1-2 sentences from the ANXIETY section",
        "habit": "1-2 sentences from the HABIT section"
    }},
    "frankenstack": "1-2 sentences from the FRANKENSTACK section",
    "extraction_confidence": 0.0-1.0
}}

CRITICAL RULES:
- Preserve every named vendor, product, and number from the narrative
- NEVER include personal names — use roles only
- If a section in the narrative is genuinely empty, return an empty string
  for that field but DO NOT omit it
- ``extraction_confidence`` should reflect how confident the original
  extractor was — high if the narrative is rich and specific, low if it
  was thin and generic"""


# ── Extraction prompt templates ──────────────────────────────────────────────


def build_extraction_prompt(
    content_type: str,
    *,
    audience: str = "av_director",
    vertical: str | None = None,
    content: str | None = None,
    file_name: str | None = None,
    context: str | None = None,
    supplementary_context: str | None = None,
    num_images: int = 1,
    corrective_instruction: str | None = None,
) -> str:
    """
    Build the extraction prompt for any content type.

    Args:
        content_type: "code", "transcript", "image", or "images"
        audience: Target audience persona
        vertical: Optional vertical for industry-specific context
        content: Text content (code source or transcript text)
        file_name: Optional file name (code only)
        context: Optional context string (transcript only)
        supplementary_context: Optional text to combine with images
        num_images: Number of images (images only)
        corrective_instruction: Optional quality-gate feedback from a rejected
            previous attempt; prepended so the model reads it first

    Returns:
        Complete prompt string ready to send to an LLM
    """
    knowledge_context = build_knowledge_context(audience)
    language_guidelines = build_language_guidelines_minimal(audience)
    value_angle_instruction = prompts.get_value_angle_instruction(audience)
    vertical_context = prompts.get_vertical_generation_context(vertical)
    request_id = f"{datetime.now().isoformat()}-{uuid.uuid4().hex[:8]}"

    # Get persona-specific extraction focus (was unused — now wired in)
    from src.tools.storyboard.epiphan_presets import get_audience_persona

    audience_info = get_audience_persona(audience)
    persona_focus = prompts.get_persona_extraction_focus(audience, audience_info)

    # JTBD extraction instructions for Forces of Progress + frankenstack detection
    jtbd_instructions = prompts.get_jtbd_extraction_instructions(audience)

    # Phase 1.3 polish:
    #   * problem_statement_anchor — verbatim BDR pain language for grounding
    #   * frankenstack_patterns — implicit-workaround detection prompt block
    # Both degrade gracefully (empty string when inputs are unknown).
    problem_statement_anchor = build_problem_statement_anchor(vertical, audience)
    frankenstack_patterns = _FRANKENSTACK_PATTERN_BLOCK

    if content_type == "code":
        prompt = _build_code_prompt(
            content=content or "",
            audience=audience,
            file_name=file_name,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
            vertical_context=vertical_context,
            persona_focus=persona_focus,
            jtbd_instructions=jtbd_instructions,
        )
    elif content_type == "transcript":
        prompt = _build_transcript_prompt(
            content=content or "",
            audience=audience,
            context=context,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
            vertical_context=vertical_context,
            persona_focus=persona_focus,
            jtbd_instructions=jtbd_instructions,
            problem_statement_anchor=problem_statement_anchor,
            frankenstack_patterns=frankenstack_patterns,
        )
    elif content_type == "image":
        prompt = _build_image_prompt(
            audience=audience,
            supplementary_context=supplementary_context,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
            vertical_context=vertical_context,
            persona_focus=persona_focus,
            jtbd_instructions=jtbd_instructions,
        )
    elif content_type == "images":
        prompt = _build_multi_image_prompt(
            audience=audience,
            supplementary_context=supplementary_context,
            num_images=num_images,
            request_id=request_id,
            knowledge_context=knowledge_context,
            language_guidelines=language_guidelines,
            value_angle_instruction=value_angle_instruction,
            vertical_context=vertical_context,
            persona_focus=persona_focus,
            jtbd_instructions=jtbd_instructions,
        )
    else:
        raise ValueError(f"Unknown content_type: {content_type}")

    if corrective_instruction:
        prompt = f"{corrective_instruction}\n\n{prompt}"
    return prompt


def _build_code_prompt(
    content: str,
    audience: str,
    file_name: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
    vertical_context: str = "",
    persona_focus: str = "",
    jtbd_instructions: str = "",
) -> str:
    return f"""Analyze this code and extract business value.
REQUEST_ID: {request_id}

{f"File: {file_name}" if file_name else ""}

CODE:
```
{_truncate_with_marker(content, 8000)}
```

TARGET AUDIENCE: {audience}
{vertical_context}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

{persona_focus}

{jtbd_instructions}

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
- CMS/LMS BRAND AGNOSTIC: Never favor one platform. Say "your CMS/LMS" or list multiple (Panopto, Kaltura, YuJa, etc.)
- Highlight: All-in-one streaming, recording, switching, multicasting in one box
- Highlight when relevant: Dante audio, direct CMS/LMS publish, EC20 at $1,899 vs $7-8K competitors

{_COMPETITOR_RULES_BLOCK}

Return JSON:
{{
    "raw_extracted_text": "Key technical elements: classes, functions, logic",
    "extraction_confidence": 0.0-1.0,
    "headline": "Reframe headline — the insight, not the feature (8 words max)",
    "tagline": "Unique to THIS code (10 words max)",
    "what_it_does": "Plain English — the NEW WAY, not features (2 sentences max)",
    "business_value": "Quantified impact — rational drowning numbers",
    "who_benefits": "Role/persona titles ONLY - NO personal names",
    "differentiator": "What makes Epiphan the ONLY solution for this job",
    "pain_point_addressed": "The PUSH force — current pain driving change",
    "suggested_icon": "Simple icon name",
    "job_to_be_done": "JTBD: When [circumstance], I want to [job], so I can [outcome]",
    "forces_of_progress": {{
        "push": "Current pain driving change",
        "pull": "New solution attraction",
        "anxiety": "Fear of switching",
        "habit": "Comfort of current state"
    }},
    "frankenstack": "Description of current messy setup (if detectable from code)",
    "recommended_products": ["product_id_1", "product_id_2"],
    "challenger_reframe": "The insight: Most [audience]s believe X, but Y shows Z"
}}"""


def _build_transcript_prompt(
    content: str,
    audience: str,
    context: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
    vertical_context: str = "",
    persona_focus: str = "",
    jtbd_instructions: str = "",
    problem_statement_anchor: str = "",
    frankenstack_patterns: str = "",
) -> str:
    # Phase 1.3 Fix #1: extractive compaction in place of [:32000] slice.
    # Long calls preserve their tail (where decisions live) and high-signal
    # turns get a dedicated key_moments slot so the model sees them first.
    compacted = compact_transcript(content, target_chars=24_000)
    content_block = (
        f"=== KEY MOMENTS (highest-signal turns first) ===\n"
        f"{compacted.key_moments}\n\n"
        f"=== FULL CONTEXT (compaction_ratio={compacted.compaction_ratio:.2f}"
        f"{', fallback_used' if compacted.fallback_used else ''}) ===\n"
        f"{compacted.full_context}"
    )

    return f"""Extract key insights from this content.
REQUEST_ID: {request_id}

{f"CONTEXT: {context}" if context else ""}

CONTENT:
{content_block}

TARGET AUDIENCE: {audience}
{vertical_context}

{problem_statement_anchor}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

{persona_focus}

{frankenstack_patterns}

EXTRACTION PRIORITIES:
- Preserve EXACT quotes and specific numbers
- Note speaker ROLES (not personal names - generalize to "Field Tech", "Project Manager", "Operations Team")
- ALWAYS derive business value - infer it from context if not explicitly stated

EXTRACT BUYER SIGNALS:
- PUSH (pain driving change): What frustrations did they describe? What's broken?
- PULL (new solution attraction): What capabilities are they looking for?
- ANXIETY (switching fear): What concerns about changing? Risk? Timeline?
- HABIT (current comfort): What are they used to? "We've always done it this way"?
- TIMELINE: Budget cycle? Event date? Mandate? Fiscal year end?
- AUTHORITY: Who else weighs in? Economic buyer vs champion vs user?
- FRANKENSTACK: What mismatched gear/software/workarounds do they have today?

{jtbd_instructions}

{value_angle_instruction}

CRITICAL RULES:
- NEVER output "Not mentioned in transcript" - always derive/infer value
- NEVER include personal names - use titles/roles/personas instead (e.g., "Operations Team" not "John and Sarah")
- If value isn't explicit, INFER it from the problem being solved

{_COMPETITOR_RULES_BLOCK}

Return JSON:
{{
    "raw_extracted_text": "Key quotes, numbers, specifics from content",
    "extraction_confidence": 0.0-1.0,
    "headline": "Reframe headline — the insight, not the feature (8 words max)",
    "tagline": "Unique to this content (10 words max)",
    "what_it_does": "The NEW WAY — not features (2 sentences max)",
    "business_value": "Quantified impact — rational drowning numbers",
    "who_benefits": "Role/persona titles ONLY - NO personal names",
    "differentiator": "What makes Epiphan the ONLY solution for this job",
    "pain_point_addressed": "The PUSH force — current pain driving change",
    "suggested_icon": "Simple icon name",
    "job_to_be_done": "JTBD: When [circumstance], I want to [job], so I can [outcome]",
    "forces_of_progress": {{
        "push": "Current pain from transcript",
        "pull": "New capability they're attracted to",
        "anxiety": "Switching fears mentioned",
        "habit": "Current comfort / status quo"
    }},
    "frankenstack": "Their current messy setup from transcript",
    "recommended_products": ["product_id_1", "product_id_2"],
    "challenger_reframe": "The insight: Most [audience]s believe X, but Y shows Z",
    "buyer_signals": {{
        "timeline": "Budget cycle, event date, mandate",
        "authority": "Who else weighs in",
        "proof": "Competitors mentioned, reference checks"
    }}
}}"""


def _build_image_prompt(
    audience: str,
    supplementary_context: str | None,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
    vertical_context: str = "",
    persona_focus: str = "",
    jtbd_instructions: str = "",
) -> str:
    # Build text context section - TEXT IS A PRIMARY INPUT, NOT SECONDARY
    context_section = ""
    has_text = supplementary_context and supplementary_context.strip()
    if has_text:
        context_section = f"""=== PRIMARY INPUT #1: TEXT TRANSCRIPT ===
This text is a PRIMARY INPUT with EQUAL weight to the image below.
Extract insights from THIS TEXT FIRST, then synthesize with the image.

{_truncate_with_marker(supplementary_context, 16000)}
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
{vertical_context}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

{persona_focus}

{jtbd_instructions}

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

{_COMPETITOR_RULES_BLOCK}

Return JSON:
{{
    "raw_extracted_text": "Everything visible: labels, names, numbers",
    "extraction_confidence": 0.0-1.0,
    "headline": "Reframe headline — the insight (8 words max)",
    "tagline": "Unique to THIS content (10 words max)",
    "what_it_does": "The NEW WAY — not features (2 sentences max)",
    "business_value": "Quantified impact — infer from what this enables",
    "who_benefits": "Role/persona titles ONLY - NO personal names",
    "differentiator": "What makes Epiphan the ONLY solution for this job",
    "pain_point_addressed": "The PUSH force — INFER the problem this solves",
    "suggested_icon": "Icon representing content",
    "job_to_be_done": "JTBD: When [circumstance], I want to [job], so I can [outcome]",
    "forces_of_progress": {{
        "push": "Current pain",
        "pull": "New solution attraction",
        "anxiety": "Switching fear",
        "habit": "Current comfort"
    }},
    "frankenstack": "Current messy setup visible in image (if applicable)",
    "recommended_products": ["product_id_1", "product_id_2"],
    "challenger_reframe": "The insight: Most [audience]s believe X, but Y shows Z"
}}"""


def _build_multi_image_prompt(
    audience: str,
    supplementary_context: str | None,
    num_images: int,
    request_id: str,
    knowledge_context: str,
    language_guidelines: str,
    value_angle_instruction: str,
    vertical_context: str = "",
    persona_focus: str = "",
    jtbd_instructions: str = "",
) -> str:
    # Build text context section - TEXT IS A PRIMARY INPUT, NOT SECONDARY
    context_section = ""
    has_text = supplementary_context and supplementary_context.strip()
    if has_text:
        context_section = f"""=== PRIMARY INPUT #1: TEXT TRANSCRIPT ===
This text is a PRIMARY INPUT with EQUAL weight to the images below.
Extract insights from THIS TEXT FIRST, then synthesize with the images.

{_truncate_with_marker(supplementary_context, 16000)}
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
{vertical_context}

{knowledge_context if knowledge_context else ""}

{language_guidelines if language_guidelines else ""}

{persona_focus}

{jtbd_instructions}

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

{_COMPETITOR_RULES_BLOCK}

Return JSON:
{{
    "raw_extracted_text": "IMAGE 1: [content]... IMAGE 2: [content]...",
    "extraction_confidence": 0.0-1.0,
    "headline": "Reframe headline — the insight (8 words max)",
    "tagline": "Unique to THIS content (10 words max)",
    "what_it_does": "The NEW WAY — synthesized across images",
    "business_value": "Quantified impact from images",
    "who_benefits": "Role/persona titles ONLY",
    "differentiator": "What makes Epiphan the ONLY solution for this job",
    "pain_point_addressed": "The PUSH force — problem solved",
    "suggested_icon": "Icon representing theme",
    "job_to_be_done": "JTBD: When [circumstance], I want to [job], so I can [outcome]",
    "forces_of_progress": {{
        "push": "Current pain",
        "pull": "New solution attraction",
        "anxiety": "Switching fear",
        "habit": "Current comfort"
    }},
    "frankenstack": "Current messy setup visible across images",
    "recommended_products": ["product_id_1", "product_id_2"],
    "challenger_reframe": "The insight: Most [audience]s believe X, but Y shows Z"
}}"""
