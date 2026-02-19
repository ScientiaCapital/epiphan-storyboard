"""Pre-built tool chains for agent routing.

Each chain orchestrates one or more tools to accomplish a specific task type.
Chains are selected based on TaskClassifier results.

Available chains:
- StoryboardChain: Generate storyboards/infographics from code/images
- VideoChain: Video generation and editing
- ScrapeChain: Web scraping and data extraction
- CodeRunChain: Sandboxed code execution
- KnowledgeChain: Knowledge base / CRM queries
- SqlChain: Database queries
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.router.schemas import ClassificationResult, TaskType
from src.tools.base import ToolResult

if TYPE_CHECKING:
    from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class BaseChain(ABC):
    """Abstract base class for tool chains.

    Subclasses must implement:
    - chain_type: TaskType this chain handles
    - required_tools: List of tool names needed
    - execute: Execute the chain logic
    """

    def __init__(self, tool_registry: ToolRegistry):
        """Initialize chain with tool registry.

        Args:
            tool_registry: Registry to look up tools
        """
        self._registry = tool_registry

    @property
    @abstractmethod
    def chain_type(self) -> TaskType:
        """Task type this chain handles."""
        pass

    @property
    @abstractmethod
    def required_tools(self) -> list[str]:
        """List of required tool names."""
        pass

    @abstractmethod
    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Execute the chain with given parameters.

        Args:
            params: Execution parameters (from classification or user)
            classification: Classification result that triggered this chain

        Returns:
            Dict with chain_type, success, and result data
        """
        pass

    def _get_tool(self, name: str) -> Any | None:
        """Get a tool from the registry."""
        return self._registry.get(name)


class StoryboardChain(BaseChain):
    """Generate storyboards/infographics from code or images.

    Uses: unified_storyboard tool
    Output: PNG storyboard image with understanding
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.STORYBOARD

    @property
    def required_tools(self) -> list[str]:
        return ["unified_storyboard"]

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Generate storyboard from input."""
        tool = self._get_tool("unified_storyboard")

        if not tool:
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": "unified_storyboard tool not found",
            }

        try:
            # Get input from params or classification
            input_data = params.get("input") or classification.extracted_params.get("input")

            result: ToolResult = await tool.run({
                "input": input_data,
                "icp_preset": params.get("icp_preset", "epiphan_av"),
                "stage": params.get("stage", "demo"),
                "audience": params.get("audience", "c_suite"),
                "open_browser": False,  # Never open browser in API
            })

            if not result.success:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": result.error,
                }

            result_data = result.result or {}
            return {
                "chain_type": self.chain_type.value,
                "success": True,
                "storyboard_png": result_data.get("storyboard_png"),
                "understanding": result_data.get("understanding"),
                "execution_time_ms": result.execution_time_ms,
            }

        except Exception as e:
            logger.error(f"StoryboardChain execution failed: {e}")
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": str(e),
            }


class VideoChain(BaseChain):
    """Generate video from scripts or prompts.

    Uses: video_script_generator, video_generator tools
    Output: Video URL
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.VIDEO

    @property
    def required_tools(self) -> list[str]:
        return ["video_script_generator", "video_generator"]

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Generate video from script or prompt."""
        try:
            script = params.get("script")

            # Step 1: Generate script if not provided
            if not script:
                script_tool = self._get_tool("video_script_generator")
                if script_tool:
                    prompt = params.get("prompt", classification.extracted_params.get("prompt", ""))
                    script_result = await script_tool.run({"prompt": prompt})

                    if script_result.success:
                        script = script_result.result.get("script")
                    else:
                        return {
                            "chain_type": self.chain_type.value,
                            "success": False,
                            "error": f"Script generation failed: {script_result.error}",
                        }

            # Step 2: Generate video
            video_tool = self._get_tool("video_generator")
            if not video_tool:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": "video_generator tool not found",
                }

            video_result = await video_tool.run({
                "script": script,
                "provider": params.get("provider", "kling"),
            })

            if not video_result.success:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": video_result.error,
                }

            return {
                "chain_type": self.chain_type.value,
                "success": True,
                "video_url": video_result.result.get("video_url"),
                "script": script,
                "execution_time_ms": video_result.execution_time_ms,
            }

        except Exception as e:
            logger.error(f"VideoChain execution failed: {e}")
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": str(e),
            }


class ScrapeChain(BaseChain):
    """Web scraping and data extraction.

    Uses: web_fetch tool
    Output: HTML content, status, headers
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.SCRAPE

    @property
    def required_tools(self) -> list[str]:
        return ["web_fetch"]

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Scrape content from URL."""
        tool = self._get_tool("web_fetch")

        if not tool:
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": "web_fetch tool not found",
            }

        try:
            # Get URL from params or classification
            url = params.get("url")
            if not url:
                urls = classification.extracted_params.get("urls", [])
                url = urls[0] if urls else None

            if not url:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": "No URL provided",
                }

            result = await tool.run({
                "url": url,
                "method": params.get("method", "GET"),
            })

            if not result.success:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": result.error,
                }

            return {
                "chain_type": self.chain_type.value,
                "success": True,
                "content": result.result.get("body"),
                "status": result.result.get("status"),
                "headers": result.result.get("headers"),
                "execution_time_ms": result.execution_time_ms,
            }

        except Exception as e:
            logger.error(f"ScrapeChain execution failed: {e}")
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": str(e),
            }


class CodeRunChain(BaseChain):
    """Execute code in sandbox.

    Uses: code_run tool
    Output: stdout, stderr, exit_code
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.CODE_RUN

    @property
    def required_tools(self) -> list[str]:
        return ["code_run"]

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Execute code in sandbox."""
        tool = self._get_tool("code_run")

        if not tool:
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": "code_run tool not found",
            }

        try:
            code = params.get("code", classification.extracted_params.get("code", ""))
            language = params.get("language", classification.extracted_params.get("language", "python"))

            result = await tool.run({
                "code": code,
                "language": language,
                "timeout": params.get("timeout", 30),
            })

            if not result.success:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": result.error,
                }

            return {
                "chain_type": self.chain_type.value,
                "success": True,
                "stdout": result.result.get("stdout"),
                "stderr": result.result.get("stderr"),
                "exit_code": result.result.get("exit_code"),
                "execution_time_ms": result.execution_time_ms,
            }

        except Exception as e:
            logger.error(f"CodeRunChain execution failed: {e}")
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": str(e),
            }


class KnowledgeChain(BaseChain):
    """Search knowledge base / CRM queries.

    Uses: knowledge search tools
    Output: Search results, extracted data
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.KNOWLEDGE

    @property
    def required_tools(self) -> list[str]:
        return ["knowledge_search"]  # Placeholder

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Search knowledge base."""
        # Knowledge chain is a placeholder for now
        # In production, would integrate with knowledge module
        return {
            "chain_type": self.chain_type.value,
            "success": True,
            "message": "Knowledge search not yet fully implemented",
            "query": params.get("query", classification.extracted_params.get("query", "")),
            "execution_time_ms": 0,
        }


class SqlChain(BaseChain):
    """Execute SQL queries.

    Uses: sql_query tool
    Output: Query results, columns, row count
    """

    @property
    def chain_type(self) -> TaskType:
        return TaskType.SQL

    @property
    def required_tools(self) -> list[str]:
        return ["sql_query"]

    async def execute(
        self,
        params: dict[str, Any],
        classification: ClassificationResult,
    ) -> dict[str, Any]:
        """Execute SQL query."""
        tool = self._get_tool("sql_query")

        if not tool:
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": "sql_query tool not found",
            }

        try:
            query = params.get("query", classification.extracted_params.get("query", ""))

            result = await tool.run({
                "query": query,
                "params": params.get("params", []),
                "max_rows": params.get("max_rows", 100),
            })

            if not result.success:
                return {
                    "chain_type": self.chain_type.value,
                    "success": False,
                    "error": result.error,
                }

            return {
                "chain_type": self.chain_type.value,
                "success": True,
                "rows": result.result.get("rows"),
                "columns": result.result.get("columns"),
                "row_count": result.result.get("row_count"),
                "execution_time_ms": result.execution_time_ms,
            }

        except Exception as e:
            logger.error(f"SqlChain execution failed: {e}")
            return {
                "chain_type": self.chain_type.value,
                "success": False,
                "error": str(e),
            }


class ChainRegistry:
    """Registry for managing and accessing chains.

    Provides lookup of chains by TaskType.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """Initialize registry with all chains.

        Args:
            tool_registry: ToolRegistry for chains to use
        """
        self._chains: dict[TaskType, BaseChain] = {
            TaskType.STORYBOARD: StoryboardChain(tool_registry),
            TaskType.VIDEO: VideoChain(tool_registry),
            TaskType.SCRAPE: ScrapeChain(tool_registry),
            TaskType.CODE_RUN: CodeRunChain(tool_registry),
            TaskType.KNOWLEDGE: KnowledgeChain(tool_registry),
            TaskType.SQL: SqlChain(tool_registry),
        }

    def get(self, task_type: TaskType) -> BaseChain | None:
        """Get chain by task type.

        Args:
            task_type: TaskType to get chain for

        Returns:
            Chain instance or None if not found
        """
        return self._chains.get(task_type)

    def list_chains(self) -> list[dict[str, Any]]:
        """List all available chains.

        Returns:
            List of chain info dicts with chain_type and required_tools
        """
        return [
            {
                "chain_type": chain.chain_type.value,
                "required_tools": chain.required_tools,
            }
            for chain in self._chains.values()
        ]
