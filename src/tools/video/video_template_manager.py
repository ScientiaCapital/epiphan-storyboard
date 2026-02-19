"""Video template manager tool for industry-specific demo generation."""

import json
import os
from enum import Enum
from time import perf_counter
from typing import Any

import aiohttp

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class Industry(str, Enum):
    """Supported industry verticals for video templates."""

    SOLAR = "solar"
    HVAC = "hvac"
    ELECTRICAL = "electrical"
    ROOFING = "roofing"
    MEP = "mep"
    GENERAL_CONTRACTOR = "general_contractor"


class SceneType(str, Enum):
    """Video demo scene types."""

    INTRO_SCENE = "intro_scene"
    PROBLEM_SCENE = "problem_scene"
    SOLUTION_SCENE = "solution_scene"
    DIFFERENTIATION_SCENE = "differentiation_scene"
    RESULTS_SCENE = "results_scene"
    CTA_SCENE = "cta_scene"


# Industry-specific pain points and features
INDUSTRY_PRESETS = {
    Industry.SOLAR: {
        "pain_points": [
            "Permit tracking across multiple jurisdictions",
            "Complex financing options confusing customers",
            "Customer portal access for installation progress",
            "Rebate and incentive management",
        ],
        "key_features": [
            "Permit tracking dashboard",
            "Customer self-service portal",
            "Financing integration (Mosaic, Sunlight, GoodLeap)",
            "Automated rebate calculations",
        ],
        "roi_metrics": [
            "40% reduction in permit approval time",
            "85% customer satisfaction with portal access",
            "30% increase in financing conversion rate",
        ],
    },
    Industry.HVAC: {
        "pain_points": [
            "Service scheduling conflicts and double-bookings",
            "Equipment tracking across job sites",
            "Maintenance contract renewals falling through cracks",
            "Technician skill matching for complex jobs",
        ],
        "key_features": [
            "Real-time service scheduling",
            "Equipment inventory management",
            "Automated maintenance contract reminders",
            "Technician certification tracking",
        ],
        "roi_metrics": [
            "50% reduction in scheduling conflicts",
            "95% equipment utilization tracking",
            "25% increase in maintenance contract renewals",
        ],
    },
    Industry.ELECTRICAL: {
        "pain_points": [
            "Job costing inaccuracies leading to profit loss",
            "Material ordering delays and waste",
            "Compliance documentation scattered across systems",
            "Change order management chaos",
        ],
        "key_features": [
            "Real-time job cost tracking",
            "Integrated material ordering",
            "Centralized compliance documentation",
            "Digital change order workflow",
        ],
        "roi_metrics": [
            "35% improvement in job profitability",
            "20% reduction in material waste",
            "90% compliance audit success rate",
        ],
    },
    Industry.ROOFING: {
        "pain_points": [
            "Weather delays disrupting schedules",
            "Material waste from poor estimating",
            "Crew scheduling inefficiencies",
            "Customer communication gaps during installation",
        ],
        "key_features": [
            "Weather-aware scheduling",
            "AI-powered material estimation",
            "Crew availability tracking",
            "Automated customer progress updates",
        ],
        "roi_metrics": [
            "30% reduction in weather-related delays",
            "25% decrease in material waste",
            "40% improvement in crew utilization",
        ],
    },
    Industry.MEP: {
        "pain_points": [
            "Multi-trade coordination nightmares",
            "BIM integration challenges",
            "RFI management across disciplines",
            "Clash detection follow-up",
        ],
        "key_features": [
            "Multi-trade coordination dashboard",
            "BIM model integration",
            "Centralized RFI workflow",
            "Automated clash resolution tracking",
        ],
        "roi_metrics": [
            "50% reduction in coordination meetings",
            "70% faster RFI response time",
            "90% clash resolution tracking accuracy",
        ],
    },
    Industry.GENERAL_CONTRACTOR: {
        "pain_points": [
            "Subcontractor management complexity",
            "Change order tracking and approval delays",
            "Progress billing inaccuracies",
            "Document version control chaos",
        ],
        "key_features": [
            "Subcontractor performance tracking",
            "Digital change order workflow",
            "Automated progress billing",
            "Cloud-based document management",
        ],
        "roi_metrics": [
            "60% faster change order approvals",
            "95% billing accuracy",
            "80% reduction in document retrieval time",
        ],
    },
}

# Scene timing templates (in seconds)
SCENE_TIMING = {
    SceneType.INTRO_SCENE: {"start": 0, "end": 15, "duration": 15},
    SceneType.PROBLEM_SCENE: {"start": 15, "end": 45, "duration": 30},
    SceneType.SOLUTION_SCENE: {"start": 45, "end": 90, "duration": 45},
    SceneType.DIFFERENTIATION_SCENE: {"start": 90, "end": 120, "duration": 30},
    SceneType.RESULTS_SCENE: {"start": 120, "end": 150, "duration": 30},
    SceneType.CTA_SCENE: {"start": 150, "end": 180, "duration": 30},
}


class VideoTemplateManagerTool(BaseTool):
    """
    Tool for managing industry-specific video demo templates.

    Generates customized demo structures with scene-by-scene breakdowns,
    timing, talking points, and suggested b-roll for various construction
    and contracting industries.

    Uses DeepSeek V3 via OpenRouter for intelligent template customization
    based on prospect segment, product features, and competitive landscape.
    """

    # DeepSeek V3 model for template customization
    MODEL_ID = "deepseek/deepseek-chat-v3"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_TIMEOUT = 60  # seconds

    def __init__(self) -> None:
        """Initialize the tool with in-memory template storage."""
        # In-memory template storage (can be extended to Redis/DB later)
        self._templates: dict[str, dict[str, Any]] = {}
        self._api_key = os.getenv("OPENROUTER_API_KEY")

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for video_template_manager."""
        return ToolDefinition(
            name="video_template_manager",
            description=(
                "Generate customized video demo templates for construction/contracting industries. "
                "Creates scene-by-scene breakdowns with timing, talking points, and b-roll suggestions. "
                "Supports SOLAR, HVAC, ELECTRICAL, ROOFING, MEP, and GENERAL_CONTRACTOR industries."
            ),
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform: customize_template, get_template, list_templates",
                        "enum": ["customize_template", "get_template", "list_templates"],
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry vertical",
                        "enum": [
                            "solar",
                            "hvac",
                            "electrical",
                            "roofing",
                            "mep",
                            "general_contractor",
                        ],
                    },
                    "prospect_segment": {
                        "type": "string",
                        "description": "Target prospect segment (e.g., 'residential installer', 'commercial GC', 'service company')",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Name of the product/service being demoed",
                    },
                    "key_features": {
                        "type": "array",
                        "description": "List of key product features to highlight",
                        "items": {"type": "string"},
                    },
                    "competitor_mentioned": {
                        "type": "string",
                        "description": "Competitor name if differentiation is needed (optional)",
                    },
                    "template_id": {
                        "type": "string",
                        "description": "Template ID for get_template operation",
                    },
                },
                "required": ["operation"],
            },
        )

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the video template manager operation.

        Args:
            arguments: Tool arguments containing operation and parameters

        Returns:
            ToolResult with template data or error
        """
        operation = arguments.get("operation")

        if operation == "customize_template":
            return await self._customize_template(arguments)
        elif operation == "get_template":
            return await self._get_template(arguments)
        elif operation == "list_templates":
            return await self._list_templates()
        else:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Unknown operation: {operation}",
                execution_time_ms=0,
            )

    async def _customize_template(self, arguments: dict) -> ToolResult:
        """
        Generate a customized video template using LLM.

        Args:
            arguments: Template customization parameters

        Returns:
            ToolResult with customized template
        """
        # Extract arguments
        industry = arguments.get("industry")
        prospect_segment = arguments.get("prospect_segment")
        product_name = arguments.get("product_name")
        key_features = arguments.get("key_features", [])
        competitor_mentioned = arguments.get("competitor_mentioned")

        # Validate required fields
        if not industry:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Missing required field: industry",
                execution_time_ms=0,
            )

        if not prospect_segment or not product_name:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Missing required fields: prospect_segment, product_name",
                execution_time_ms=0,
            )

        # Get industry preset
        try:
            industry_enum = Industry(industry.lower())
        except ValueError:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Invalid industry: {industry}. Must be one of: {[i.value for i in Industry]}",
                execution_time_ms=0,
            )

        preset = INDUSTRY_PRESETS[industry_enum]

        # Build base template structure
        base_template = self._build_base_template(
            industry_enum,
            preset,
            prospect_segment,
            product_name,
            key_features,
            competitor_mentioned,
        )

        # Use LLM to customize template
        try:
            customized_template = await self._llm_customize_template(
                base_template,
                industry_enum,
                preset,
                prospect_segment,
                product_name,
                key_features,
                competitor_mentioned,
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"LLM customization failed: {str(e)}",
                execution_time_ms=0,
            )

        # Generate template ID and store
        template_id = self._generate_template_id(industry_enum, prospect_segment, product_name)
        self._templates[template_id] = customized_template

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result={
                "template_id": template_id,
                "template": customized_template,
            },
            error=None,
            execution_time_ms=0,
        )

    async def _get_template(self, arguments: dict) -> ToolResult:
        """
        Retrieve a stored template by ID.

        Args:
            arguments: Contains template_id

        Returns:
            ToolResult with template data
        """
        template_id = arguments.get("template_id")

        if not template_id:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Missing required field: template_id",
                execution_time_ms=0,
            )

        template = self._templates.get(template_id)

        if not template:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Template not found: {template_id}",
                execution_time_ms=0,
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result={
                "template_id": template_id,
                "template": template,
            },
            error=None,
            execution_time_ms=0,
        )

    async def _list_templates(self) -> ToolResult:
        """
        List all stored templates.

        Returns:
            ToolResult with list of template IDs and metadata
        """
        template_list = [
            {
                "template_id": tid,
                "industry": template.get("industry"),
                "prospect_segment": template.get("prospect_segment"),
                "product_name": template.get("product_name"),
                "total_duration": template.get("total_duration"),
                "scene_count": len(template.get("scenes", [])),
            }
            for tid, template in self._templates.items()
        ]

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result={
                "count": len(template_list),
                "templates": template_list,
            },
            error=None,
            execution_time_ms=0,
        )

    def _build_base_template(
        self,
        industry: Industry,
        preset: dict[str, Any],
        prospect_segment: str,
        product_name: str,
        key_features: list[str],
        competitor_mentioned: str | None,
    ) -> dict[str, Any]:
        """
        Build base template structure before LLM customization.

        Args:
            industry: Industry enum
            preset: Industry preset data
            prospect_segment: Target segment
            product_name: Product name
            key_features: List of features
            competitor_mentioned: Optional competitor name

        Returns:
            Base template dictionary
        """
        # Select relevant pain points based on key features
        relevant_pain_points = preset["pain_points"][:3]  # Top 3 pain points
        relevant_features = preset["key_features"][:4]  # Top 4 features
        roi_metrics = preset["roi_metrics"][:3]  # Top 3 ROI metrics

        scenes: list[dict[str, Any]] = []

        # INTRO_SCENE (0-15s)
        scenes.append({
            "scene_type": SceneType.INTRO_SCENE.value,
            "timing": SCENE_TIMING[SceneType.INTRO_SCENE],
            "title": "Introduction",
            "description": f"Personalized greeting for {prospect_segment} with agenda preview",
            "talking_points": [
                f"Welcome to {product_name} demo",
                f"Tailored for {prospect_segment} in {industry.value}",
                "Quick overview of what we'll cover today",
            ],
            "suggested_broll": [
                "Company logo animation",
                "Quick montage of industry-specific work",
                "Presenter intro card",
            ],
        })

        # PROBLEM_SCENE (15-45s)
        scenes.append({
            "scene_type": SceneType.PROBLEM_SCENE.value,
            "timing": SCENE_TIMING[SceneType.PROBLEM_SCENE],
            "title": "Industry Pain Points",
            "description": f"Visualization of key challenges facing {prospect_segment}",
            "talking_points": [
                f"Challenge: {pain_point}"
                for pain_point in relevant_pain_points
            ],
            "suggested_broll": [
                "Split-screen showing current vs ideal workflow",
                "Animation of pain point scenarios",
                "Customer testimonial quotes (optional)",
            ],
        })

        # SOLUTION_SCENE (45-90s)
        scenes.append({
            "scene_type": SceneType.SOLUTION_SCENE.value,
            "timing": SCENE_TIMING[SceneType.SOLUTION_SCENE],
            "title": "Product Walkthrough",
            "description": f"{product_name} feature demonstration",
            "talking_points": [
                f"Feature: {feature}"
                for feature in (key_features if key_features else relevant_features)
            ],
            "suggested_broll": [
                "Screen recording: Dashboard overview",
                "Screen recording: Key feature demos",
                "Screen recording: Mobile app preview",
                "UI/UX highlights with callouts",
            ],
        })

        # DIFFERENTIATION_SCENE (90-120s) - only if competitor mentioned
        if competitor_mentioned:
            scenes.append({
                "scene_type": SceneType.DIFFERENTIATION_SCENE.value,
                "timing": SCENE_TIMING[SceneType.DIFFERENTIATION_SCENE],
                "title": "Competitive Differentiation",
                "description": f"Why {product_name} vs {competitor_mentioned}",
                "talking_points": [
                    f"Unlike {competitor_mentioned}, we offer...",
                    "Unique value propositions",
                    "Customer success stories switching from competitors",
                ],
                "suggested_broll": [
                    "Side-by-side feature comparison table",
                    "Customer testimonials",
                    "Pricing transparency graphic",
                ],
            })
        else:
            # Skip differentiation scene, use time for extended solution demo
            scenes[2]["timing"]["end"] = 120  # Extend solution scene

        # RESULTS_SCENE (120-150s)
        results_start = 120 if competitor_mentioned else 120
        results_end = 150 if competitor_mentioned else 150
        scenes.append({
            "scene_type": SceneType.RESULTS_SCENE.value,
            "timing": {"start": results_start, "end": results_end, "duration": 30},
            "title": "ROI & Results",
            "description": f"Case study and metrics for {industry.value} vertical",
            "talking_points": [
                f"Result: {metric}"
                for metric in roi_metrics
            ],
            "suggested_broll": [
                "Animated charts showing ROI metrics",
                "Case study customer logo",
                "Before/after workflow comparison",
                "Time/cost savings visualization",
            ],
        })

        # CTA_SCENE (150-180s)
        scenes.append({
            "scene_type": SceneType.CTA_SCENE.value,
            "timing": SCENE_TIMING[SceneType.CTA_SCENE],
            "title": "Next Steps",
            "description": "Clear call-to-action and calendar link",
            "talking_points": [
                "Schedule your personalized demo",
                "Get started with free trial",
                "Contact information and resources",
            ],
            "suggested_broll": [
                "Calendar booking interface",
                "Contact card with team info",
                "Resource links (docs, pricing, case studies)",
                "Thank you card with social proof badges",
            ],
        })

        return {
            "industry": industry.value,
            "prospect_segment": prospect_segment,
            "product_name": product_name,
            "key_features": key_features if key_features else relevant_features,
            "competitor_mentioned": competitor_mentioned,
            "total_duration": 180,
            "scenes": scenes,
            "metadata": {
                "pain_points_addressed": relevant_pain_points,
                "roi_metrics_highlighted": roi_metrics,
            },
        }

    async def _llm_customize_template(
        self,
        base_template: dict[str, Any],
        industry: Industry,
        preset: dict[str, Any],
        prospect_segment: str,
        product_name: str,
        key_features: list[str],
        competitor_mentioned: str | None,
    ) -> dict[str, Any]:
        """
        Use DeepSeek V3 to customize template with intelligent suggestions.

        Args:
            base_template: Base template structure
            industry: Industry enum
            preset: Industry preset
            prospect_segment: Target segment
            product_name: Product name
            key_features: Feature list
            competitor_mentioned: Optional competitor

        Returns:
            Customized template with enhanced talking points and suggestions
        """
        if not self._api_key:
            # Return base template if no API key (graceful degradation)
            return base_template

        # Build LLM prompt
        prompt = self._build_customization_prompt(
            base_template,
            industry,
            prospect_segment,
            product_name,
            key_features,
            competitor_mentioned,
        )

        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://conductor-ai.com",
            "X-Title": "Conductor AI - Video Template Manager",
        }

        payload = {
            "model": self.MODEL_ID,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert video demo script writer for construction/contracting software. "
                        "You create compelling, industry-specific talking points and b-roll suggestions "
                        "that resonate with target prospects. Focus on pain points, ROI, and clear CTAs."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT),
                ) as resp:
                    if resp.status >= 400:
                        # Fallback to base template on error
                        return base_template

                    data = await resp.json()
                    llm_response = data["choices"][0]["message"]["content"]

                    # Parse LLM response and enhance template
                    enhanced_template = self._merge_llm_suggestions(base_template, llm_response)
                    return enhanced_template

        except Exception:
            # Graceful degradation: return base template on any error
            return base_template

    def _build_customization_prompt(
        self,
        base_template: dict[str, Any],
        industry: Industry,
        prospect_segment: str,
        product_name: str,
        key_features: list[str],
        competitor_mentioned: str | None,
    ) -> str:
        """
        Build LLM prompt for template customization.

        Args:
            base_template: Base template
            industry: Industry
            prospect_segment: Segment
            product_name: Product
            key_features: Features
            competitor_mentioned: Competitor

        Returns:
            Prompt string
        """
        prompt = f"""
I need to create a compelling video demo script for {product_name}, targeting {prospect_segment} in the {industry.value} industry.

Base Template:
{json.dumps(base_template, indent=2)}

Please enhance this template by:

1. **Refining talking points**: Make them more specific, compelling, and prospect-focused. Use industry jargon where appropriate.

2. **Adding emotional hooks**: Include pain point storytelling that resonates with {prospect_segment}.

3. **Optimizing b-roll suggestions**: Suggest specific screen recordings, animations, or visual elements that would be most impactful.

4. **Strengthening the CTA**: Make the call-to-action more urgent and compelling.

{f"5. **Competitive positioning**: Provide specific talking points for why {product_name} is superior to {competitor_mentioned}." if competitor_mentioned else ""}

Return ONLY a JSON object with the enhanced template structure. Keep the same overall structure but enhance the content.
"""
        return prompt

    def _merge_llm_suggestions(self, base_template: dict[str, Any], llm_response: str) -> dict[str, Any]:
        """
        Merge LLM suggestions into base template.

        Args:
            base_template: Original template
            llm_response: LLM's enhanced suggestions

        Returns:
            Merged template
        """
        try:
            # Try to parse JSON from LLM response
            # Look for JSON object in response (handle markdown code blocks)
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                enhanced = json.loads(json_str)

                # Merge enhanced content while preserving structure
                if isinstance(enhanced, dict) and "scenes" in enhanced:
                    base_template["scenes"] = enhanced.get("scenes", base_template["scenes"])

                    # Update other fields if provided
                    for key in ["talking_points", "metadata", "key_features"]:
                        if key in enhanced:
                            base_template[key] = enhanced[key]

                return base_template
            else:
                # If no valid JSON, return base template
                return base_template

        except (json.JSONDecodeError, KeyError, ValueError):
            # Fallback to base template on parse error
            return base_template

    def _generate_template_id(self, industry: Industry, prospect_segment: str, product_name: str) -> str:
        """
        Generate unique template ID.

        Args:
            industry: Industry enum
            prospect_segment: Segment
            product_name: Product

        Returns:
            Template ID string
        """
        # Create slug-like ID
        segment_slug = prospect_segment.lower().replace(" ", "-")
        product_slug = product_name.lower().replace(" ", "-")
        timestamp = str(int(perf_counter() * 1000))[-6:]  # Last 6 digits of timestamp

        return f"{industry.value}_{segment_slug}_{product_slug}_{timestamp}"
