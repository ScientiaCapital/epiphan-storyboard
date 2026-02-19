"""
Model Catalog Module

Unified catalog of all available models across providers.
Provides OpenAI-compatible /v1/models endpoint.

NOTE: NO OpenAI or Groq. Uses Anthropic, Google Gemini, OpenRouter only.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO)


@dataclass
class ModelInfo:
    """Information about a model"""

    id: str
    provider: str
    owned_by: str

    # Capabilities
    context_window: int = 4096
    max_output_tokens: int = 4096
    supports_vision: bool = False
    supports_functions: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False

    # Pricing (per 1M tokens)
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0

    # Quality indicators
    quality_tier: str = "standard"  # budget, standard, premium, flagship
    best_for: list[str] = field(default_factory=list)

    # Availability
    available: bool = True
    deprecated: bool = False
    deprecation_date: str | None = None

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI /v1/models format"""
        return {
            "id": self.id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": self.owned_by,
            "permission": [],
            "root": self.id,
            "parent": None,
            # Extended fields
            "provider": self.provider,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "capabilities": {
                "vision": self.supports_vision,
                "function_calling": self.supports_functions,
                "streaming": self.supports_streaming,
                "json_mode": self.supports_json_mode,
            },
            "pricing": {
                "input_per_million": self.input_price_per_million,
                "output_per_million": self.output_price_per_million,
            },
            "quality_tier": self.quality_tier,
            "best_for": self.best_for,
        }


class ModelCatalog:
    """
    Unified catalog of all available models.

    Configure via environment variables:
    - CATALOG_INCLUDE_PRICING: Include pricing info (default: true)
    - CATALOG_INCLUDE_LOCAL: Include local vLLM models (default: true)
    """

    def __init__(self):
        self.include_pricing = (
            os.getenv("CATALOG_INCLUDE_PRICING", "true").lower() == "true"
        )
        self.include_local = (
            os.getenv("CATALOG_INCLUDE_LOCAL", "true").lower() == "true"
        )

        self._models: dict[str, ModelInfo] = {}
        self._load_models()

        logging.info(f"[CATALOG] Loaded {len(self._models)} models")

    def _load_models(self):
        """Load all model definitions (NO OpenAI)"""

        # =============================================
        # Anthropic Models (Primary Provider)
        # =============================================

        # Claude 4.5 (Latest - Primary for Agents)
        self._add_model(
            ModelInfo(
                id="claude-opus-4-5-20251101",
                provider="anthropic",
                owned_by="anthropic",
                context_window=200000,
                max_output_tokens=32000,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=15.00,
                output_price_per_million=75.00,
                quality_tier="flagship",
                best_for=["agents", "complex-reasoning", "research", "coding"],
            )
        )

        self._add_model(
            ModelInfo(
                id="claude-sonnet-4-5-20250929",
                provider="anthropic",
                owned_by="anthropic",
                context_window=200000,
                max_output_tokens=16000,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=3.00,
                output_price_per_million=15.00,
                quality_tier="flagship",
                best_for=["agents", "coding", "analysis", "tool-use"],
            )
        )

        # Claude 3.5 (Still excellent)
        self._add_model(
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                provider="anthropic",
                owned_by="anthropic",
                context_window=200000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                input_price_per_million=3.00,
                output_price_per_million=15.00,
                quality_tier="premium",
                best_for=["coding", "analysis", "writing", "vision"],
            )
        )

        self._add_model(
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                provider="anthropic",
                owned_by="anthropic",
                context_window=200000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                input_price_per_million=0.25,
                output_price_per_million=1.25,
                quality_tier="standard",
                best_for=["fast", "cost-effective", "simple-tasks"],
            )
        )

        # =============================================
        # Google Gemini Models
        # =============================================
        self._add_model(
            ModelInfo(
                id="gemini-1.5-pro",
                provider="google",
                owned_by="google",
                context_window=2000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=1.25,
                output_price_per_million=5.00,
                quality_tier="flagship",
                best_for=["long-context", "analysis", "vision", "coding"],
            )
        )

        self._add_model(
            ModelInfo(
                id="gemini-1.5-flash",
                provider="google",
                owned_by="google",
                context_window=1000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.075,
                output_price_per_million=0.30,
                quality_tier="standard",
                best_for=["fast", "cost-effective", "general"],
            )
        )

        self._add_model(
            ModelInfo(
                id="gemini-1.5-flash-8b",
                provider="google",
                owned_by="google",
                context_window=1000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                input_price_per_million=0.0375,
                output_price_per_million=0.15,
                quality_tier="budget",
                best_for=["ultra-fast", "simple-tasks", "high-volume"],
            )
        )

        self._add_model(
            ModelInfo(
                id="gemini-2.0-flash-exp",
                provider="google",
                owned_by="google",
                context_window=1000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.0,  # Free during preview
                output_price_per_million=0.0,
                quality_tier="premium",
                best_for=["experimental", "agents", "multimodal"],
            )
        )

        # =============================================
        # Gemini 2.5 via OpenRouter (2025 Latest)
        # =============================================

        # Gemini 2.5 Flash - Main workhorse with thinking
        self._add_model(
            ModelInfo(
                id="google/gemini-2.5-flash",
                provider="openrouter",
                owned_by="google",
                context_window=1048576,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.30,
                output_price_per_million=2.50,
                quality_tier="flagship",
                best_for=["reasoning", "coding", "math", "thinking", "agents"],
            )
        )

        # Gemini 2.5 Flash Image Preview (NANO BANANA) - Image generation
        self._add_model(
            ModelInfo(
                id="google/gemini-2.5-flash-image-preview",
                provider="openrouter",
                owned_by="google",
                context_window=1048576,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.30,
                output_price_per_million=2.50,
                quality_tier="flagship",
                best_for=["image-generation", "storyboard", "visual", "design"],
            )
        )

        # Gemini 2.0 Flash via OpenRouter (stable)
        self._add_model(
            ModelInfo(
                id="google/gemini-2.0-flash-001",
                provider="openrouter",
                owned_by="google",
                context_window=1000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.10,
                output_price_per_million=0.40,
                quality_tier="standard",
                best_for=["fast", "multimodal", "agents"],
            )
        )

        # Gemini 2.0 Flash FREE via OpenRouter
        self._add_model(
            ModelInfo(
                id="google/gemini-2.0-flash-exp:free",
                provider="openrouter",
                owned_by="google",
                context_window=1000000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_functions=True,
                input_price_per_million=0.0,
                output_price_per_million=0.0,
                quality_tier="budget",
                best_for=["free", "experimental", "testing", "prototyping"],
            )
        )

        # =============================================
        # OpenRouter Models - Chinese LLMs (2025 BEST-IN-CLASS)
        # =============================================

        # ----- DeepSeek Models (Best Value + Reasoning) -----

        # DeepSeek V3.1 - 671B MoE (37B active) - BEST VALUE FLAGSHIP
        # 97.3% MATH-500, 79.8% AIME 2024 - Trained for $5.6M
        self._add_model(
            ModelInfo(
                id="deepseek/deepseek-chat-v3",
                provider="openrouter",
                owned_by="deepseek",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.20,
                output_price_per_million=0.80,
                quality_tier="flagship",
                best_for=[
                    "reasoning",
                    "math",
                    "coding",
                    "agents",
                    "chinese",
                    "cost-effective",
                ],
            )
        )

        # DeepSeek R1 (Full) - o1-COMPETITOR for deep reasoning
        # Open-sourced reasoning tokens, 671B params
        self._add_model(
            ModelInfo(
                id="deepseek/deepseek-r1",
                provider="openrouter",
                owned_by="deepseek",
                context_window=164000,
                max_output_tokens=32000,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=3.00,
                output_price_per_million=7.00,
                quality_tier="flagship",
                best_for=[
                    "deep-reasoning",
                    "math",
                    "complex-analysis",
                    "research",
                    "chain-of-thought",
                ],
            )
        )

        # DeepSeek R1 Distilled (Qwen3-8B) - Budget reasoning
        self._add_model(
            ModelInfo(
                id="deepseek/deepseek-r1-distill-qwen-8b",
                provider="openrouter",
                owned_by="deepseek",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=0.02,
                output_price_per_million=0.10,
                quality_tier="budget",
                best_for=["reasoning", "fast", "cost-effective", "simple-tasks"],
            )
        )

        # DeepSeek Coder V2 - Coding specialist
        self._add_model(
            ModelInfo(
                id="deepseek/deepseek-coder",
                provider="openrouter",
                owned_by="deepseek",
                context_window=128000,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=0.14,
                output_price_per_million=0.28,
                quality_tier="premium",
                best_for=["coding", "debugging", "code-generation", "code-review"],
            )
        )

        # ----- Qwen3 Models (Alibaba - Hybrid Thinking) -----

        # Qwen3-235B-A22B - 235B MoE (22B active) - Dual mode
        # Supports "Thinking Mode" (complex) + "Non-Thinking Mode" (fast)
        # Trained on 36T tokens, 119 languages
        self._add_model(
            ModelInfo(
                id="qwen/qwen3-235b-a22b",
                provider="openrouter",
                owned_by="alibaba",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.30,
                output_price_per_million=1.20,
                quality_tier="flagship",
                best_for=[
                    "reasoning",
                    "coding",
                    "multilingual",
                    "chinese",
                    "hybrid-thinking",
                ],
            )
        )

        # Qwen 2.5-Max - Arena-Hard leader (89.4)
        self._add_model(
            ModelInfo(
                id="qwen/qwen-2.5-72b-instruct",
                provider="openrouter",
                owned_by="alibaba",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.35,
                output_price_per_million=0.40,
                quality_tier="flagship",
                best_for=["coding", "reasoning", "multilingual", "chinese", "tool-use"],
            )
        )

        # Qwen 2.5 Coder 32B - 92.7% HumanEval
        self._add_model(
            ModelInfo(
                id="qwen/qwen-2.5-coder-32b-instruct",
                provider="openrouter",
                owned_by="alibaba",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=0.18,
                output_price_per_million=0.18,
                quality_tier="premium",
                best_for=["coding", "debugging", "code-review", "refactoring"],
            )
        )

        # Qwen3-8B - Fast + potentially FREE tier
        self._add_model(
            ModelInfo(
                id="qwen/qwen3-8b",
                provider="openrouter",
                owned_by="alibaba",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=0.06,
                output_price_per_million=0.18,
                quality_tier="budget",
                best_for=["fast", "cost-effective", "simple-tasks", "chinese"],
            )
        )

        # ----- Moonshot AI (Kimi) -----

        # Kimi K2 - 1T MoE (32B active) - State-of-the-art coding
        self._add_model(
            ModelInfo(
                id="moonshotai/kimi-k2",
                provider="openrouter",
                owned_by="moonshot",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.15,
                output_price_per_million=0.60,
                quality_tier="flagship",
                best_for=["coding", "reasoning", "agents", "chinese", "tool-use"],
            )
        )

        # ----- Zhipu AI (GLM) -----

        # GLM-4.5 - Top open-source, strong tool-calling
        self._add_model(
            ModelInfo(
                id="zhipu/glm-4.5",
                provider="openrouter",
                owned_by="zhipu",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                supports_json_mode=True,
                input_price_per_million=0.20,
                output_price_per_million=0.80,
                quality_tier="premium",
                best_for=["tool-use", "chinese", "reasoning", "agents"],
            )
        )

        self._add_model(
            ModelInfo(
                id="meta-llama/llama-3.1-70b-instruct",
                provider="openrouter",
                owned_by="meta",
                context_window=131072,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=0.52,
                output_price_per_million=0.75,
                quality_tier="premium",
                best_for=["general", "reasoning", "open-source"],
            )
        )

        self._add_model(
            ModelInfo(
                id="meta-llama/llama-3.1-8b-instruct",
                provider="openrouter",
                owned_by="meta",
                context_window=131072,
                max_output_tokens=8192,
                input_price_per_million=0.055,
                output_price_per_million=0.055,
                quality_tier="budget",
                best_for=["fast", "simple-tasks", "open-source"],
            )
        )

        self._add_model(
            ModelInfo(
                id="mistralai/mistral-large",
                provider="openrouter",
                owned_by="mistral",
                context_window=128000,
                max_output_tokens=8192,
                supports_functions=True,
                input_price_per_million=2.00,
                output_price_per_million=6.00,
                quality_tier="flagship",
                best_for=["reasoning", "multilingual", "coding"],
            )
        )

        self._add_model(
            ModelInfo(
                id="mistralai/mixtral-8x7b-instruct",
                provider="openrouter",
                owned_by="mistral",
                context_window=32768,
                max_output_tokens=8192,
                input_price_per_million=0.24,
                output_price_per_million=0.24,
                quality_tier="standard",
                best_for=["fast", "multilingual", "coding"],
            )
        )

    def _add_model(self, model: ModelInfo):
        """Add a model to the catalog"""
        self._models[model.id] = model

    def add_local_model(self, model_id: str, context_window: int = 4096):
        """Add a local vLLM model to the catalog"""
        if not self.include_local:
            return

        self._models[model_id] = ModelInfo(
            id=model_id,
            provider="local",
            owned_by="local",
            context_window=context_window,
            max_output_tokens=context_window,
            supports_streaming=True,
            input_price_per_million=0.0,  # Self-hosted
            output_price_per_million=0.0,
            quality_tier="standard",
            best_for=["self-hosted", "privacy", "custom"],
        )

    def get_model(self, model_id: str) -> ModelInfo | None:
        """Get a specific model"""
        return self._models.get(model_id)

    def list_models(
        self,
        provider: str | None = None,
        quality_tier: str | None = None,
        supports_vision: bool | None = None,
        max_price: float | None = None,
    ) -> list[ModelInfo]:
        """List models with optional filtering"""
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if quality_tier:
            models = [m for m in models if m.quality_tier == quality_tier]

        if supports_vision is not None:
            models = [m for m in models if m.supports_vision == supports_vision]

        if max_price is not None:
            models = [m for m in models if m.input_price_per_million <= max_price]

        return models

    def get_openai_models_response(self) -> dict[str, Any]:
        """Get response in OpenAI /v1/models format"""
        models = [m.to_openai_format() for m in self._models.values()]

        return {
            "object": "list",
            "data": models,
        }

    def compare_models(self, model_ids: list[str]) -> dict[str, Any]:
        """Compare multiple models"""
        comparison = []

        for model_id in model_ids:
            model = self._models.get(model_id)
            if model:
                comparison.append(
                    {
                        "id": model.id,
                        "provider": model.provider,
                        "context_window": model.context_window,
                        "input_price": model.input_price_per_million,
                        "output_price": model.output_price_per_million,
                        "quality_tier": model.quality_tier,
                        "supports_vision": model.supports_vision,
                        "supports_functions": model.supports_functions,
                    }
                )

        return {
            "models": comparison,
            "count": len(comparison),
        }

    def recommend_for_task(self, task_type: str) -> list[ModelInfo]:
        """Recommend models for a specific task type"""
        recommendations = []

        for model in self._models.values():
            if task_type.lower() in [t.lower() for t in model.best_for]:
                recommendations.append(model)

        # Sort by quality tier
        tier_order = {"flagship": 0, "premium": 1, "standard": 2, "budget": 3}
        recommendations.sort(key=lambda m: tier_order.get(m.quality_tier, 99))

        return recommendations


# Global catalog
_catalog: ModelCatalog | None = None


def get_model_catalog() -> ModelCatalog:
    """Get or create the global model catalog"""
    global _catalog
    if _catalog is None:
        _catalog = ModelCatalog()
    return _catalog


def handle_models_list_request(
    provider: str | None = None, quality_tier: str | None = None
) -> dict[str, Any]:
    """Handle /v1/models request"""
    catalog = get_model_catalog()

    if provider or quality_tier:
        models = catalog.list_models(provider=provider, quality_tier=quality_tier)
        return {
            "object": "list",
            "data": [m.to_openai_format() for m in models],
        }

    return catalog.get_openai_models_response()


def handle_models_retrieve_request(model_id: str) -> dict[str, Any]:
    """Handle /v1/models/{model} request"""
    catalog = get_model_catalog()
    model = catalog.get_model(model_id)

    if model:
        return model.to_openai_format()
    else:
        return {"error": "model_not_found", "model": model_id}


def handle_models_compare_request(model_ids: list[str]) -> dict[str, Any]:
    """Handle /models/compare request"""
    catalog = get_model_catalog()
    return catalog.compare_models(model_ids)


def handle_models_recommend_request(task_type: str) -> dict[str, Any]:
    """Handle /models/recommend request"""
    catalog = get_model_catalog()
    models = catalog.recommend_for_task(task_type)
    return {
        "task_type": task_type,
        "recommendations": [m.to_openai_format() for m in models[:5]],
        "count": len(models),
    }


# =============================================
# Smart Model Selector (Black Box Selection)
# =============================================

# Task-to-model mappings for automatic selection
TASK_MODEL_MAP = {
    # Coding tasks - Use specialized coders
    "coding": "qwen/qwen-2.5-coder-32b-instruct",
    "code": "qwen/qwen-2.5-coder-32b-instruct",
    "debug": "deepseek/deepseek-coder",
    "refactor": "qwen/qwen-2.5-coder-32b-instruct",
    # Deep reasoning - Use reasoning specialists
    "reasoning": "deepseek/deepseek-r1",
    "math": "deepseek/deepseek-r1",
    "analysis": "deepseek/deepseek-chat-v3",
    "research": "deepseek/deepseek-r1",
    # Agents / tool-use - Optimized for function calling
    "agent": "deepseek/deepseek-chat-v3",
    "agents": "deepseek/deepseek-chat-v3",
    "tool-use": "moonshotai/kimi-k2",
    # Fast/cheap tasks
    "fast": "qwen/qwen3-8b",
    "simple": "deepseek/deepseek-r1-distill-qwen-8b",
    "budget": "deepseek/deepseek-r1-distill-qwen-8b",
    "free": "google/gemini-2.0-flash-exp:free",
    # Long context
    "long-context": "gemini-1.5-pro",
    "document": "gemini-1.5-pro",
    # Vision tasks
    "vision": "claude-sonnet-4-5-20250929",
    "image": "claude-sonnet-4-5-20250929",
    # Image Generation / Storyboard (NANO BANANA)
    "image-generation": "google/gemini-2.5-flash-image-preview",
    "storyboard": "google/gemini-2.5-flash-image-preview",
    "visual": "google/gemini-2.5-flash-image-preview",
    "design": "google/gemini-2.5-flash-image-preview",
    # Thinking / Advanced Reasoning
    "thinking": "google/gemini-2.5-flash",
    # Chinese language
    "chinese": "qwen/qwen3-235b-a22b",
    "multilingual": "qwen/qwen3-235b-a22b",
    # Default fallback
    "general": "deepseek/deepseek-chat-v3",
    "default": "deepseek/deepseek-chat-v3",
}

# Cost tiers for budget-conscious selection
COST_TIER_MODELS = {
    "free": "google/gemini-2.0-flash-exp:free",  # FREE via OpenRouter
    "budget": "deepseek/deepseek-r1-distill-qwen-8b",  # $0.02/$0.10
    "standard": "deepseek/deepseek-chat-v3",  # $0.20/$0.80
    "premium": "google/gemini-2.5-flash",  # $0.30/$2.50 with thinking
    "flagship": "claude-opus-4-5-20251101",  # $15/$75
}


def select_model(
    task: str | None = None,
    budget: str | None = None,
    require_vision: bool = False,
    require_long_context: bool = False,
    require_function_calling: bool = False,
    prefer_chinese: bool = False,
) -> str:
    """
    Smart model selector - automatically picks the best model.

    This "black boxes" the model selection process. Users specify what they
    need, and the system picks the optimal model for cost/performance.

    Args:
        task: Task type (coding, reasoning, agents, fast, etc.)
        budget: Cost tier (free, budget, standard, premium, flagship)
        require_vision: Must support image/vision input
        require_long_context: Needs >100K context window
        require_function_calling: Must support tool/function calling
        prefer_chinese: Prefer Chinese-trained models (Qwen, DeepSeek)

    Returns:
        Model ID string for the recommended model

    Examples:
        # For coding with budget constraints
        model = select_model(task="coding", budget="budget")

        # For complex reasoning
        model = select_model(task="reasoning")

        # For agent workflows with tool calling
        model = select_model(task="agents", require_function_calling=True)

        # For vision tasks
        model = select_model(require_vision=True)
    """
    catalog = get_model_catalog()

    # Vision requirement narrows choices significantly
    if require_vision:
        if budget == "budget":
            return "gemini-1.5-flash"
        return "claude-sonnet-4-5-20250929"

    # Long context requirement
    if require_long_context:
        return "gemini-1.5-pro"  # 2M context

    # Budget-first selection
    if budget:
        model_id = COST_TIER_MODELS.get(budget)
        if model_id:
            model = catalog.get_model(model_id)
            # Verify it meets other requirements
            if model and (not require_function_calling or model.supports_functions):
                return model_id

    # Chinese preference
    if prefer_chinese:
        if task == "reasoning":
            return "deepseek/deepseek-r1"
        elif task == "coding":
            return "qwen/qwen-2.5-coder-32b-instruct"
        return "deepseek/deepseek-chat-v3"

    # Task-based selection
    if task:
        task_lower = task.lower()
        model_id = TASK_MODEL_MAP.get(task_lower)
        if model_id:
            return model_id

    # Default: Best value flagship
    return "deepseek/deepseek-chat-v3"


def get_model_for_agent() -> str:
    """Get the best model for agent/ReAct workflows.

    Returns a model optimized for:
    - Function/tool calling
    - Reasoning ability
    - Cost efficiency
    - Reliability
    """
    return select_model(task="agents", require_function_calling=True)


def get_model_for_coding() -> str:
    """Get the best model for coding tasks."""
    return select_model(task="coding", prefer_chinese=True)


def get_model_for_reasoning() -> str:
    """Get the best model for complex reasoning/math."""
    return select_model(task="reasoning")
