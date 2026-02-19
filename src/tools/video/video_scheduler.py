"""Video Scheduler Tool for predicting optimal video send times based on prospect data."""

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from src.providers import ProviderError, get_provider_manager
from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


class VideoSchedulerTool(BaseTool):
    """
    Tool for predicting optimal video send times based on prospect data.

    Uses rule-based logic for industry-specific timing patterns and role-level
    adjustments, with optional LLM enhancement for personalized reasoning.

    Key Features:
    - Industry-specific timing patterns (Construction/MEP, Tech/SaaS, Finance)
    - Role-level adjustments (C-level, VP, Director, Manager, IC)
    - Day of week ranking (Tuesday/Wednesday highest engagement)
    - Timezone handling for accurate delivery
    - Confidence scoring for each recommendation
    """

    # Industry-specific optimal time windows (24-hour format)
    INDUSTRY_PATTERNS = {
        "construction": [
            {"start": time(6, 0), "end": time(7, 30), "confidence": 0.85, "reason": "Before job site departure"},
        ],
        "mep": [
            {"start": time(6, 0), "end": time(7, 30), "confidence": 0.85, "reason": "Before job site departure"},
        ],
        "tech": [
            {"start": time(9, 0), "end": time(10, 30), "confidence": 0.80, "reason": "Mid-morning focus time"},
            {"start": time(15, 0), "end": time(16, 30), "confidence": 0.75, "reason": "Late afternoon break"},
        ],
        "saas": [
            {"start": time(9, 0), "end": time(10, 30), "confidence": 0.80, "reason": "Mid-morning focus time"},
            {"start": time(15, 0), "end": time(16, 30), "confidence": 0.75, "reason": "Late afternoon break"},
        ],
        "finance": [
            {"start": time(7, 0), "end": time(8, 30), "confidence": 0.82, "reason": "Pre-market preparation"},
            {"start": time(17, 0), "end": time(18, 30), "confidence": 0.78, "reason": "Post-market review"},
        ],
        "default": [
            {"start": time(9, 0), "end": time(10, 30), "confidence": 0.70, "reason": "Standard business hours"},
            {"start": time(14, 0), "end": time(15, 30), "confidence": 0.65, "reason": "Afternoon focus time"},
        ],
    }

    # Role-level adjustments (modifies base confidence)
    ROLE_ADJUSTMENTS = {
        "c-level": {
            "early_morning_boost": 0.10,  # +10% for early morning
            "evening_boost": 0.10,  # +10% for evening
            "midday_penalty": -0.15,  # -15% for mid-day (meeting-heavy)
        },
        "vp": {
            "morning_boost": 0.05,
            "afternoon_boost": 0.05,
            "early_penalty": -0.10,
        },
        "director": {
            "morning_boost": 0.05,
            "afternoon_boost": 0.05,
            "early_penalty": -0.10,
        },
        "manager": {
            "business_hours_boost": 0.05,
        },
        "ic": {
            "business_hours_boost": 0.05,
        },
    }

    # Day of week engagement scores (0=Monday, 6=Sunday)
    DAY_SCORES: dict[int, dict[str, float | str]] = {
        0: {"score": 0.70, "name": "Monday", "note": "Inbox overload"},
        1: {"score": 0.90, "name": "Tuesday", "note": "Highest engagement"},
        2: {"score": 0.90, "name": "Wednesday", "note": "Highest engagement"},
        3: {"score": 0.75, "name": "Thursday", "note": "Good engagement"},
        4: {"score": 0.55, "name": "Friday", "note": "Weekend mindset"},
        5: {"score": 0.30, "name": "Saturday", "note": "Weekend - avoid"},
        6: {"score": 0.30, "name": "Sunday", "note": "Weekend - avoid"},
    }

    # Default timezone if not specified
    DEFAULT_TIMEZONE = "America/New_York"

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for video_scheduler."""
        return ToolDefinition(
            name="video_scheduler",
            description="Predict optimal video send times based on prospect data (industry, role, timezone)",
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "prospect_email": {
                        "type": "string",
                        "description": "Prospect's email address (for reference)",
                    },
                    "prospect_timezone": {
                        "type": "string",
                        "description": "Prospect's timezone (e.g., 'America/New_York', 'Europe/London'). Optional.",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry sector (construction, mep, tech, saas, finance, etc.)",
                    },
                    "company_size": {
                        "type": "string",
                        "description": "Company size (1-10, 11-50, 51-200, 201-1000, 1000+)",
                    },
                    "role_level": {
                        "type": "string",
                        "description": "Role level (c-level, vp, director, manager, ic)",
                        "enum": ["c-level", "vp", "director", "manager", "ic"],
                    },
                    "use_llm": {
                        "type": "boolean",
                        "description": "Use LLM to enhance reasoning (default: false for cost optimization)",
                        "default": False,
                    },
                },
                "required": ["prospect_email", "industry", "role_level"],
            },
        )

    def _get_industry_windows(self, industry: str) -> list[dict[str, Any]]:
        """
        Get base time windows for a given industry.

        Args:
            industry: Industry sector

        Returns:
            List of time windows with confidence scores
        """
        industry_key = industry.lower()
        return self.INDUSTRY_PATTERNS.get(industry_key, self.INDUSTRY_PATTERNS["default"])

    def _apply_role_adjustment(
        self,
        window: dict[str, Any],
        role_level: str
    ) -> float:
        """
        Apply role-level adjustments to confidence score.

        Args:
            window: Time window dict with start/end times
            role_level: Role level (c-level, vp, director, manager, ic)

        Returns:
            Adjusted confidence score (0-1)
        """
        base_confidence = window["confidence"]
        role_key = role_level.lower()
        adjustments: dict[str, float] = self.ROLE_ADJUSTMENTS.get(role_key, {})

        hour = window["start"].hour

        # Apply role-specific boosts/penalties
        adjusted_confidence = base_confidence

        if role_key == "c-level":
            if hour < 8:  # Early morning
                adjusted_confidence += adjustments.get("early_morning_boost", 0)
            elif hour >= 17:  # Evening
                adjusted_confidence += adjustments.get("evening_boost", 0)
            elif 11 <= hour <= 14:  # Midday (meeting-heavy)
                adjusted_confidence += adjustments.get("midday_penalty", 0)

        elif role_key in ["vp", "director"]:
            if 9 <= hour <= 11:  # Morning
                adjusted_confidence += adjustments.get("morning_boost", 0)
            elif 14 <= hour <= 16:  # Afternoon
                adjusted_confidence += adjustments.get("afternoon_boost", 0)
            elif hour < 8:  # Too early
                adjusted_confidence += adjustments.get("early_penalty", 0)

        elif role_key in ["manager", "ic"]:
            if 9 <= hour <= 17:  # Standard business hours
                adjusted_confidence += adjustments.get("business_hours_boost", 0)

        # Clamp to valid range [0, 1]
        return float(max(0.0, min(1.0, adjusted_confidence)))

    def _get_top_days(self) -> list[int]:
        """
        Get top engagement days (excluding weekends).

        Returns:
            List of day indices sorted by engagement score (descending)
        """
        # Filter out weekends and sort by score
        weekdays: list[tuple[int, float]] = [
            (day, float(info["score"])) for day, info in self.DAY_SCORES.items() if day < 5
        ]
        weekdays.sort(key=lambda x: x[1], reverse=True)
        return [day for day, _ in weekdays[:3]]  # Top 3 days

    def _format_time_range(self, start: time, end: time, timezone_str: str) -> str:
        """
        Format time range with timezone.

        Args:
            start: Start time
            end: End time
            timezone_str: Timezone string

        Returns:
            Formatted time range string
        """
        tz_abbr = ZoneInfo(timezone_str).tzname(datetime.now())
        return f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')} {tz_abbr}"

    def _calculate_recommendations(
        self,
        industry: str,
        role_level: str,
        timezone_str: str
    ) -> dict[str, Any]:
        """
        Calculate optimal send time recommendations using rule-based logic.

        Args:
            industry: Industry sector
            role_level: Role level
            timezone_str: Timezone string

        Returns:
            Dict with top_3_windows, reasoning, and avoid_times
        """
        # Get industry-specific windows
        base_windows = self._get_industry_windows(industry)

        # Apply role adjustments
        adjusted_windows = []
        for window in base_windows:
            adjusted_conf = self._apply_role_adjustment(window, role_level)
            adjusted_windows.append({
                "start": window["start"],
                "end": window["end"],
                "confidence": adjusted_conf,
                "reason": window["reason"],
            })

        # Sort by adjusted confidence
        adjusted_windows.sort(key=lambda x: x["confidence"], reverse=True)

        # Get top 3 days
        top_days = self._get_top_days()

        # Build top 3 recommendations (combine top window with top days)
        top_3_windows = []
        for i, day_idx in enumerate(top_days):
            day_info = self.DAY_SCORES[day_idx]
            window = adjusted_windows[0] if i == 0 else adjusted_windows[min(i, len(adjusted_windows) - 1)]

            # Apply day score to confidence
            final_confidence = window["confidence"] * day_info["score"]

            top_3_windows.append({
                "day": day_info["name"],
                "time_range": self._format_time_range(window["start"], window["end"], timezone_str),
                "timezone": timezone_str,
                "confidence_score": round(final_confidence, 2),
                "reason": window["reason"],
            })

        # Generate reasoning
        reasoning_parts = [
            f"Industry: {industry.title()} - {base_windows[0]['reason'].lower()}",
            f"Role: {role_level.upper()} - Adjusted for typical {role_level} schedules",
            f"Best days: {', '.join(str(self.DAY_SCORES[d]['name']) for d in top_days)} (highest engagement)",
        ]
        reasoning = ". ".join(reasoning_parts) + "."

        # Avoid times
        avoid_times = [
            f"{self.DAY_SCORES[5]['name']}/{self.DAY_SCORES[6]['name']} - {self.DAY_SCORES[5]['note']}",
            "Early mornings (before 6 AM) - Too early for most professionals",
            "Late evenings (after 7 PM) - Work-life boundary",
        ]

        return {
            "top_3_windows": top_3_windows,
            "reasoning": reasoning,
            "avoid_times": avoid_times,
        }

    async def _enhance_with_llm(
        self,
        base_recommendations: dict[str, Any],
        prospect_email: str,
        industry: str,
        company_size: str,
        role_level: str
    ) -> str:
        """
        Optionally enhance reasoning with LLM-generated insights.

        Args:
            base_recommendations: Rule-based recommendations
            prospect_email: Prospect's email
            industry: Industry sector
            company_size: Company size
            role_level: Role level

        Returns:
            Enhanced reasoning text
        """
        try:
            provider_manager = get_provider_manager()

            # Use lightweight model for cost optimization
            model = "qwen/qwen3-8b"

            # Build prompt for LLM
            prompt = f"""You are an expert in sales outreach timing optimization. Given the following prospect data and rule-based recommendations, provide a brief (2-3 sentences) personalized insight about why these times are optimal.

Prospect Data:
- Email: {prospect_email}
- Industry: {industry}
- Company Size: {company_size}
- Role Level: {role_level}

Rule-Based Recommendations:
{base_recommendations['reasoning']}

Top Windows:
{chr(10).join(f"- {w['day']} {w['time_range']} (confidence: {w['confidence_score']})" for w in base_recommendations['top_3_windows'])}

Provide personalized insight in 2-3 sentences focusing on WHY these times work for this specific prospect profile."""

            messages = [{"role": "user", "content": prompt}]

            response = await provider_manager.complete(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=200,
            )

            return f"{base_recommendations['reasoning']} {response.content.strip()}"

        except (ProviderError, Exception):
            # Fallback to base reasoning if LLM fails
            return str(base_recommendations["reasoning"])

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the video scheduler tool.

        Args:
            arguments: Tool arguments containing prospect_email, prospect_timezone,
                      industry, company_size, role_level, use_llm

        Returns:
            ToolResult with optimal send time recommendations
        """
        # Extract arguments with defaults
        prospect_email: str = arguments.get("prospect_email", "unknown@example.com")
        prospect_timezone: str = arguments.get("prospect_timezone", self.DEFAULT_TIMEZONE)
        industry: str = arguments.get("industry", "general")
        company_size: str = arguments.get("company_size", "Unknown")
        role_level: str = arguments.get("role_level", "manager")
        use_llm: bool = arguments.get("use_llm", False)

        # Validate timezone
        try:
            ZoneInfo(prospect_timezone)
        except Exception:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Invalid timezone: {prospect_timezone}",
                execution_time_ms=0,
            )

        # Calculate rule-based recommendations
        try:
            recommendations = self._calculate_recommendations(
                industry=industry,
                role_level=role_level,
                timezone_str=prospect_timezone
            )

            # Optionally enhance with LLM
            if use_llm:
                enhanced_reasoning = await self._enhance_with_llm(
                    base_recommendations=recommendations,
                    prospect_email=prospect_email,
                    industry=industry,
                    company_size=company_size,
                    role_level=role_level
                )
                recommendations["reasoning"] = enhanced_reasoning

            # Build result
            result_data = {
                "prospect_email": prospect_email,
                "timezone": prospect_timezone,
                "industry": industry,
                "role_level": role_level,
                "top_3_windows": recommendations["top_3_windows"],
                "reasoning": recommendations["reasoning"],
                "avoid_times": recommendations["avoid_times"],
                "llm_enhanced": use_llm,
            }

            return ToolResult(
                tool_name=self.definition.name,
                success=True,
                result=result_data,
                error=None,
                execution_time_ms=0,  # Will be set by _execute_with_timing
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Failed to calculate recommendations: {str(e)}",
                execution_time_ms=0,
            )
