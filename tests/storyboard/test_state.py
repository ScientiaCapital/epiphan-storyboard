"""
Tests for StoryboardJobManager state management.

These tests mock Redis and Supabase to test the state manager in isolation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.storyboard.schemas import JobStatus, JobType, StoryboardJob


class TestStoryboardJobManagerInit:
    """Tests for StoryboardJobManager initialization."""

    def test_init_requires_redis_url(self):
        """Test that init requires REDIS_URL."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Redis URL"):
                from src.storyboard.state import StoryboardJobManager
                StoryboardJobManager()

    def test_init_requires_supabase_url(self):
        """Test that init requires SUPABASE_URL."""
        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost"}, clear=True):
            with pytest.raises(ValueError, match="SUPABASE_URL"):
                from src.storyboard.state import StoryboardJobManager
                StoryboardJobManager()

    def test_init_with_explicit_params(self):
        """Test init with explicit parameters."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis.return_value = MagicMock()
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                    job_ttl=7200,
                )
                assert manager._job_ttl == 7200


class TestJobKeyGeneration:
    """Tests for Redis key generation."""

    def test_job_key_format(self):
        """Test that job key follows expected format."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis.return_value = MagicMock()
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )
                key = manager._job_key("abc-123")
                assert key == "storyboard:job:abc-123"


class TestCreateJob:
    """Tests for create_job method."""

    @pytest.mark.asyncio
    async def test_create_job_returns_job(self):
        """Test that create_job returns a StoryboardJob."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = await manager.create_job(
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    input_params={"file_content": "test"},
                )

                assert isinstance(job, StoryboardJob)
                assert job.org_id == "test-org"
                assert job.job_type == JobType.CODE_TO_STORYBOARD
                assert job.status == JobStatus.PENDING
                assert job.input_params == {"file_content": "test"}

    @pytest.mark.asyncio
    async def test_create_job_generates_uuid(self):
        """Test that create_job generates a unique UUID."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job1 = await manager.create_job(
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    input_params={},
                )
                job2 = await manager.create_job(
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    input_params={},
                )

                assert job1.job_id != job2.job_id

    @pytest.mark.asyncio
    async def test_create_job_stores_in_redis(self):
        """Test that create_job stores job in Redis with TTL."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                    job_ttl=3600,
                )

                job = await manager.create_job(
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    input_params={},
                )

                mock_redis_instance.setex.assert_called_once()
                call_args = mock_redis_instance.setex.call_args
                assert call_args[0][0] == f"storyboard:job:{job.job_id}"
                assert call_args[0][1] == 3600  # TTL


class TestGetJob:
    """Tests for get_job method."""

    @pytest.mark.asyncio
    async def test_get_job_from_redis(self):
        """Test that get_job retrieves from Redis first."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                # Create a job to get its JSON representation
                test_job = StoryboardJob(
                    job_id="test-123",
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    input_params={},
                )
                mock_redis_instance.get.return_value = test_job.model_dump_json()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = await manager.get_job("test-123")

                assert job is not None
                assert job.job_id == "test-123"
                assert job.org_id == "test-org"
                mock_redis_instance.get.assert_called_once_with("storyboard:job:test-123")

    @pytest.mark.asyncio
    async def test_get_job_redis_miss_checks_supabase(self):
        """Test that get_job falls back to Supabase on Redis miss."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.get.return_value = None  # Redis miss
                mock_redis.return_value = mock_redis_instance

                mock_supabase_instance = MagicMock()
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_eq = MagicMock()
                mock_single = MagicMock()
                mock_execute = MagicMock()

                mock_supabase_instance.table.return_value = mock_table
                mock_table.select.return_value = mock_select
                mock_select.eq.return_value = mock_eq
                mock_eq.single.return_value = mock_single
                mock_single.execute.return_value = MagicMock(
                    data={
                        "id": "test-123",
                        "org_id": "test-org",
                        "job_type": "code_to_storyboard",
                        "status": "pending",
                        "input_params": {},
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "metadata": {},
                    }
                )
                mock_supabase.return_value = mock_supabase_instance

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = await manager.get_job("test-123")

                assert job is not None
                assert job.job_id == "test-123"
                mock_supabase_instance.table.assert_called_with("storyboard_jobs")

    @pytest.mark.asyncio
    async def test_get_job_not_found_returns_none(self):
        """Test that get_job returns None when job not found."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis_instance.get.return_value = None  # Redis miss
                mock_redis.return_value = mock_redis_instance

                mock_supabase_instance = MagicMock()
                mock_table = MagicMock()
                mock_select = MagicMock()
                mock_eq = MagicMock()
                mock_single = MagicMock()
                mock_single.execute.side_effect = Exception("Not found")
                mock_eq.single.return_value = mock_single
                mock_select.eq.return_value = mock_eq
                mock_table.select.return_value = mock_select
                mock_supabase_instance.table.return_value = mock_table
                mock_supabase.return_value = mock_supabase_instance

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = await manager.get_job("nonexistent")
                assert job is None


class TestUpdateJob:
    """Tests for update_job method."""

    @pytest.mark.asyncio
    async def test_update_job_stores_in_redis(self):
        """Test that update_job updates Redis with fresh TTL."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                    job_ttl=3600,
                )

                job = StoryboardJob(
                    job_id="test-123",
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    status=JobStatus.PROCESSING,
                    input_params={},
                )

                await manager.update_job(job)

                mock_redis_instance.setex.assert_called_once()
                call_args = mock_redis_instance.setex.call_args
                assert call_args[0][0] == "storyboard:job:test-123"
                assert call_args[0][1] == 3600  # TTL reset


class TestPersistToSupabase:
    """Tests for persist_to_supabase method."""

    @pytest.mark.asyncio
    async def test_persist_inserts_to_supabase(self):
        """Test that persist_to_supabase inserts job to Supabase."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance

                mock_supabase_instance = MagicMock()
                mock_table = MagicMock()
                mock_upsert = MagicMock()
                mock_upsert.execute.return_value = MagicMock()
                mock_table.upsert.return_value = mock_upsert
                mock_supabase_instance.table.return_value = mock_table
                mock_supabase.return_value = mock_supabase_instance

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = StoryboardJob(
                    job_id="test-123",
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    status=JobStatus.COMPLETED,
                    input_params={},
                )

                await manager.persist_to_supabase(job)

                mock_supabase_instance.table.assert_called_with("storyboard_jobs")
                mock_table.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_persist_deletes_from_redis(self):
        """Test that persist_to_supabase deletes job from Redis."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance

                mock_supabase_instance = MagicMock()
                mock_table = MagicMock()
                mock_upsert = MagicMock()
                mock_upsert.execute.return_value = MagicMock()
                mock_table.upsert.return_value = mock_upsert
                mock_supabase_instance.table.return_value = mock_table
                mock_supabase.return_value = mock_supabase_instance

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                job = StoryboardJob(
                    job_id="test-123",
                    org_id="test-org",
                    job_type=JobType.CODE_TO_STORYBOARD,
                    status=JobStatus.COMPLETED,
                    input_params={},
                )

                await manager.persist_to_supabase(job)

                mock_redis_instance.delete.assert_called_once_with("storyboard:job:test-123")


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_redis(self):
        """Test that close method closes Redis connection."""
        with patch("src.storyboard.state.aioredis.from_url") as mock_redis:
            with patch("src.storyboard.state.create_client") as mock_supabase:
                mock_redis_instance = AsyncMock()
                mock_redis.return_value = mock_redis_instance
                mock_supabase.return_value = MagicMock()

                from src.storyboard.state import StoryboardJobManager
                manager = StoryboardJobManager(
                    redis_url="redis://test",
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key",
                )

                await manager.close()

                mock_redis_instance.aclose.assert_called_once()
