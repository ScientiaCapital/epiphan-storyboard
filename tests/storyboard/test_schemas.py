"""
Unit tests for Storyboard Pipeline schemas.

Tests Pydantic models for request/response validation.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.storyboard.schemas import (
    CodeStoryboardRequest,
    JobStatus,
    JobType,
    RoadmapStoryboardRequest,
    StoryboardJob,
    StoryboardJobResponse,
    StoryboardJobStatusResponse,
)


class TestCodeStoryboardRequest:
    """Tests for CodeStoryboardRequest schema."""

    def test_valid_request_minimal(self):
        """Test minimal valid request."""
        request = CodeStoryboardRequest(
            file_content="def hello(): pass",
        )
        assert request.file_content == "def hello(): pass"
        assert request.file_name is None
        assert request.icp_preset == "coperniq_mep"
        assert request.stage == "preview"
        assert request.audience == "c_suite"
        assert request.custom_headline is None

    def test_valid_request_full(self):
        """Test fully populated valid request."""
        request = CodeStoryboardRequest(
            file_content="def hello(): pass",
            file_name="test.py",
            icp_preset="coperniq_mep",
            stage="demo",
            audience="business_owner",
            custom_headline="Custom Headline",
        )
        assert request.file_content == "def hello(): pass"
        assert request.file_name == "test.py"
        assert request.icp_preset == "coperniq_mep"
        assert request.stage == "demo"
        assert request.audience == "business_owner"
        assert request.custom_headline == "Custom Headline"

    def test_empty_file_content_fails(self):
        """Test that empty file_content fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            CodeStoryboardRequest(file_content="")
        # Check that validation error is about string length or non-empty requirement
        error_str = str(exc_info.value)
        assert ("at least 1 character" in error_str or "must not be empty" in error_str)

    def test_whitespace_file_content_fails(self):
        """Test that whitespace-only file_content fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            CodeStoryboardRequest(file_content="   ")
        assert "file_content must not be empty" in str(exc_info.value)

    def test_missing_file_content_fails(self):
        """Test that missing file_content fails validation."""
        with pytest.raises(ValidationError):
            CodeStoryboardRequest(file_name="test.py")

    def test_invalid_stage_fails(self):
        """Test that invalid stage value fails validation."""
        with pytest.raises(ValidationError):
            CodeStoryboardRequest(
                file_content="def hello(): pass",
                stage="invalid",
            )

    def test_invalid_audience_fails(self):
        """Test that invalid audience value fails validation."""
        with pytest.raises(ValidationError):
            CodeStoryboardRequest(
                file_content="def hello(): pass",
                audience="invalid",
            )


class TestRoadmapStoryboardRequest:
    """Tests for RoadmapStoryboardRequest schema."""

    def test_valid_request_minimal(self):
        """Test minimal valid request."""
        request = RoadmapStoryboardRequest(
            image_data="base64encodeddata",
        )
        assert request.image_data == "base64encodeddata"
        assert request.icp_preset == "coperniq_mep"
        assert request.audience == "c_suite"
        assert request.custom_headline is None
        assert request.sanitize_ip is True

    def test_valid_request_full(self):
        """Test fully populated valid request."""
        request = RoadmapStoryboardRequest(
            image_data="base64encodeddata",
            icp_preset="coperniq_mep",
            audience="btl_champion",
            custom_headline="Coming Soon",
            sanitize_ip=False,
        )
        assert request.image_data == "base64encodeddata"
        assert request.icp_preset == "coperniq_mep"
        assert request.audience == "btl_champion"
        assert request.custom_headline == "Coming Soon"
        assert request.sanitize_ip is False

    def test_empty_image_data_fails(self):
        """Test that empty image_data fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            RoadmapStoryboardRequest(image_data="")
        # Check that validation error is about string length or non-empty requirement
        error_str = str(exc_info.value)
        assert ("at least 1 character" in error_str or "must not be empty" in error_str)

    def test_whitespace_image_data_fails(self):
        """Test that whitespace-only image_data fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            RoadmapStoryboardRequest(image_data="   ")
        assert "image_data must not be empty" in str(exc_info.value)

    def test_missing_image_data_fails(self):
        """Test that missing image_data fails validation."""
        with pytest.raises(ValidationError):
            RoadmapStoryboardRequest(icp_preset="coperniq_mep")


class TestStoryboardJobResponse:
    """Tests for StoryboardJobResponse schema."""

    def test_valid_response(self):
        """Test valid job response."""
        response = StoryboardJobResponse(
            job_id="123",
            status=JobStatus.PENDING,
            poll_url="/storyboard/jobs/123",
        )
        assert response.job_id == "123"
        assert response.status == JobStatus.PENDING
        assert response.poll_url == "/storyboard/jobs/123"


class TestStoryboardJobStatusResponse:
    """Tests for StoryboardJobStatusResponse schema."""

    def test_valid_response_pending(self):
        """Test valid pending job status."""
        now = datetime.now(timezone.utc)
        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.PENDING,
            result_image=None,
            understanding=None,
            error_message=None,
            execution_time_ms=None,
            created_at=now,
            completed_at=None,
        )
        assert response.job_id == "123"
        assert response.status == JobStatus.PENDING
        assert response.result_image is None
        assert response.understanding is None
        assert response.error_message is None
        assert response.execution_time_ms is None
        assert response.created_at == now
        assert response.completed_at is None

    def test_valid_response_completed(self):
        """Test valid completed job status."""
        now = datetime.now(timezone.utc)
        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.COMPLETED,
            result_image="base64image",
            understanding={"headline": "Test"},
            error_message=None,
            execution_time_ms=1000,
            created_at=now,
            completed_at=now,
        )
        assert response.job_id == "123"
        assert response.status == JobStatus.COMPLETED
        assert response.result_image == "base64image"
        assert response.understanding == {"headline": "Test"}
        assert response.error_message is None
        assert response.execution_time_ms == 1000
        assert response.completed_at == now

    def test_valid_response_failed(self):
        """Test valid failed job status."""
        now = datetime.now(timezone.utc)
        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.FAILED,
            result_image=None,
            understanding=None,
            error_message="Something went wrong",
            execution_time_ms=500,
            created_at=now,
            completed_at=now,
        )
        assert response.job_id == "123"
        assert response.status == JobStatus.FAILED
        assert response.result_image is None
        assert response.understanding is None
        assert response.error_message == "Something went wrong"
        assert response.execution_time_ms == 500


class TestStoryboardJob:
    """Tests for StoryboardJob internal model."""

    def test_job_creation_minimal(self):
        """Test minimal job creation with auto-generated fields."""
        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={"file_content": "test"},
        )
        assert job.job_id  # Should be auto-generated UUID
        assert job.org_id == "test-org"
        assert job.job_type == JobType.CODE_TO_STORYBOARD
        assert job.status == JobStatus.PENDING
        assert job.input_params == {"file_content": "test"}
        assert job.result_image is None
        assert job.understanding is None
        assert job.error_message is None
        assert job.created_at
        assert job.completed_at is None
        assert job.execution_time_ms is None
        assert job.metadata == {}

    def test_job_creation_full(self):
        """Test full job creation with all fields."""
        now = datetime.now(timezone.utc)
        job = StoryboardJob(
            job_id="custom-id",
            org_id="test-org",
            job_type=JobType.ROADMAP_TO_STORYBOARD,
            status=JobStatus.COMPLETED,
            input_params={"image_data": "base64"},
            result_image="base64image",
            understanding={"headline": "Test"},
            error_message=None,
            created_at=now,
            completed_at=now,
            execution_time_ms=1000,
            metadata={"stage": "preview"},
        )
        assert job.job_id == "custom-id"
        assert job.org_id == "test-org"
        assert job.job_type == JobType.ROADMAP_TO_STORYBOARD
        assert job.status == JobStatus.COMPLETED
        assert job.result_image == "base64image"
        assert job.understanding == {"headline": "Test"}
        assert job.execution_time_ms == 1000
        assert job.metadata == {"stage": "preview"}

    def test_job_model_dump(self):
        """Test job serialization to dict."""
        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={"file_content": "test"},
        )
        job_dict = job.model_dump()
        assert job_dict["org_id"] == "test-org"
        assert job_dict["job_type"] == JobType.CODE_TO_STORYBOARD
        assert job_dict["status"] == JobStatus.PENDING
        assert job_dict["input_params"] == {"file_content": "test"}

    def test_job_model_dump_json(self):
        """Test job serialization to JSON."""
        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={"file_content": "test"},
        )
        job_json = job.model_dump_json()
        assert isinstance(job_json, str)
        assert "test-org" in job_json
        assert "code_to_storyboard" in job_json


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses(self):
        """Test all job status values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


class TestJobType:
    """Tests for JobType enum."""

    def test_all_types(self):
        """Test all job type values."""
        assert JobType.CODE_TO_STORYBOARD.value == "code_to_storyboard"
        assert JobType.ROADMAP_TO_STORYBOARD.value == "roadmap_to_storyboard"
