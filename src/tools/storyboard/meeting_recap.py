"""
Meeting Recap Tool — JTBD + Challenger + NSTTD
===============================================

Analyzes a call transcript and produces a structured meeting recap with:
- JTBD: Job statement, Forces of Progress, frankenstack detection
- Challenger: Reframe, rational drowning, emotional impact
- NSTTD: Accusation audit email, calibrated questions, "That's right" summary
- Product recommendations with validated links
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.storyboard import prompts
from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_PRODUCTS,
    SALES_COLLATERAL,
    get_audience_persona,
    get_collateral_links,
)
from src.tools.storyboard.prompt_builders import (
    build_knowledge_context,
    build_language_guidelines_minimal,
    build_narrative_extraction_prompt,
    build_schema_mapping_prompt,
)
from src.tools.storyboard.scenario_library import match_scenarios_by_phrases
from src.tools.storyboard.transcript_compactor import compact_transcript

logger = logging.getLogger(__name__)


def build_meeting_recap_prompt(
    transcript: str,
    audience: str = "av_integrator",
    vertical: str | None = None,
) -> str:
    """
    Build the meeting recap prompt using JTBD + Challenger + NSTTD frameworks.

    Returns a prompt that extracts structured meeting intelligence from a call
    transcript, grounded in the three sales methodology frameworks.
    """
    knowledge_context = build_knowledge_context(audience)
    language_guidelines = build_language_guidelines_minimal(audience)
    value_angle = prompts.get_value_angle_instruction(audience)
    job_statement = prompts.get_persona_job_statement(audience)
    jtbd_instructions = prompts.get_jtbd_extraction_instructions(audience)
    nsttd_framework = prompts.get_nsttd_email_framework(audience)
    vertical_context = prompts.get_vertical_generation_context(vertical)

    persona_info = get_audience_persona(audience)
    persona_focus = prompts.get_persona_extraction_focus(audience, persona_info)

    # Build product context for recommendations
    product_context = _build_product_context()

    # Extractive compaction in place of the old transcript[:50000] hard slice.
    # A raw 50K slice silently dropped the tail of long calls — exactly where
    # decisions, next steps, and budget/timeline signals tend to surface.
    # compact_transcript keeps the head + tail and the highest-signal middle
    # turns, and exposes key_moments so the model sees JTBD-rich content first.
    compacted = compact_transcript(transcript, target_chars=24_000)
    transcript_block = (
        f"=== KEY MOMENTS (highest-signal turns first) ===\n"
        f"{compacted.key_moments}\n\n"
        f"=== FULL CALL (compaction_ratio={compacted.compaction_ratio:.2f}"
        f"{', fallback_used' if compacted.fallback_used else ''}) ===\n"
        f"{compacted.full_context}"
    )

    return f"""You are a sales intelligence analyst. Analyze this call transcript and produce
a structured meeting recap using JTBD, Challenger Sale, and NSTTD frameworks.

CALL TRANSCRIPT:
{transcript_block}

TARGET PERSONA: {audience}
PERSONA'S CORE JOB: "{job_statement}"
{vertical_context}

{knowledge_context if knowledge_context else ""}
{language_guidelines if language_guidelines else ""}
{persona_focus}

{jtbd_instructions}

{value_angle}

PRODUCT CATALOG FOR RECOMMENDATIONS:
{product_context}

{nsttd_framework}

CRITICAL RULES:
- NEVER include personal names — use roles only (e.g., "AV Director" not "John")
- ALL quotes must use roles, not names
- Be SPECIFIC — reference actual discussion points from the transcript
- Calibrated questions use How/What ONLY — never Why
- Email draft must be under 100 words
- Accusation audit must front-run their SPECIFIC likely objection
- Product recommendations must map to discussed pain points

Return JSON:
{{
    "job_statement": "When [circumstance from call], I want to [job], so I can [outcome]",
    "forces_of_progress": {{
        "push": "Specific pain from transcript",
        "pull": "What attracted them to looking",
        "anxiety": "Switching fears mentioned",
        "habit": "Current comfort / status quo"
    }},
    "hiring_firing": {{
        "currently_hired": "What they use today (the frankenstack)",
        "fired_for": "Why it fails them",
        "workarounds": "Hacks they've assembled"
    }},
    "summary": "Single STRING (not an array) of 3-5 bullets separated by newlines, each prefixed with '• '",
    "key_topics": ["topic1", "topic2", "topic3"],
    "participants": [{{"role": "AV Director"}}, {{"role": "IT Manager"}}],
    "frankenstack_description": "Their current messy setup — specific vendors/gear mentioned",
    "buyer_signals": {{
        "pain": "Frustrations described",
        "need": "Capabilities sought",
        "timeline": "Budget cycle, dates, mandates",
        "authority": "Who else weighs in",
        "proof": "Competitors, references mentioned"
    }},
    "challenger_reframe": "Most [persona]s believe [X from call]. But [evidence] shows [Y].",
    "rational_drowning": "Quantified impact using THEIR numbers from the call",
    "emotional_impact": "Personal consequence for THEIR role",
    "product_recommendations": [
        {{
            "product_id": "pearl_mini",
            "product_name": "Pearl Mini",
            "reason": "Why this fits their discussed need",
            "bundle_option": "Studio Essential (Mini + 1 EC20) at $5,179 — saves $470"
        }}
    ],
    "follow_up_email": "Under 100 words. Accusation audit opener. Label. Call reference. No-oriented CTA.",
    "calibrated_questions": [
        "What does success look like for your team?",
        "How does this fit into your broader priorities?"
    ],
    "thats_right_summary": "Summary of their position designed to get 'That's right'",
    "detected_vertical": "higher_ed",
    "detected_persona": "av_director"
}}"""


def _build_product_context() -> str:
    """Build product catalog context for the LLM to use in recommendations."""
    lines = []
    for pid, product in EPIPHAN_PRODUCTS.items():
        price = product.get("price", "")
        name = product.get("name", "")
        tagline = product.get("tagline", "")
        advantage = product.get("competitive_advantage", "")
        savings = product.get("savings", "")

        line = f"- {pid}: {name} ({price}) — {tagline}"
        if advantage:
            line += f" | {advantage}"
        if savings:
            line += f" | Bundle saves {savings}"
        lines.append(line)

    return "\n".join(lines)


async def process_meeting_recap(
    transcript: str,
    audience: str = "av_integrator",
    vertical: str | None = None,
    include_product_recs: bool = True,
    include_follow_up: bool = True,
) -> dict[str, Any]:
    """
    Process a call transcript into a structured meeting recap.

    Uses Gemini Flash for extraction, then enriches with:
    - Scenario matching from the deployment library
    - Validated product links from SALES_COLLATERAL
    - Collateral links based on detected vertical
    """
    from src.tools.storyboard.gemini_client import (
        GeminiStoryboardClient,
        _repair_json,
    )

    # Build the prompt
    prompt = build_meeting_recap_prompt(transcript, audience, vertical)

    # Call the configured text model for single-pass extraction.
    # NOTE (DA-R1.1, 2026-05-09): the previous call was
    # ``await client.extract_content(prompt)`` — a method that does NOT exist
    # on GeminiStoryboardClient. The endpoint had been silently 500-ing
    # in production. ``_call_text_model`` is the same helper DA-R1's
    # two-pass uses, so meeting-recap and storyboard share routing.
    client = GeminiStoryboardClient()
    raw_response = await client._call_text_model(prompt)

    # Parse JSON from response
    result = _parse_json_response(raw_response)

    # DA-R1.1.b (2026-05-09): Coerce known-fragile fields where the LLM
    # occasionally returns a list when MeetingRecapResponse expects a string.
    # The ``summary`` field is documented in the prompt as "3-5 bullet
    # executive summary" which the LLM frequently interprets as a JSON array.
    # MeetingRecapResponse.summary is typed ``str``, so without this coercion
    # the router's Pydantic validation 500s — exactly the failure mode that
    # was masked by the broken ``extract_content`` AttributeError before
    # DA-R1.1. Defensive normalization keeps the contract honest.
    if isinstance(result.get("summary"), list):
        bullets = [str(item).strip() for item in result["summary"] if item]
        result["summary"] = "\n".join(
            b if b.startswith(("•", "-", "*")) else f"• {b}" for b in bullets
        )

    # DA-R1.1: Augment with two-pass narrative+schema for long transcripts.
    # The meeting-recap prompt already extracts forces_of_progress and
    # frankenstack_description in a single pass, but the rigid 17-key JSON
    # shape pressures the LLM to compress nuance under schema-fitting.
    # For transcripts >= two_pass_threshold_chars, run the narrative+schema
    # two-pass (same building blocks DA-R1 uses in gemini_client._understand)
    # and OVERLAY the richer forces + frankenstack onto the meeting-recap dict.
    # The other 15 keys (job_statement, challenger_reframe, follow_up_email,
    # etc.) come from the single-pass and are left untouched — that is the
    # contract MeetingRecapResponse depends on.
    if (
        client.config.enable_two_pass_extraction
        and len(transcript) >= client.config.two_pass_threshold_chars
    ):
        try:
            narrative_prompt = build_narrative_extraction_prompt(
                transcript=transcript,
                audience=audience,
                vertical=vertical,
            )
            narrative = await client._call_text_model(narrative_prompt)

            schema_prompt = build_schema_mapping_prompt(
                narrative=narrative,
                audience=audience,
            )
            schema_response = await client._call_text_model(schema_prompt)
            two_pass = json.loads(_repair_json(schema_response))

            if two_pass.get("forces_of_progress"):
                result["forces_of_progress"] = two_pass["forces_of_progress"]
            if two_pass.get("frankenstack"):
                result["frankenstack_description"] = two_pass["frankenstack"]
            # Surface the extraction confidence so a low-confidence recap can
            # be flagged before a rep acts on it (rather than passing silently).
            confidence = two_pass.get("extraction_confidence")
            if confidence is not None:
                result["extraction_confidence"] = confidence
                if isinstance(confidence, int | float) and confidence < 0.1:
                    logger.warning(
                        "[MEETING-RECAP] Two-pass extraction confidence is "
                        "%.2f (<0.10) — recap is likely ungrounded; flag for "
                        "review (transcript=%d chars).",
                        confidence,
                        len(transcript),
                    )
            result["two_pass_applied"] = True
            logger.info(
                "[MEETING-RECAP] Two-pass augmentation applied "
                "(transcript=%d chars, forces+frankenstack overlaid).",
                len(transcript),
            )
        except Exception as exc:
            logger.warning(
                "[MEETING-RECAP] Two-pass augmentation failed (%s: %s); "
                "keeping single-pass result.",
                type(exc).__name__,
                exc,
            )
            result["two_pass_applied"] = False
    else:
        result["two_pass_applied"] = False

    # Enrich with scenario matching
    scenario_matches = match_scenarios_by_phrases(
        transcript,
        vertical_filter=result.get("detected_vertical") or vertical,
        top_n=3,
    )
    result["scenario_matches"] = [s.id for s, _ in scenario_matches]

    # Enrich with validated product links
    if include_product_recs and result.get("product_recommendations"):
        for rec in result["product_recommendations"]:
            pid = rec.get("product_id", "")
            if pid in SALES_COLLATERAL.get("product_pages", {}):
                rec["url"] = SALES_COLLATERAL["product_pages"][pid]["url"]

    # Add collateral links
    detected_vertical = result.get("detected_vertical") or vertical
    rec_products = [
        r.get("product_id") for r in result.get("product_recommendations", [])
    ]
    collateral = get_collateral_links(
        audience=audience,
        vertical=detected_vertical,
        products=rec_products,
    )
    result["collateral_links"] = collateral

    return result


def _parse_json_response(response: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks AND any
    natural-language preamble the model might emit before the JSON.

    DA-R1.1.b (2026-05-09) — DeepSeek frequently returns "Here's the
    structured meeting recap in JSON format:\\n\\n```json\\n{...}\\n```".
    The previous implementation only stripped the leading ``` fence, so any
    preamble before the fence (or any text after the closing fence) caused
    json.loads() to fail and the function returned the entire raw text in
    a degraded ``{"summary": text}`` fallback. That degraded result then
    failed router validation with a misleading 500.

    The robust parse: find the first ``{`` and the matching last ``}`` and
    parse only that slice. ``_repair_json`` handles the remaining markdown
    cleanup + trailing comma / unterminated string repair.
    """
    from src.tools.storyboard.gemini_client import _repair_json

    text = response.strip()

    # Locate the JSON object by braces — survives any preamble/postscript.
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]

    try:
        return json.loads(_repair_json(text))
    except json.JSONDecodeError:
        logger.warning("Failed to parse meeting recap JSON, returning raw text")
        return {"summary": text, "key_topics": [], "product_recommendations": []}
