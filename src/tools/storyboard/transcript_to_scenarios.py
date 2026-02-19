"""
TranscriptToScenariosTool — Paste Transcript, Get Scenario Storyboards
========================================================================

4-stage pipeline:
1. EXTRACT — Detect vertical, interests, pain points, buyer signals from transcript
2. MATCH + CUSTOMIZE — Rank scenarios from library, customize with call details
3. GENERATE STORYBOARDS — One PNG per matched scenario (parallel)
4. DRAFT EMAIL — BDR follow-up email with call-specific references

BDR motion: qualification and imagination, not closing.
Show prospects "here's what other orgs in your space have built with Epiphan."

NO OpenAI — Gemini + DeepSeek/Qwen only.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from time import perf_counter
from typing import Any

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult
from src.tools.storyboard.epiphan_presets import (
    EPIPHAN_PRODUCTS,
    EPIPHAN_VERTICALS,
    get_icp_preset,
)
from src.tools.storyboard.gemini_client import (
    GeminiStoryboardClient,
    StoryboardUnderstanding,
)
from src.tools.storyboard.scenario_library import (
    SCENARIO_LIBRARY,
    get_scenario_by_id,
    match_scenarios_by_phrases,
)

logger = logging.getLogger(__name__)


def _repair_json(text: str) -> str:
    """Strip markdown fences and fix common JSON issues from LLM output."""
    import re

    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Fix trailing commas
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    # Close unclosed braces
    open_braces = text.count("{") - text.count("}")
    if open_braces > 0:
        text += "}" * open_braces
    open_brackets = text.count("[") - text.count("]")
    if open_brackets > 0:
        text += "]" * open_brackets

    return text


def _build_scenario_summary() -> str:
    """Build a compact summary of the scenario library for the LLM prompt."""
    lines = []
    for s in SCENARIO_LIBRARY:
        product_names = [
            EPIPHAN_PRODUCTS[p]["name"] for p in s.products if p in EPIPHAN_PRODUCTS
        ]
        lines.append(
            f'- {s.id}: "{s.name}" ({s.vertical}) — {", ".join(product_names)}\n'
            f"  Triggers: {', '.join(s.trigger_phrases[:5])}...\n"
            f"  Hook: {s.creative_hook[:80]}..."
        )
    return "\n".join(lines)


class TranscriptToScenariosTool(BaseTool):
    """
    Transform call transcripts into deployment scenario storyboards + BDR email.

    4-stage pipeline:
    1. Extract signals from transcript (vertical, pain points, interests)
    2. Match + customize scenarios from the curated library
    3. Generate one storyboard PNG per scenario (parallel)
    4. Draft a BDR follow-up email

    Example:
        tool = TranscriptToScenariosTool()
        result = await tool.run({
            "transcript": "We talked about streaming our Friday night football games...",
            "prospect_name": "Mike",
            "prospect_company": "Lincoln High School",
        })
    """

    def __init__(self, gemini_client: GeminiStoryboardClient | None = None):
        self._gemini_client = gemini_client

    @property
    def gemini_client(self) -> GeminiStoryboardClient:
        """Lazy initialization of Gemini client."""
        if self._gemini_client is None:
            self._gemini_client = GeminiStoryboardClient()
        return self._gemini_client

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="transcript_to_scenarios",
            description=(
                "Transform call transcripts into deployment scenario storyboards and BDR follow-up email. "
                "Detects vertical, pain points, and buyer signals from the transcript, "
                "matches against 20 curated Epiphan deployment scenarios, "
                "generates visual storyboards for the top matches, "
                "and drafts a personalized follow-up email. "
                "For BDR qualification and prospect imagination."
            ),
            category=ToolCategory.DATA,
            parameters={
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Pasted call transcript or summary text",
                    },
                    "vertical_hint": {
                        "type": "string",
                        "description": "Optional vertical if BDR already knows",
                    },
                    "persona_hint": {
                        "type": "string",
                        "description": "Optional buyer persona if BDR already knows",
                    },
                    "prospect_name": {
                        "type": "string",
                        "description": "Prospect name for email personalization",
                    },
                    "prospect_company": {
                        "type": "string",
                        "description": "Prospect company for email personalization",
                    },
                },
                "required": ["transcript"],
            },
            requires_approval=False,
        )

    # ── Stage 1: Extract ─────────────────────────────────────────────────

    async def extract_signals(
        self,
        transcript: str,
        vertical_hint: str | None = None,
        persona_hint: str | None = None,
    ) -> dict[str, Any]:
        """
        Stage 1: Extract signals from transcript using Gemini Flash.

        Returns dict with keys:
            detected_vertical, detected_persona, interests, pain_points,
            products_mentioned, org_size_hints, buyer_signals, confidence
        """
        verticals_list = ", ".join(EPIPHAN_VERTICALS.keys())

        hint_section = ""
        if vertical_hint:
            hint_section += f"\nBDR HINT — Vertical: {vertical_hint}"
        if persona_hint:
            hint_section += f"\nBDR HINT — Persona: {persona_hint}"

        prompt = f"""Read this call transcript and extract structured signals for Epiphan Video sales follow-up.
{hint_section}

TRANSCRIPT:
{transcript[:32000]}

KNOWN VERTICALS: {verticals_list}

KNOWN PRODUCTS: Pearl Mini, Pearl Nano, Pearl Nexus, Pearl-2, EC20 PTZ, AV.io 4K, AV.io HD+, AV.io SDI+

Extract the following and return ONLY valid JSON:
{{
    "detected_vertical": "best matching vertical key from list above (e.g., 'higher_ed', 'k12')",
    "detected_persona": "best matching buyer persona (e.g., 'av_director', 'court_admin', 'ehs_manager')",
    "interests": ["list of specific use cases or topics they mentioned"],
    "pain_points": ["list of specific problems or frustrations expressed"],
    "products_mentioned": ["any Epiphan or competitor products mentioned"],
    "org_size_hints": ["any mentions of room counts, campus size, locations, employees"],
    "buyer_signals": ["phrases that indicate buying intent or urgency"],
    "confidence": 0.85
}}

RULES:
- Use EXACT quotes from the transcript where possible
- If vertical is ambiguous, pick the best match and note low confidence
- If no products mentioned, leave the list empty
- confidence is 0.0-1.0 based on how clear the signals are"""

        response_text = await self.gemini_client._call_deepseek(prompt)
        repaired = _repair_json(response_text)

        try:
            signals = json.loads(repaired)
        except json.JSONDecodeError:
            logger.error(f"[EXTRACT] Failed to parse extraction: {response_text[:500]}")
            signals = {
                "detected_vertical": vertical_hint or "corporate",
                "detected_persona": persona_hint or "av_director",
                "interests": [],
                "pain_points": [],
                "products_mentioned": [],
                "org_size_hints": [],
                "buyer_signals": [],
                "confidence": 0.3,
            }

        # Apply BDR hints as overrides if provided
        if vertical_hint and vertical_hint in EPIPHAN_VERTICALS:
            signals["detected_vertical"] = vertical_hint
        if persona_hint:
            signals["detected_persona"] = persona_hint

        return signals

    # ── Stage 2: Match + Customize ────────────────────────────────────────

    async def match_and_customize(
        self,
        transcript: str,
        signals: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Stage 2: Match scenarios from library and customize with call details.

        Uses both keyword matching (fast) and LLM ranking (smart).
        """
        vertical = signals.get("detected_vertical", "")

        # Step 1: Keyword-based pre-filter
        keyword_matches = match_scenarios_by_phrases(
            transcript,
            vertical_filter=None,  # Don't restrict — cross-vertical matches are valuable
            top_n=8,
        )

        # Build scenario context for LLM
        scenario_summaries = _build_scenario_summary()

        # Step 2: LLM ranking + customization
        interests = signals.get("interests", [])
        pain_points = signals.get("pain_points", [])
        org_hints = signals.get("org_size_hints", [])

        # Pre-filter IDs for context
        prefilt_ids = [s.id for s, _ in keyword_matches]

        prompt = f"""You are matching call transcript signals to Epiphan deployment scenarios.

DETECTED SIGNALS:
- Vertical: {vertical}
- Interests: {json.dumps(interests)}
- Pain points: {json.dumps(pain_points)}
- Org size hints: {json.dumps(org_hints)}
- Keyword pre-matches: {json.dumps(prefilt_ids)}

FULL SCENARIO LIBRARY:
{scenario_summaries}

TRANSCRIPT EXCERPT (for context):
{transcript[:8000]}

YOUR TASK:
1. Pick the TOP 3-4 scenarios that best match this prospect's situation
2. For each, CUSTOMIZE the setup_description and creative_hook using specifics from the call
3. If the transcript suggests a deployment NOT in the library, you may INVENT one new scenario (use id "custom_1")

Return ONLY valid JSON — an array of objects:
[
    {{
        "scenario_id": "higher_ed_campus_capture",
        "customized_setup": "Customized 2-3 sentence narrative using call specifics (room counts, specific pain points mentioned, etc.)",
        "customized_hook": "Customized creative hook referencing what the prospect said",
        "relevance_reason": "Why this scenario matches (1 sentence)"
    }}
]

RULES:
- Always include 3-4 scenarios (never fewer than 2, never more than 5)
- Use SPECIFIC details from the transcript (room counts, quoted frustrations, named products)
- For invented scenarios, include full details: scenario_id="custom_1", customized_setup, customized_hook
- Rank by relevance — most relevant first"""

        response_text = await self.gemini_client._call_deepseek(prompt)
        repaired = _repair_json(response_text)

        try:
            ranked = json.loads(repaired)
            if not isinstance(ranked, list):
                ranked = [ranked]
        except json.JSONDecodeError:
            logger.error(f"[MATCH] Failed to parse ranking: {response_text[:500]}")
            # Fall back to keyword matches
            ranked = [
                {
                    "scenario_id": s.id,
                    "customized_setup": s.setup_description,
                    "customized_hook": s.creative_hook,
                    "relevance_reason": f"Matched {hits} trigger phrases",
                }
                for s, hits in keyword_matches[:3]
            ]

        # Enrich with full scenario data
        enriched: list[dict[str, Any]] = []
        for item in ranked[:4]:
            sid = item.get("scenario_id", "")
            scenario = get_scenario_by_id(sid)

            if scenario:
                product_names = [
                    EPIPHAN_PRODUCTS[p]["name"]
                    for p in scenario.products
                    if p in EPIPHAN_PRODUCTS
                ]
                enriched.append(
                    {
                        "scenario_id": scenario.id,
                        "scenario_name": scenario.name,
                        "vertical": scenario.vertical,
                        "products": product_names,
                        "bundle_name": scenario.bundle_name,
                        "setup_description": item.get(
                            "customized_setup", scenario.setup_description
                        ),
                        "reference_story": scenario.reference_story,
                        "creative_hook": item.get(
                            "customized_hook", scenario.creative_hook
                        ),
                        "relevance_reason": item.get("relevance_reason", ""),
                    }
                )
            elif sid.startswith("custom_"):
                # Invented scenario
                enriched.append(
                    {
                        "scenario_id": sid,
                        "scenario_name": item.get("customized_hook", "Custom Scenario")[
                            :60
                        ],
                        "vertical": signals.get("detected_vertical", "corporate"),
                        "products": [],
                        "bundle_name": None,
                        "setup_description": item.get("customized_setup", ""),
                        "reference_story": None,
                        "creative_hook": item.get("customized_hook", ""),
                        "relevance_reason": item.get("relevance_reason", ""),
                    }
                )

        return enriched

    # ── Stage 3: Generate Storyboards (parallel) ─────────────────────────

    async def generate_scenario_storyboard(
        self,
        scenario: dict[str, Any],
        audience: str,
    ) -> str:
        """Generate a single storyboard PNG for one scenario. Returns base64 string."""
        # Build an understanding object from scenario data
        understanding = StoryboardUnderstanding(
            headline=scenario["scenario_name"][:50],
            tagline=scenario.get("creative_hook", "")[:80],
            what_it_does=scenario["setup_description"][:200],
            business_value=scenario.get(
                "relevance_reason", "Tailored Epiphan deployment for your organization"
            ),
            who_benefits=f"{scenario['vertical']} professionals",
            differentiator=scenario.get("creative_hook", "")[:150],
            pain_point_addressed=scenario.get("relevance_reason", ""),
            suggested_icon="video-camera",
            raw_extracted_text=(
                f"Products: {', '.join(scenario.get('products', []))}\n"
                f"Reference: {scenario.get('reference_story', 'N/A')}\n"
                f"Bundle: {scenario.get('bundle_name', 'N/A')}"
            ),
            extraction_confidence=0.9,
        )

        png_bytes = await self.gemini_client.generate_storyboard(
            understanding=understanding,
            stage="preview",
            audience=audience,
            icp_preset=get_icp_preset("epiphan_av"),
        )

        return base64.b64encode(png_bytes).decode("utf-8")

    async def generate_all_storyboards(
        self,
        scenarios: list[dict[str, Any]],
        audience: str,
    ) -> list[str]:
        """Generate storyboard PNGs for all scenarios in parallel."""
        tasks = [self.generate_scenario_storyboard(s, audience) for s in scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pngs: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[GENERATE] Storyboard failed for scenario {i}: {result}")
                pngs.append("")
            else:
                pngs.append(result)
        return pngs

    # ── Stage 4: Draft Email ──────────────────────────────────────────────

    async def draft_email(
        self,
        scenarios: list[dict[str, Any]],
        signals: dict[str, Any],
        prospect_name: str | None = None,
        prospect_company: str | None = None,
    ) -> dict[str, str]:
        """
        Stage 4: Draft a BDR follow-up email.

        Returns dict with 'subject' and 'body' keys.
        """
        scenario_names = [s["scenario_name"] for s in scenarios]
        interests = signals.get("interests", [])
        pain_points = signals.get("pain_points", [])

        # Sanitize user-supplied strings before interpolating into LLM prompt
        safe_name = (prospect_name or "there")[:200].replace("\n", " ").strip()
        safe_company = (prospect_company or "")[:200].replace("\n", " ").strip()
        name_line = safe_name or "there"
        company_ref = f" at {safe_company}" if safe_company else ""

        prompt = f"""Write a BDR follow-up email after a discovery call with {name_line}{company_ref}.

CALL CONTEXT:
- They're interested in: {json.dumps(interests)}
- They're frustrated by: {json.dumps(pain_points)}
- Vertical: {signals.get("detected_vertical", "unknown")}

VISUAL SCENARIOS WE'RE ATTACHING (reference these by name):
{json.dumps(scenario_names)}

RULES:
- Tone: helpful peer, NOT salesy. Like a friend who knows AV.
- Reference 2-3 SPECIFIC things from the call
- Mention the attached visual scenarios by name
- NO pricing — just product names (Pearl Mini, Pearl Nano, etc.)
- Under 150 words in the body
- Subject line should reference THEIR situation, not ours

Return ONLY valid JSON:
{{
    "subject": "Short subject referencing their situation",
    "body": "Email body text under 150 words"
}}"""

        response_text = await self.gemini_client._call_deepseek(prompt)
        repaired = _repair_json(response_text)

        try:
            email = json.loads(repaired)
            return {
                "subject": email.get("subject", "Following up on our conversation"),
                "body": email.get("body", ""),
            }
        except json.JSONDecodeError:
            logger.error(f"[EMAIL] Failed to parse email draft: {response_text[:500]}")
            return {
                "subject": f"Following up on our conversation{company_ref}",
                "body": (
                    f"Hi {name_line},\n\n"
                    "Great speaking with you. I put together a few visual deployment scenarios "
                    "based on what we discussed — see attached.\n\n"
                    "Would love to walk through them with you.\n\nBest"
                ),
            }

    # ── Main Pipeline ─────────────────────────────────────────────────────

    async def run(self, arguments: dict) -> ToolResult:
        """Execute the full transcript-to-scenarios pipeline."""
        start_time = perf_counter()

        transcript = arguments.get("transcript", "")
        if not transcript or not transcript.strip():
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result={},
                error="Missing required 'transcript' parameter",
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )

        vertical_hint = arguments.get("vertical_hint")
        persona_hint = arguments.get("persona_hint")
        prospect_name = arguments.get("prospect_name")
        prospect_company = arguments.get("prospect_company")

        try:
            # Stage 1: Extract signals
            logger.info("[TRANSCRIPT_PIPELINE] Stage 1: Extracting signals...")
            signals = await self.extract_signals(
                transcript, vertical_hint, persona_hint
            )
            audience = signals.get("detected_persona", "av_director")
            logger.info(
                f"[TRANSCRIPT_PIPELINE] Detected vertical={signals.get('detected_vertical')}, "
                f"persona={audience}, confidence={signals.get('confidence', 0)}"
            )

            # Stage 2: Match + customize scenarios
            logger.info("[TRANSCRIPT_PIPELINE] Stage 2: Matching scenarios...")
            matched_scenarios = await self.match_and_customize(transcript, signals)
            logger.info(
                f"[TRANSCRIPT_PIPELINE] Matched {len(matched_scenarios)} scenarios"
            )

            if not matched_scenarios:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    result={"signals": signals},
                    error="No matching scenarios found for this transcript",
                    execution_time_ms=int((perf_counter() - start_time) * 1000),
                )

            # Stage 3: Generate storyboards (parallel)
            logger.info("[TRANSCRIPT_PIPELINE] Stage 3: Generating storyboards...")
            storyboard_pngs = await self.generate_all_storyboards(
                matched_scenarios, audience
            )

            # Stage 4: Draft email
            logger.info("[TRANSCRIPT_PIPELINE] Stage 4: Drafting email...")
            email = await self.draft_email(
                matched_scenarios, signals, prospect_name, prospect_company
            )

            # Assemble result
            scenario_results = []
            for i, scenario in enumerate(matched_scenarios):
                scenario_results.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "scenario_name": scenario["scenario_name"],
                        "vertical": scenario["vertical"],
                        "products": scenario.get("products", []),
                        "bundle_name": scenario.get("bundle_name"),
                        "setup_description": scenario["setup_description"],
                        "reference_story": scenario.get("reference_story"),
                        "storyboard_png": storyboard_pngs[i]
                        if i < len(storyboard_pngs)
                        else "",
                        "creative_hook": scenario.get("creative_hook", ""),
                    }
                )

            execution_time_ms = int((perf_counter() - start_time) * 1000)
            logger.info(
                f"[TRANSCRIPT_PIPELINE] Complete in {execution_time_ms}ms — "
                f"{len(scenario_results)} scenarios, email drafted"
            )

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result={
                    "scenarios": scenario_results,
                    "email_draft": email,
                    "detected_vertical": signals.get("detected_vertical", ""),
                    "detected_persona": audience,
                    "extraction_confidence": signals.get("confidence", 0.0),
                    "signals": signals,
                },
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.exception(f"[TRANSCRIPT_PIPELINE] Error: {e}")
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result={},
                error=str(e),
                execution_time_ms=int((perf_counter() - start_time) * 1000),
            )
