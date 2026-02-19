"""Tests for demo pipeline Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.tools.video.demo_pipeline_schemas import (
    DemoSceneType,
    DemoPipelineStatus,
    SceneTemplate,
    SceneExtractionResult,
    VideoAsset,
    VideoAssetBatchResult,
    DemoPipelineJob,
    DemoPipelineRequest,
    DemoPipelineResponse,
    DemoPipelineStatusResponse,
    SCENE_TIMING_DEFAULTS,
    MVP_CLIP_DURATION_SECONDS,
)


class TestDemoSceneType:
    def test_intro_value(self):
        assert DemoSceneType.INTRO.value == "intro"

    def test_pain_point_value(self):
        assert DemoSceneType.PAIN_POINT.value == "pain_point"

    def test_solution_value(self):
        assert DemoSceneType.SOLUTION.value == "solution"

    def test_differentiation_value(self):
        assert DemoSceneType.DIFFERENTIATION.value == "differentiation"

    def test_results_value(self):
        assert DemoSceneType.RESULTS.value == "results"

    def test_cta_value(self):
        assert DemoSceneType.CTA.value == "cta"

    def test_has_exactly_six_members(self):
        assert len(DemoSceneType) == 6


class TestDemoPipelineStatus:
    def test_pending_value(self):
        assert DemoPipelineStatus.PENDING.value == "pending"

    def test_extracting_scenes_value(self):
        assert DemoPipelineStatus.EXTRACTING_SCENES.value == "extracting_scenes"

    def test_generating_assets_value(self):
        assert DemoPipelineStatus.GENERATING_ASSETS.value == "generating_assets"

    def test_completed_value(self):
        assert DemoPipelineStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert DemoPipelineStatus.FAILED.value == "failed"

    def test_has_exactly_five_members(self):
        assert len(DemoPipelineStatus) == 5


class TestSceneTemplate:
    def test_creation_with_required_fields(self):
        scene = SceneTemplate(
            scene_type=DemoSceneType.INTRO,
            video_prompt="A professional AV setup in a modern lecture hall",
        )
        assert scene.scene_type == DemoSceneType.INTRO
        assert scene.video_prompt == "A professional AV setup in a modern lecture hall"

    def test_defaults(self):
        scene = SceneTemplate(
            scene_type=DemoSceneType.SOLUTION,
            video_prompt="Pearl Mini capturing a live event",
        )
        assert scene.talking_points == []
        assert scene.duration_seconds == MVP_CLIP_DURATION_SECONDS
        assert scene.start_time == 0
        assert scene.end_time == 0
        assert scene.visual_description == ""

    def test_video_prompt_min_length_validation(self):
        with pytest.raises(ValidationError, match="video_prompt"):
            SceneTemplate(
                scene_type=DemoSceneType.INTRO,
                video_prompt="short",
            )

    def test_duration_lower_bound(self):
        with pytest.raises(ValidationError):
            SceneTemplate(
                scene_type=DemoSceneType.INTRO,
                video_prompt="A valid prompt that is long enough",
                duration_seconds=0,
            )

    def test_duration_upper_bound(self):
        with pytest.raises(ValidationError):
            SceneTemplate(
                scene_type=DemoSceneType.INTRO,
                video_prompt="A valid prompt that is long enough",
                duration_seconds=61,
            )

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError, match="extra"):
            SceneTemplate(
                scene_type=DemoSceneType.INTRO,
                video_prompt="A valid prompt that is long enough",
                unknown_field="bad",
            )


class TestSceneExtractionResult:
    def _make_scene(self, scene_type=DemoSceneType.INTRO):
        return SceneTemplate(
            scene_type=scene_type,
            video_prompt="A detailed video prompt for testing purposes",
        )

    def test_creation(self):
        result = SceneExtractionResult(scenes=[self._make_scene()])
        assert len(result.scenes) == 1
        assert result.persona == "av_director"
        assert result.vertical == "higher_ed"
        assert result.product_focus == "pearl_mini"

    def test_scenes_min_length(self):
        with pytest.raises(ValidationError, match="scenes"):
            SceneExtractionResult(scenes=[])

    def test_model_used_default(self):
        result = SceneExtractionResult(scenes=[self._make_scene()])
        assert result.model_used == "deepseek/deepseek-chat-v3"

    def test_extraction_time_default(self):
        result = SceneExtractionResult(scenes=[self._make_scene()])
        assert result.extraction_time_ms == 0


class TestVideoAsset:
    def test_creation(self):
        asset = VideoAsset(
            scene_type=DemoSceneType.SOLUTION,
            scene_name="Solution Overview",
        )
        assert asset.scene_type == DemoSceneType.SOLUTION
        assert asset.scene_name == "Solution Overview"

    def test_defaults(self):
        asset = VideoAsset(
            scene_type=DemoSceneType.CTA,
            scene_name="Call to Action",
        )
        assert asset.video_url is None
        assert asset.thumbnail_url is None
        assert asset.duration_seconds == MVP_CLIP_DURATION_SECONDS
        assert asset.provider == "kling"
        assert asset.estimated_cost_usd == 0.0
        assert asset.success is True
        assert asset.error is None

    def test_cost_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            VideoAsset(
                scene_type=DemoSceneType.INTRO,
                scene_name="Intro",
                estimated_cost_usd=-1.0,
            )


class TestVideoAssetBatchResult:
    def test_creation(self):
        result = VideoAssetBatchResult()
        assert result.assets == []
        assert result.total_scenes == 0
        assert result.successful_scenes == 0
        assert result.failed_scenes == 0

    def test_defaults(self):
        result = VideoAssetBatchResult()
        assert result.total_estimated_cost_usd == 0.0
        assert result.provider == "kling"


class TestDemoPipelineJob:
    def test_creation_with_org_id(self):
        job = DemoPipelineJob(org_id="org_123")
        assert job.org_id == "org_123"

    def test_auto_generated_job_id(self):
        job = DemoPipelineJob(org_id="org_abc")
        assert job.job_id is not None
        assert len(job.job_id) > 0

    def test_unique_job_ids(self):
        job1 = DemoPipelineJob(org_id="org_1")
        job2 = DemoPipelineJob(org_id="org_2")
        assert job1.job_id != job2.job_id

    def test_status_default(self):
        job = DemoPipelineJob(org_id="org_test")
        assert job.status == DemoPipelineStatus.PENDING

    def test_understanding_field(self):
        understanding = {"headline": "Test", "pain_point": "Manual recording"}
        job = DemoPipelineJob(org_id="org_x", understanding=understanding)
        assert job.understanding == understanding

    def test_defaults(self):
        job = DemoPipelineJob(org_id="org_defaults")
        assert job.persona == "av_director"
        assert job.vertical == "higher_ed"
        assert job.product_focus == "pearl_mini"
        assert job.skip_video_generation is False
        assert job.scene_extraction is None
        assert job.video_assets is None
        assert job.error_message is None
        assert job.completed_at is None
        assert job.execution_time_ms is None
        assert job.metadata == {}


class TestDemoPipelineRequest:
    def test_creation_with_understanding(self):
        req = DemoPipelineRequest(
            understanding={"headline": "Test headline"},
        )
        assert req.understanding == {"headline": "Test headline"}
        assert req.persona == "av_director"

    def test_creation_with_raw_fields(self):
        req = DemoPipelineRequest(
            headline="Automate lecture capture",
            pain_point="Manual recording is unreliable",
            business_value="Save 20 hours per week",
        )
        assert req.headline == "Automate lecture capture"
        assert req.pain_point == "Manual recording is unreliable"
        assert req.business_value == "Save 20 hours per week"

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError, match="extra"):
            DemoPipelineRequest(
                understanding={"headline": "Test"},
                rogue_field="not allowed",
            )

    def test_defaults(self):
        req = DemoPipelineRequest()
        assert req.understanding is None
        assert req.storyboard_job_id is None
        assert req.headline is None
        assert req.skip_video_generation is False
        assert req.provider == "kling"


class TestDemoPipelineResponse:
    def test_creation(self):
        resp = DemoPipelineResponse(
            job_id="job_abc",
            status=DemoPipelineStatus.PENDING,
            poll_url="/video/demo-pipeline/jobs/job_abc",
        )
        assert resp.job_id == "job_abc"
        assert resp.status == DemoPipelineStatus.PENDING
        assert resp.poll_url == "/video/demo-pipeline/jobs/job_abc"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            DemoPipelineResponse(
                job_id="job_abc",
                status=DemoPipelineStatus.PENDING,
            )


class TestDemoPipelineStatusResponse:
    def test_creation(self):
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        resp = DemoPipelineStatusResponse(
            job_id="job_xyz",
            status=DemoPipelineStatus.COMPLETED,
            created_at=now,
        )
        assert resp.job_id == "job_xyz"
        assert resp.status == DemoPipelineStatus.COMPLETED
        assert resp.created_at == now
        assert resp.scene_extraction is None
        assert resp.video_assets is None
        assert resp.error_message is None
        assert resp.completed_at is None


class TestSceneTimingDefaults:
    def test_all_six_scene_types_have_timing(self):
        for scene_type in DemoSceneType:
            assert scene_type in SCENE_TIMING_DEFAULTS

    def test_each_entry_has_start_end_duration(self):
        for scene_type, timing in SCENE_TIMING_DEFAULTS.items():
            assert "start" in timing
            assert "end" in timing
            assert "duration" in timing

    def test_durations_are_consistent(self):
        for scene_type, timing in SCENE_TIMING_DEFAULTS.items():
            assert timing["end"] - timing["start"] == timing["duration"]


class TestMVPClipDuration:
    def test_value_equals_five(self):
        assert MVP_CLIP_DURATION_SECONDS == 5
