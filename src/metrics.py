"""
Prometheus Metrics Module

Provides /metrics endpoint in Prometheus format for monitoring:
- Grafana dashboards
- Datadog integration
- PagerDuty alerting
"""

import os
import time
import logging
from typing import Optional, Dict, List
from collections import defaultdict
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)


@dataclass
class HistogramBucket:
    """A histogram bucket with upper bound and count"""
    le: float  # less than or equal
    count: int = 0


class Histogram:
    """Simple histogram implementation"""

    def __init__(self, name: str, help_text: str, buckets: List[float]):
        self.name = name
        self.help = help_text
        self.buckets = sorted(buckets) + [float("inf")]
        self._counts = [0] * len(self.buckets)
        self._sum = 0.0
        self._count = 0

    def observe(self, value: float):
        """Record a value"""
        self._sum += value
        self._count += 1
        for i, bound in enumerate(self.buckets):
            if value <= bound:
                self._counts[i] += 1

    def to_prometheus(self, labels: str = "") -> str:
        """Export in Prometheus format"""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} histogram",
        ]
        label_str = f"{{{labels}}}" if labels else ""
        label_prefix = f"{labels}," if labels else ""

        for i, bound in enumerate(self.buckets):
            le = "+Inf" if bound == float("inf") else str(bound)
            lines.append(f'{self.name}_bucket{{{label_prefix}le="{le}"}} {self._counts[i]}')

        lines.append(f"{self.name}_sum{label_str} {self._sum}")
        lines.append(f"{self.name}_count{label_str} {self._count}")
        return "\n".join(lines)


class Counter:
    """Simple counter implementation"""

    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help = help_text
        self._value = 0

    def inc(self, value: int = 1):
        """Increment counter"""
        self._value += value

    def to_prometheus(self, labels: str = "") -> str:
        """Export in Prometheus format"""
        label_str = f"{{{labels}}}" if labels else ""
        return f"# HELP {self.name} {self.help}\n# TYPE {self.name} counter\n{self.name}{label_str} {self._value}"


class Gauge:
    """Simple gauge implementation"""

    def __init__(self, name: str, help_text: str):
        self.name = name
        self.help = help_text
        self._value = 0.0

    def set(self, value: float):
        """Set gauge value"""
        self._value = value

    def inc(self, value: float = 1):
        """Increment gauge"""
        self._value += value

    def dec(self, value: float = 1):
        """Decrement gauge"""
        self._value -= value

    def to_prometheus(self, labels: str = "") -> str:
        """Export in Prometheus format"""
        label_str = f"{{{labels}}}" if labels else ""
        return f"# HELP {self.name} {self.help}\n# TYPE {self.name} gauge\n{self.name}{label_str} {self._value}"


class MetricsCollector:
    """
    Collects and exposes metrics in Prometheus format.

    Configure via environment variables:
    - METRICS_ENABLED: Enable/disable metrics (default: true)
    - METRICS_PREFIX: Prefix for metric names (default: vllm_worker)
    """

    def __init__(self):
        self.enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        self.prefix = os.getenv("METRICS_PREFIX", "vllm_worker")
        self._start_time = time.time()

        # Request metrics
        self.request_total = Counter(
            f"{self.prefix}_requests_total",
            "Total number of requests processed"
        )
        self.request_success = Counter(
            f"{self.prefix}_requests_success_total",
            "Total number of successful requests"
        )
        self.request_errors = Counter(
            f"{self.prefix}_requests_errors_total",
            "Total number of failed requests"
        )

        # Latency histogram (in milliseconds)
        latency_buckets = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000, 60000]
        self.request_latency = Histogram(
            f"{self.prefix}_request_latency_ms",
            "Request latency in milliseconds",
            latency_buckets
        )

        # Time to first token histogram
        ttft_buckets = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
        self.time_to_first_token = Histogram(
            f"{self.prefix}_time_to_first_token_ms",
            "Time to first token in milliseconds",
            ttft_buckets
        )

        # Token metrics
        self.tokens_input_total = Counter(
            f"{self.prefix}_tokens_input_total",
            "Total input tokens processed"
        )
        self.tokens_output_total = Counter(
            f"{self.prefix}_tokens_output_total",
            "Total output tokens generated"
        )

        # Throughput gauge (tokens per second, updated per request)
        self.tokens_per_second = Gauge(
            f"{self.prefix}_tokens_per_second",
            "Current tokens per second throughput"
        )

        # Active requests gauge
        self.active_requests = Gauge(
            f"{self.prefix}_active_requests",
            "Number of currently active requests"
        )

        # Error counters by type
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Model info
        self._model_name = ""
        self._model_loaded = False

        if self.enabled:
            logging.info("[METRICS] Prometheus metrics enabled")

    def set_model_info(self, model_name: str):
        """Set model information"""
        self._model_name = model_name
        self._model_loaded = True

    def record_request_start(self):
        """Record that a request has started"""
        if not self.enabled:
            return
        self.active_requests.inc()

    def record_request_complete(
        self,
        latency_ms: float,
        time_to_first_token_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        error_code: Optional[str] = None
    ):
        """Record request completion metrics"""
        if not self.enabled:
            return

        self.active_requests.dec()
        self.request_total.inc()

        if success:
            self.request_success.inc()
        else:
            self.request_errors.inc()
            if error_code:
                self._error_counts[error_code] += 1

        self.request_latency.observe(latency_ms)

        if time_to_first_token_ms > 0:
            self.time_to_first_token.observe(time_to_first_token_ms)

        self.tokens_input_total.inc(input_tokens)
        self.tokens_output_total.inc(output_tokens)

        # Update throughput
        if latency_ms > 0:
            tps = output_tokens / (latency_ms / 1000)
            self.tokens_per_second.set(tps)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        if not self.enabled:
            return "# Metrics disabled\n"

        lines = []

        # Uptime
        uptime = time.time() - self._start_time
        lines.append(f"# HELP {self.prefix}_uptime_seconds Worker uptime in seconds")
        lines.append(f"# TYPE {self.prefix}_uptime_seconds gauge")
        lines.append(f"{self.prefix}_uptime_seconds {uptime:.2f}")
        lines.append("")

        # Model info
        lines.append(f"# HELP {self.prefix}_model_loaded Whether model is loaded")
        lines.append(f"# TYPE {self.prefix}_model_loaded gauge")
        lines.append(f'{self.prefix}_model_loaded{{model="{self._model_name}"}} {1 if self._model_loaded else 0}')
        lines.append("")

        # Request counters
        lines.append(self.request_total.to_prometheus())
        lines.append("")
        lines.append(self.request_success.to_prometheus())
        lines.append("")
        lines.append(self.request_errors.to_prometheus())
        lines.append("")

        # Error breakdown
        if self._error_counts:
            lines.append(f"# HELP {self.prefix}_errors_by_type_total Errors by error code")
            lines.append(f"# TYPE {self.prefix}_errors_by_type_total counter")
            for error_code, count in self._error_counts.items():
                lines.append(f'{self.prefix}_errors_by_type_total{{error_code="{error_code}"}} {count}')
            lines.append("")

        # Latency histogram
        lines.append(self.request_latency.to_prometheus())
        lines.append("")

        # TTFT histogram
        lines.append(self.time_to_first_token.to_prometheus())
        lines.append("")

        # Token counters
        lines.append(self.tokens_input_total.to_prometheus())
        lines.append("")
        lines.append(self.tokens_output_total.to_prometheus())
        lines.append("")

        # Gauges
        lines.append(self.tokens_per_second.to_prometheus())
        lines.append("")
        lines.append(self.active_requests.to_prometheus())
        lines.append("")

        # GPU metrics (if available)
        gpu_metrics = self._get_gpu_metrics()
        if gpu_metrics:
            lines.extend(gpu_metrics)

        return "\n".join(lines)

    def _get_gpu_metrics(self) -> List[str]:
        """Get GPU metrics if available"""
        lines = []
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    # Memory
                    mem_allocated = torch.cuda.memory_allocated(i) / 1e9
                    mem_reserved = torch.cuda.memory_reserved(i) / 1e9

                    lines.append(f"# HELP {self.prefix}_gpu_memory_allocated_gb GPU memory allocated in GB")
                    lines.append(f"# TYPE {self.prefix}_gpu_memory_allocated_gb gauge")
                    lines.append(f'{self.prefix}_gpu_memory_allocated_gb{{device="{i}"}} {mem_allocated:.2f}')
                    lines.append("")

                    lines.append(f"# HELP {self.prefix}_gpu_memory_reserved_gb GPU memory reserved in GB")
                    lines.append(f"# TYPE {self.prefix}_gpu_memory_reserved_gb gauge")
                    lines.append(f'{self.prefix}_gpu_memory_reserved_gb{{device="{i}"}} {mem_reserved:.2f}')
                    lines.append("")

        except Exception:
            pass

        return lines


# Global metrics collector
_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def handle_metrics_request() -> str:
    """Handle /metrics request"""
    return get_metrics_collector().get_metrics()
