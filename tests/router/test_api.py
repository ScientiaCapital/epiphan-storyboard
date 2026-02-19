"""Tests for Agent Router API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from src.router.schemas import (
    TaskType,
    ClassificationResult,
    RouterJob,
    RouterJobStatus,
)


@pytest.fixture
def mock_job_manager():
    """Create mock RouterJobManager."""
    manager = AsyncMock()
    return manager


@pytest.fixture
def mock_classifier():
    """Create mock TaskClassifier."""
    classifier = AsyncMock()
    classifier.classify = AsyncMock(return_value=ClassificationResult(
        task_type=TaskType.SCRAPE,
        confidence=0.95,
        reasoning="Pattern match",
        extracted_params={},
        recommended_model="deepseek/deepseek-chat-v3",
    ))
    return classifier


@pytest.fixture
def mock_chain_registry():
    """Create mock ChainRegistry."""
    registry = MagicMock()
    mock_chain = AsyncMock()
    mock_chain.execute = AsyncMock(return_value={
        "chain_type": "scrape",
        "success": True,
        "content": "test",
    })
    registry.get = MagicMock(return_value=mock_chain)
    registry.list_chains = MagicMock(return_value=[
        {"chain_type": "storyboard", "required_tools": ["unified_storyboard"]},
        {"chain_type": "scrape", "required_tools": ["web_fetch"]},
    ])
    return registry


class TestPostAgentsRoute:
    """Test POST /agents/route endpoint."""

    @pytest.mark.asyncio
    async def test_post_agents_route_success(
        self, mock_job_manager, mock_classifier, mock_chain_registry
    ):
        """Test successful task routing (202 Accepted)."""
        mock_job = RouterJob(
            job_id="test-job-123",
            org_id="test-org",
            query="scrape https://example.com",
            status=RouterJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        mock_job_manager.create_job = AsyncMock(return_value=mock_job)

        from src.router.api import router, get_job_manager, get_classifier, get_chain_registry
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        app.dependency_overrides[get_job_manager] = lambda: mock_job_manager
        app.dependency_overrides[get_classifier] = lambda: mock_classifier
        app.dependency_overrides[get_chain_registry] = lambda: mock_chain_registry

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/agents/route",
                json={"query": "scrape https://example.com"},
                headers={"X-Org-ID": "test-org"},
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "/agents/route/" in data["poll_url"]

    @pytest.mark.asyncio
    async def test_post_agents_route_empty_query(self):
        """Test routing with empty query returns 422."""
        from src.router.api import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/agents/route",
                json={"query": ""},
                headers={"X-Org-ID": "test-org"},
            )

            assert response.status_code == 422  # Validation error


class TestGetAgentsRouteJob:
    """Test GET /agents/route/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_job_status_pending(self, mock_job_manager):
        """Test getting pending job status."""
        mock_job = RouterJob(
            job_id="test-job-123",
            org_id="test-org",
            query="test query",
            status=RouterJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        mock_job_manager.get_job = AsyncMock(return_value=mock_job)

        from src.router.api import router, get_job_manager
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_job_manager] = lambda: mock_job_manager

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/agents/route/test-job-123",
                headers={"X-Org-ID": "test-org"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-123"
            assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_job_status_completed(self, mock_job_manager):
        """Test getting completed job with results."""
        classification = ClassificationResult(
            task_type=TaskType.SCRAPE,
            confidence=0.95,
            reasoning="Pattern match",
            extracted_params={},
            recommended_model="deepseek/deepseek-chat-v3",
        )

        mock_job = RouterJob(
            job_id="test-job-123",
            org_id="test-org",
            query="scrape example.com",
            status=RouterJobStatus.COMPLETED,
            classification=classification,
            chain_result={"success": True, "content": "data"},
            execution_time_ms=500,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        mock_job_manager.get_job = AsyncMock(return_value=mock_job)

        from src.router.api import router, get_job_manager
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_job_manager] = lambda: mock_job_manager

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/agents/route/test-job-123",
                headers={"X-Org-ID": "test-org"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["task_type"] == "scrape"
            assert data["chain_result"]["success"] is True

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_job_manager):
        """Test getting non-existent job returns 404."""
        mock_job_manager.get_job = AsyncMock(return_value=None)

        from src.router.api import router, get_job_manager
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_job_manager] = lambda: mock_job_manager

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/agents/route/nonexistent",
                headers={"X-Org-ID": "test-org"},
            )

            assert response.status_code == 404


class TestGetAgentsRouteChains:
    """Test GET /agents/route/chains endpoint."""

    @pytest.mark.asyncio
    async def test_list_chains(self, mock_chain_registry):
        """Test listing available chains."""
        from src.router.api import router, get_chain_registry
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_chain_registry] = lambda: mock_chain_registry

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/agents/route/chains")

            assert response.status_code == 200
            data = response.json()
            assert "chains" in data
            assert len(data["chains"]) >= 2
