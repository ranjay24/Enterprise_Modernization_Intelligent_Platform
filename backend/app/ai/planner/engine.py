"""AI Migration Planner — generates phased migration plans."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext
from app.ai.contracts.migration import (
    AIMigrationPlan,
    AIMigrationService,
    AIMigrationWave,
    EffortEstimate,
    MigrationPhase,
)
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


class AIMigrationPlanner:
    """Generates AI-powered phased migration plans."""

    def generate(self, ai_context: AIContext, parsed_response: dict) -> AIMigrationPlan:
        """Generate migration plan from parsed AI response."""
        waves = []
        for wave_data in parsed_response.get("waves", []):
            try:
                wave = self._build_wave(wave_data)
                waves.append(wave)
            except Exception as exc:
                logger.warning("wave_build_failed", error=str(exc))

        total_services = sum(len(w.services) for w in waves)
        total_weeks = sum(w.timeline_weeks for w in waves)

        return AIMigrationPlan(
            project_name=ai_context.project_name,
            total_waves=len(waves),
            total_weeks=total_weeks,
            total_services=total_services,
            waves=waves,
            recommended_order=parsed_response.get("recommended_order", []),
            critical_path=parsed_response.get("critical_path", []),
        )

    def generate_deterministic(self, ai_context: AIContext) -> AIMigrationPlan:
        """Generate migration plan without AI — fallback."""
        services = ai_context.candidate_services
        waves = []
        profile = get_profile_for_settings()

        low_risk = [s for s in services if s.get("risk_level") == "low"]
        med_risk = [s for s in services if s.get("risk_level") == "medium"]
        high_risk = [s for s in services if s.get("risk_level") in ("high", "critical")]

        if low_risk:
            wave_services = [
                AIMigrationService(
                    service_name=s.get("name", ""),
                    description=s.get("description", ""),
                    source_classes=s.get("classes", []),
                    risks=[],
                )
                for s in low_risk[:profile.planner_max_low_risk]
            ]
            waves.append(AIMigrationWave(
                wave_number=1, name="Foundation Services",
                phase=MigrationPhase.WAVE_1,
                objectives=["Extract low-risk services", "Establish deployment pipeline"],
                services=wave_services,
                timeline_weeks=4, estimated_engineers=2,
                risk_level="low",
            ))

        if med_risk:
            wave_services = [
                AIMigrationService(
                    service_name=s.get("name", ""),
                    description=s.get("description", ""),
                    source_classes=s.get("classes", []),
                )
                for s in med_risk[:profile.planner_max_med_risk]
            ]
            waves.append(AIMigrationWave(
                wave_number=2, name="Core Services",
                phase=MigrationPhase.WAVE_2,
                objectives=["Extract medium-risk services"],
                services=wave_services,
                timeline_weeks=6, estimated_engineers=3,
                risk_level="medium",
            ))

        if high_risk:
            wave_services = [
                AIMigrationService(
                    service_name=s.get("name", ""),
                    description=s.get("description", ""),
                    source_classes=s.get("classes", []),
                )
                for s in high_risk[:profile.planner_max_high_risk]
            ]
            waves.append(AIMigrationWave(
                wave_number=3, name="Complex Services",
                phase=MigrationPhase.WAVE_3,
                objectives=["Extract high-risk services", "Break circular dependencies"],
                services=wave_services,
                timeline_weeks=8, estimated_engineers=3,
                risk_level="high",
            ))

        total_services = sum(len(w.services) for w in waves)
        total_weeks = sum(w.timeline_weeks for w in waves)

        return AIMigrationPlan(
            project_name=ai_context.project_name,
            total_waves=len(waves),
            total_weeks=total_weeks,
            total_services=total_services,
            waves=waves,
            recommended_order=[w.name for w in waves],
        )

    def _build_wave(self, data: dict) -> AIMigrationWave:
        services = []
        for s in data.get("services", []):
            effort = None
            if s.get("effort"):
                effort = EffortEstimate(**s["effort"])
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

        total_effort = None
        if data.get("total_effort"):
            total_effort = EffortEstimate(**data["total_effort"])

        return AIMigrationWave(
            wave_number=data.get("wave_number", 1),
            name=data.get("name", ""),
            phase=MigrationPhase(data.get("phase", "wave_1")),
            objectives=data.get("objectives", []),
            services=services,
            timeline_weeks=data.get("timeline_weeks", 4),
            estimated_engineers=data.get("estimated_engineers", 2),
            dependencies=data.get("dependencies", []),
            risk_level=data.get("risk_level", "medium"),
            migration_complexity=data.get("migration_complexity", "moderate"),
            total_effort=total_effort,
            rollback_considerations=data.get("rollback_considerations", []),
            validation_criteria=data.get("validation_criteria", []),
        )
