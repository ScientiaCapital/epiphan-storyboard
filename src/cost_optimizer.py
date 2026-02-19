"""
Cost Optimization Engine

Automatically selects the best model for cost, latency, or quality.
Tracks spending and provides optimization recommendations.

NOTE: NO OpenAI or Groq. Uses Anthropic, Google Gemini, OpenRouter only.
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logging.basicConfig(level=logging.INFO)


class OptimizationStrategy(Enum):
    """Optimization strategies for model selection"""
    COST = "cost"            # Cheapest model that can handle the task
    LATENCY = "latency"      # Fastest model
    QUALITY = "quality"      # Best quality model
    BALANCED = "balanced"    # Balance of cost and quality


class TaskComplexity(Enum):
    """Complexity levels for tasks"""
    SIMPLE = "simple"        # Simple Q&A, short responses
    MODERATE = "moderate"    # Multi-turn, reasoning
    COMPLEX = "complex"      # Long context, analysis, coding


@dataclass
class ModelCapability:
    """Capabilities and costs for a model"""
    model_id: str
    provider: str

    # Capabilities
    max_context: int = 4096
    supports_vision: bool = False
    supports_functions: bool = False
    supports_streaming: bool = True

    # Quality scores (0-100)
    quality_score: int = 50
    reasoning_score: int = 50
    coding_score: int = 50

    # Costs per 1K tokens
    input_cost: float = 0.0
    output_cost: float = 0.0

    # Performance
    avg_latency_ms: float = 1000.0
    tokens_per_second: float = 50.0

    def total_cost_per_1k(self) -> float:
        return self.input_cost + self.output_cost


@dataclass
class OptimizationResult:
    """Result of model optimization"""
    recommended_model: str
    provider: str
    reason: str
    estimated_cost_cents: float
    estimated_latency_ms: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CostReport:
    """Cost tracking report"""
    total_cost_cents: float = 0.0
    total_tokens: int = 0
    total_requests: int = 0
    by_provider: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    savings_from_optimization: float = 0.0
    period_start: str = ""
    period_end: str = ""


class CostOptimizer:
    """
    Optimizes model selection based on cost, latency, and quality.

    Configure via environment variables:
    - OPTIMIZER_ENABLED: Enable optimization (default: true)
    - OPTIMIZER_STRATEGY: Default strategy (default: balanced)
    - OPTIMIZER_MAX_COST_CENTS: Max cost per request (default: 100)
    - OPTIMIZER_PREFER_PROVIDER: Preferred provider (default: none)
    """

    def __init__(self):
        self.enabled = os.getenv("OPTIMIZER_ENABLED", "true").lower() == "true"
        self.default_strategy = OptimizationStrategy(os.getenv("OPTIMIZER_STRATEGY", "balanced"))
        self.max_cost_cents = float(os.getenv("OPTIMIZER_MAX_COST_CENTS", "100"))
        self.prefer_provider = os.getenv("OPTIMIZER_PREFER_PROVIDER")

        # Model capabilities database
        self._models: Dict[str, ModelCapability] = {}
        self._load_model_capabilities()

        # Cost tracking
        self._cost_history: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

        # Statistics
        self._total_optimized = 0
        self._total_savings = 0.0

        if self.enabled:
            logging.info(f"[OPTIMIZER] Cost optimizer enabled (strategy={self.default_strategy.value})")

    def _load_model_capabilities(self):
        """Load model capabilities database (NO OpenAI or Groq)"""

        # =============================================
        # Anthropic Models (Primary Provider)
        # =============================================

        # Claude 4.5 (Latest - Primary for Agents)
        self._models["claude-opus-4-5-20251101"] = ModelCapability(
            model_id="claude-opus-4-5-20251101", provider="anthropic",
            max_context=200000, supports_vision=True, supports_functions=True,
            quality_score=99, reasoning_score=99, coding_score=98,
            input_cost=1.5, output_cost=7.5, avg_latency_ms=2500
        )
        self._models["claude-sonnet-4-5-20250929"] = ModelCapability(
            model_id="claude-sonnet-4-5-20250929", provider="anthropic",
            max_context=200000, supports_vision=True, supports_functions=True,
            quality_score=97, reasoning_score=97, coding_score=97,
            input_cost=0.3, output_cost=1.5, avg_latency_ms=900
        )

        # Claude 3.5 (Still excellent)
        self._models["claude-3-5-sonnet-20241022"] = ModelCapability(
            model_id="claude-3-5-sonnet-20241022", provider="anthropic",
            max_context=200000, supports_vision=True, supports_functions=True,
            quality_score=95, reasoning_score=95, coding_score=95,
            input_cost=0.3, output_cost=1.5, avg_latency_ms=900
        )
        self._models["claude-3-5-haiku-20241022"] = ModelCapability(
            model_id="claude-3-5-haiku-20241022", provider="anthropic",
            max_context=200000, supports_vision=True, supports_functions=True,
            quality_score=80, reasoning_score=75, coding_score=80,
            input_cost=0.025, output_cost=0.125, avg_latency_ms=300
        )

        # =============================================
        # Google Gemini Models
        # =============================================
        self._models["gemini-1.5-pro"] = ModelCapability(
            model_id="gemini-1.5-pro", provider="google",
            max_context=2000000, supports_vision=True, supports_functions=True,
            quality_score=92, reasoning_score=90, coding_score=88,
            input_cost=0.125, output_cost=0.5, avg_latency_ms=1000
        )
        self._models["gemini-1.5-flash"] = ModelCapability(
            model_id="gemini-1.5-flash", provider="google",
            max_context=1000000, supports_vision=True, supports_functions=True,
            quality_score=82, reasoning_score=78, coding_score=80,
            input_cost=0.0075, output_cost=0.03, avg_latency_ms=400
        )
        self._models["gemini-1.5-flash-8b"] = ModelCapability(
            model_id="gemini-1.5-flash-8b", provider="google",
            max_context=1000000, supports_vision=True, supports_functions=True,
            quality_score=70, reasoning_score=65, coding_score=70,
            input_cost=0.00375, output_cost=0.015, avg_latency_ms=200
        )
        self._models["gemini-2.0-flash-exp"] = ModelCapability(
            model_id="gemini-2.0-flash-exp", provider="google",
            max_context=1000000, supports_vision=True, supports_functions=True,
            quality_score=88, reasoning_score=85, coding_score=85,
            input_cost=0.0, output_cost=0.0, avg_latency_ms=350  # Free preview
        )

        # =============================================
        # OpenRouter Models (Chinese LLMs, Llama, Mistral)
        # =============================================
        self._models["qwen/qwen-2.5-72b-instruct"] = ModelCapability(
            model_id="qwen/qwen-2.5-72b-instruct", provider="openrouter",
            max_context=131072, supports_functions=True,
            quality_score=90, reasoning_score=88, coding_score=92,
            input_cost=0.035, output_cost=0.04, avg_latency_ms=800
        )
        self._models["qwen/qwen-2.5-coder-32b-instruct"] = ModelCapability(
            model_id="qwen/qwen-2.5-coder-32b-instruct", provider="openrouter",
            max_context=131072, supports_functions=True,
            quality_score=85, reasoning_score=80, coding_score=95,
            input_cost=0.018, output_cost=0.018, avg_latency_ms=600
        )
        self._models["deepseek/deepseek-chat"] = ModelCapability(
            model_id="deepseek/deepseek-chat", provider="openrouter",
            max_context=65536, supports_functions=True,
            quality_score=82, reasoning_score=85, coding_score=80,
            input_cost=0.014, output_cost=0.028, avg_latency_ms=700
        )
        self._models["deepseek/deepseek-coder"] = ModelCapability(
            model_id="deepseek/deepseek-coder", provider="openrouter",
            max_context=65536, supports_functions=True,
            quality_score=80, reasoning_score=75, coding_score=90,
            input_cost=0.014, output_cost=0.028, avg_latency_ms=700
        )
        self._models["meta-llama/llama-3.1-70b-instruct"] = ModelCapability(
            model_id="meta-llama/llama-3.1-70b-instruct", provider="openrouter",
            max_context=131072, supports_functions=True,
            quality_score=85, reasoning_score=82, coding_score=80,
            input_cost=0.052, output_cost=0.075, avg_latency_ms=500
        )
        self._models["meta-llama/llama-3.1-8b-instruct"] = ModelCapability(
            model_id="meta-llama/llama-3.1-8b-instruct", provider="openrouter",
            max_context=131072,
            quality_score=68, reasoning_score=62, coding_score=65,
            input_cost=0.0055, output_cost=0.0055, avg_latency_ms=200
        )
        self._models["mistralai/mistral-large"] = ModelCapability(
            model_id="mistralai/mistral-large", provider="openrouter",
            max_context=128000, supports_functions=True,
            quality_score=88, reasoning_score=85, coding_score=85,
            input_cost=0.2, output_cost=0.6, avg_latency_ms=900
        )
        self._models["mistralai/mixtral-8x7b-instruct"] = ModelCapability(
            model_id="mistralai/mixtral-8x7b-instruct", provider="openrouter",
            max_context=32768,
            quality_score=75, reasoning_score=72, coding_score=75,
            input_cost=0.024, output_cost=0.024, avg_latency_ms=300
        )

    def estimate_complexity(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None
    ) -> TaskComplexity:
        """Estimate task complexity from messages"""
        # Calculate total input length
        total_chars = sum(len(m.get("content", "")) for m in messages)

        # Count messages (multi-turn indicator)
        num_messages = len(messages)

        # Check for complexity indicators in content
        last_message = messages[-1].get("content", "").lower() if messages else ""

        complexity_indicators = [
            "analyze", "explain", "compare", "evaluate", "synthesize",
            "code", "implement", "debug", "refactor", "optimize",
            "step by step", "reasoning", "think through", "consider",
        ]

        has_complex_task = any(ind in last_message for ind in complexity_indicators)

        # Determine complexity
        if total_chars > 10000 or num_messages > 10 or has_complex_task:
            return TaskComplexity.COMPLEX
        elif total_chars > 2000 or num_messages > 3:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE

    def recommend_model(
        self,
        messages: List[Dict[str, str]],
        strategy: Optional[OptimizationStrategy] = None,
        max_tokens: Optional[int] = None,
        required_features: Optional[List[str]] = None,
        excluded_providers: Optional[List[str]] = None,
        min_quality: Optional[int] = None
    ) -> OptimizationResult:
        """
        Recommend the best model for a task.

        Args:
            messages: Input messages
            strategy: Optimization strategy
            max_tokens: Expected output tokens
            required_features: Required features (vision, functions, etc.)
            excluded_providers: Providers to exclude
            min_quality: Minimum quality score required

        Returns:
            OptimizationResult with recommendation
        """
        if not self.enabled:
            # Return a default (NO OpenAI - use Haiku)
            return OptimizationResult(
                recommended_model="claude-3-5-haiku-20241022",
                provider="anthropic",
                reason="optimization_disabled",
                estimated_cost_cents=0,
                estimated_latency_ms=300
            )

        strategy = strategy or self.default_strategy
        complexity = self.estimate_complexity(messages, max_tokens)

        # Filter eligible models
        eligible = []
        for model_id, cap in self._models.items():
            # Check provider exclusion
            if excluded_providers and cap.provider in excluded_providers:
                continue

            # Check required features
            if required_features:
                if "vision" in required_features and not cap.supports_vision:
                    continue
                if "functions" in required_features and not cap.supports_functions:
                    continue

            # Check minimum quality
            if min_quality and cap.quality_score < min_quality:
                continue

            # Check context length
            input_chars = sum(len(m.get("content", "")) for m in messages)
            estimated_tokens = input_chars // 4
            if estimated_tokens > cap.max_context * 0.8:
                continue

            eligible.append(cap)

        if not eligible:
            # Fallback to Haiku (NO OpenAI)
            return OptimizationResult(
                recommended_model="claude-3-5-haiku-20241022",
                provider="anthropic",
                reason="no_eligible_models",
                estimated_cost_cents=0,
                estimated_latency_ms=300
            )

        # Score models based on strategy
        scored = []
        for cap in eligible:
            score = self._score_model(cap, strategy, complexity, max_tokens or 1000)
            scored.append((cap, score))

        # Sort by score (higher is better)
        scored.sort(key=lambda x: x[1], reverse=True)

        best = scored[0][0]

        # Calculate estimated cost
        input_tokens = sum(len(m.get("content", "")) for m in messages) // 4
        output_tokens = max_tokens or 1000
        estimated_cost = (
            (input_tokens / 1000) * best.input_cost +
            (output_tokens / 1000) * best.output_cost
        )

        # Build alternatives
        alternatives = []
        for cap, score in scored[1:4]:  # Top 3 alternatives
            alt_cost = (
                (input_tokens / 1000) * cap.input_cost +
                (output_tokens / 1000) * cap.output_cost
            )
            alternatives.append({
                "model": cap.model_id,
                "provider": cap.provider,
                "estimated_cost_cents": round(alt_cost, 4),
                "quality_score": cap.quality_score,
            })

        self._total_optimized += 1

        return OptimizationResult(
            recommended_model=best.model_id,
            provider=best.provider,
            reason=f"{strategy.value}_optimized_{complexity.value}",
            estimated_cost_cents=round(estimated_cost, 4),
            estimated_latency_ms=best.avg_latency_ms,
            alternatives=alternatives
        )

    def _score_model(
        self,
        cap: ModelCapability,
        strategy: OptimizationStrategy,
        complexity: TaskComplexity,
        output_tokens: int
    ) -> float:
        """Score a model based on strategy and task"""
        # Base scores
        cost_score = 100 - (cap.total_cost_per_1k() * 10)  # Lower cost = higher score
        latency_score = 100 - (cap.avg_latency_ms / 50)  # Lower latency = higher score
        quality_score = cap.quality_score

        # Adjust quality requirement by complexity
        if complexity == TaskComplexity.SIMPLE:
            min_quality = 60
        elif complexity == TaskComplexity.MODERATE:
            min_quality = 75
        else:  # COMPLEX
            min_quality = 85

        # Penalize if below minimum quality for task
        if quality_score < min_quality:
            quality_score -= (min_quality - quality_score) * 2

        # Weight based on strategy
        if strategy == OptimizationStrategy.COST:
            return cost_score * 0.7 + latency_score * 0.1 + quality_score * 0.2
        elif strategy == OptimizationStrategy.LATENCY:
            return cost_score * 0.1 + latency_score * 0.7 + quality_score * 0.2
        elif strategy == OptimizationStrategy.QUALITY:
            return cost_score * 0.1 + latency_score * 0.1 + quality_score * 0.8
        else:  # BALANCED
            return cost_score * 0.4 + latency_score * 0.2 + quality_score * 0.4

    async def record_usage(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost_cents: float,
        was_optimized: bool = False,
        original_model: Optional[str] = None
    ):
        """Record usage for cost tracking"""
        async with self._lock:
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_cents": cost_cents,
                "was_optimized": was_optimized,
                "original_model": original_model,
            }
            self._cost_history.append(record)

            # Calculate savings if optimized
            if was_optimized and original_model and original_model in self._models:
                orig_cap = self._models[original_model]
                orig_cost = (
                    (input_tokens / 1000) * orig_cap.input_cost +
                    (output_tokens / 1000) * orig_cap.output_cost
                )
                savings = orig_cost - cost_cents
                self._total_savings += max(0, savings)

            # Keep last 10000 records
            if len(self._cost_history) > 10000:
                self._cost_history = self._cost_history[-10000:]

    def get_cost_report(self, hours: int = 24) -> CostReport:
        """Get cost report for the specified time period"""
        cutoff = time.time() - (hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

        filtered = [
            r for r in self._cost_history
            if r["timestamp"] >= cutoff_iso
        ]

        report = CostReport(
            period_start=cutoff_iso,
            period_end=datetime.now(timezone.utc).isoformat(),
        )

        for record in filtered:
            report.total_cost_cents += record["cost_cents"]
            report.total_tokens += record["input_tokens"] + record["output_tokens"]
            report.total_requests += 1

            # By provider
            provider = record["provider"]
            report.by_provider[provider] = report.by_provider.get(provider, 0) + record["cost_cents"]

            # By model
            model = record["model"]
            report.by_model[model] = report.by_model.get(model, 0) + record["cost_cents"]

        report.savings_from_optimization = self._total_savings

        return report

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "enabled": self.enabled,
            "strategy": self.default_strategy.value,
            "total_optimized": self._total_optimized,
            "total_savings_cents": round(self._total_savings, 2),
            "models_available": len(self._models),
        }


# Global cost optimizer
_optimizer: Optional[CostOptimizer] = None


def get_cost_optimizer() -> CostOptimizer:
    """Get or create the global cost optimizer"""
    global _optimizer
    if _optimizer is None:
        _optimizer = CostOptimizer()
    return _optimizer


def handle_optimizer_stats_request() -> Dict[str, Any]:
    """Handle /optimizer/stats request"""
    optimizer = get_cost_optimizer()
    return optimizer.get_stats()


def handle_optimizer_recommend_request(
    messages: List[Dict[str, str]],
    strategy: Optional[str] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """Handle /optimizer/recommend request"""
    optimizer = get_cost_optimizer()
    strat = OptimizationStrategy(strategy) if strategy else None
    result = optimizer.recommend_model(messages, strat, max_tokens)
    return {
        "recommended_model": result.recommended_model,
        "provider": result.provider,
        "reason": result.reason,
        "estimated_cost_cents": result.estimated_cost_cents,
        "estimated_latency_ms": result.estimated_latency_ms,
        "alternatives": result.alternatives,
    }


def handle_optimizer_report_request(hours: int = 24) -> Dict[str, Any]:
    """Handle /optimizer/report request"""
    optimizer = get_cost_optimizer()
    report = optimizer.get_cost_report(hours)
    return {
        "total_cost_cents": round(report.total_cost_cents, 2),
        "total_tokens": report.total_tokens,
        "total_requests": report.total_requests,
        "by_provider": {k: round(v, 2) for k, v in report.by_provider.items()},
        "by_model": {k: round(v, 2) for k, v in report.by_model.items()},
        "savings_from_optimization": round(report.savings_from_optimization, 2),
        "period_start": report.period_start,
        "period_end": report.period_end,
    }
