"""
Health Check Module for Production Deployments

Provides health and readiness endpoints for:
- Load balancers (ALB, nginx, HAProxy)
- Kubernetes probes (liveness, readiness)
- Monitoring systems (Datadog, Prometheus)
"""

import os
import time
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict


@dataclass
class HealthStatus:
    """Health check response"""
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: str
    uptime_seconds: float
    version: str
    checks: Dict[str, Any]


@dataclass
class ReadinessStatus:
    """Readiness check response"""
    ready: bool
    timestamp: str
    model_loaded: bool
    model_name: str
    engine_status: str
    gpu_available: bool
    details: Dict[str, Any]


@dataclass
class ModelInfo:
    """Model information response"""
    model_name: str
    model_path: str
    max_model_len: int
    tensor_parallel_size: int
    dtype: str
    quantization: Optional[str]
    gpu_memory_utilization: float
    loaded_at: str


class HealthChecker:
    """
    Health check manager for the vLLM worker.

    Tracks engine state and provides health/readiness status for
    load balancers, Kubernetes, and monitoring systems.
    """

    def __init__(self):
        self._start_time = time.time()
        self._engine = None
        self._engine_ready = False
        self._model_loaded_at: Optional[str] = None
        self._last_request_time: Optional[float] = None
        self._request_count = 0
        self._error_count = 0
        self._version = os.getenv("WORKER_VERSION", "2.8.0")

    def set_engine(self, engine):
        """Register the vLLM engine for health checks"""
        self._engine = engine
        self._engine_ready = True
        self._model_loaded_at = datetime.now(timezone.utc).isoformat()

    def record_request(self, success: bool = True):
        """Record a request for health metrics"""
        self._last_request_time = time.time()
        self._request_count += 1
        if not success:
            self._error_count += 1

    @property
    def uptime_seconds(self) -> float:
        """Get worker uptime in seconds"""
        return time.time() - self._start_time

    def get_health(self) -> HealthStatus:
        """
        Get health status (liveness check).

        Returns healthy if the worker process is running.
        Used by load balancers to check if the instance is alive.
        """
        checks = {
            "process": "ok",
            "memory": self._check_memory(),
        }

        # Determine overall status
        if all(v == "ok" for v in checks.values()):
            status = "healthy"
        elif checks["process"] == "ok":
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthStatus(
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=round(self.uptime_seconds, 2),
            version=self._version,
            checks=checks
        )

    def get_readiness(self) -> ReadinessStatus:
        """
        Get readiness status (readiness check).

        Returns ready only if the vLLM engine is loaded and can serve requests.
        Used by Kubernetes/load balancers to know when to route traffic.
        """
        model_name = ""
        engine_status = "not_initialized"
        gpu_available = False
        details = {}

        if self._engine:
            try:
                engine_status = "ready"
                model_name = self._engine.engine_args.model

                # Check GPU availability
                try:
                    import torch
                    gpu_available = torch.cuda.is_available()
                    if gpu_available:
                        details["gpu_count"] = torch.cuda.device_count()
                        details["gpu_name"] = torch.cuda.get_device_name(0)
                except ImportError:
                    pass

                details["max_concurrency"] = self._engine.max_concurrency
                details["request_count"] = self._request_count
                details["error_count"] = self._error_count

                if self._last_request_time:
                    details["seconds_since_last_request"] = round(
                        time.time() - self._last_request_time, 2
                    )

            except Exception as e:
                engine_status = f"error: {str(e)}"

        return ReadinessStatus(
            ready=self._engine_ready and engine_status == "ready",
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_loaded=self._engine_ready,
            model_name=model_name,
            engine_status=engine_status,
            gpu_available=gpu_available,
            details=details
        )

    def get_model_info(self) -> Optional[ModelInfo]:
        """
        Get detailed model information.

        Returns None if no model is loaded.
        """
        if not self._engine:
            return None

        try:
            args = self._engine.engine_args
            return ModelInfo(
                model_name=args.model,
                model_path=args.model,
                max_model_len=args.max_model_len or 0,
                tensor_parallel_size=args.tensor_parallel_size,
                dtype=str(args.dtype),
                quantization=args.quantization,
                gpu_memory_utilization=args.gpu_memory_utilization,
                loaded_at=self._model_loaded_at or ""
            )
        except Exception:
            return None

    def _check_memory(self) -> str:
        """Check memory status"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                return "critical"
            elif memory.percent > 85:
                return "warning"
            return "ok"
        except ImportError:
            return "ok"  # psutil not available, assume ok


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def handle_health_request(route: str) -> Dict[str, Any]:
    """
    Handle health check requests.

    Routes:
    - /health: Liveness check
    - /ready: Readiness check
    - /model: Model information
    """
    checker = get_health_checker()

    if route == "/health":
        result = checker.get_health()
        return asdict(result)

    elif route == "/ready":
        result = checker.get_readiness()
        return asdict(result)

    elif route == "/model":
        result = checker.get_model_info()
        if result:
            return asdict(result)
        else:
            return {
                "error": "Model not loaded",
                "status": "unavailable"
            }

    else:
        return {
            "error": f"Unknown health route: {route}",
            "available_routes": ["/health", "/ready", "/model"]
        }
