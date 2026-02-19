"""Pydantic schemas for Agent Router module.

Defines request/response models for task classification and routing.
Follows epiphan-storyboard patterns from agents/schemas.py and storyboard/schemas.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Task classification types for routing to specialized chains."""

    STORYBOARD = "storyboard"  # Generate storyboards/infographics from code/images
    VIDEO = "video"  # Video generation/editing/recording
    SCRAPE = "scrape"  # Web scraping and data extraction
    CODE_RUN = "code_run"  # Execute code in sandbox
    KNOWLEDGE = "knowledge"  # Knowledge base / CRM queries
    SQL = "sql"  # Database queries


class RouterJobStatus(str, Enum):
    """Status of a router job."""

    PENDING = "pending"
    CLASSIFYING = "classifying"
    ROUTING = "routing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClassificationResult(BaseModel):
    """Result from task classification."""

    task_type: TaskType = Field(..., description="Classified task type")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Classification confidence (0.0-1.0)"
    )
    reasoning: str = Field(..., description="Explanation of classification decision")
    extracted_params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters extracted from query"
    )
    recommended_model: str | None = Field(
        default=None, description="Recommended LLM model for this task type"
    )

    model_config = {"extra": "forbid"}


class ClassificationRequest(BaseModel):
    """Request for task classification."""

    query: str = Field(..., min_length=1, description="User query to classify")
    context: str | None = Field(
        default=None, description="Additional context to improve classification"
    )

    model_config = {"extra": "forbid"}


class RouterRequest(BaseModel):
    """Request to route and execute a task."""

    query: str = Field(..., min_length=1, description="User query/task description")
    context: dict[str, Any] | None = Field(
        default=None, description="Additional context/metadata"
    )
    force_chain: TaskType | None = Field(
        default=None, description="Force specific chain (bypass classification)"
    )
    max_steps: int = Field(
        default=10, ge=1, le=100, description="Maximum execution steps"
    )

    model_config = {"extra": "forbid"}


class RouterJob(BaseModel):
    """Internal model for router job state (Redis + Supabase)."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str = Field(..., description="Organization ID")
    status: RouterJobStatus = Field(default=RouterJobStatus.PENDING)
    query: str = Field(..., description="Original query")
    context: dict[str, Any] = Field(default_factory=dict)
    max_steps: int = Field(default=10)
    classification: ClassificationResult | None = Field(
        default=None, description="Classification result (populated after classifying)"
    )
    chain_result: dict[str, Any] | None = Field(
        default=None, description="Chain execution result (populated after executing)"
    )
    error_message: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int | None = Field(
        default=None, description="Total execution time in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    completed_at: datetime | None = Field(default=None)

    model_config = {"extra": "forbid"}


class RouterJobResponse(BaseModel):
    """Response from POST /agents/route (202 Accepted)."""

    job_id: str = Field(..., description="Job ID for polling")
    status: RouterJobStatus = Field(..., description="Current job status")
    poll_url: str = Field(..., description="URL to poll for status")
    classification: ClassificationResult | None = Field(
        default=None, description="Classification result (if available)"
    )

    model_config = {"extra": "forbid"}


class RouterJobStatusResponse(BaseModel):
    """Response from GET /agents/route/{job_id}."""

    job_id: str
    status: RouterJobStatus
    task_type: TaskType | None = Field(
        default=None, description="Classified task type"
    )
    classification: ClassificationResult | None = Field(
        default=None, description="Full classification result"
    )
    chain_result: dict[str, Any] | None = Field(
        default=None, description="Execution result (when completed)"
    )
    error_message: str | None = Field(
        default=None, description="Error message (when failed)"
    )
    execution_time_ms: int | None = Field(default=None)
    created_at: datetime
    completed_at: datetime | None = Field(default=None)

    model_config = {"extra": "forbid"}
