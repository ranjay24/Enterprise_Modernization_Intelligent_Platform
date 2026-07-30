"""Artifact models — versioned outputs from pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

ARTIFACT_SCHEMA_VERSION = "1.0.0"


@dataclass
class ArtifactMetadata:
    """Metadata attached to every artifact for traceability."""
    artifact_id: str = ""
    artifact_type: str = ""
    artifact_version: str = "1.0.0"
    analysis_version: str = "2.0.0"
    job_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generator: str = ""
    model_id: str = ""
    platform_version: str = "1.0.0"
    checksum: str = ""
    size_bytes: int = 0
    phase_duration_ms: float = 0.0
    is_degraded: bool = False
    parent_artifact_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "artifact_version": self.artifact_version,
            "analysis_version": self.analysis_version,
            "job_id": self.job_id,
            "generated_at": self.generated_at,
            "generator": self.generator,
            "model_id": self.model_id,
            "platform_version": self.platform_version,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "phase_duration_ms": self.phase_duration_ms,
            "is_degraded": self.is_degraded,
            "parent_artifact_ids": self.parent_artifact_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArtifactMetadata:
        return cls(
            artifact_id=data.get("artifact_id", ""),
            artifact_type=data.get("artifact_type", ""),
            artifact_version=data.get("artifact_version", "1.0.0"),
            analysis_version=data.get("analysis_version", "2.0.0"),
            job_id=data.get("job_id", ""),
            generated_at=data.get("generated_at", ""),
            generator=data.get("generator", ""),
            model_id=data.get("model_id", ""),
            platform_version=data.get("platform_version", "1.0.0"),
            checksum=data.get("checksum", ""),
            size_bytes=data.get("size_bytes", 0),
            phase_duration_ms=data.get("phase_duration_ms", 0.0),
            is_degraded=data.get("is_degraded", False),
            parent_artifact_ids=data.get("parent_artifact_ids", []),
        )


@dataclass
class Artifact:
    """A single versioned output from a pipeline stage."""
    metadata: ArtifactMetadata = field(default_factory=ArtifactMetadata)
    content: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Artifact:
        return cls(
            metadata=ArtifactMetadata.from_dict(data.get("metadata", {})),
            content=data.get("content", {}),
        )


@dataclass
class ArtifactManifest:
    """Complete manifest for an analysis run — every artifact, every detail."""
    job_id: str = ""
    project_name: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""
    total_duration_ms: float = 0.0
    platform_version: str = "1.0.0"
    analysis_version: str = "2.0.0"
    engine_version: str = "1.0.0"
    artifacts: list[ArtifactMetadata] = field(default_factory=list)
    reports: list[ArtifactMetadata] = field(default_factory=list)
    pipeline_state: dict = field(default_factory=dict)
    ai_summary: dict = field(default_factory=dict)
    checksum: str = ""

    def to_dict(self) -> dict:
        return {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "job_id": self.job_id,
            "project_name": self.project_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "platform_version": self.platform_version,
            "analysis_version": self.analysis_version,
            "engine_version": self.engine_version,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "reports": [r.to_dict() for r in self.reports],
            "pipeline_state": self.pipeline_state,
            "ai_summary": self.ai_summary,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ArtifactManifest:
        return cls(
            job_id=data.get("job_id", ""),
            project_name=data.get("project_name", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            platform_version=data.get("platform_version", "1.0.0"),
            analysis_version=data.get("analysis_version", "2.0.0"),
            engine_version=data.get("engine_version", "1.0.0"),
            artifacts=[ArtifactMetadata.from_dict(a) for a in data.get("artifacts", [])],
            reports=[ArtifactMetadata.from_dict(r) for r in data.get("reports", [])],
            pipeline_state=data.get("pipeline_state", {}),
            ai_summary=data.get("ai_summary", {}),
            checksum=data.get("checksum", ""),
        )
