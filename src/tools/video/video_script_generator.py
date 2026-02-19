"""
Video Script Generator Tool for AI-Powered Sales Prospecting

Generates personalized 60-second Loom video scripts using Chinese LLMs via OpenRouter.
Follows Hook→Value→Proof→CTA structure optimized for cold outreach.
"""

import json
import os
from datetime import UTC, datetime
from typing import Any

import aiohttp

from src.model_catalog import select_model
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class VideoScriptGeneratorTool(BaseTool):
    """
    Tool for generating personalized video sales scripts using AI.

    Uses cost-optimized Chinese LLMs (DeepSeek V3.1 default at $0.20/$0.80 per 1M tokens)
    to create 60-second Loom scripts tailored to prospect's industry and pain points.

    Script Structure:
        - HOOK (0-10s): Pattern interrupt + personalization
        - VALUE (10-30s): Industry pain point + solution
        - PROOF (30-45s): Social proof / case study
        - CTA (45-60s): Clear next step with low-friction ask

    Supports industry-specific templates for:
        - Solar
        - HVAC
        - Electrical
        - MEP (Mechanical, Electrical, Plumbing)
        - Roofing
        - General Contractor
    """

    # Constants
    DEFAULT_MODEL = "deepseek/deepseek-chat-v3"
    FALLBACK_MODEL = "qwen/qwen-2.5-72b-instruct"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 30  # seconds

    # Industry-specific context for better personalization
    INDUSTRY_CONTEXTS = {
        "solar": {
            "pain_points": [
                "Low show rates from unqualified leads",
                "Difficulty reaching decision-makers",
                "Long sales cycles with delayed ROI",
                "Competition from local installers",
            ],
            "proof_examples": [
                "helped a California solar installer increase qualified appointments by 40%",
                "reduced no-show rates from 35% to 12% for Arizona solar companies",
            ],
        },
        "hvac": {
            "pain_points": [
                "Seasonal demand fluctuations",
                "Emergency service leads that don't convert",
                "Competing against big box stores",
                "Hard to differentiate on price alone",
            ],
            "proof_examples": [
                "helped an HVAC company in Texas book 23 maintenance contracts in 30 days",
                "increased average ticket size by $1,200 for residential HVAC installs",
            ],
        },
        "electrical": {
            "pain_points": [
                "Finding commercial project leads",
                "Lengthy bid processes with low win rates",
                "Hard to reach facility managers",
                "Competing on more than just price",
            ],
            "proof_examples": [
                "helped electrical contractors win 3 commercial bids worth $450K",
                "connected a Miami electrician with 12 property management companies",
            ],
        },
        "mep": {
            "pain_points": [
                "Complex multi-stakeholder decision processes",
                "Long lead times on commercial projects",
                "Difficulty establishing relationships with GCs",
                "Tight margins on competitive bids",
            ],
            "proof_examples": [
                "helped an MEP contractor secure 2 multi-million dollar projects",
                "reduced bid-to-award time by 6 weeks through better qualification",
            ],
        },
        "roofing": {
            "pain_points": [
                "Storm-chasing competitors flooding the market",
                "Insurance claim delays and disputes",
                "Weather-dependent lead generation",
                "High customer acquisition costs",
            ],
            "proof_examples": [
                "helped a roofing company close $380K in insurance claims in Q3",
                "generated 47 qualified residential leads during off-season",
            ],
        },
        "general_contractor": {
            "pain_points": [
                "Bidding on projects you can't win",
                "Cash flow issues with net-30/60 terms",
                "Subcontractor coordination headaches",
                "Difficulty scaling beyond word-of-mouth",
            ],
            "proof_examples": [
                "helped a GC win 5 commercial projects in 8 weeks",
                "connected contractors with vetted subcontractors saving 15+ hours/week",
            ],
        },
        "default": {
            "pain_points": [
                "Generating consistent qualified leads",
                "Wasting time on unqualified prospects",
                "Standing out in a crowded market",
                "Converting cold outreach to conversations",
            ],
            "proof_examples": [
                "helped similar companies increase conversion rates by 35%",
                "generated 50+ qualified leads in the first 30 days",
            ],
        },
    }

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for video_script_generator."""
        return ToolDefinition(
            name="video_script_generator",
            description=(
                "Generate personalized 60-second Loom video script for sales prospecting. "
                "Creates Hook→Value→Proof→CTA structure tailored to prospect's industry and company."
            ),
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "prospect_name": {
                        "type": "string",
                        "description": "First name of the prospect (e.g., 'John')",
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Company name (e.g., 'SunPower Solutions LLC')",
                    },
                    "industry": {
                        "type": "string",
                        "description": (
                            "Industry vertical: solar, hvac, electrical, mep, roofing, "
                            "general_contractor, or other"
                        ),
                        "enum": [
                            "solar",
                            "hvac",
                            "electrical",
                            "mep",
                            "roofing",
                            "general_contractor",
                            "other",
                        ],
                    },
                    "company_website": {
                        "type": "string",
                        "description": "Company website URL (optional, used for additional context)",
                    },
                    "linkedin_url": {
                        "type": "string",
                        "description": "Prospect's LinkedIn URL (optional, for personalization)",
                    },
                    "pain_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Specific pain points to address (optional, will use "
                            "industry defaults if not provided)"
                        ),
                    },
                    "product_features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Key product features to highlight (optional, generic "
                            "if not provided)"
                        ),
                    },
                },
                "required": ["prospect_name", "company_name", "industry"],
            },
        )

    def _get_industry_context(self, industry: str) -> dict:
        """
        Get industry-specific context for script generation.

        Args:
            industry: Industry vertical

        Returns:
            Dictionary with pain_points and proof_examples
        """
        industry_key = industry.lower().replace(" ", "_")
        return self.INDUSTRY_CONTEXTS.get(
            industry_key, self.INDUSTRY_CONTEXTS["default"]
        )

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM.

        Returns:
            System prompt string
        """
        return """You are an expert sales copywriter specializing in cold outreach video scripts.

Your scripts follow the proven Hook→Value→Proof→CTA structure and are designed for 60-second Loom videos.

CRITICAL RULES:
1. Keep total script under 150 words (60 seconds at natural speaking pace)
2. Use conversational, friendly tone - avoid corporate jargon
3. Include specific timestamps for each section
4. Make personalization natural, not forced
5. Focus on THEIR pain, not YOUR product
6. Keep CTA low-friction (15-min call, not "demo" or "meeting")

Structure every script as:
- HOOK (0-10s): Pattern interrupt + name drop company
- VALUE (10-30s): Specific pain point + how you solve it
- PROOF (30-45s): Brief case study or social proof
- CTA (45-60s): Clear next step with calendar link or contact method

Output format must be valid JSON with this structure:
{
  "hook": {
    "text": "Script text for hook section",
    "timestamp": "0:00-0:10",
    "notes": "Delivery guidance"
  },
  "value": {
    "text": "Script text for value section",
    "timestamp": "0:10-0:30",
    "notes": "Delivery guidance"
  },
  "proof": {
    "text": "Script text for proof section",
    "timestamp": "0:30-0:45",
    "notes": "Delivery guidance"
  },
  "cta": {
    "text": "Script text for CTA section",
    "timestamp": "0:45-0:60",
    "notes": "Delivery guidance"
  },
  "full_script": "Complete script as one paragraph for easy reading",
  "word_count": 145,
  "estimated_duration_seconds": 60
}"""

    def _build_user_prompt(
        self,
        prospect_name: str,
        company_name: str,
        industry: str,
        company_website: str | None = None,
        linkedin_url: str | None = None,
        pain_points: list | None = None,
        product_features: list | None = None,
    ) -> str:
        """
        Build the user prompt with prospect details.

        Args:
            prospect_name: Prospect's first name
            company_name: Company name
            industry: Industry vertical
            company_website: Optional company website
            linkedin_url: Optional LinkedIn URL
            pain_points: Optional list of specific pain points
            product_features: Optional list of product features

        Returns:
            User prompt string
        """
        # Get industry context
        context = self._get_industry_context(industry)

        # Use provided pain points or industry defaults
        pain_points_text = (
            "\n- ".join(pain_points)
            if pain_points
            else "\n- ".join(context["pain_points"][:2])
        )

        # Build prompt
        prompt = f"""Generate a personalized 60-second Loom video script for:

PROSPECT DETAILS:
- Name: {prospect_name}
- Company: {company_name}
- Industry: {industry}"""

        if company_website:
            prompt += f"\n- Website: {company_website}"

        if linkedin_url:
            prompt += f"\n- LinkedIn: {linkedin_url}"

        prompt += f"""

PAIN POINTS TO ADDRESS:
- {pain_points_text}"""

        if product_features:
            features_text = "\n- ".join(product_features)
            prompt += f"""

PRODUCT FEATURES TO HIGHLIGHT:
- {features_text}"""

        prompt += f"""

SOCIAL PROOF IDEAS:
- {context["proof_examples"][0]}

Create a script that:
1. Opens with a pattern interrupt that mentions {company_name} specifically
2. Addresses their biggest pain point in {industry}
3. Shows proof that your solution works for similar companies
4. Ends with a low-friction ask (15-min call)

Output valid JSON with hook, value, proof, cta sections, timestamps, and notes."""

        return prompt

    async def _call_llm(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> dict[str, Any]:
        """
        Call OpenRouter API to generate script.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt with prospect details
            model: Model ID to use

        Returns:
            Parsed JSON response from LLM

        Raises:
            Exception: If API call fails or response is invalid
        """
        # Get API key from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables"
            )

        # Build request
        url = f"{self.OPENROUTER_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://conductor-ai.com",
            "X-Title": "Conductor-AI Video Script Generator",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        # Make request
        timeout = aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"OpenRouter API error: {response.status} - {error_text}"
                    )

                # Parse response
                data = await response.json()

        if "error" in data:
            raise Exception(f"OpenRouter API error: {data['error']}")

        # Extract content
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise Exception("Empty response from LLM")

        # Parse JSON from content
        try:
            script_data: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM response as JSON: {str(e)}") from e

        return script_data

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the video script generation.

        Args:
            arguments: Tool arguments containing prospect details

        Returns:
            ToolResult with structured script data or error
        """
        # Extract arguments
        prospect_name = arguments.get("prospect_name")
        company_name = arguments.get("company_name")
        industry = arguments.get("industry")
        company_website = arguments.get("company_website")
        linkedin_url = arguments.get("linkedin_url")
        pain_points = arguments.get("pain_points")
        product_features = arguments.get("product_features")

        # Validate required fields
        if not prospect_name or not company_name or not industry:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Missing required fields: prospect_name, company_name, or industry",
                execution_time_ms=0,
            )

        try:
            # Select model (default to DeepSeek V3.1 for best value)
            model = select_model(task="agents", require_function_calling=False)
            if not model:
                model = self.DEFAULT_MODEL

            # Build prompts
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(
                prospect_name=prospect_name,
                company_name=company_name,
                industry=industry,
                company_website=company_website,
                linkedin_url=linkedin_url,
                pain_points=pain_points,
                product_features=product_features,
            )

            # Generate script
            try:
                script_data = await self._call_llm(
                    system_prompt, user_prompt, model
                )
            except Exception as primary_error:
                # Fallback to Qwen if DeepSeek fails
                try:
                    script_data = await self._call_llm(
                        system_prompt, user_prompt, self.FALLBACK_MODEL
                    )
                except Exception as fallback_error:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        result=None,
                        error=(
                            f"Both primary ({model}) and fallback ({self.FALLBACK_MODEL}) "
                            f"models failed. Primary: {str(primary_error)}. "
                            f"Fallback: {str(fallback_error)}"
                        ),
                        execution_time_ms=0,
                    )

            # Validate script structure
            required_fields = ["hook", "value", "proof", "cta", "full_script"]
            missing_fields = [
                field for field in required_fields if field not in script_data
            ]

            if missing_fields:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    result=None,
                    error=f"LLM response missing required fields: {', '.join(missing_fields)}",
                    execution_time_ms=0,
                )

            # Add metadata
            result_data = {
                **script_data,
                "metadata": {
                    "prospect_name": prospect_name,
                    "company_name": company_name,
                    "industry": industry,
                    "model_used": model,
                    "generation_timestamp": datetime.now(tz=UTC).isoformat(),
                },
            }

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result_data,
                error=None,
                execution_time_ms=0,  # Will be set by _execute_with_timing
            )

        except aiohttp.ClientResponseError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"HTTP error calling OpenRouter API: {e.status} - {e.message}",
                execution_time_ms=0,
            )
        except aiohttp.ClientError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Client error calling OpenRouter API: {str(e)}",
                execution_time_ms=0,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Unexpected error: {str(e)}",
                execution_time_ms=0,
            )
