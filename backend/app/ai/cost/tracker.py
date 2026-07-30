"""AI Cost Tracker — tracks token usage and estimated inference costs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ModelUsageRecord:
    """A single usage record for a model invocation."""
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    job_id: str = ""
    operation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ModelCostProfile:
    """Cost profile for a model."""
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0


# Default cost profiles — updated from provider config at runtime
_DEFAULT_COSTS: dict[str, ModelCostProfile] = {
    "amazon.nova-pro-v1:0": ModelCostProfile(input_cost_per_1k=0.0008, output_cost_per_1k=0.0016),
    "amazon.nova-lite-v1:0": ModelCostProfile(input_cost_per_1k=0.00006, output_cost_per_1k=0.00024),
}


class AICostTracker:
    """Tracks AI usage costs per invocation, per job, and daily.

    No billing integration required — all tracking is estimated.
    """

    def __init__(self):
        self._records: list[ModelUsageRecord] = []
        self._cost_profiles: dict[str, ModelCostProfile] = dict(_DEFAULT_COSTS)

    @staticmethod
    def estimate_cost(
        input_tokens: int,
        output_tokens: int,
        model_id: str,
    ) -> float:
        """Estimate cost for a single invocation."""
        profile = _DEFAULT_COSTS.get(model_id, ModelCostProfile(input_cost_per_1k=0.001, output_cost_per_1k=0.002))
        return (input_tokens / 1000 * profile.input_cost_per_1k) + (output_tokens / 1000 * profile.output_cost_per_1k)

    def record_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float = 0.0,
        job_id: str = "",
        operation: str = "",
    ) -> ModelUsageRecord:
        """Record a usage event."""
        cost = self.estimate_cost(input_tokens, output_tokens, model_id)
        record = ModelUsageRecord(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost=cost,
            job_id=job_id,
            operation=operation,
        )
        self._records.append(record)

        logger.debug(
            "ai_cost_recorded",
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=round(cost, 6),
            operation=operation,
        )
        return record

    def get_job_usage(self, job_id: str) -> dict:
        """Get aggregated usage for a specific job."""
        job_records = [r for r in self._records if r.job_id == job_id]
        if not job_records:
            return {"total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0, "invocations": 0}

        return {
            "total_cost": sum(r.estimated_cost for r in job_records),
            "total_input_tokens": sum(r.input_tokens for r in job_records),
            "total_output_tokens": sum(r.output_tokens for r in job_records),
            "invocations": len(job_records),
            "avg_latency_ms": sum(r.latency_ms for r in job_records) / len(job_records),
            "by_model": self._aggregate_by_model(job_records),
        }

    def get_daily_usage(self) -> dict:
        """Get aggregated usage for today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_records = [r for r in self._records if r.timestamp.startswith(today)]

        return {
            "date": today,
            "total_cost": sum(r.estimated_cost for r in today_records),
            "total_input_tokens": sum(r.input_tokens for r in today_records),
            "total_output_tokens": sum(r.output_tokens for r in today_records),
            "invocations": len(today_records),
            "by_model": self._aggregate_by_model(today_records),
            "by_job": self._aggregate_by_job(today_records),
        }

    def get_total_usage(self) -> dict:
        """Get lifetime aggregated usage."""
        return {
            "total_cost": sum(r.estimated_cost for r in self._records),
            "total_input_tokens": sum(r.input_tokens for r in self._records),
            "total_output_tokens": sum(r.output_tokens for r in self._records),
            "invocations": len(self._records),
            "by_model": self._aggregate_by_model(self._records),
        }

    def update_cost_profile(self, model_id: str, input_cost_per_1k: float, output_cost_per_1k: float):
        """Update cost profile for a model."""
        self._cost_profiles[model_id] = ModelCostProfile(
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
        )

    def _aggregate_by_model(self, records: list[ModelUsageRecord]) -> dict:
        by_model: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "input_tokens": 0, "output_tokens": 0, "count": 0})
        for r in records:
            by_model[r.model_id]["cost"] += r.estimated_cost
            by_model[r.model_id]["input_tokens"] += r.input_tokens
            by_model[r.model_id]["output_tokens"] += r.output_tokens
            by_model[r.model_id]["count"] += 1
        return dict(by_model)

    def _aggregate_by_job(self, records: list[ModelUsageRecord]) -> dict:
        by_job: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "invocations": 0})
        for r in records:
            jid = r.job_id or "unknown"
            by_job[jid]["cost"] += r.estimated_cost
            by_job[jid]["invocations"] += 1
        return dict(by_job)

    def clear(self):
        """Clear all records."""
        self._records.clear()
