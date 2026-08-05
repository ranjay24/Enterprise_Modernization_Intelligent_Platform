"""Recommendation Engine — discovers candidate services, bounded contexts, migration candidates."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


@dataclass
class Recommendation:
    title: str
    description: str
    priority: str = "medium"
    business_value: str = ""
    estimated_effort: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    category: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title, "description": self.description,
            "priority": self.priority, "business_value": self.business_value,
            "estimated_effort": self.estimated_effort, "confidence": self.confidence,
            "evidence": self.evidence, "dependencies": self.dependencies,
            "category": self.category,
        }


class RecommendationEngine(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="recommendation_engine", version="1.0.0", phase=AnalyzerPhase.RECOMMENDATION,
            description="Discovers candidate services, bounded contexts, and migration candidates",
            tags=["recommendation", "microservice", "bounded_context"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return len(context.recommendations) == 0

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        logger.info("generating_recommendations")

        candidates = self._discover_candidate_services(context)
        bounded = self._discover_bounded_contexts(context)
        migration = self._discover_migration_candidates(context)
        all_recs = candidates + bounded + migration

        context.recommendations = [r.to_dict() for r in all_recs]
        context.graph_data["candidate_services"] = [r.to_dict() for r in candidates]
        context.graph_data["bounded_contexts"] = [r.to_dict() for r in bounded]

        context.add_event(EventType.RECOMMENDATIONS_GENERATED.value, {"count": len(all_recs)})
        context.set_phase("recommendation")

        logger.info("recommendations_generated", total=len(all_recs))
        return context

    def _discover_candidate_services(self, ctx: AnalysisContext) -> list[Recommendation]:
        candidates = []
        pkg_groups: dict[str, list] = {}
        for c in ctx.parsed_classes:
            pkg_groups.setdefault(c.package or "default", []).append(c)

        for pkg, classes in pkg_groups.items():
            controllers = [c for c in classes if c.is_controller]
            services = [c for c in classes if c.is_service]
            repos = [c for c in classes if c.is_repository]
            entities = [c for c in classes if c.is_entity]

            if len(controllers) > 0 and (services or repos):
                candidates.append(Recommendation(
                    title=f"Extract {pkg} as Microservice",
                    description=f"Package {pkg} has {len(controllers)} controllers, {len(services)} services, {len(repos)} repositories — strong extraction candidate",
                    priority="high" if len(controllers) > 2 else "medium",
                    business_value="Independent deployment, scaling, team ownership",
                    estimated_effort=f"{len(classes) * 2} person-days",
                    confidence=min(0.95, 0.5 + len(controllers) * 0.1),
                    evidence=[f"Package: {pkg}", f"{len(controllers)} controllers", f"{len(services)} services"],
                    category="microservice_candidate",
                ))

        if not candidates:
            candidates = self._discover_service_layer_candidates(ctx)
        return candidates

    def _discover_service_layer_candidates(self, ctx: AnalysisContext) -> list[Recommendation]:
        """Fallback for layered packages (controllers/services/repos/entities split
        across separate packages): group each service with the controllers that use it
        and the repositories/entities it references."""
        candidates = []
        classes = {c.name: c for c in ctx.parsed_classes}
        services = [c for c in ctx.parsed_classes if c.is_service]
        for s in services:
            group = {s.name}
            for c in ctx.parsed_classes:
                if c.name == s.name:
                    continue
                if s.name in set(c.dependencies) or s.name in set(c.injected_fields):
                    group.add(c.name)
            group_classes = [classes[n] for n in group if n in classes]
            controllers = [c for c in group_classes if c.is_controller]
            repos = [c for c in group_classes if c.is_repository]
            entities = [c for c in group_classes if c.is_entity]
            if not (controllers or repos or entities):
                continue
            candidates.append(Recommendation(
                title=f"Extract {s.name} as Microservice",
                description=f"Service {s.name} is used by {len(controllers)} controller(s) with {len(repos)} repositories and {len(entities)} entities — strong extraction candidate",
                priority="high" if len(controllers) >= 2 else "medium",
                business_value="Independent deployment, scaling, team ownership",
                estimated_effort=f"{len(group_classes) * 2} person-days",
                confidence=min(0.95, 0.5 + len(controllers) * 0.1),
                evidence=[f"Service: {s.name}", f"{len(controllers)} controllers", f"{len(repos)} repositories", f"{len(entities)} entities"],
                category="microservice_candidate",
            ))
        return candidates

    def _discover_bounded_contexts(self, ctx: AnalysisContext) -> list[Recommendation]:
        contexts = []
        pkg_groups: dict[str, list] = {}
        for c in ctx.parsed_classes:
            pkg_groups.setdefault(c.package or "default", []).append(c)

        for pkg, classes in pkg_groups.items():
            entities = [c for c in classes if c.is_entity]
            services = [c for c in classes if c.is_service or c.is_repository]
            if entities and services:
                contexts.append(Recommendation(
                    title=f"Bounded Context: {pkg}",
                    description=f"Contains {len(entities)} entities and {len(services)} services — natural domain boundary",
                    priority="medium",
                    business_value="Clear domain boundaries for microservice extraction",
                    estimated_effort="Analysis and refinement",
                    confidence=min(0.85, 0.4 + len(entities) * 0.1),
                    evidence=[f"Entities: {[e.name for e in entities]}", f"Services: {len(services)}"],
                    category="bounded_context",
                ))

        if not contexts:
            contexts = self._discover_service_layer_contexts(ctx)
        return contexts

    def _discover_service_layer_contexts(self, ctx: AnalysisContext) -> list[Recommendation]:
        """Fallback for layered packages: bound each service with the entities it references."""
        contexts = []
        services = [c for c in ctx.parsed_classes if c.is_service]
        for s in services:
            s_deps = set(s.dependencies) | set(s.injected_fields)
            entities = [c for c in ctx.parsed_classes if c.is_entity and c.name in s_deps]
            if not entities:
                continue
            contexts.append(Recommendation(
                title=f"Bounded Context: {s.name}",
                description=f"Service {s.name} owns {len(entities)} entities — natural domain boundary",
                priority="medium",
                business_value="Clear domain boundaries for microservice extraction",
                estimated_effort="Analysis and refinement",
                confidence=min(0.85, 0.4 + len(entities) * 0.1),
                evidence=[f"Entities: {[e.name for e in entities]}", f"Service: {s.name}"],
                category="bounded_context",
            ))
        return contexts

    def _discover_migration_candidates(self, ctx: AnalysisContext) -> list[Recommendation]:
        candidates = []
        dep_graph = ctx.dependency_graph or {}
        highly_coupled = dep_graph.get("highly_coupled", [])

        profile = get_profile_for_settings()
        for hc in highly_coupled[:profile.rec_max_highly_coupled]:
            candidates.append(Recommendation(
                title=f"Refactor {hc['name']} Before Migration",
                description=f"{hc['name']} has {hc['dependency_count']} dependencies and {hc['injection_count']} injections",
                priority="high",
                business_value="Reduces migration risk and enables cleaner service extraction",
                estimated_effort="2-5 days per class",
                confidence=0.85,
                evidence=[f"Coupling score: {hc['coupling_score']}", f"Package: {hc['package']}"],
                category="migration_candidate",
            ))

        god_classes = ctx.metrics.get("god_classes", []) if ctx.metrics else []
        for gc in god_classes[:profile.rec_max_god_classes]:
            candidates.append(Recommendation(
                title=f"Decompose God Class: {gc.get('name', 'unknown')}",
                description=f"Class has {gc.get('lines_of_code', 0)} LOC and {gc.get('method_count', 0)} methods",
                priority="critical",
                business_value="Essential for microservice extraction",
                estimated_effort="1-3 weeks per class",
                confidence=0.90,
                evidence=[f"LOC: {gc.get('lines_of_code', 0)}", f"Methods: {gc.get('method_count', 0)}"],
                category="migration_candidate",
            ))
        return candidates
