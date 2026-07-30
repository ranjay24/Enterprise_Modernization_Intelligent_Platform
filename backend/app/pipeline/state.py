"""Pipeline state — rich status tracking for every stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PipelineStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CACHED = "cached"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class StageState:
    """State of a single pipeline stage."""
    stage_name: str = ""
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: float = 0.0
    artifact_key: str | None = None
    artifact_id: str | None = None
    error: str | None = None
    retry_count: int = 0
    is_degraded: bool = False
    tokens_used: int = 0
    cost_estimate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "artifact_key": self.artifact_key,
            "artifact_id": self.artifact_id,
            "error": self.error,
            "retry_count": self.retry_count,
            "is_degraded": self.is_degraded,
            "tokens_used": self.tokens_used,
            "cost_estimate": self.cost_estimate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StageState:
        return cls(
            stage_name=data.get("stage_name", ""),
            status=PipelineStatus(data.get("status", "pending")),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms", 0.0),
            artifact_key=data.get("artifact_key"),
            artifact_id=data.get("artifact_id"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            is_degraded=data.get("is_degraded", False),
            tokens_used=data.get("tokens_used", 0),
            cost_estimate=data.get("cost_estimate", 0.0),
        )


# Maps pipeline stage names to progress percentages
STAGE_PROGRESS: dict[str, int] = {
    "extraction": 10,
    "static_analysis": 20,
    "enterprise_analysis": 30,
    "ai_boundaries": 40,
    "ai_readiness": 50,
    "ai_adrs": 60,
    "ai_migration": 70,
    "ai_cost": 75,
    "ai_explainability": 80,
    "results_assembly": 85,
    "report_generation": 90,
    "manifest": 95,
}


@dataclass
class PipelineState:
    """Complete state of a pipeline execution."""
    job_id: str = ""
    status: str = "pending"
    current_stage: str = ""
    progress: int = 0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    total_duration_ms: float = 0.0
    stages: dict[str, StageState] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    is_degraded: bool = False
    degraded_stages: list[str] = field(default_factory=list)
    total_artifacts: int = 0
    total_reports: int = 0
    # Sprint 5: parallel execution metrics
    parallel_execution: bool = False
    execution_layers: list[list[str]] = field(default_factory=list)
    max_concurrency: int = 1
    contention_events: int = 0
    scheduling_overhead_ms: float = 0.0
    layer_timings: dict[str, float] = field(default_factory=dict)

    def mark_started(self, stage_name: str) -> None:
        self.current_stage = stage_name
        self.status = "running"
        state = StageState(
            stage_name=stage_name,
            status=PipelineStatus.STARTED,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.stages[stage_name] = state
        self.progress = STAGE_PROGRESS.get(stage_name, self.progress)

    def mark_completed(self, stage_name: str, artifact_key: str = "", artifact_id: str = "") -> None:
        state = self.stages.get(stage_name)
        if state:
            state.status = PipelineStatus.COMPLETED
            state.completed_at = datetime.now(timezone.utc).isoformat()
            state.artifact_key = artifact_key
            state.artifact_id = artifact_id
            if state.started_at:
                from datetime import datetime as dt
                start = dt.fromisoformat(state.started_at)
                end = dt.fromisoformat(state.completed_at)
                state.duration_ms = (end - start).total_seconds() * 1000
        self.total_artifacts += 1

    def mark_failed(self, stage_name: str, error: str) -> None:
        state = self.stages.get(stage_name)
        if state:
            state.status = PipelineStatus.FAILED
            state.completed_at = datetime.now(timezone.utc).isoformat()
            state.error = error
        self.errors.append({"stage": stage_name, "error": error, "timestamp": datetime.now(timezone.utc).isoformat()})

    def mark_skipped(self, stage_name: str) -> None:
        state = self.stages.get(stage_name)
        if state:
            state.status = PipelineStatus.SKIPPED

    def mark_cached(self, stage_name: str, artifact_key: str = "") -> None:
        state = self.stages.get(stage_name)
        if state:
            state.status = PipelineStatus.CACHED
            state.artifact_key = artifact_key
        self.total_artifacts += 1

    def has_completed(self, stage_name: str) -> bool:
        state = self.stages.get(stage_name)
        return state is not None and state.status in (
            PipelineStatus.COMPLETED, PipelineStatus.CACHED
        )

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.status = "completed" if not self.errors else "completed_with_errors"
        if self.started_at:
            from datetime import datetime as dt
            start = dt.fromisoformat(self.started_at)
            end = dt.fromisoformat(self.completed_at)
            self.total_duration_ms = (end - start).total_seconds() * 1000

    def finalize_failed(self, error: str) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.status = "failed"
        self.errors.append({"error": error, "timestamp": self.completed_at})

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "progress": self.progress,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "errors": self.errors,
            "is_degraded": self.is_degraded,
            "degraded_stages": self.degraded_stages,
            "total_artifacts": self.total_artifacts,
            "total_reports": self.total_reports,
            "parallel_execution": self.parallel_execution,
            "execution_layers": self.execution_layers,
            "max_concurrency": self.max_concurrency,
            "contention_events": self.contention_events,
            "scheduling_overhead_ms": self.scheduling_overhead_ms,
            "layer_timings": self.layer_timings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PipelineState:
        return cls(
            job_id=data.get("job_id", ""),
            status=data.get("status", "pending"),
            current_stage=data.get("current_stage", ""),
            progress=data.get("progress", 0),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            stages={k: StageState.from_dict(v) for k, v in data.get("stages", {}).items()},
            errors=data.get("errors", []),
            is_degraded=data.get("is_degraded", False),
            degraded_stages=data.get("degraded_stages", []),
            total_artifacts=data.get("total_artifacts", 0),
            total_reports=data.get("total_reports", 0),
            parallel_execution=data.get("parallel_execution", False),
            execution_layers=data.get("execution_layers", []),
            max_concurrency=data.get("max_concurrency", 1),
            contention_events=data.get("contention_events", 0),
            scheduling_overhead_ms=data.get("scheduling_overhead_ms", 0.0),
            layer_timings=data.get("layer_timings", {}),
        )
