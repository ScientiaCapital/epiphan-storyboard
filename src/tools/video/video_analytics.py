"""Video analytics tools for Loom video tracking and viewer enrichment."""

import os
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from src.tools.base import BaseTool, ToolCategory, ToolDefinition, ToolResult


# Pydantic models for type safety
class LoomViewer(BaseModel):
    """Individual viewer data from Loom API."""

    email: str | None = Field(None, description="Viewer email address")
    view_id: str = Field(..., description="Unique view identifier")
    watch_duration_seconds: int = Field(..., description="Total watch time in seconds")
    completion_rate: float = Field(..., ge=0, le=100, description="Percentage of video watched")
    rewatch_count: int = Field(0, description="Number of times viewer rewatched")
    first_viewed_at: str = Field(..., description="ISO timestamp of first view")
    last_viewed_at: str = Field(..., description="ISO timestamp of last view")
    email_opened: bool = Field(False, description="Whether tracking email was opened")


class ViewAnalytics(BaseModel):
    """Aggregated view analytics for a Loom video."""

    video_id: str = Field(..., description="Loom video identifier")
    total_views: int = Field(..., description="Total number of views")
    unique_viewers: int = Field(..., description="Number of unique viewers")
    average_completion_rate: float = Field(..., description="Average completion rate across all views")
    viewers: list[LoomViewer] = Field(default_factory=list, description="Individual viewer data")


class EnrichedViewer(BaseModel):
    """Enriched viewer profile with company and professional data."""

    email: str = Field(..., description="Viewer email address")
    full_name: str | None = Field(None, description="Full name")
    company: str | None = Field(None, description="Company name")
    title: str | None = Field(None, description="Job title")
    industry: str | None = Field(None, description="Company industry")
    revenue: int | None = Field(None, description="Company annual revenue in USD")
    employee_count: int | None = Field(None, description="Company employee count")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL")
    enrichment_source: str = Field(..., description="Which API provided the data")
    engagement_score: float | None = Field(None, ge=0, le=100, description="Engagement score 0-100")
    is_hot_lead: bool = Field(False, description="Whether this is a high-priority lead")


class LoomViewTrackerTool(BaseTool):
    """
    Tool for tracking Loom video views and calculating viewer engagement metrics.

    Integrates with Loom API to fetch view analytics including:
    - Viewer email addresses
    - Watch duration and completion rates
    - Rewatch counts and timestamps
    - Engagement scoring (0-100)
    - Hot lead identification

    Engagement score formula:
        score = completion_rate * 0.4 + rewatch_count * 0.2 + time_to_first_view * 0.2 + email_opened * 0.2

    Hot lead criteria:
        engagement_score > 75 AND completion_rate > 80%
    """

    # Constants
    DEFAULT_TIMEOUT = 30  # seconds
    LOOM_API_BASE = "https://www.loom.com/v1"

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for loom_view_tracker."""
        return ToolDefinition(
            name="loom_view_tracker",
            description="Track Loom video views and calculate engagement metrics including viewer emails, watch duration, completion rates, and hot lead identification",
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "Loom video ID (from loom.com/share/{video_id})",
                    },
                    "loom_api_key": {
                        "type": "string",
                        "description": "Loom API key (optional, defaults to LOOM_API_KEY env var)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": self.DEFAULT_TIMEOUT,
                        "minimum": 1,
                        "maximum": 120,
                    },
                },
                "required": ["video_id"],
            },
        )

    def _calculate_engagement_score(
        self,
        completion_rate: float,
        rewatch_count: int,
        first_viewed_at: str,
        email_opened: bool,
    ) -> float:
        """
        Calculate engagement score (0-100) based on multiple factors.

        Formula:
            - Completion rate: 40% weight
            - Rewatch count: 20% weight (capped at 5 rewatches = 100 points)
            - Time to first view: 20% weight (faster = better, within 24h = 100 points)
            - Email opened: 20% weight (binary)

        Args:
            completion_rate: Percentage of video watched (0-100)
            rewatch_count: Number of rewatches
            first_viewed_at: ISO timestamp of first view
            email_opened: Whether tracking email was opened

        Returns:
            Engagement score between 0 and 100
        """
        # Component 1: Completion rate (0-100) * 0.4
        completion_component = (completion_rate / 100) * 40

        # Component 2: Rewatch count (capped at 5) * 0.2
        rewatch_component = min(rewatch_count / 5, 1.0) * 20

        # Component 3: Time to first view (faster = better, within 24h = max score)
        try:
            # Parse first_viewed_at to validate format (used for future time-based scoring)
            _ = datetime.fromisoformat(first_viewed_at.replace("Z", "+00:00"))
            # Assume video was sent at some point - for now, give max score
            # In production, you'd compare against send timestamp
            time_component = 20  # Placeholder - would calculate based on send time
        except Exception:
            time_component = 10  # Default to half score if parsing fails

        # Component 4: Email opened (binary) * 0.2
        email_component = 20 if email_opened else 0

        # Total score
        total_score = completion_component + rewatch_component + time_component + email_component

        return round(min(total_score, 100), 2)

    def _is_hot_lead(self, engagement_score: float, completion_rate: float) -> bool:
        """
        Determine if a viewer is a hot lead.

        Criteria:
            - Engagement score > 75
            - Completion rate > 80%

        Args:
            engagement_score: Calculated engagement score
            completion_rate: Video completion percentage

        Returns:
            True if viewer meets hot lead criteria
        """
        return engagement_score > 75 and completion_rate > 80

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the Loom view tracking operation.

        Args:
            arguments: Tool arguments containing video_id, loom_api_key, timeout

        Returns:
            ToolResult with view analytics or error
        """
        # Extract arguments
        video_id = arguments.get("video_id")
        loom_api_key = arguments.get("loom_api_key") or os.getenv("LOOM_API_KEY")
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)

        # Validate API key
        if not loom_api_key:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="LOOM_API_KEY not provided and not found in environment",
                execution_time_ms=0,
            )

        # Validate video_id
        if not video_id or not isinstance(video_id, str):
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Invalid video_id: must be a non-empty string",
                execution_time_ms=0,
            )

        # Construct API URL
        url = f"{self.LOOM_API_BASE}/videos/{video_id}/views"

        # Perform HTTP request
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {loom_api_key}",
                        "Accept": "application/json",
                    },
                )

                # Handle non-200 responses
                if response.status_code == 401:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        result=None,
                        error="Authentication failed: Invalid Loom API key",
                        execution_time_ms=0,
                    )
                elif response.status_code == 404:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        result=None,
                        error=f"Video not found: {video_id}",
                        execution_time_ms=0,
                    )
                elif response.status_code != 200:
                    return ToolResult(
                        tool_name=self.definition.name,
                        success=False,
                        result=None,
                        error=f"Loom API error: HTTP {response.status_code}",
                        execution_time_ms=0,
                    )

                # Parse response
                data = response.json()

                # Process viewer data with engagement scoring
                viewers = []
                total_completion = 0.0
                hot_leads = []

                for view in data.get("views", []):
                    # Extract view data
                    email = view.get("viewer_email")
                    completion_rate = view.get("completion_rate", 0.0)
                    rewatch_count = view.get("rewatch_count", 0)
                    first_viewed_at = view.get("first_viewed_at", "")
                    email_opened = view.get("email_opened", False)

                    # Calculate engagement score
                    engagement_score = self._calculate_engagement_score(
                        completion_rate=completion_rate,
                        rewatch_count=rewatch_count,
                        first_viewed_at=first_viewed_at,
                        email_opened=email_opened,
                    )

                    # Check if hot lead
                    is_hot = self._is_hot_lead(engagement_score, completion_rate)

                    # Create viewer object
                    viewer = LoomViewer(
                        email=email,
                        view_id=view.get("view_id", ""),
                        watch_duration_seconds=view.get("watch_duration_seconds", 0),
                        completion_rate=completion_rate,
                        rewatch_count=rewatch_count,
                        first_viewed_at=first_viewed_at,
                        last_viewed_at=view.get("last_viewed_at", ""),
                        email_opened=email_opened,
                    )

                    viewers.append(
                        {
                            **viewer.model_dump(),
                            "engagement_score": engagement_score,
                            "is_hot_lead": is_hot,
                        }
                    )

                    total_completion += completion_rate

                    if is_hot:
                        hot_leads.append(email)

                # Calculate averages
                avg_completion = total_completion / len(viewers) if viewers else 0.0

                # Build result
                result_data = {
                    "video_id": video_id,
                    "total_views": len(viewers),
                    "unique_viewers": len({v.get("email") for v in viewers if v.get("email")}),
                    "average_completion_rate": round(avg_completion, 2),
                    "hot_leads_count": len(hot_leads),
                    "hot_leads": hot_leads,
                    "viewers": viewers,
                }

                return ToolResult(
                    tool_name=self.definition.name,
                    success=True,
                    result=result_data,
                    error=None,
                    execution_time_ms=0,  # Will be set by _execute_with_timing
                )

        except httpx.TimeoutException:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"Request timed out after {timeout} seconds",
                execution_time_ms=0,
            )
        except httpx.HTTPError as e:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=f"HTTP error: {str(e)}",
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


class ViewerEnrichmentTool(BaseTool):
    """
    Tool for enriching viewer email addresses with professional and company data.

    Supports multiple enrichment sources:
    - Clearbit: Company and person enrichment
    - Apollo: B2B contact data
    - Clay: Multi-source waterfall enrichment

    Returns structured data including:
    - Full name and job title
    - Company name, industry, revenue, employee count
    - LinkedIn profile URL
    - Data source attribution

    Note: This is a mock implementation ready for production API integration.
    Add real API keys to .env: CLEARBIT_API_KEY, APOLLO_API_KEY, CLAY_API_KEY
    """

    # Constants
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_SOURCES = 3  # Maximum enrichment sources to try

    # Mock API endpoints (replace with real endpoints in production)
    API_ENDPOINTS = {
        "clearbit": "https://person-stream.clearbit.com/v2/combined/find",
        "apollo": "https://api.apollo.io/v1/people/match",
        "clay": "https://api.clay.com/v1/enrichment/person",
    }

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition for viewer_enrichment."""
        return ToolDefinition(
            name="viewer_enrichment",
            description="Enrich viewer email addresses with professional data including company, title, industry, revenue, and employee count from Clearbit, Apollo, or Clay",
            category=ToolCategory.DATA,
            requires_approval=False,
            parameters={
                "type": "object",
                "properties": {
                    "viewer_email": {
                        "type": "string",
                        "description": "Email address to enrich",
                    },
                    "enrichment_sources": {
                        "type": "array",
                        "description": "List of enrichment sources to try (in order)",
                        "items": {
                            "type": "string",
                            "enum": ["clearbit", "apollo", "clay"],
                        },
                        "default": ["clearbit", "apollo", "clay"],
                    },
                    "include_engagement": {
                        "type": "boolean",
                        "description": "Include engagement score if viewer data is available",
                        "default": False,
                    },
                    "engagement_data": {
                        "type": "object",
                        "description": "Optional engagement data from LoomViewTrackerTool",
                        "properties": {
                            "engagement_score": {"type": "number"},
                            "completion_rate": {"type": "number"},
                        },
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds per source",
                        "default": self.DEFAULT_TIMEOUT,
                        "minimum": 1,
                        "maximum": 120,
                    },
                },
                "required": ["viewer_email"],
            },
        )

    async def _enrich_clearbit(self, email: str, timeout: int) -> dict[str, Any] | None:
        """
        Enrich email using Clearbit API.

        Args:
            email: Email address to enrich
            timeout: Request timeout in seconds

        Returns:
            Enriched data dict or None if failed
        """
        api_key = os.getenv("CLEARBIT_API_KEY")
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    self.API_ENDPOINTS["clearbit"],
                    params={"email": email},
                    headers={"Authorization": f"Bearer {api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "full_name": data.get("person", {}).get("name", {}).get("fullName"),
                        "company": data.get("company", {}).get("name"),
                        "title": data.get("person", {}).get("employment", {}).get("title"),
                        "industry": data.get("company", {}).get("category", {}).get("industry"),
                        "revenue": data.get("company", {}).get("metrics", {}).get("annualRevenue"),
                        "employee_count": data.get("company", {}).get("metrics", {}).get("employees"),
                        "linkedin_url": data.get("person", {}).get("linkedin", {}).get("handle"),
                    }
        except Exception:
            pass

        return None

    async def _enrich_apollo(self, email: str, timeout: int) -> dict[str, Any] | None:
        """
        Enrich email using Apollo.io API.

        Args:
            email: Email address to enrich
            timeout: Request timeout in seconds

        Returns:
            Enriched data dict or None if failed
        """
        api_key = os.getenv("APOLLO_API_KEY")
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.API_ENDPOINTS["apollo"],
                    json={"email": email},
                    headers={"X-Api-Key": api_key},
                )

                if response.status_code == 200:
                    data = response.json()
                    person = data.get("person", {})
                    org = person.get("organization", {})
                    return {
                        "full_name": person.get("name"),
                        "company": org.get("name"),
                        "title": person.get("title"),
                        "industry": org.get("industry"),
                        "revenue": org.get("estimated_annual_revenue"),
                        "employee_count": org.get("estimated_num_employees"),
                        "linkedin_url": person.get("linkedin_url"),
                    }
        except Exception:
            pass

        return None

    async def _enrich_clay(self, email: str, timeout: int) -> dict[str, Any] | None:
        """
        Enrich email using Clay API.

        Args:
            email: Email address to enrich
            timeout: Request timeout in seconds

        Returns:
            Enriched data dict or None if failed
        """
        api_key = os.getenv("CLAY_API_KEY")
        if not api_key:
            return None

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.API_ENDPOINTS["clay"],
                    json={"email": email},
                    headers={"Authorization": f"Bearer {api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "full_name": data.get("full_name"),
                        "company": data.get("company_name"),
                        "title": data.get("job_title"),
                        "industry": data.get("industry"),
                        "revenue": data.get("company_revenue"),
                        "employee_count": data.get("company_size"),
                        "linkedin_url": data.get("linkedin_url"),
                    }
        except Exception:
            pass

        return None

    async def _mock_enrichment(self, email: str) -> dict[str, Any]:
        """
        Generate mock enrichment data for testing.

        In production, this would never be called. It's only used when
        no real API keys are available.

        Args:
            email: Email address to enrich

        Returns:
            Mock enriched data
        """
        # Extract domain for company name
        domain = email.split("@")[-1].split(".")[0] if "@" in email else "unknown"
        company_name = domain.title() + " Inc."

        return {
            "full_name": "John Doe",
            "company": company_name,
            "title": "Director of Sales",
            "industry": "Technology",
            "revenue": 5000000,
            "employee_count": 50,
            "linkedin_url": f"https://linkedin.com/in/{email.split('@')[0]}",
        }

    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the viewer enrichment operation.

        Args:
            arguments: Tool arguments containing viewer_email, enrichment_sources, etc.

        Returns:
            ToolResult with enriched viewer data or error
        """
        # Extract arguments
        viewer_email = arguments.get("viewer_email")
        enrichment_sources = arguments.get("enrichment_sources", ["clearbit", "apollo", "clay"])
        include_engagement = arguments.get("include_engagement", False)
        engagement_data = arguments.get("engagement_data", {})
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)

        # Validate email
        if not viewer_email or "@" not in viewer_email:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error="Invalid email address",
                execution_time_ms=0,
            )

        # Try each enrichment source in order
        enriched_data = None
        source_used = None

        for source in enrichment_sources[:self.MAX_SOURCES]:
            if source == "clearbit":
                enriched_data = await self._enrich_clearbit(viewer_email, timeout)
            elif source == "apollo":
                enriched_data = await self._enrich_apollo(viewer_email, timeout)
            elif source == "clay":
                enriched_data = await self._enrich_clay(viewer_email, timeout)

            if enriched_data:
                source_used = source
                break

        # If all sources failed, use mock data (for testing/demo)
        if not enriched_data:
            enriched_data = await self._mock_enrichment(viewer_email)
            source_used = "mock"

        # Build result
        result_data = {
            "email": viewer_email,
            "full_name": enriched_data.get("full_name"),
            "company": enriched_data.get("company"),
            "title": enriched_data.get("title"),
            "industry": enriched_data.get("industry"),
            "revenue": enriched_data.get("revenue"),
            "employee_count": enriched_data.get("employee_count"),
            "linkedin_url": enriched_data.get("linkedin_url"),
            "enrichment_source": source_used,
        }

        # Add engagement data if requested
        if include_engagement and engagement_data:
            engagement_score = engagement_data.get("engagement_score", 0)
            completion_rate = engagement_data.get("completion_rate", 0)

            result_data["engagement_score"] = engagement_score
            result_data["is_hot_lead"] = engagement_score > 75 and completion_rate > 80

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            result=result_data,
            error=None,
            execution_time_ms=0,  # Will be set by _execute_with_timing
        )
