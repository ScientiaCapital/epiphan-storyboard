"""
Model Router & A/B Testing Module

Enables traffic splitting, canary deployments, and A/B testing
for safe production rollouts and performance comparison.
"""

import os
import random
import time
import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logging.basicConfig(level=logging.INFO)


class RoutingStrategy(Enum):
    """Strategies for routing requests"""
    WEIGHTED = "weighted"        # Random based on weights
    STICKY = "sticky"            # Same user gets same model
    ROUND_ROBIN = "round_robin"  # Cycle through models
    LATENCY = "latency"          # Route to lowest latency


@dataclass
class ModelBackend:
    """Configuration for a model backend"""
    name: str
    model_id: str
    weight: int = 100          # Percentage weight (0-100)
    enabled: bool = True

    # Metadata
    version: str = "1.0"
    description: str = ""

    # Feature flags
    is_canary: bool = False
    is_default: bool = False

    # Performance tracking
    total_requests: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0
    error_count: int = 0

    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.total_latency_ms / self.total_requests

    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.error_count / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "weight": self.weight,
            "enabled": self.enabled,
            "version": self.version,
            "is_canary": self.is_canary,
            "is_default": self.is_default,
            "stats": {
                "total_requests": self.total_requests,
                "total_tokens": self.total_tokens,
                "avg_latency_ms": round(self.avg_latency_ms(), 2),
                "error_count": self.error_count,
                "error_rate": round(self.error_rate() * 100, 2),
            }
        }


@dataclass
class RoutingDecision:
    """Result of a routing decision"""
    backend: ModelBackend
    reason: str
    experiment_id: Optional[str] = None


@dataclass
class Experiment:
    """A/B test experiment configuration"""
    id: str
    name: str
    control_backend: str
    treatment_backend: str
    traffic_percentage: int = 10  # % of traffic to treatment

    # Targeting
    user_ids: List[str] = field(default_factory=list)  # Specific users
    tiers: List[str] = field(default_factory=list)     # Specific tiers

    # State
    enabled: bool = True
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Results
    control_requests: int = 0
    treatment_requests: int = 0
    control_latency_sum: float = 0
    treatment_latency_sum: float = 0
    control_errors: int = 0
    treatment_errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        control_avg = self.control_latency_sum / self.control_requests if self.control_requests else 0
        treatment_avg = self.treatment_latency_sum / self.treatment_requests if self.treatment_requests else 0

        return {
            "id": self.id,
            "name": self.name,
            "control_backend": self.control_backend,
            "treatment_backend": self.treatment_backend,
            "traffic_percentage": self.traffic_percentage,
            "enabled": self.enabled,
            "started_at": self.started_at,
            "results": {
                "control": {
                    "requests": self.control_requests,
                    "avg_latency_ms": round(control_avg, 2),
                    "errors": self.control_errors,
                },
                "treatment": {
                    "requests": self.treatment_requests,
                    "avg_latency_ms": round(treatment_avg, 2),
                    "errors": self.treatment_errors,
                },
            }
        }


@dataclass
class RouterStats:
    """Router statistics"""
    total_routed: int = 0
    by_backend: Dict[str, int] = field(default_factory=dict)
    by_strategy: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_routed": self.total_routed,
            "by_backend": self.by_backend,
            "by_strategy": self.by_strategy,
        }


class ModelRouter:
    """
    Routes requests to model backends with traffic splitting.

    Configure via environment variables:
    - ROUTER_ENABLED: Enable routing (default: false)
    - ROUTER_STRATEGY: Routing strategy (default: weighted)
    - ROUTER_DEFAULT_MODEL: Default model if routing disabled
    - ROUTER_CANARY_PERCENTAGE: Default canary traffic % (default: 10)
    """

    def __init__(self):
        self.enabled = os.getenv("ROUTER_ENABLED", "false").lower() == "true"
        self.strategy = RoutingStrategy(os.getenv("ROUTER_STRATEGY", "weighted"))
        self.default_model = os.getenv("ROUTER_DEFAULT_MODEL", "")
        self.canary_percentage = int(os.getenv("ROUTER_CANARY_PERCENTAGE", "10"))

        # Backends
        self._backends: Dict[str, ModelBackend] = {}
        self._experiments: Dict[str, Experiment] = {}
        self._lock = asyncio.Lock()

        # Round robin state
        self._round_robin_index = 0

        # Statistics
        self._stats = RouterStats()

        if self.enabled:
            logging.info(f"[ROUTER] Model router enabled (strategy={self.strategy.value})")
        else:
            logging.info("[ROUTER] Model router disabled")

    async def register_backend(
        self,
        name: str,
        model_id: str,
        weight: int = 100,
        is_canary: bool = False,
        is_default: bool = False,
        version: str = "1.0",
        description: str = ""
    ) -> ModelBackend:
        """Register a model backend"""
        async with self._lock:
            backend = ModelBackend(
                name=name,
                model_id=model_id,
                weight=weight,
                is_canary=is_canary,
                is_default=is_default,
                version=version,
                description=description,
            )
            self._backends[name] = backend
            logging.info(f"[ROUTER] Registered backend: {name} ({model_id})")
            return backend

    async def create_experiment(
        self,
        name: str,
        control_backend: str,
        treatment_backend: str,
        traffic_percentage: int = 10,
        user_ids: Optional[List[str]] = None,
        tiers: Optional[List[str]] = None
    ) -> Experiment:
        """Create an A/B test experiment"""
        async with self._lock:
            exp_id = f"exp_{int(time.time() * 1000)}"
            experiment = Experiment(
                id=exp_id,
                name=name,
                control_backend=control_backend,
                treatment_backend=treatment_backend,
                traffic_percentage=traffic_percentage,
                user_ids=user_ids or [],
                tiers=tiers or [],
            )
            self._experiments[exp_id] = experiment
            logging.info(f"[ROUTER] Created experiment: {name} ({traffic_percentage}% to treatment)")
            return experiment

    async def route(
        self,
        user_id: Optional[str] = None,
        tier: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> RoutingDecision:
        """
        Route a request to a model backend.

        Args:
            user_id: User identifier for sticky routing
            tier: User tier for experiment targeting
            request_id: Request ID for logging

        Returns:
            RoutingDecision with selected backend
        """
        if not self.enabled or not self._backends:
            # Return a default backend
            default = ModelBackend(
                name="default",
                model_id=self.default_model,
                is_default=True
            )
            return RoutingDecision(backend=default, reason="routing_disabled")

        # Check experiments first
        experiment_decision = await self._check_experiments(user_id, tier)
        if experiment_decision:
            return experiment_decision

        # Get enabled backends
        enabled = [b for b in self._backends.values() if b.enabled]
        if not enabled:
            raise NoBackendsAvailableError("No enabled backends available")

        # Route based on strategy
        if self.strategy == RoutingStrategy.WEIGHTED:
            backend = self._route_weighted(enabled)
            reason = "weighted"
        elif self.strategy == RoutingStrategy.STICKY:
            backend = self._route_sticky(enabled, user_id or request_id or "")
            reason = "sticky"
        elif self.strategy == RoutingStrategy.ROUND_ROBIN:
            backend = self._route_round_robin(enabled)
            reason = "round_robin"
        elif self.strategy == RoutingStrategy.LATENCY:
            backend = self._route_latency(enabled)
            reason = "lowest_latency"
        else:
            backend = enabled[0]
            reason = "default"

        # Update stats
        self._stats.total_routed += 1
        self._stats.by_backend[backend.name] = self._stats.by_backend.get(backend.name, 0) + 1
        self._stats.by_strategy[reason] = self._stats.by_strategy.get(reason, 0) + 1

        return RoutingDecision(backend=backend, reason=reason)

    async def _check_experiments(
        self,
        user_id: Optional[str],
        tier: Optional[str]
    ) -> Optional[RoutingDecision]:
        """Check if request should be routed to an experiment"""
        for exp in self._experiments.values():
            if not exp.enabled:
                continue

            # Check targeting
            if exp.user_ids and user_id not in exp.user_ids:
                continue
            if exp.tiers and tier not in exp.tiers:
                continue

            # Determine if treatment or control
            is_treatment = random.randint(1, 100) <= exp.traffic_percentage

            if is_treatment:
                backend_name = exp.treatment_backend
                exp.treatment_requests += 1
            else:
                backend_name = exp.control_backend
                exp.control_requests += 1

            if backend_name in self._backends:
                return RoutingDecision(
                    backend=self._backends[backend_name],
                    reason="experiment",
                    experiment_id=exp.id
                )

        return None

    def _route_weighted(self, backends: List[ModelBackend]) -> ModelBackend:
        """Route based on weights"""
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return backends[0]

        rand = random.randint(1, total_weight)
        cumulative = 0

        for backend in backends:
            cumulative += backend.weight
            if rand <= cumulative:
                return backend

        return backends[-1]

    def _route_sticky(self, backends: List[ModelBackend], key: str) -> ModelBackend:
        """Route consistently based on key hash"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        index = hash_value % len(backends)
        return backends[index]

    def _route_round_robin(self, backends: List[ModelBackend]) -> ModelBackend:
        """Route in round-robin fashion"""
        backend = backends[self._round_robin_index % len(backends)]
        self._round_robin_index += 1
        return backend

    def _route_latency(self, backends: List[ModelBackend]) -> ModelBackend:
        """Route to backend with lowest average latency"""
        # Sort by latency, prioritize those with data
        with_data = [b for b in backends if b.total_requests > 0]
        without_data = [b for b in backends if b.total_requests == 0]

        if with_data:
            return min(with_data, key=lambda b: b.avg_latency_ms())
        else:
            return without_data[0] if without_data else backends[0]

    async def record_result(
        self,
        backend_name: str,
        latency_ms: float,
        tokens: int = 0,
        success: bool = True,
        experiment_id: Optional[str] = None
    ):
        """Record result for a routed request"""
        async with self._lock:
            if backend_name in self._backends:
                backend = self._backends[backend_name]
                backend.total_requests += 1
                backend.total_latency_ms += latency_ms
                backend.total_tokens += tokens
                if not success:
                    backend.error_count += 1

            # Update experiment results
            if experiment_id and experiment_id in self._experiments:
                exp = self._experiments[experiment_id]
                if backend_name == exp.treatment_backend:
                    exp.treatment_latency_sum += latency_ms
                    if not success:
                        exp.treatment_errors += 1
                else:
                    exp.control_latency_sum += latency_ms
                    if not success:
                        exp.control_errors += 1

    async def set_weight(self, backend_name: str, weight: int):
        """Set weight for a backend"""
        async with self._lock:
            if backend_name in self._backends:
                self._backends[backend_name].weight = weight
                logging.info(f"[ROUTER] Set {backend_name} weight to {weight}")

    async def enable_backend(self, backend_name: str, enabled: bool):
        """Enable or disable a backend"""
        async with self._lock:
            if backend_name in self._backends:
                self._backends[backend_name].enabled = enabled
                status = "enabled" if enabled else "disabled"
                logging.info(f"[ROUTER] Backend {backend_name} {status}")

    async def stop_experiment(self, experiment_id: str):
        """Stop an experiment"""
        async with self._lock:
            if experiment_id in self._experiments:
                self._experiments[experiment_id].enabled = False
                logging.info(f"[ROUTER] Stopped experiment {experiment_id}")

    def get_backends(self) -> List[Dict[str, Any]]:
        """Get all backends"""
        return [b.to_dict() for b in self._backends.values()]

    def get_experiments(self) -> List[Dict[str, Any]]:
        """Get all experiments"""
        return [e.to_dict() for e in self._experiments.values()]

    def get_stats(self) -> RouterStats:
        """Get router statistics"""
        return self._stats


class NoBackendsAvailableError(Exception):
    """Raised when no backends are available for routing"""
    pass


# Global router instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create the global model router"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def handle_router_stats_request() -> Dict[str, Any]:
    """Handle /router/stats request"""
    router = get_router()
    stats = router.get_stats()
    return {
        "enabled": router.enabled,
        "strategy": router.strategy.value,
        "canary_percentage": router.canary_percentage,
        **stats.to_dict(),
    }


def handle_router_backends_request() -> Dict[str, Any]:
    """Handle /router/backends request"""
    router = get_router()
    return {
        "backends": router.get_backends(),
        "count": len(router._backends),
    }


def handle_router_experiments_request() -> Dict[str, Any]:
    """Handle /router/experiments request"""
    router = get_router()
    return {
        "experiments": router.get_experiments(),
        "count": len(router._experiments),
    }


async def handle_router_weight_request(backend: str, weight: int) -> Dict[str, Any]:
    """Handle /router/weight request"""
    router = get_router()
    await router.set_weight(backend, weight)
    return {"backend": backend, "weight": weight, "updated": True}
