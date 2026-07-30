"""AI Migration Plan contract — strongly typed migration model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MigrationPhase(str, Enum):
    WAVE_1 = "wave_1"
    WAVE_2 = "wave_2"
    WAVE_3 = "wave_3"
    WAVE_4 = "wave_4"
    WAVE_5 = "wave_5"


@dataclass
class EffortEstimate:
    """Effort estimation for a migration unit."""
    story_points: int = 0
    engineer_weeks: float = 0.0
    engineers_needed: int = 1
    complexity: str = "moderate"

    def to_dict(self) -> dict:
        return {
            "story_points": self.story_points,
            "engineer_weeks": self.engineer_weeks,
            "engineers_needed": self.engineers_needed,
            "complexity": self.complexity,
        }


@dataclass
class AIMigrationService:
    """A single service within a migration wave."""
    service_name: str = ""
    description: str = ""
    source_classes: list[str] = field(default_factory=list)
    effort: EffortEstimate | None = None
    risks: list[str] = field(default_factory=list)
    rollback_strategy: str = ""
    dependencies: list[str] = field(default_factory=list)
    aws_services: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "description": self.description,
            "source_classes": self.source_classes,
            "effort": self.effort.to_dict() if self.effort else None,
            "risks": self.risks,
            "rollback_strategy": self.rollback_strategy,
            "dependencies": self.dependencies,
            "aws_services": self.aws_services,
        }


@dataclass
class AIMigrationWave:
    """A single wave in the migration plan."""
    wave_number: int = 1
    name: str = ""
    phase: MigrationPhase = MigrationPhase.WAVE_1
    objectives: list[str] = field(default_factory=list)
    services: list[AIMigrationService] = field(default_factory=list)
    timeline_weeks: int = 4
    estimated_engineers: int = 2
    dependencies: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    migration_complexity: str = "moderate"
    total_effort: EffortEstimate | None = None
    rollback_considerations: list[str] = field(default_factory=list)
    validation_criteria: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "wave_number": self.wave_number,
            "name": self.name,
            "phase": self.phase.value,
            "objectives": self.objectives,
            "services": [s.to_dict() for s in self.services],
            "timeline_weeks": self.timeline_weeks,
            "estimated_engineers": self.estimated_engineers,
            "dependencies": self.dependencies,
            "risk_level": self.risk_level,
            "migration_complexity": self.migration_complexity,
            "total_effort": self.total_effort.to_dict() if self.total_effort else None,
            "rollback_considerations": self.rollback_considerations,
            "validation_criteria": self.validation_criteria,
        }


@dataclass
class AIMigrationPlan:
    """Complete AI-generated migration plan."""
    plan_id: str = field(default_factory=lambda: f"MP-{uuid.uuid4().hex[:8].upper()}")
    project_name: str = ""
    total_waves: int = 0
    total_weeks: int = 0
    total_services: int = 0
    waves: list[AIMigrationWave] = field(default_factory=list)
    recommended_order: list[str] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    overall_risk: str = "medium"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_id: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "project_name": self.project_name,
            "total_waves": self.total_waves,
            "total_weeks": self.total_weeks,
            "total_services": self.total_services,
            "waves": [w.to_dict() for w in self.waves],
            "recommended_order": self.recommended_order,
            "critical_path": self.critical_path,
            "prerequisites": self.prerequisites,
            "overall_risk": self.overall_risk,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AIMigrationPlan:
        waves = []
        for w in data.get("waves", []):
            services = []
            for s in w.get("services", []):
                effort = EffortEstimate(**s["effort"]) if s.get("effort") else None
                services.append(AIMigrationService(
                    service_name=s.get("service_name", ""),
                    description=s.get("description", ""),
                    source_classes=s.get("source_classes", []),
                    effort=effort,
                    risks=s.get("risks", []),
                    rollback_strategy=s.get("rollback_strategy", ""),
                    dependencies=s.get("dependencies", []),
                    aws_services=s.get("aws_services", []),
                ))
            total_effort = EffortEstimate(**w["total_effort"]) if w.get("total_effort") else None
            waves.append(AIMigrationWave(
                wave_number=w.get("wave_number", 1),
                name=w.get("name", ""),
                phase=MigrationPhase(w.get("phase", "wave_1")),
                objectives=w.get("objectives", []),
                services=services,
                timeline_weeks=w.get("timeline_weeks", 4),
                estimated_engineers=w.get("estimated_engineers", 2),
                dependencies=w.get("dependencies", []),
                risk_level=w.get("risk_level", "medium"),
                migration_complexity=w.get("migration_complexity", "moderate"),
                total_effort=total_effort,
                rollback_considerations=w.get("rollback_considerations", []),
                validation_criteria=w.get("validation_criteria", []),
            ))

        return cls(
            plan_id=data.get("plan_id", f"MP-{uuid.uuid4().hex[:8].upper()}"),
            project_name=data.get("project_name", ""),
            total_waves=data.get("total_waves", len(waves)),
            total_weeks=data.get("total_weeks", 0),
            total_services=data.get("total_services", 0),
            waves=waves,
            recommended_order=data.get("recommended_order", []),
            critical_path=data.get("critical_path", []),
            prerequisites=data.get("prerequisites", []),
            overall_risk=data.get("overall_risk", "medium"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            model_id=data.get("model_id", ""),
            prompt_version=data.get("prompt_version", ""),
        )
