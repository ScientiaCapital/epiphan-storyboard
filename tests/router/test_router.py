"""Tests for AgentRouter - routing logic.

TDD approach: Write tests FIRST, then implement router.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.router.schemas import (
    TaskType,
    ClassificationResult,
    RouterRequest,
    RouterJob,
    RouterJobStatus,
)
from src.router.router import AgentRouter


@pytest.fixture
def mock_classifier():
    """Create mock TaskClassifier."""
    classifier = AsyncMock()
    classifier.classify = AsyncMock(return_value=ClassificationResult(
        task_type=TaskType.SCRAPE,
        confidence=0.95,
        reasoning="Pattern match for scrape",
        extracted_params={"urls": ["https://example.com"]},
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
        "content": "test content",
    })
    mock_chain.chain_type = TaskType.SCRAPE

    registry.get = MagicMock(return_value=mock_chain)
    return registry


@pytest.fixture
def mock_job_manager():
    """Create mock RouterJobManager."""
    manager = AsyncMock()
    manager.create_job = AsyncMock(return_value=RouterJob(
        job_id="test-job-123",
        org_id="test-org",
        query="scrape https://example.com",
        status=RouterJobStatus.PENDING,
    ))
    manager.get_job = AsyncMock()
    manager.update_job = AsyncMock()
    manager.persist_to_supabase = AsyncMock()
    return manager


@pytest.fixture
def router(mock_classifier, mock_chain_registry, mock_job_manager):
    """Create AgentRouter with mocked dependencies."""
    return AgentRouter(
        classifier=mock_classifier,
        chain_registry=mock_chain_registry,
        job_manager=mock_job_manager,
    )


class TestRouterSelection:
    """Test router chain selection logic."""

    @pytest.mark.asyncio
    async def test_router_selects_correct_chain(self, router, mock_classifier):
        """Test that router selects chain based on classification."""
        request = RouterRequest(
            query="scrape https://example.com",
        )

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        # Verify classifier was called
        mock_classifier.classify.assert_called_once()

        # Verify result contains chain info
        assert result.classification is not None
        assert result.classification.task_type == TaskType.SCRAPE

    @pytest.mark.asyncio
    async def test_router_respects_force_chain(self, router, mock_classifier, mock_chain_registry):
        """Test that force_chain bypasses classification."""
        # Set up chain for forced type
        mock_chain = AsyncMock()
        mock_chain.execute = AsyncMock(return_value={
            "chain_type": "storyboard",
            "success": True,
        })
        mock_chain.chain_type = TaskType.STORYBOARD
        mock_chain_registry.get = MagicMock(return_value=mock_chain)

        request = RouterRequest(
            query="do something",
            force_chain=TaskType.STORYBOARD,
        )

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        # Classifier should NOT be called when force_chain is set
        mock_classifier.classify.assert_not_called()

        # Chain should be the forced type
        assert result.classification.task_type == TaskType.STORYBOARD

    @pytest.mark.asyncio
    async def test_router_handles_unknown_chain(self, router, mock_chain_registry):
        """Test router handles case when chain not found."""
        mock_chain_registry.get = MagicMock(return_value=None)

        request = RouterRequest(query="unknown task type")

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        assert result.status == RouterJobStatus.FAILED
        assert result.error_message is not None


class TestRouterConfidence:
    """Test router confidence handling."""

    @pytest.mark.asyncio
    async def test_router_low_confidence_still_executes(
        self, router, mock_classifier
    ):
        """Test that low confidence classifications still execute."""
        mock_classifier.classify = AsyncMock(return_value=ClassificationResult(
            task_type=TaskType.KNOWLEDGE,
            confidence=0.4,  # Low confidence
            reasoning="Fallback classification",
            extracted_params={},
            recommended_model="deepseek/deepseek-chat-v3",
        ))

        request = RouterRequest(query="vague request")

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        # Should still execute even with low confidence
        assert result.classification is not None
        assert result.classification.confidence == 0.4


class TestRouterExecution:
    """Test router execution flow."""

    @pytest.mark.asyncio
    async def test_router_returns_chain_result(
        self, router, mock_chain_registry
    ):
        """Test that router returns chain execution result."""
        mock_chain = AsyncMock()
        mock_chain.execute = AsyncMock(return_value={
            "chain_type": "scrape",
            "success": True,
            "content": "scraped content",
            "status": 200,
        })
        mock_chain.chain_type = TaskType.SCRAPE
        mock_chain_registry.get = MagicMock(return_value=mock_chain)

        request = RouterRequest(query="scrape https://example.com")

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        assert result.chain_result is not None
        assert result.chain_result["success"] is True
        assert "content" in result.chain_result

    @pytest.mark.asyncio
    async def test_router_handles_chain_failure(
        self, router, mock_chain_registry
    ):
        """Test router handles chain execution failure."""
        mock_chain = AsyncMock()
        mock_chain.execute = AsyncMock(return_value={
            "chain_type": "scrape",
            "success": False,
            "error": "Connection timeout",
        })
        mock_chain.chain_type = TaskType.SCRAPE
        mock_chain_registry.get = MagicMock(return_value=mock_chain)

        request = RouterRequest(query="scrape https://example.com")

        result = await router.route_and_execute(
            request=request,
            org_id="test-org",
        )

        # Chain failure should be reflected in result
        assert result.chain_result["success"] is False
        assert "error" in result.chain_result
