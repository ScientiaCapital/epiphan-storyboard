"""
Pydantic schemas for Storyboard Pipeline API.

Defines request/response models for async storyboard generation jobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Job type enum."""

    CODE_TO_STORYBOARD = "code_to_storyboard"
    ROADMAP_TO_STORYBOARD = "roadmap_to_storyboard"


class CodeStoryboardRequest(BaseModel):
    """Request model for POST /storyboard/code endpoint."""

    file_content: str = Field(
        ...,
        description="The source code content to analyze",
        min_length=1,
    )
    file_name: str | None = Field(
        None,
        description="Name of the file for context (e.g., 'main.py')",
    )
    icp_preset: str = Field(
        "coperniq_mep",
        description="ICP preset to use",
    )
    stage: Literal["preview", "demo", "shipped"] = Field(
        "preview",
        description="Storyboard stage for BDR cadence",
    )
    audience: Literal["business_owner", "c_suite", "btl_champion"] = Field(
        "c_suite",
        description="Target audience persona",
    )
    custom_headline: str | None = Field(
        None,
        description="Optional custom headline override",
    )

    @field_validator("file_content")
    @classmethod
    def validate_file_content_not_empty(cls, v: str) -> str:
        """Ensure file_content is not empty."""
        if not v or not v.strip():
            raise ValueError("file_content must not be empty")
        return v


class RoadmapStoryboardRequest(BaseModel):
    """Request model for POST /storyboard/roadmap endpoint."""

    image_data: str = Field(
        ...,
        description="Base64-encoded image data or data URL",
        min_length=1,
    )
    icp_preset: str = Field(
        "coperniq_mep",
        description="ICP preset to use",
    )
    audience: Literal["business_owner", "c_suite", "btl_champion"] = Field(
        "c_suite",
        description="Target audience persona",
    )
    custom_headline: str | None = Field(
        None,
        description="Optional custom headline override",
    )
    sanitize_ip: bool = Field(
        True,
        description="Apply extra IP sanitization",
    )

    @field_validator("image_data")
    @classmethod
    def validate_image_data_not_empty(cls, v: str) -> str:
        """Ensure image_data is not empty."""
        if not v or not v.strip():
            raise ValueError("image_data must not be empty")
        return v


class StoryboardJobResponse(BaseModel):
    """Response model for POST /storyboard/{code|roadmap} (202 Accepted)."""

    job_id: str = Field(
        ...,
        description="Unique job identifier for polling",
    )
    status: JobStatus = Field(
        ...,
        description="Current job status",
    )
    poll_url: str = Field(
        ...,
        description="URL to poll for job status and results",
    )


class StoryboardJobStatusResponse(BaseModel):
    """Response model for GET /storyboard/jobs/{job_id}."""

    job_id: str = Field(
        ...,
        description="Unique job identifier",
    )
    status: JobStatus = Field(
        ...,
        description="Current job status",
    )
    result_image: str | None = Field(
        None,
        description="Base64-encoded PNG storyboard image (available when status=completed)",
    )
    understanding: dict | None = Field(
        None,
        description="Extracted business insights (available when status=completed)",
    )
    error_message: str | None = Field(
        None,
        description="Error details (available when status=failed)",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Total execution time in milliseconds (available when completed/failed)",
    )
    created_at: datetime = Field(
        ...,
        description="Job creation timestamp",
    )
    completed_at: datetime | None = Field(
        None,
        description="Job completion timestamp (available when completed/failed)",
    )


class StoryboardJob(BaseModel):
    """Internal model for storyboard job state."""

    job_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique job identifier",
    )
    org_id: str = Field(
        ...,
        description="Organization identifier",
    )
    job_type: JobType = Field(
        ...,
        description="Type of storyboard job",
    )
    status: JobStatus = Field(
        JobStatus.PENDING,
        description="Current job status",
    )
    input_params: dict = Field(
        ...,
        description="Input parameters for the job",
    )
    result_image: str | None = Field(
        None,
        description="Base64-encoded PNG storyboard image",
    )
    understanding: dict | None = Field(
        None,
        description="Extracted business insights",
    )
    error_message: str | None = Field(
        None,
        description="Error details if job failed",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Job creation timestamp",
    )
    completed_at: datetime | None = Field(
        None,
        description="Job completion timestamp",
    )
    execution_time_ms: int | None = Field(
        None,
        description="Total execution time in milliseconds",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata",
    )
