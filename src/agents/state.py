"""Hybrid state manager using Redis for hot state and Supabase for cold persistence.

This module provides a StateManager class that implements a two-tier storage strategy:
- Redis: Fast in-memory storage for active sessions (1 hour TTL)
- Supabase: Durable PostgreSQL storage for completed sessions

Architecture:
- Sessions are created in Redis with automatic TTL
- Steps are stored as Redis lists for fast append operations
- Completed sessions are persisted to Supabase and removed from Redis
- Read operations check Redis first, then fallback to Supabase
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from supabase import create_client, Client

from src.agents.schemas import AgentSession, AgentStep, SessionStatus


class StateManager:
    """Manages agent session state across Redis (hot) and Supabase (cold) storage.

    Attributes:
        _redis: Async Redis client for hot state
        _supabase: Supabase client for cold persistence
        _session_ttl: TTL in seconds for Redis session keys (default: 3600 = 1 hour)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        session_ttl: int = 3600,
    ):
        """Initialize StateManager with Redis and Supabase connections.

        Args:
            redis_url: Redis connection string (default: from REDIS_URL env var)
            supabase_url: Supabase project URL (default: from SUPABASE_URL env var)
            supabase_key: Supabase service key (default: from SUPABASE_SERVICE_KEY env var)
            session_ttl: TTL in seconds for Redis entries (default: 3600)
        """
        # Redis setup - require explicit URL or env var
        self._redis_url = redis_url or os.getenv("REDIS_URL")
        if not self._redis_url:
            raise ValueError(
                "Redis URL must be provided or set via REDIS_URL environment variable"
            )

        self._redis = aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        # Supabase setup
        self._supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self._supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided "
                "or set as environment variables"
            )

        self._supabase: Client = create_client(self._supabase_url, supabase_key)
        self._session_ttl = session_ttl

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.aclose()

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"session:{session_id}"

    def _steps_key(self, session_id: str) -> str:
        """Generate Redis key for session steps list."""
        return f"steps:{session_id}"

    async def create_session(self, org_id: str, model: str) -> AgentSession:
        """Create a new agent session in Redis.

        Args:
            org_id: Organization identifier
            model: Model identifier to use for this session

        Returns:
            Newly created AgentSession with generated UUID

        Raises:
            redis.RedisError: If Redis operations fail
        """
        session = AgentSession(
            org_id=org_id,
            status=SessionStatus.PENDING,
        )

        # Store session in Redis with TTL
        session_data = session.model_dump_json()
        session_key = self._session_key(session.session_id)

        await self._redis.setex(
            session_key,
            self._session_ttl,
            session_data
        )

        return session

    async def get_session(self, session_id: str) -> AgentSession | None:
        """Get session from Redis (fast path) or Supabase (cold storage).

        Args:
            session_id: Unique session identifier

        Returns:
            AgentSession if found, None otherwise

        Raises:
            redis.RedisError: If Redis operations fail
            Exception: If Supabase query fails
        """
        # Try Redis first (hot state)
        session_key = self._session_key(session_id)
        session_data = await self._redis.get(session_key)

        if session_data:
            return AgentSession.model_validate_json(session_data)

        # Fallback to Supabase (cold storage)
        try:
            response = self._supabase.table("agent_sessions").select("*").eq(
                "session_id", session_id
            ).single().execute()

            if response.data:
                # Convert Supabase response to AgentSession
                # Note: steps are stored separately, fetch them if needed
                session_dict = response.data

                # Fetch steps from agent_steps table
                steps_response = self._supabase.table("agent_steps").select("*").eq(
                    "session_id", session_id
                ).order("created_at").execute()

                # Convert steps data to AgentStep objects
                steps = []
                if steps_response.data:
                    for step_data in steps_response.data:
                        steps.append(AgentStep(
                            thought=step_data["thought"],
                            action=step_data.get("action"),
                            observation=step_data.get("observation"),
                            is_final=step_data.get("is_final", False),
                            final_answer=step_data.get("final_answer"),
                        ))

                session_dict["steps"] = steps
                return AgentSession.model_validate(session_dict)

        except Exception:
            # Session not found in Supabase either
            return None

        return None

    async def update_session(self, session: AgentSession) -> None:
        """Update session in Redis and reset TTL.

        Args:
            session: AgentSession to update

        Raises:
            redis.RedisError: If Redis operations fail
        """
        session.updated_at = datetime.now(timezone.utc)
        session_data = session.model_dump_json()
        session_key = self._session_key(session.session_id)

        # Update with fresh TTL
        await self._redis.setex(
            session_key,
            self._session_ttl,
            session_data
        )

    async def add_step(self, session_id: str, step: AgentStep) -> None:
        """Append a step to the session's step list in Redis.

        Args:
            session_id: Unique session identifier
            step: AgentStep to append

        Raises:
            redis.RedisError: If Redis operations fail
        """
        steps_key = self._steps_key(session_id)
        step_data = step.model_dump_json()

        # Append to Redis list
        await self._redis.rpush(steps_key, step_data)

        # Set TTL on steps list (match session TTL)
        await self._redis.expire(steps_key, self._session_ttl)

        # Update step count in session
        session = await self.get_session(session_id)
        if session:
            session.steps.append(step)
            await self.update_session(session)

    async def get_steps(self, session_id: str) -> list[AgentStep]:
        """Get all steps for a session from Redis.

        Args:
            session_id: Unique session identifier

        Returns:
            List of AgentStep objects (may be empty)

        Raises:
            redis.RedisError: If Redis operations fail
        """
        steps_key = self._steps_key(session_id)
        steps_data = await self._redis.lrange(steps_key, 0, -1)

        steps = []
        for step_json in steps_data:
            steps.append(AgentStep.model_validate_json(step_json))

        return steps

    async def update_token_usage(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """Update token usage counters for a session.

        Args:
            session_id: Unique session identifier
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
            cost: Cost in USD to add

        Raises:
            redis.RedisError: If Redis operations fail
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.input_tokens += input_tokens
        session.output_tokens += output_tokens
        session.total_cost_usd += cost

        await self.update_session(session)

    async def persist_to_supabase(self, session: AgentSession) -> None:
        """Persist session and steps to Supabase and remove from Redis.

        This should be called when a session reaches a terminal state:
        - completed
        - failed
        - cancelled

        Args:
            session: AgentSession to persist

        Raises:
            Exception: If Supabase operations fail
            redis.RedisError: If Redis cleanup fails
        """
        # Prepare session data for Supabase (exclude steps - stored separately)
        session_dict = session.model_dump(exclude={"steps"})

        # Insert or update session in Supabase
        self._supabase.table("agent_sessions").upsert(session_dict).execute()

        # Insert steps into agent_steps table
        if session.steps:
            steps_data = []
            for step in session.steps:
                step_dict = step.model_dump()
                step_dict["session_id"] = session.session_id
                steps_data.append(step_dict)

            self._supabase.table("agent_steps").upsert(steps_data).execute()

        # Delete from Redis after successful persist
        session_key = self._session_key(session.session_id)
        steps_key = self._steps_key(session.session_id)

        await self._redis.delete(session_key, steps_key)
