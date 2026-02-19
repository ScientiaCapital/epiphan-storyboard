"""
Provider Adapter Framework

Abstract interface for multiple LLM providers.
Enables unified API across Anthropic, Google Gemini, OpenRouter, and local vLLM.

NOTE: OpenAI is NOT supported in this project. Use Anthropic Claude, Google Gemini, or OpenRouter.
"""

import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore[assignment]

logging.basicConfig(level=logging.INFO)


class ProviderType(Enum):
    """Supported provider types - NO OPENAI, NO GROQ"""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    LOCAL = "local"  # Local vLLM


@dataclass
class ProviderConfig:
    """Configuration for a provider"""

    name: str
    provider_type: ProviderType
    api_key: str | None = None
    base_url: str | None = None
    enabled: bool = True

    # Rate limiting
    max_rpm: int = 0  # 0 = unlimited
    max_tpm: int = 0

    # Timeouts
    timeout_seconds: int = 120

    # Cost tracking
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


@dataclass
class ProviderResponse:
    """Unified response from any provider"""

    content: str
    model: str
    provider: str

    # Usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Cost
    cost_cents: float = 0.0

    # Metadata
    finish_reason: str | None = None
    latency_ms: float = 0.0

    # Raw response for debugging
    raw_response: dict | None = None

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible response format"""
        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.content,
                    },
                    "finish_reason": self.finish_reason or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": self.input_tokens,
                "completion_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
            },
            "provider": self.provider,
            "cost_cents": self.cost_cents,
        }


class ProviderAdapter(ABC):
    """Abstract base class for provider adapters"""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name

        # Statistics
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost_cents = 0.0
        self.total_errors = 0
        self.total_latency_ms = 0.0

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> ProviderResponse:
        """Execute a completion request"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str]:
        """Stream a completion request"""
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models for this provider"""
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in cents"""
        input_cost = (input_tokens / 1000) * self.config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.config.output_cost_per_1k
        return input_cost + output_cost

    def record_request(self, response: ProviderResponse):
        """Record request statistics"""
        self.total_requests += 1
        self.total_tokens += response.total_tokens
        self.total_cost_cents += response.cost_cents
        self.total_latency_ms += response.latency_ms

    def get_stats(self) -> dict[str, Any]:
        """Get provider statistics"""
        return {
            "name": self.name,
            "type": self.config.provider_type.value,
            "enabled": self.config.enabled,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost_cents": round(self.total_cost_cents, 2),
            "total_errors": self.total_errors,
            "avg_latency_ms": round(self.total_latency_ms / self.total_requests, 2)
            if self.total_requests
            else 0,
        }


class AnthropicAdapter(ProviderAdapter):
    """Adapter for Anthropic API"""

    MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.anthropic.com/v1"
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> ProviderResponse:
        start_time = time.time()

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Convert OpenAI format to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
        }
        if system_msg:
            payload["system"] = system_msg
        if temperature != 1.0:
            payload["temperature"] = temperature

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as resp:
                data = await resp.json()

                if resp.status >= 400:
                    self.total_errors += 1
                    raise ProviderError(
                        f"Anthropic error: {data.get('error', {}).get('message', 'Unknown')}"
                    )

        latency_ms = (time.time() - start_time) * 1000

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        response = ProviderResponse(
            content=content,
            model=model,
            provider="anthropic",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=self.calculate_cost(input_tokens, output_tokens),
            finish_reason=data.get("stop_reason"),
            latency_ms=latency_ms,
            raw_response=data,
        )

        self.record_request(response)
        return response

    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str]:
        # Similar to complete but with streaming
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append(msg)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as resp:
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            content = data.get("delta", {}).get("text", "")
                            if content:
                                yield content

    def list_models(self) -> list[str]:
        return self.MODELS


class GoogleAdapter(ProviderAdapter):
    """Adapter for Google Gemini API"""

    MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-2.0-flash-exp",
        "gemini-1.0-pro",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = (
            config.base_url or "https://generativelanguage.googleapis.com/v1beta"
        )
        self.api_key = config.api_key or os.getenv("GOOGLE_API_KEY")

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> ProviderResponse:
        start_time = time.time()

        # Convert messages to Gemini format
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_contents.append(
                    {"role": "user", "parts": [{"text": msg["content"]}]}
                )
            elif msg["role"] == "assistant":
                gemini_contents.append(
                    {"role": "model", "parts": [{"text": msg["content"]}]}
                )

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 4096,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as resp:
                data = await resp.json()

                if resp.status >= 400:
                    self.total_errors += 1
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    raise ProviderError(f"Google Gemini error: {error_msg}")

        latency_ms = (time.time() - start_time) * 1000

        # Parse response
        candidate = data.get("candidates", [{}])[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in content_parts)

        # Get usage metadata
        usage_metadata = data.get("usageMetadata", {})
        input_tokens = usage_metadata.get("promptTokenCount", 0)
        output_tokens = usage_metadata.get("candidatesTokenCount", 0)

        response = ProviderResponse(
            content=content,
            model=model,
            provider="google",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=self.calculate_cost(input_tokens, output_tokens),
            finish_reason=candidate.get("finishReason", "STOP"),
            latency_ms=latency_ms,
            raw_response=data,
        )

        self.record_request(response)
        return response

    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str]:
        # Convert messages to Gemini format
        gemini_contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_contents.append(
                    {"role": "user", "parts": [{"text": msg["content"]}]}
                )
            elif msg["role"] == "assistant":
                gemini_contents.append(
                    {"role": "model", "parts": [{"text": msg["content"]}]}
                )

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 4096,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"{self.base_url}/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            parts = (
                                data.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [])
                            )
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue

    def list_models(self) -> list[str]:
        return self.MODELS


class OpenRouterAdapter(ProviderAdapter):
    """
    Adapter for OpenRouter API.

    OpenRouter provides access to many models including:
    - Chinese LLMs (Qwen, DeepSeek)
    - Meta Llama models
    - Mistral models
    - And many more

    Uses OpenAI-compatible API format.
    """

    MODELS = [
        # Google Gemini via OpenRouter (2025 Latest)
        "google/gemini-2.5-flash",  # Main workhorse + thinking
        "google/gemini-2.5-flash-image-preview",  # NANO BANANA - Image gen
        "google/gemini-2.0-flash-001",  # Stable 2.0
        "google/gemini-2.0-flash-exp:free",  # FREE tier
        "google/gemma-2-27b-it",
        # Chinese LLMs (Best Value)
        "qwen/qwen-2.5-72b-instruct",
        "qwen/qwen-2.5-coder-32b-instruct",
        "deepseek/deepseek-chat",
        "deepseek/deepseek-chat-v3",  # 671B MoE flagship
        "deepseek/deepseek-r1",  # Deep reasoning
        "deepseek/deepseek-coder",
        "moonshotai/kimi-k2",  # 1T MoE coding
        # Meta Llama
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "meta-llama/llama-3.2-90b-vision-instruct",
        # Mistral
        "mistralai/mixtral-8x7b-instruct",
        "mistralai/mistral-large",
    ]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://openrouter.ai/api/v1"
        self.api_key = config.api_key or os.getenv("OPENROUTER_API_KEY")

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> ProviderResponse:
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://www.epiphan.com",
            "X-Title": "Epiphan Storyboard",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as resp:
                data = await resp.json()

                if resp.status >= 400:
                    self.total_errors += 1
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    raise ProviderError(f"OpenRouter error: {error_msg}")

        latency_ms = (time.time() - start_time) * 1000

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        response = ProviderResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider="openrouter",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_cents=self.calculate_cost(input_tokens, output_tokens),
            finish_reason=data["choices"][0].get("finish_reason"),
            latency_ms=latency_ms,
            raw_response=data,
        )

        self.record_request(response)
        return response

    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncGenerator[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://www.epiphan.com",
            "X-Title": "Epiphan Storyboard",
        }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as resp:
                async for line in resp.content:
                    line = line.decode().strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            content = (
                                data["choices"][0].get("delta", {}).get("content", "")
                            )
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    def list_models(self) -> list[str]:
        return self.MODELS


class ProviderError(Exception):
    """Error from a provider"""

    pass


class ProviderManager:
    """
    Manages multiple LLM providers.

    Configure via environment variables (NO OPENAI, NO GROQ):
    - ANTHROPIC_API_KEY: Anthropic Claude API key
    - GOOGLE_API_KEY: Google Gemini API key
    - OPENROUTER_API_KEY: OpenRouter API key
    """

    def __init__(self):
        self._providers: dict[str, ProviderAdapter] = {}
        self._model_to_provider: dict[str, str] = {}
        self._lock = asyncio.Lock()

        # Auto-configure from environment
        self._auto_configure()

        logging.info(f"[PROVIDERS] Initialized {len(self._providers)} providers")

    def _auto_configure(self):
        """Auto-configure providers from environment variables (NO OPENAI)"""

        # Anthropic (Claude)
        if os.getenv("ANTHROPIC_API_KEY"):
            config = ProviderConfig(
                name="anthropic",
                provider_type=ProviderType.ANTHROPIC,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                input_cost_per_1k=0.3,  # Claude 3.5 Sonnet pricing
                output_cost_per_1k=1.5,
            )
            self.register_provider(AnthropicAdapter(config))

        # Google (Gemini)
        if os.getenv("GOOGLE_API_KEY"):
            config = ProviderConfig(
                name="google",
                provider_type=ProviderType.GOOGLE,
                api_key=os.getenv("GOOGLE_API_KEY"),
                input_cost_per_1k=0.075,  # Gemini 1.5 Flash pricing
                output_cost_per_1k=0.30,
            )
            self.register_provider(GoogleAdapter(config))

        # OpenRouter (Chinese LLMs, Llama, Mistral, etc.)
        if os.getenv("OPENROUTER_API_KEY"):
            config = ProviderConfig(
                name="openrouter",
                provider_type=ProviderType.OPENROUTER,
                api_key=os.getenv("OPENROUTER_API_KEY"),
                input_cost_per_1k=0.1,  # Varies by model
                output_cost_per_1k=0.3,
            )
            self.register_provider(OpenRouterAdapter(config))

    def register_provider(self, adapter: ProviderAdapter):
        """Register a provider adapter"""
        self._providers[adapter.name] = adapter

        # Map models to provider
        for model in adapter.list_models():
            self._model_to_provider[model] = adapter.name

        logging.info(
            f"[PROVIDERS] Registered {adapter.name} with {len(adapter.list_models())} models"
        )

    def get_provider_for_model(self, model: str) -> ProviderAdapter | None:
        """Get the provider adapter for a model"""
        provider_name = self._model_to_provider.get(model)
        if provider_name:
            return self._providers.get(provider_name)
        return None

    def get_provider(self, name: str) -> ProviderAdapter | None:
        """Get a provider by name"""
        return self._providers.get(name)

    def list_all_models(self) -> list[dict[str, Any]]:
        """List all available models across providers"""
        models = []
        for provider_name, adapter in self._providers.items():
            for model in adapter.list_models():
                models.append(
                    {
                        "id": model,
                        "provider": provider_name,
                        "input_cost_per_1k": adapter.config.input_cost_per_1k,
                        "output_cost_per_1k": adapter.config.output_cost_per_1k,
                    }
                )
        return models

    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all providers"""
        return {name: adapter.get_stats() for name, adapter in self._providers.items()}

    async def complete(
        self, model: str, messages: list[dict[str, str]], **kwargs
    ) -> ProviderResponse:
        """Route a completion to the appropriate provider"""
        adapter = self.get_provider_for_model(model)
        if not adapter:
            raise ProviderError(f"No provider found for model: {model}")

        return await adapter.complete(messages, model, **kwargs)


# Global provider manager
_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """Get or create the global provider manager"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def handle_providers_stats_request() -> dict[str, Any]:
    """Handle /providers/stats request"""
    manager = get_provider_manager()
    return {
        "providers": manager.get_all_stats(),
        "total_providers": len(manager._providers),
    }


def handle_providers_models_request() -> dict[str, Any]:
    """Handle /providers/models request"""
    manager = get_provider_manager()
    models = manager.list_all_models()
    return {
        "models": models,
        "total_models": len(models),
    }
