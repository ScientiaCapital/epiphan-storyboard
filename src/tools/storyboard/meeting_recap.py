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
)
from src.tools.storyboard.scenario_library import match_scenarios_by_phrases

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

    return f"""You are a sales intelligence analyst. Analyze this call transcript and produce
a structured meeting recap using JTBD, Challenger Sale, and NSTTD frameworks.

CALL TRANSCRIPT:
{transcript[:50000]}

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
    "summary": "3-5 bullet executive summary",
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
    from src.tools.storyboard.gemini_client import GeminiStoryboardClient

    # Build the prompt
    prompt = build_meeting_recap_prompt(transcript, audience, vertical)

    # Call Gemini for extraction
    client = GeminiStoryboardClient()
    raw_response = await client.extract_content(prompt)

    # Parse JSON from response
    result = _parse_json_response(raw_response)

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
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse meeting recap JSON, returning raw text")
        return {"summary": text, "key_topics": [], "product_recommendations": []}
