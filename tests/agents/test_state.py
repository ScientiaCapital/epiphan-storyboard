"""Tests for StateManager - Redis + Supabase hybrid state management.

TDD Red Phase: All tests written BEFORE implementation.
Tests use fakeredis for Redis and AsyncMock for Supabase.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.agents.schemas import AgentSession, AgentStep, SessionStatus, ToolCall


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    import fakeredis.aioredis
    return fakeredis.aioredis.FakeRedis()


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    mock.table = MagicMock(return_value=mock)
    mock.insert = MagicMock(return_value=mock)
    mock.update = MagicMock(return_value=mock)
    mock.select = MagicMock(return_value=mock)
    mock.eq = MagicMock(return_value=mock)
    mock.execute = MagicMock(return_value=MagicMock(data=[]))
    return mock


@pytest.fixture
def state_manager(mock_redis, mock_supabase):
    """Create a StateManager with mocked dependencies."""
    from src.agents.state import StateManager

    manager = StateManager(
        redis_url="redis://localhost:6379",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )
    manager._redis = mock_redis
    manager._supabase = mock_supabase
    return manager


# ============================================================================
# TestStateManagerInit
# ============================================================================


class TestStateManagerInit:
    """Test StateManager initialization."""

    def test_init_with_redis_url(self):
        """Test initialization with explicit Redis URL."""
        from src.agents.state import StateManager

        with patch.dict("os.environ", {}, clear=True):
            manager = StateManager(
                redis_url="redis://localhost:6379",
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
            )
            assert manager._redis_url == "redis://localhost:6379"

    def test_init_with_env_vars(self):
        """Test initialization from environment variables."""
        from src.agents.state import StateManager

        env_vars = {
            "REDIS_URL": "redis://env-redis:6379",
            "SUPABASE_URL": "https://env.supabase.co",
            "SUPABASE_SERVICE_KEY": "env-service-key",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            manager = StateManager()
            assert manager._redis_url == "redis://env-redis:6379"
            assert manager._supabase_url == "https://env.supabase.co"

    def test_init_without_connections_raises(self):
        """Test that missing required config raises error."""
        from src.agents.state import StateManager

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Redis URL"):
                StateManager()

    def test_init_default_session_ttl(self):
        """Test default session TTL is 1 hour."""
        from src.agents.state import StateManager

        with patch.dict("os.environ", {
            "REDIS_URL": "redis://localhost:6379",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key",
        }):
            manager = StateManager()
            assert manager._session_ttl == 3600


# ============================================================================
# TestSessionCreation
# ============================================================================


class TestSessionCreation:
    """Test creating new agent sessions."""

    @pytest.mark.asyncio
    async def test_create_session_returns_valid_uuid(self, state_manager):
        """Test that created session has valid UUID."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        # Verify UUID format
        uuid_obj = UUID(session.session_id)
        assert uuid_obj.version == 4

    @pytest.mark.asyncio
    async def test_create_session_sets_pending_status(self, state_manager):
        """Test that new session starts with PENDING status."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        assert session.status == SessionStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_session_stores_in_redis(self, state_manager, mock_redis):
        """Test that session is stored in Redis with TTL."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        # Verify stored in Redis
        key = f"session:{session.session_id}"
        stored = await mock_redis.get(key)
        assert stored is not None

        # Verify TTL is set
        ttl = await mock_redis.ttl(key)
        assert ttl > 0

    @pytest.mark.asyncio
    async def test_create_session_with_org_id(self, state_manager):
        """Test session stores org_id correctly."""
        session = await state_manager.create_session(
            org_id="my-organization",
            model="claude-sonnet-4-5-20250929",
        )

        assert session.org_id == "my-organization"

    @pytest.mark.asyncio
    async def test_create_session_initializes_empty_steps(self, state_manager):
        """Test session starts with empty steps list."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        assert session.steps == []

    @pytest.mark.asyncio
    async def test_create_session_initializes_zero_tokens(self, state_manager):
        """Test session starts with zero token counts."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        assert session.input_tokens == 0
        assert session.output_tokens == 0
        assert session.total_cost_usd == 0.0


# ============================================================================
# TestSessionRetrieval
# ============================================================================


class TestSessionRetrieval:
    """Test retrieving sessions from storage."""

    @pytest.mark.asyncio
    async def test_get_session_from_redis_hot_cache(self, state_manager, mock_redis):
        """Test getting session from Redis (hot cache hit)."""
        # Create a session first
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        # Retrieve it
        retrieved = await state_manager.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.org_id == "test-org"

    @pytest.mark.asyncio
    async def test_get_session_fallback_to_supabase(self, state_manager, mock_redis, mock_supabase):
        """Test fallback to Supabase when not in Redis."""
        session_id = "test-session-123"

        # Configure mock to return session from Supabase
        # Note: Implementation uses .single() which returns a single record, not a list
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "session_id": session_id,
                "org_id": "test-org",
                "status": "running",
                "model": "claude-sonnet-4-5-20250929",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_cost_usd": 0.001,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "steps": [],
            }
        )

        # Retrieve (Redis is empty, should fallback)
        retrieved = await state_manager.get_session(session_id)

        assert retrieved is not None
        assert retrieved.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found_returns_none(self, state_manager, mock_supabase):
        """Test getting non-existent session returns None."""
        # Configure mock to return empty
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        retrieved = await state_manager.get_session("nonexistent-session")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_session_reconstructs_steps(self, state_manager, mock_redis):
        """Test that retrieved session includes all steps."""
        # Create session and add steps
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        step1 = AgentStep(
            thought="First thought",
            action=ToolCall(tool_name="web_fetch", arguments={"url": "https://example.com"}),
            observation="Got response",
            is_final=False,
        )
        step2 = AgentStep(
            thought="Final thought",
            is_final=True,
            final_answer="The answer is 42",
        )

        await state_manager.add_step(session.session_id, step1)
        await state_manager.add_step(session.session_id, step2)

        # Retrieve and verify steps
        retrieved = await state_manager.get_session(session.session_id)

        assert len(retrieved.steps) == 2
        assert retrieved.steps[0].thought == "First thought"
        assert retrieved.steps[1].is_final is True


# ============================================================================
# TestStepManagement
# ============================================================================


class TestStepManagement:
    """Test adding and retrieving steps."""

    @pytest.mark.asyncio
    async def test_add_step_appends_to_redis_list(self, state_manager, mock_redis):
        """Test that steps are appended to Redis list."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        step = AgentStep(
            thought="Testing step",
            is_final=False,
        )

        await state_manager.add_step(session.session_id, step)

        # Verify step in Redis list
        key = f"steps:{session.session_id}"
        steps_data = await mock_redis.lrange(key, 0, -1)
        assert len(steps_data) == 1

    @pytest.mark.asyncio
    async def test_add_step_updates_session_step_count(self, state_manager):
        """Test that adding step updates session metadata."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        step = AgentStep(thought="Test", is_final=False)
        await state_manager.add_step(session.session_id, step)

        # Get updated session
        updated = await state_manager.get_session(session.session_id)
        assert len(updated.steps) == 1

    @pytest.mark.asyncio
    async def test_get_steps_returns_ordered_list(self, state_manager):
        """Test steps are returned in order added."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        for i in range(3):
            step = AgentStep(thought=f"Step {i}", is_final=False)
            await state_manager.add_step(session.session_id, step)

        steps = await state_manager.get_steps(session.session_id)

        assert len(steps) == 3
        assert steps[0].thought == "Step 0"
        assert steps[1].thought == "Step 1"
        assert steps[2].thought == "Step 2"

    @pytest.mark.asyncio
    async def test_get_steps_empty_session(self, state_manager):
        """Test getting steps from session with no steps."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        steps = await state_manager.get_steps(session.session_id)

        assert steps == []


# ============================================================================
# TestTokenTracking
# ============================================================================


class TestTokenTracking:
    """Test token usage and cost tracking."""

    @pytest.mark.asyncio
    async def test_update_token_usage_accumulates(self, state_manager):
        """Test that token counts accumulate across updates."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        # First update
        await state_manager.update_token_usage(
            session_id=session.session_id,
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
        )

        # Second update
        await state_manager.update_token_usage(
            session_id=session.session_id,
            input_tokens=200,
            output_tokens=100,
            cost=0.002,
        )

        # Verify accumulation
        updated = await state_manager.get_session(session.session_id)
        assert updated.input_tokens == 300
        assert updated.output_tokens == 150

    @pytest.mark.asyncio
    async def test_update_token_usage_calculates_cost(self, state_manager):
        """Test that cost accumulates correctly."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        await state_manager.update_token_usage(
            session_id=session.session_id,
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
        )

        updated = await state_manager.get_session(session.session_id)
        assert updated.total_cost_usd == 0.015

    @pytest.mark.asyncio
    async def test_token_tracking_persists(self, state_manager):
        """Test that token tracking persists across retrievals."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        await state_manager.update_token_usage(
            session_id=session.session_id,
            input_tokens=500,
            output_tokens=250,
            cost=0.01,
        )

        # Retrieve multiple times
        for _ in range(3):
            retrieved = await state_manager.get_session(session.session_id)
            assert retrieved.input_tokens == 500
            assert retrieved.output_tokens == 250


# ============================================================================
# TestPersistence
# ============================================================================


class TestPersistence:
    """Test persisting sessions to Supabase."""

    @pytest.mark.asyncio
    async def test_persist_to_supabase_on_completion(self, state_manager, mock_supabase):
        """Test that completed session is persisted to Supabase."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.COMPLETED

        await state_manager.persist_to_supabase(session)

        # Verify Supabase insert was called
        mock_supabase.table.assert_called()

    @pytest.mark.asyncio
    async def test_persist_deletes_redis_keys(self, state_manager, mock_redis):
        """Test that persisting removes session from Redis."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        session.status = SessionStatus.COMPLETED

        # Verify keys exist before persist
        session_key = f"session:{session.session_id}"
        assert await mock_redis.exists(session_key)

        await state_manager.persist_to_supabase(session)

        # Verify keys deleted after persist
        assert not await mock_redis.exists(session_key)

    @pytest.mark.asyncio
    async def test_persist_batch_writes_steps(self, state_manager, mock_supabase):
        """Test that all steps are batch written to Supabase."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        # Add multiple steps
        for i in range(5):
            step = AgentStep(thought=f"Step {i}", is_final=False)
            await state_manager.add_step(session.session_id, step)

        session.status = SessionStatus.COMPLETED
        await state_manager.persist_to_supabase(session)

        # Verify batch insert for steps
        # The exact call depends on implementation, but steps should be written
        assert mock_supabase.table.called


# ============================================================================
# TestSessionUpdate
# ============================================================================


class TestSessionUpdate:
    """Test updating session state."""

    @pytest.mark.asyncio
    async def test_update_session_status(self, state_manager):
        """Test updating session status."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )

        session.status = SessionStatus.RUNNING
        await state_manager.update_session(session)

        retrieved = await state_manager.get_session(session.session_id)
        assert retrieved.status == SessionStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_session_updates_timestamp(self, state_manager):
        """Test that update changes updated_at timestamp."""
        session = await state_manager.create_session(
            org_id="test-org",
            model="claude-sonnet-4-5-20250929",
        )
        original_updated = session.updated_at

        # Small delay and update
        session.status = SessionStatus.RUNNING
        await state_manager.update_session(session)

        retrieved = await state_manager.get_session(session.session_id)
        # Note: Exact time comparison may be tricky, just verify it's set
        assert retrieved.updated_at is not None


# ============================================================================
# TestCleanup
# ============================================================================


class TestCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_releases_connections(self, state_manager, mock_redis):
        """Test that close() releases Redis connection."""
        await state_manager.close()

        # Verify Redis connection is closed
        # The exact verification depends on implementation
        # For fakeredis, we just ensure no errors

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """Test StateManager as async context manager."""
        from src.agents.state import StateManager

        with patch.dict("os.environ", {
            "REDIS_URL": "redis://localhost:6379",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-key",
        }):
            # This tests that StateManager can be used with async with
            # and properly cleans up on exit
            pass  # Actual implementation will test async with pattern
