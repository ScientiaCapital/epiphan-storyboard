"""Tests for pre-built tool chains.

TDD approach: Write tests FIRST, then implement chains.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.router.schemas import TaskType, ClassificationResult
from src.router.chains import (
    BaseChain,
    StoryboardChain,
    VideoChain,
    ScrapeChain,
    CodeRunChain,
    KnowledgeChain,
    SqlChain,
    ChainRegistry,
)
from src.tools.base import ToolResult


@pytest.fixture
def mock_tool_registry():
    """Create mock ToolRegistry with mock tools."""
    registry = MagicMock()

    # Mock tool that returns success
    mock_tool = AsyncMock()
    mock_tool.run = AsyncMock(return_value=ToolResult(
        tool_name="mock_tool",
        success=True,
        result={"data": "test result"},
        execution_time_ms=100,
    ))

    registry.get = MagicMock(return_value=mock_tool)
    return registry


@pytest.fixture
def mock_tool_registry_with_failure():
    """Create mock ToolRegistry where tools fail."""
    registry = MagicMock()

    mock_tool = AsyncMock()
    mock_tool.run = AsyncMock(return_value=ToolResult(
        tool_name="mock_tool",
        success=False,
        result=None,
        error="Tool execution failed",
        execution_time_ms=50,
    ))

    registry.get = MagicMock(return_value=mock_tool)
    return registry


@pytest.fixture
def classification_storyboard():
    """Classification result for storyboard task."""
    return ClassificationResult(
        task_type=TaskType.STORYBOARD,
        confidence=0.95,
        reasoning="Pattern match for storyboard",
        extracted_params={"input": "def hello(): pass"},
        recommended_model="gemini-1.5-flash",
    )


@pytest.fixture
def classification_scrape():
    """Classification result for scrape task."""
    return ClassificationResult(
        task_type=TaskType.SCRAPE,
        confidence=0.95,
        reasoning="Pattern match for scrape",
        extracted_params={"urls": ["https://example.com"]},
        recommended_model="deepseek/deepseek-chat-v3",
    )


class TestBaseChain:
    """Test BaseChain abstract class."""

    def test_base_chain_is_abstract(self):
        """Verify BaseChain cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseChain(MagicMock())

    def test_chain_has_required_properties(self, mock_tool_registry):
        """Verify chains have required properties."""
        chain = StoryboardChain(mock_tool_registry)

        assert hasattr(chain, "chain_type")
        assert hasattr(chain, "required_tools")
        assert callable(getattr(chain, "execute", None))


class TestStoryboardChain:
    """Test StoryboardChain execution."""

    @pytest.mark.asyncio
    async def test_storyboard_chain_success(
        self, mock_tool_registry, classification_storyboard
    ):
        """Test successful storyboard generation."""
        # Setup mock tool to return storyboard result
        mock_tool = AsyncMock()
        mock_tool.run = AsyncMock(return_value=ToolResult(
            tool_name="unified_storyboard",
            success=True,
            result={
                "storyboard_png": "/tmp/storyboard.png",
                "understanding": {"headline": "Test", "bullet_points": []},
            },
            execution_time_ms=500,
        ))
        mock_tool_registry.get = MagicMock(return_value=mock_tool)

        chain = StoryboardChain(mock_tool_registry)
        result = await chain.execute(
            params={"input": "def hello(): print('world')"},
            classification=classification_storyboard,
        )

        assert result["chain_type"] == "storyboard"
        assert "storyboard_png" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_storyboard_chain_tool_not_found(self, mock_tool_registry):
        """Test error when storyboard tool not found."""
        mock_tool_registry.get = MagicMock(return_value=None)

        chain = StoryboardChain(mock_tool_registry)
        result = await chain.execute(
            params={"input": "code"},
            classification=MagicMock(),
        )

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower() or result.get("error") is not None


class TestScrapeChain:
    """Test ScrapeChain execution."""

    @pytest.mark.asyncio
    async def test_scrape_chain_url_fetch(
        self, mock_tool_registry, classification_scrape
    ):
        """Test scraping a URL."""
        mock_tool = AsyncMock()
        mock_tool.run = AsyncMock(return_value=ToolResult(
            tool_name="web_fetch",
            success=True,
            result={
                "body": "<html><body>Test content</body></html>",
                "status": 200,
                "headers": {"content-type": "text/html"},
            },
            execution_time_ms=200,
        ))
        mock_tool_registry.get = MagicMock(return_value=mock_tool)

        chain = ScrapeChain(mock_tool_registry)
        result = await chain.execute(
            params={"url": "https://example.com"},
            classification=classification_scrape,
        )

        assert result["chain_type"] == "scrape"
        assert result["success"] is True
        assert "content" in result or "body" in result


class TestCodeRunChain:
    """Test CodeRunChain execution."""

    @pytest.mark.asyncio
    async def test_code_run_chain_python(self, mock_tool_registry):
        """Test executing Python code."""
        mock_tool = AsyncMock()
        mock_tool.run = AsyncMock(return_value=ToolResult(
            tool_name="code_run",
            success=True,
            result={
                "stdout": "Hello, World!",
                "stderr": "",
                "exit_code": 0,
            },
            execution_time_ms=1000,
        ))
        mock_tool_registry.get = MagicMock(return_value=mock_tool)

        chain = CodeRunChain(mock_tool_registry)
        result = await chain.execute(
            params={
                "code": "print('Hello, World!')",
                "language": "python",
            },
            classification=MagicMock(task_type=TaskType.CODE_RUN),
        )

        assert result["chain_type"] == "code_run"
        assert result["success"] is True
        assert "stdout" in result


class TestChainErrorHandling:
    """Test chain error handling."""

    @pytest.mark.asyncio
    async def test_chain_handles_tool_failure(
        self, mock_tool_registry_with_failure
    ):
        """Test that chains handle tool failures gracefully."""
        chain = ScrapeChain(mock_tool_registry_with_failure)
        result = await chain.execute(
            params={"url": "https://example.com"},
            classification=MagicMock(task_type=TaskType.SCRAPE),
        )

        assert result["success"] is False
        assert result.get("error") is not None


class TestChainRegistry:
    """Test ChainRegistry for chain management."""

    def test_registry_contains_all_chains(self, mock_tool_registry):
        """Verify registry contains all 6 chain types."""
        registry = ChainRegistry(mock_tool_registry)

        assert registry.get(TaskType.STORYBOARD) is not None
        assert registry.get(TaskType.VIDEO) is not None
        assert registry.get(TaskType.SCRAPE) is not None
        assert registry.get(TaskType.CODE_RUN) is not None
        assert registry.get(TaskType.KNOWLEDGE) is not None
        assert registry.get(TaskType.SQL) is not None

    def test_registry_returns_correct_chain_type(self, mock_tool_registry):
        """Verify registry returns chains matching TaskType."""
        registry = ChainRegistry(mock_tool_registry)

        storyboard_chain = registry.get(TaskType.STORYBOARD)
        assert storyboard_chain.chain_type == TaskType.STORYBOARD

        scrape_chain = registry.get(TaskType.SCRAPE)
        assert scrape_chain.chain_type == TaskType.SCRAPE

    def test_registry_list_chains(self, mock_tool_registry):
        """Test listing all available chains."""
        registry = ChainRegistry(mock_tool_registry)
        chains = registry.list_chains()

        assert len(chains) == 6
        chain_types = [c["chain_type"] for c in chains]
        assert "storyboard" in chain_types
        assert "video" in chain_types
        assert "scrape" in chain_types
        assert "code_run" in chain_types
        assert "knowledge" in chain_types
        assert "sql" in chain_types
