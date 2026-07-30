"""AI Observability — captures AI-specific metrics for monitoring."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AIObservation:
    """A single AI observation record."""
    operation: str = ""
    model_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    success: bool = True
    retry_count: int = 0
    error: str = ""
    job_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "model_id": self.model_id,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "estimated_cost": self.estimated_cost,
            "success": self.success,
            "retry_count": self.retry_count,
            "error": self.error,
            "job_id": self.job_id,
        }


class AIObservabilityMetrics:
    """Captures AI-specific observability metrics.

    Tracks:
    - Prompt execution time
    - Model latency
    - Token usage
    - Estimated inference cost
    - Retry count
    - Failure rate
    - Success rate

    Does NOT log sensitive prompt contents.
    """

    def __init__(self):
        self._observations: list[AIObservation] = []

    def record(self, observation: AIObservation):
        """Record an AI observation."""
        self._observations.append(observation)

        logger.info(
            "ai_observation",
            operation=observation.operation,
            model_id=observation.model_id,
            latency_ms=observation.latency_ms,
            prompt_tokens=observation.prompt_tokens,
            completion_tokens=observation.completion_tokens,
            success=observation.success,
            job_id=observation.job_id,
        )

    def startObservation(self, operation: str, model_id: str = "", job_id: str = "") -> _ObservationTimer:
        """Start timing an AI operation."""
        return _ObservationTimer(self, operation, model_id, job_id)

    def get_operation_stats(self, operation: str) -> dict:
        """Get aggregated stats for an operation type."""
        ops = [o for o in self._observations if o.operation == operation]
        if not ops:
            return {"count": 0}

        successful = [o for o in ops if o.success]
        failed = [o for o in ops if not o.success]

        return {
            "count": len(ops),
            "success_count": len(successful),
            "failure_count": len(failed),
            "success_rate": len(successful) / len(ops) if ops else 0,
            "avg_latency_ms": sum(o.latency_ms for o in ops) / len(ops),
            "p95_latency_ms": self._percentile([o.latency_ms for o in sorted(ops, key=lambda x: x.latency_ms)], 95),
            "total_prompt_tokens": sum(o.prompt_tokens for o in ops),
            "total_completion_tokens": sum(o.completion_tokens for o in ops),
            "total_cost": sum(o.estimated_cost for o in ops),
            "avg_retries": sum(o.retry_count for o in ops) / len(ops),
        }

    def get_model_stats(self, model_id: str) -> dict:
        """Get stats for a specific model."""
        ops = [o for o in self._observations if o.model_id == model_id]
        return {
            "count": len(ops),
            "success_rate": sum(1 for o in ops if o.success) / len(ops) if ops else 0,
            "avg_latency_ms": sum(o.latency_ms for o in ops) / len(ops) if ops else 0,
            "total_cost": sum(o.estimated_cost for o in ops),
        }

    def get_failure_rate(self) -> float:
        if not self._observations:
            return 0.0
        return sum(1 for o in self._observations if not o.success) / len(self._observations)

    def get_total_cost(self) -> float:
        return sum(o.estimated_cost for o in self._observations)

    def get_total_tokens(self) -> dict:
        return {
            "prompt_tokens": sum(o.prompt_tokens for o in self._observations),
            "completion_tokens": sum(o.completion_tokens for o in self._observations),
            "total": sum(o.prompt_tokens + o.completion_tokens for o in self._observations),
        }

    @staticmethod
    def _percentile(values, pct):
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * pct / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def clear(self):
        self._observations.clear()


class _ObservationTimer:
    """Context manager for timing AI operations."""

    def __init__(self, metrics: AIObservabilityMetrics, operation: str, model_id: str, job_id: str):
        self._metrics = metrics
        self._operation = operation
        self._model_id = model_id
        self._job_id = job_id
        self._start = 0.0
        self._observation = AIObservation(operation=operation, model_id=model_id, job_id=job_id)

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._observation.latency_ms = (time.monotonic() - self._start) * 1000
        if exc_type:
            self._observation.success = False
            self._observation.error = str(exc_val)
        self._metrics.record(self._observation)
        return False

    @property
    def observation(self) -> AIObservation:
        return self._observation
