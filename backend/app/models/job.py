"""Internal domain model for jobs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class JobDomain:
    """Internal domain representation of a job."""
    job_id: str
    status: str
    filename: str
    file_size: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    progress: int = 0
    current_phase: str | None = None
    error: str | None = None
    # Sprint 5 — codegen progress persistence (P2.4)
    codegen_stage: str | None = None
    # Sprint 4 — async pipeline
    checkpoint_phase: str | None = None
    retry_count: int = 0
    worker_id: str | None = None
    event_id: str | None = None
    is_degraded: bool = False
    degraded_stages: list[str] = field(default_factory=list)
    completed_phases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "filename": self.filename,
            "file_size": self.file_size,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "current_phase": self.current_phase,
            "error": self.error,
            "codegen_stage": self.codegen_stage,
            "checkpoint_phase": self.checkpoint_phase,
            "retry_count": self.retry_count,
            "worker_id": self.worker_id,
            "event_id": self.event_id,
            "is_degraded": self.is_degraded,
            "degraded_stages": self.degraded_stages,
            "completed_phases": self.completed_phases,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobDomain":
        return cls(
            job_id=data["job_id"],
            status=data["status"],
            filename=data["filename"],
            file_size=data.get("file_size", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            progress=data.get("progress", 0),
            current_phase=data.get("current_phase"),
            error=data.get("error"),
            codegen_stage=data.get("codegen_stage"),
            checkpoint_phase=data.get("checkpoint_phase"),
            retry_count=data.get("retry_count", 0),
            worker_id=data.get("worker_id"),
            event_id=data.get("event_id"),
            is_degraded=data.get("is_degraded", False),
            degraded_stages=data.get("degraded_stages", []),
            completed_phases=data.get("completed_phases", []),
        )
