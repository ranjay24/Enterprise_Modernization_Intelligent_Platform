"""AnalysisEngine — plugin-based orchestrator for analysis modules."""

from __future__ import annotations

import time
import tracemalloc

import structlog

from app.analysis.cache.store import AnalysisCache
from app.analysis.contracts.analyzer import Analyzer
from app.analysis.contracts.context import AnalysisContext
from app.analysis.contracts.result import AnalysisResult
from app.analysis.events.bus import EventBus, EventType

logger = structlog.get_logger(__name__)

ENGINE_VERSION = "1.0.0"
ANALYSIS_VERSION = "2.0.0"
RULES_VERSION = "1.0.0"


class AnalysisEngine:
    """Plugin-based engine that orchestrates Analyzer instances."""

    def __init__(self) -> None:
        self._analyzers: list[Analyzer] = []
        self._event_bus = EventBus()
        self._cache = AnalysisCache()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def cache(self) -> AnalysisCache:
        return self._cache

    def register(self, analyzer: Analyzer) -> None:
        meta = analyzer.metadata()
        logger.info("analyzer_registered", name=meta.name, phase=meta.phase.value)
        self._analyzers.append(analyzer)

    def register_many(self, analyzers: list[Analyzer]) -> None:
        for a in analyzers:
            self.register(a)

    def _sorted_analyzers(self) -> list[Analyzer]:
        phase_order = [
            "scanner", "parser", "metrics", "dependency",
            "architecture", "risk", "readiness", "recommendation", "graph",
        ]
        def sort_key(a: Analyzer) -> int:
            phase = a.metadata().phase.value
            return phase_order.index(phase) if phase in phase_order else 99
        return sorted(self._analyzers, key=sort_key)

    def analyze(self, context: AnalysisContext) -> AnalysisResult:
        tracemalloc.start()
        start = time.time()

        self._event_bus.emit(
            EventType.ANALYSIS_STARTED,
            source="engine",
            data={"job_id": context.job_id},
        )

        ordered = self._sorted_analyzers()
        phases_completed: list[str] = []

        for analyzer in ordered:
            meta = analyzer.metadata()
            phase_name = meta.phase.value

            if context.has_phase(phase_name):
                continue

            if not analyzer.supports(context):
                logger.info("analyzer_skipped", name=meta.name, reason="unsupported")
                continue

            unmet = analyzer.validate_prerequisites(context)
            if unmet:
                logger.warning("analyzer_prerequisites_unmet", name=meta.name, unmet=unmet)
                context.add_error(meta.name, f"Unmet prerequisites: {unmet}")
                continue

            self._event_bus.emit(
                EventType.ANALYZER_STARTED,
                source=meta.name,
                data={"phase": phase_name},
            )

            try:
                context = analyzer.analyze(context)
                context.set_phase(phase_name)
                phases_completed.append(phase_name)

                self._event_bus.emit(
                    EventType.ANALYZER_COMPLETED,
                    source=meta.name,
                    data={"phase": phase_name},
                )
            except Exception as exc:
                logger.error("analyzer_failed", name=meta.name, error=str(exc))
                context.add_error(meta.name, str(exc))
                self._event_bus.emit(
                    EventType.ANALYZER_FAILED,
                    source=meta.name,
                    data={"phase": phase_name, "error": str(exc)},
                )

        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        duration_ms = round((time.time() - start) * 1000, 2)
        memory_mb = round(peak_memory / (1024 * 1024), 2)

        result = self._build_result(context, phases_completed, duration_ms, memory_mb)

        self._event_bus.emit(
            EventType.ANALYSIS_COMPLETED,
            source="engine",
            data={"job_id": context.job_id, "duration_ms": duration_ms},
        )

        return result

    def _build_result(
        self,
        context: AnalysisContext,
        phases_completed: list[str],
        duration_ms: float,
        memory_mb: float,
    ) -> AnalysisResult:
        overall_score = self._compute_overall_score(context)
        complexity = self._estimate_migration_complexity(context)

        return AnalysisResult(
            job_id=context.job_id,
            analysis_version=ANALYSIS_VERSION,
            engine_version=ENGINE_VERSION,
            rules_version=RULES_VERSION,
            project_summary=context.project_metadata or {},
            architecture_summary=context.architecture_style or {},
            metrics=context.metrics,
            quality_metrics=context.quality_metrics,
            readiness_scores=context.readiness_scores,
            readiness_dimensions=context.readiness_dimensions,
            risk_report={
                "findings": context.risk_findings,
                "summary": context.risk_summary or {},
                "total": len(context.risk_findings),
            },
            dependency_graph=context.dependency_graph or {},
            architecture_graph=context.graph_data.get("architecture", {}),
            candidate_services=context.graph_data.get("candidate_services", []),
            bounded_contexts=context.graph_data.get("bounded_contexts", []),
            recommendations=context.recommendations,
            confidence_scores=context.architecture_scores,
            overall_modernization_score=overall_score,
            migration_complexity=complexity,
            analysis_duration_ms=duration_ms,
            memory_usage_mb=memory_mb,
            phases_completed=phases_completed,
            errors=context.errors,
            graph_data=context.graph_data,
        )

    def _compute_overall_score(self, ctx: AnalysisContext) -> float:
        weights = {
            "readiness": 0.30,
            "quality": 0.25,
            "architecture": 0.20,
            "risk": 0.15,
            "dependency": 0.10,
        }
        scores: dict[str, float] = {}

        if ctx.readiness_scores:
            scores["readiness"] = ctx.readiness_scores.get("overall", 50)
        if ctx.quality_metrics:
            scores["quality"] = ctx.quality_metrics.get("maintainability_score", 50)
        if ctx.architecture_scores:
            avg = sum(ctx.architecture_scores.values()) / len(ctx.architecture_scores) if ctx.architecture_scores else 50
            scores["architecture"] = avg
        if ctx.risk_findings:
            critical = sum(1 for r in ctx.risk_findings if r.get("severity") == "critical")
            high = sum(1 for r in ctx.risk_findings if r.get("severity") == "high")
            risk_score = max(0, 100 - (critical * 20) - (high * 10))
            scores["risk"] = risk_score
        if ctx.dependency_graph:
            scores["dependency"] = 100 - min(100, ctx.dependency_graph.get("circular_count", 0) * 15)

        if not scores:
            return 0.0

        total_weight = sum(weights[k] for k in scores if k in weights)
        if total_weight == 0:
            return 0.0

        weighted = sum(scores[k] * weights[k] for k in scores if k in weights)
        return round(weighted / total_weight, 1)

    def _estimate_migration_complexity(self, ctx: AnalysisContext) -> str:
        score = self._compute_overall_score(ctx)
        risk_count = len(ctx.risk_findings)
        circular = ctx.dependency_graph.get("circular_count", 0) if ctx.dependency_graph else 0

        if score >= 75 and risk_count < 5 and circular == 0:
            return "low"
        if score >= 50 and risk_count < 15:
            return "medium"
        if score >= 25:
            return "high"
        return "critical"
