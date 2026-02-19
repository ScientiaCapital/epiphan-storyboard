"""
Integration tests for Storyboard Pipeline API.

Tests the schemas and validation without importing the full app (to avoid supabase import issues).
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestCodeStoryboardRequestValidation:
    """Tests for CodeStoryboardRequest validation."""

    def test_valid_request_with_defaults(self):
        """Test valid request with default values."""
        from src.storyboard.schemas import CodeStoryboardRequest

        request = CodeStoryboardRequest(
            file_content="def hello(): pass",
        )
        assert request.file_content == "def hello(): pass"
        assert request.file_name is None
        assert request.icp_preset == "coperniq_mep"
        assert request.stage == "preview"
        assert request.audience == "c_suite"
        assert request.custom_headline is None

    def test_valid_request_with_all_fields(self):
        """Test valid request with all fields specified."""
        from src.storyboard.schemas import CodeStoryboardRequest

        request = CodeStoryboardRequest(
            file_content="def hello(): pass",
            file_name="hello.py",
            icp_preset="custom_icp",
            stage="demo",
            audience="business_owner",
            custom_headline="Custom Headline",
        )
        assert request.file_name == "hello.py"
        assert request.stage == "demo"
        assert request.audience == "business_owner"
        assert request.custom_headline == "Custom Headline"

    def test_empty_file_content_fails(self):
        """Test that empty file_content fails validation."""
        from src.storyboard.schemas import CodeStoryboardRequest

        with pytest.raises(ValidationError):
            CodeStoryboardRequest(file_content="")

    def test_whitespace_file_content_fails(self):
        """Test that whitespace-only file_content fails validation."""
        from src.storyboard.schemas import CodeStoryboardRequest

        with pytest.raises(ValidationError):
            CodeStoryboardRequest(file_content="   ")

    def test_missing_file_content_fails(self):
        """Test that missing file_content fails validation."""
        from src.storyboard.schemas import CodeStoryboardRequest

        with pytest.raises(ValidationError):
            CodeStoryboardRequest(file_name="test.py")

    def test_invalid_stage_fails(self):
        """Test that invalid stage fails validation."""
        from src.storyboard.schemas import CodeStoryboardRequest

        with pytest.raises(ValidationError):
            CodeStoryboardRequest(
                file_content="test",
                stage="invalid_stage",
            )

    def test_invalid_audience_fails(self):
        """Test that invalid audience fails validation."""
        from src.storyboard.schemas import CodeStoryboardRequest

        with pytest.raises(ValidationError):
            CodeStoryboardRequest(
                file_content="test",
                audience="invalid_audience",
            )


class TestRoadmapStoryboardRequestValidation:
    """Tests for RoadmapStoryboardRequest validation."""

    def test_valid_request_with_defaults(self):
        """Test valid request with default values."""
        from src.storyboard.schemas import RoadmapStoryboardRequest

        request = RoadmapStoryboardRequest(
            image_data="base64encodeddata",
        )
        assert request.image_data == "base64encodeddata"
        assert request.icp_preset == "coperniq_mep"
        assert request.audience == "c_suite"
        assert request.custom_headline is None
        assert request.sanitize_ip is True

    def test_valid_request_with_all_fields(self):
        """Test valid request with all fields specified."""
        from src.storyboard.schemas import RoadmapStoryboardRequest

        request = RoadmapStoryboardRequest(
            image_data="base64data",
            icp_preset="custom_icp",
            audience="btl_champion",
            custom_headline="Coming Soon",
            sanitize_ip=False,
        )
        assert request.audience == "btl_champion"
        assert request.sanitize_ip is False

    def test_empty_image_data_fails(self):
        """Test that empty image_data fails validation."""
        from src.storyboard.schemas import RoadmapStoryboardRequest

        with pytest.raises(ValidationError):
            RoadmapStoryboardRequest(image_data="")

    def test_whitespace_image_data_fails(self):
        """Test that whitespace-only image_data fails validation."""
        from src.storyboard.schemas import RoadmapStoryboardRequest

        with pytest.raises(ValidationError):
            RoadmapStoryboardRequest(image_data="   ")

    def test_missing_image_data_fails(self):
        """Test that missing image_data fails validation."""
        from src.storyboard.schemas import RoadmapStoryboardRequest

        with pytest.raises(ValidationError):
            RoadmapStoryboardRequest(icp_preset="coperniq_mep")


class TestStoryboardJobResponse:
    """Tests for StoryboardJobResponse schema."""

    def test_valid_response(self):
        """Test valid job response."""
        from src.storyboard.schemas import JobStatus, StoryboardJobResponse

        response = StoryboardJobResponse(
            job_id="123-456",
            status=JobStatus.PENDING,
            poll_url="/storyboard/jobs/123-456",
        )
        assert response.job_id == "123-456"
        assert response.status == JobStatus.PENDING
        assert response.poll_url == "/storyboard/jobs/123-456"

    def test_missing_fields_fails(self):
        """Test that missing required fields fails."""
        from src.storyboard.schemas import StoryboardJobResponse

        with pytest.raises(ValidationError):
            StoryboardJobResponse(job_id="123")


class TestStoryboardJobStatusResponse:
    """Tests for StoryboardJobStatusResponse schema."""

    def test_valid_pending_response(self):
        """Test valid pending job status response."""
        from src.storyboard.schemas import JobStatus, StoryboardJobStatusResponse

        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        assert response.job_id == "123"
        assert response.status == JobStatus.PENDING
        assert response.result_image is None
        assert response.understanding is None
        assert response.error_message is None

    def test_valid_completed_response(self):
        """Test valid completed job status response."""
        from src.storyboard.schemas import JobStatus, StoryboardJobStatusResponse

        now = datetime.now(timezone.utc)
        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.COMPLETED,
            result_image="base64imagedata",
            understanding={"headline": "Test Headline", "business_value": "Value"},
            execution_time_ms=45000,
            created_at=now,
            completed_at=now,
        )
        assert response.status == JobStatus.COMPLETED
        assert response.result_image == "base64imagedata"
        assert response.understanding["headline"] == "Test Headline"
        assert response.execution_time_ms == 45000

    def test_valid_failed_response(self):
        """Test valid failed job status response."""
        from src.storyboard.schemas import JobStatus, StoryboardJobStatusResponse

        now = datetime.now(timezone.utc)
        response = StoryboardJobStatusResponse(
            job_id="123",
            status=JobStatus.FAILED,
            error_message="Gemini API error",
            execution_time_ms=5000,
            created_at=now,
            completed_at=now,
        )
        assert response.status == JobStatus.FAILED
        assert response.error_message == "Gemini API error"
        assert response.result_image is None


class TestStoryboardJob:
    """Tests for StoryboardJob internal model."""

    def test_job_creation_minimal(self):
        """Test job creation with minimal parameters."""
        from src.storyboard.schemas import JobStatus, JobType, StoryboardJob

        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={"file_content": "test"},
        )
        assert job.job_id  # Auto-generated UUID
        assert job.org_id == "test-org"
        assert job.job_type == JobType.CODE_TO_STORYBOARD
        assert job.status == JobStatus.PENDING
        assert job.input_params == {"file_content": "test"}
        assert job.result_image is None
        assert job.understanding is None
        assert job.error_message is None
        assert job.created_at is not None
        assert job.completed_at is None
        assert job.execution_time_ms is None
        assert job.metadata == {}

    def test_job_creation_full(self):
        """Test job creation with all parameters."""
        from src.storyboard.schemas import JobStatus, JobType, StoryboardJob

        now = datetime.now(timezone.utc)
        job = StoryboardJob(
            job_id="custom-id",
            org_id="test-org",
            job_type=JobType.ROADMAP_TO_STORYBOARD,
            status=JobStatus.COMPLETED,
            input_params={"image_data": "base64"},
            result_image="result-base64",
            understanding={"headline": "Test"},
            error_message=None,
            created_at=now,
            completed_at=now,
            execution_time_ms=30000,
            metadata={"stage": "preview"},
        )
        assert job.job_id == "custom-id"
        assert job.status == JobStatus.COMPLETED
        assert job.result_image == "result-base64"
        assert job.execution_time_ms == 30000
        assert job.metadata == {"stage": "preview"}

    def test_job_model_dump(self):
        """Test that model_dump works correctly."""
        from src.storyboard.schemas import JobType, StoryboardJob

        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={},
        )
        data = job.model_dump()
        assert "job_id" in data
        assert "org_id" in data
        assert "job_type" in data
        assert "status" in data
        assert "input_params" in data

    def test_job_model_dump_json(self):
        """Test that model_dump_json works correctly."""
        from src.storyboard.schemas import JobType, StoryboardJob
        import json

        job = StoryboardJob(
            org_id="test-org",
            job_type=JobType.CODE_TO_STORYBOARD,
            input_params={"key": "value"},
        )
        json_str = job.model_dump_json()
        data = json.loads(json_str)
        assert data["org_id"] == "test-org"
        assert data["input_params"] == {"key": "value"}


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_statuses_exist(self):
        """Test that all expected statuses exist."""
        from src.storyboard.schemas import JobStatus

        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"

    def test_status_count(self):
        """Test that we have exactly 4 statuses."""
        from src.storyboard.schemas import JobStatus

        assert len(JobStatus) == 4


class TestJobType:
    """Tests for JobType enum."""

    def test_all_types_exist(self):
        """Test that all expected job types exist."""
        from src.storyboard.schemas import JobType

        assert JobType.CODE_TO_STORYBOARD == "code_to_storyboard"
        assert JobType.ROADMAP_TO_STORYBOARD == "roadmap_to_storyboard"

    def test_type_count(self):
        """Test that we have exactly 2 job types."""
        from src.storyboard.schemas import JobType

        assert len(JobType) == 2
