"""Tests for demo pipeline integration — router, chain, and schema models."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.router.chains import DemoPipelineChain
from src.router.schemas import ClassificationResult, TaskType
from src.tools.base import ToolResult
from src.tools.video.demo_pipeline_router import _resolve_understanding
from src.tools.video.demo_pipeline_schemas import (
    DemoPipelineJob,
    DemoPipelineRequest,
    DemoPipelineResponse,
    DemoPipelineStatus,
    DemoPipelineStatusResponse,
)


# ============================================================================
# TestDemoPipelineRouterResolveUnderstanding
# ============================================================================


class TestDemoPipelineRouterResolveUnderstanding:
    def test_returns_understanding_dict_when_provided(self):
        understanding = {"headline": "Test", "pain_point_addressed": "Problem"}
        request = DemoPipelineRequest(understanding=understanding)
        result = _resolve_understanding(request)
        assert result == understanding

    def test_returns_none_when_storyboard_job_id_provided(self):
        request = DemoPipelineRequest(storyboard_job_id="job_abc123")
        result = _resolve_understanding(request)
        assert result is None

    def test_returns_synthetic_understanding_when_raw_fields_provided(self):
        request = DemoPipelineRequest(
            headline="Automate lecture capture",
            pain_point="Manual recording is unreliable",
            business_value="Save 20 hours per week",
        )
        result = _resolve_understanding(request)
        assert result is not None
        assert result["headline"] == "Automate lecture capture"
        assert result["pain_point_addressed"] == "Manual recording is unreliable"
        assert result["business_value"] == "Save 20 hours per week"
        assert result["what_it_does"] == ""
        assert result["who_benefits"] == ""
        assert result["differentiator"] == ""

    def test_returns_none_when_no_input_source_provided(self):
        request = DemoPipelineRequest()
        result = _resolve_understanding(request)
        assert result is None


# ============================================================================
# TestDemoPipelineChain
# ============================================================================


class TestDemoPipelineChain:
    def test_chain_type_is_demo_pipeline(self):
        mock_registry = MagicMock()
        chain = DemoPipelineChain(mock_registry)
        assert chain.chain_type == TaskType.DEMO_PIPELINE

    def test_required_tools_contains_expected(self):
        mock_registry = MagicMock()
        chain = DemoPipelineChain(mock_registry)
        assert "scene_extractor" in chain.required_tools
        assert "video_asset_generator" in chain.required_tools

    @pytest.mark.asyncio
    @patch("src.tools.video.scene_extractor.SceneExtractorTool")
    async def test_execute_with_mocked_tools_returns_success(self, mock_extractor_cls):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None

        mock_extractor_instance = AsyncMock()
        mock_extractor_instance.run.return_value = ToolResult(
            tool_name="scene_extractor",
            success=True,
            result={"scenes": [{"scene_type": "intro", "video_prompt": "Test prompt"}]},
            execution_time_ms=150,
        )
        mock_extractor_cls.return_value = mock_extractor_instance

        chain = DemoPipelineChain(mock_registry)
        classification = ClassificationResult(
            task_type=TaskType.DEMO_PIPELINE,
            confidence=1.0,
            reasoning="test",
        )

        with patch(
            "src.tools.video.video_asset_generator.VideoAssetGeneratorTool"
        ) as mock_gen_cls:
            mock_gen_instance = AsyncMock()
            mock_gen_instance.run.return_value = ToolResult(
                tool_name="video_asset_generator",
                success=True,
                result={"assets": []},
                execution_time_ms=200,
            )
            mock_gen_cls.return_value = mock_gen_instance

            result = await chain.execute(
                params={"understanding": {"headline": "Test"}},
                classification=classification,
            )

        assert result["success"] is True
        assert result["chain_type"] == "demo_pipeline"
        assert "scene_extraction" in result

    @pytest.mark.asyncio
    @patch("src.tools.video.scene_extractor.SceneExtractorTool")
    async def test_execute_skip_video_generation(self, mock_extractor_cls):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None

        mock_extractor_instance = AsyncMock()
        mock_extractor_instance.run.return_value = ToolResult(
            tool_name="scene_extractor",
            success=True,
            result={"scenes": [{"scene_type": "intro", "video_prompt": "Test prompt"}]},
            execution_time_ms=100,
        )
        mock_extractor_cls.return_value = mock_extractor_instance

        chain = DemoPipelineChain(mock_registry)
        classification = ClassificationResult(
            task_type=TaskType.DEMO_PIPELINE,
            confidence=1.0,
            reasoning="test",
        )

        result = await chain.execute(
            params={
                "understanding": {"headline": "Test"},
                "skip_video_generation": True,
            },
            classification=classification,
        )

        assert result["success"] is True
        assert "video_assets" not in result


# ============================================================================
# TestDemoPipelineStatusModel
# ============================================================================


class TestDemoPipelineStatusModel:
    def test_has_all_five_expected_values(self):
        expected = {
            "pending",
            "extracting_scenes",
            "generating_assets",
            "completed",
            "failed",
        }
        actual = {s.value for s in DemoPipelineStatus}
        assert actual == expected

    def test_can_be_used_in_demo_pipeline_job(self):
        job = DemoPipelineJob(
            org_id="org_test",
            status=DemoPipelineStatus.EXTRACTING_SCENES,
        )
        assert job.status == DemoPipelineStatus.EXTRACTING_SCENES

    def test_job_status_default_is_pending(self):
        job = DemoPipelineJob(org_id="org_test")
        assert job.status == DemoPipelineStatus.PENDING


# ============================================================================
# TestDemoPipelineJobModel
# ============================================================================


class TestDemoPipelineJobModel:
    def test_creates_with_auto_generated_uuid_job_id(self):
        job = DemoPipelineJob(org_id="org_uuid_test")
        parsed = uuid.UUID(job.job_id)
        assert parsed.version == 4

    def test_serializes_and_deserializes_correctly(self):
        job = DemoPipelineJob(
            org_id="org_roundtrip",
            status=DemoPipelineStatus.COMPLETED,
            understanding={"headline": "Roundtrip test"},
            persona="av_director",
            vertical="higher_ed",
            product_focus="pearl_mini",
        )
        json_str = job.model_dump_json()
        restored = DemoPipelineJob.model_validate_json(json_str)
        assert restored.job_id == job.job_id
        assert restored.org_id == job.org_id
        assert restored.status == DemoPipelineStatus.COMPLETED
        assert restored.understanding == {"headline": "Roundtrip test"}
        assert restored.persona == "av_director"


# ============================================================================
# TestDemoPipelineResponseModels
# ============================================================================


class TestDemoPipelineResponseModels:
    def test_demo_pipeline_response_with_required_fields(self):
        resp = DemoPipelineResponse(
            job_id="job_resp_test",
            status=DemoPipelineStatus.PENDING,
            poll_url="/video/demo-pipeline/jobs/job_resp_test",
        )
        assert resp.job_id == "job_resp_test"
        assert resp.status == DemoPipelineStatus.PENDING
        assert resp.poll_url == "/video/demo-pipeline/jobs/job_resp_test"

    def test_demo_pipeline_status_response_with_optional_fields_none(self):
        now = datetime.now(UTC)
        resp = DemoPipelineStatusResponse(
            job_id="job_status_test",
            status=DemoPipelineStatus.PENDING,
            created_at=now,
        )
        assert resp.job_id == "job_status_test"
        assert resp.status == DemoPipelineStatus.PENDING
        assert resp.scene_extraction is None
        assert resp.video_assets is None
        assert resp.error_message is None
        assert resp.execution_time_ms is None
        assert resp.completed_at is None
