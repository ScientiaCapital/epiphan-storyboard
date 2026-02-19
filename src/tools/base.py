"""Base classes for tool infrastructure in the agent orchestration system."""

from abc import ABC, abstractmethod
from enum import Enum
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categories for organizing tools by functionality."""

    WEB = "web"
    DATA = "data"
    CODE = "code"
    FILE = "file"
    SYSTEM = "system"


class ToolDefinition(BaseModel):
    """
    Definition of a tool that can be used by agents.

    Attributes:
        name: Unique identifier for the tool (e.g., "web_fetch", "sql_query")
        description: Human-readable description of what the tool does (used by LLM)
        parameters: JSON Schema definition of the tool's input parameters
        category: Category this tool belongs to
        requires_approval: Whether this tool requires user approval before execution
    """

    name: str = Field(..., description="Unique identifier for the tool")
    description: str = Field(..., description="What the tool does (for LLM)")
    parameters: dict = Field(
        default_factory=dict,
        description="JSON Schema for tool arguments",
    )
    category: ToolCategory = Field(..., description="Tool category")
    requires_approval: bool = Field(
        default=False,
        description="Whether execution requires user approval",
    )


class ToolResult(BaseModel):
    """
    Result from executing a tool.

    Attributes:
        tool_name: Name of the tool that was executed
        success: Whether the tool execution succeeded
        result: The output data if success=True, None otherwise
        error: Error message if success=False, None otherwise
        execution_time_ms: Time taken to execute the tool in milliseconds
    """

    tool_name: str = Field(..., description="Name of executed tool")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Any | None = Field(
        default=None,
        description="Output data if successful",
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )
    execution_time_ms: int = Field(
        ...,
        ge=0,
        description="Execution time in milliseconds",
    )


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Subclasses must implement:
    - definition property: Returns the ToolDefinition for this tool
    - run method: Executes the tool with given arguments

    The get_llm_schema method is provided to convert the tool definition
    to OpenAI/Anthropic-compatible function calling format.
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Get the definition for this tool.

        Returns:
            ToolDefinition describing this tool's interface
        """
        pass

    @abstractmethod
    async def run(self, arguments: dict) -> ToolResult:
        """
        Execute the tool with the given arguments.

        Args:
            arguments: Dictionary of input parameters matching the tool's schema

        Returns:
            ToolResult containing the execution outcome

        Raises:
            Exception: Any exception during execution should be caught and
                      returned as a failed ToolResult
        """
        pass

    def get_llm_schema(self) -> dict:
        """
        Get OpenAI/Anthropic-compatible function calling schema for this tool.

        Returns:
            Dictionary in the format:
            {
                "type": "function",
                "function": {
                    "name": "tool_name",
                    "description": "What it does",
                    "parameters": { ... JSON Schema ... }
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": self.definition.name,
                "description": self.definition.description,
                "parameters": self.definition.parameters,
            },
        }

    async def _execute_with_timing(self, arguments: dict) -> ToolResult:
        """
        Internal helper to execute tool and measure execution time.

        Args:
            arguments: Tool arguments

        Returns:
            ToolResult with execution time recorded
        """
        start_time = perf_counter()
        try:
            result = await self.run(arguments)
            end_time = perf_counter()
            execution_time_ms = int((end_time - start_time) * 1000)
            # Update the execution time in the result
            result.execution_time_ms = execution_time_ms
            return result
        except Exception as e:
            end_time = perf_counter()
            execution_time_ms = int((end_time - start_time) * 1000)
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
