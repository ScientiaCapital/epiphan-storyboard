"""AgentRunner - ReAct execution loop with multi-provider LLM support.

This module implements the core agent execution loop using the ReAct pattern:
- Reasoning: LLM thinks about what to do next
- Acting: Execute tools based on LLM decisions
- Observation: Feed tool results back to LLM

Supports multiple LLM providers:
- Anthropic (Claude) for complex reasoning
- OpenRouter for cost-optimized inference (DeepSeek, Qwen, Mistral)
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from src.agents.schemas import (
    AgentRunRequest,
    AgentSession,
    AgentStep,
    SessionStatus,
    ToolCall,
)
from src.agents.state import StateManager
from src.tools.base import ToolResult
from src.tools.registry import ToolRegistry


# ============================================================================
# Custom Exceptions
# ============================================================================


class ParseError(Exception):
    """Raised when LLM response cannot be parsed."""
    pass


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found in the registry."""
    pass


# ============================================================================
# Model Pricing (USD per 1K tokens)
# ============================================================================

MODEL_PRICING = {
    # Anthropic models
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
    "claude-3-opus-latest": {"input": 0.015, "output": 0.075},
    "claude-3-haiku-latest": {"input": 0.00025, "output": 0.00125},
    # OpenRouter models (DeepSeek, Qwen - MoE architecture, much cheaper)
    "deepseek/deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek/deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "qwen/qwen-2.5-72b-instruct": {"input": 0.00035, "output": 0.0004},
    "qwen/qwen-2.5-coder-32b-instruct": {"input": 0.00018, "output": 0.00018},
    "mistralai/mistral-large-latest": {"input": 0.002, "output": 0.006},
    "google/gemini-2.0-flash-exp:free": {"input": 0.0, "output": 0.0},
}

# OpenRouter model prefixes
OPENROUTER_PREFIXES = [
    "deepseek/",
    "qwen/",
    "mistralai/",
    "google/",
    "meta-llama/",
    "anthropic/",  # Also available via OpenRouter
]


# ============================================================================
# AgentRunner
# ============================================================================


class AgentRunner:
    """Executes ReAct agent loops with multi-provider LLM support.

    Attributes:
        _state_manager: StateManager for session persistence
        _tool_registry: ToolRegistry for tool execution
        _anthropic_client: Anthropic API client (for Claude models)
        _openrouter_client: HTTP client for OpenRouter API
        _default_model: Default model to use
    """

    def __init__(
        self,
        state_manager: StateManager,
        tool_registry: ToolRegistry,
        anthropic_client: Any = None,
        openrouter_client: Any = None,
        default_model: str = "claude-sonnet-4-5-20250929",
    ):
        """Initialize AgentRunner with dependencies.

        Args:
            state_manager: StateManager for session state
            tool_registry: ToolRegistry with available tools
            anthropic_client: Optional Anthropic client (created if not provided)
            openrouter_client: Optional HTTP client for OpenRouter
            default_model: Default model identifier
        """
        self._state_manager = state_manager
        self._tool_registry = tool_registry
        self._anthropic_client = anthropic_client
        self._openrouter_client = openrouter_client
        self._default_model = default_model

    def is_openrouter_model(self, model: str) -> bool:
        """Check if a model should be routed through OpenRouter.

        Args:
            model: Model identifier

        Returns:
            True if model should use OpenRouter, False for Anthropic
        """
        return any(model.startswith(prefix) for prefix in OPENROUTER_PREFIXES)

    def build_system_prompt(
        self,
        tool_names: list[str] | None = None,
        custom_system_prompt: str | None = None,
    ) -> str:
        """Build system prompt with tool descriptions and ReAct format.

        Args:
            tool_names: List of tool names to include (None = all tools)
            custom_system_prompt: Optional custom prompt to prepend

        Returns:
            Complete system prompt string
        """
        # Get tool schemas
        if tool_names:
            tools = self._tool_registry.get_tools_for_llm(tool_names)
        else:
            tools = self._tool_registry.get_tools_for_llm()

        # Build tool descriptions
        tool_descriptions = []
        for tool in tools:
            func = tool["function"]
            tool_descriptions.append(
                f"- {func['name']}: {func['description']}"
            )

        tools_text = "\n".join(tool_descriptions) if tool_descriptions else "No tools available."

        # ReAct format instructions
        react_format = """
You are a helpful AI assistant that can use tools to accomplish tasks.
You must respond in JSON format with the following structure:

For tool calls:
{
    "thought": "Your reasoning about what to do next",
    "action": {
        "tool_name": "name_of_tool",
        "arguments": {"arg1": "value1", ...}
    }
}

For final answers:
{
    "thought": "Your final reasoning",
    "is_final": true,
    "final_answer": "Your answer to the user"
}

IMPORTANT:
- Always include a "thought" field explaining your reasoning
- Use tools when you need external information or actions
- Provide a final answer when you have enough information
- Your response must be valid JSON
"""

        # Combine components
        prompt_parts = []

        if custom_system_prompt:
            prompt_parts.append(custom_system_prompt)

        prompt_parts.append(react_format)
        prompt_parts.append(f"\nAvailable tools:\n{tools_text}")

        return "\n".join(prompt_parts)

    def parse_llm_response(self, response_text: str) -> AgentStep:
        """Parse LLM response text into an AgentStep.

        Args:
            response_text: Raw JSON response from LLM

        Returns:
            Parsed AgentStep

        Raises:
            ParseError: If response is invalid JSON or missing required fields
        """
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON in LLM response: {e}")

        # Validate required fields
        if "thought" not in data:
            raise ParseError("Missing required 'thought' field in LLM response")

        # Build AgentStep
        thought = data["thought"]
        is_final = data.get("is_final", False)
        final_answer = data.get("final_answer")
        action = None

        if "action" in data and data["action"]:
            action_data = data["action"]
            action = ToolCall(
                tool_name=action_data["tool_name"],
                arguments=action_data.get("arguments", {}),
            )

        return AgentStep(
            thought=thought,
            action=action,
            is_final=is_final,
            final_answer=final_answer,
        )

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool from the registry.

        Args:
            tool_call: ToolCall with tool name and arguments

        Returns:
            ToolResult from tool execution

        Raises:
            ToolNotFoundError: If tool is not in registry
        """
        tool = self._tool_registry.get(tool_call.tool_name)
        if tool is None:
            raise ToolNotFoundError(
                f"Tool '{tool_call.tool_name}' not found in registry"
            )

        return await tool.run(tool_call.arguments)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        pricing = MODEL_PRICING.get(model, {"input": 0.003, "output": 0.015})
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    async def _call_anthropic(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str,
    ) -> tuple[str, int, int]:
        """Call Anthropic API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            model: Model identifier

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        response = await self._anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        response_text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return response_text, input_tokens, output_tokens

    async def _call_openrouter(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str,
    ) -> tuple[str, int, int]:
        """Call OpenRouter API.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            model: Model identifier

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        # Prepare messages with system prompt
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self._openrouter_client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": model,
                "messages": full_messages,
                "max_tokens": 4096,
            },
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}",
                "HTTP-Referer": "https://conductor-ai.com",
                "X-Title": "Conductor-AI",
            },
        )

        data = response.json()
        response_text = data["choices"][0]["message"]["content"]
        input_tokens = data["usage"]["prompt_tokens"]
        output_tokens = data["usage"]["completion_tokens"]

        return response_text, input_tokens, output_tokens

    async def _call_llm(
        self,
        messages: list[dict],
        system_prompt: str,
        model: str,
    ) -> tuple[str, int, int]:
        """Route LLM call to appropriate provider.

        Args:
            messages: Conversation messages
            system_prompt: System prompt
            model: Model identifier

        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        if self.is_openrouter_model(model):
            return await self._call_openrouter(messages, system_prompt, model)
        else:
            return await self._call_anthropic(messages, system_prompt, model)

    async def run(
        self,
        request: AgentRunRequest,
        org_id: str,
    ) -> AgentSession:
        """Execute the ReAct loop for an agent request.

        Args:
            request: AgentRunRequest with messages and configuration
            org_id: Organization identifier

        Returns:
            Completed AgentSession with all steps and results
        """
        model = request.model or self._default_model

        # Create session
        session = await self._state_manager.create_session(
            org_id=org_id,
            model=model,
        )
        session.status = SessionStatus.RUNNING
        await self._state_manager.update_session(session)

        # Build system prompt
        system_prompt = self.build_system_prompt(tool_names=request.tools)

        # Initialize conversation
        conversation = list(request.messages)

        try:
            for step_num in range(request.max_steps):
                # Check if session was cancelled
                current_session = await self._state_manager.get_session(session.session_id)
                if current_session and current_session.status == SessionStatus.CANCELLED:
                    session.status = SessionStatus.CANCELLED
                    await self._state_manager.update_session(session)
                    await self._state_manager.persist_to_supabase(session)
                    return session

                # Call LLM
                response_text, input_tokens, output_tokens = await self._call_llm(
                    messages=conversation,
                    system_prompt=system_prompt,
                    model=model,
                )

                # Track token usage
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                session.input_tokens += input_tokens
                session.output_tokens += output_tokens
                session.total_cost_usd += cost

                # Parse response
                step = self.parse_llm_response(response_text)

                # Execute tool if action present
                if step.action:
                    result = await self.execute_tool(step.action)
                    step.observation = result.result if result.success else f"Error: {result.error}"

                    # Add assistant message and tool result to conversation
                    conversation.append({
                        "role": "assistant",
                        "content": response_text,
                    })
                    conversation.append({
                        "role": "user",
                        "content": f"Tool result: {step.observation}",
                    })

                # Record step
                session.steps.append(step)
                await self._state_manager.add_step(session.session_id, step)

                # Check if final answer
                if step.is_final:
                    break

            # Mark completed
            session.status = SessionStatus.COMPLETED
            await self._state_manager.update_session(session)
            await self._state_manager.persist_to_supabase(session)

        except Exception as e:
            # Mark failed
            session.status = SessionStatus.FAILED
            await self._state_manager.update_session(session)
            await self._state_manager.persist_to_supabase(session)

        return session
