"""Architecture Detector — infers architectural style from code structure."""

from __future__ import annotations

import structlog

from app.analysis.architecture.patterns import PATTERNS, ArchitecturePattern
from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType

logger = structlog.get_logger(__name__)


class ArchitectureDetector(Analyzer):
    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="architecture_detector", version="1.0.0", phase=AnalyzerPhase.ARCHITECTURE,
            description="Infers architectural style (layered, clean, hexagonal, modular monolith)",
            tags=["architecture", "pattern", "detection"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return context.architecture_style is None

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        classes = context.parsed_classes
        pkg_tree = context.metrics.get("package_tree", {}) if context.metrics else {}
        dep_graph = context.dependency_graph or {}
        circular_count = dep_graph.get("circular_count", 0)

        all_packages = set(c.package.lower() for c in classes if c.package)
        all_annotations = set()
        for c in classes:
            all_annotations.update(c.annotations)

        scores: dict[str, float] = {}
        detected_patterns: list[dict] = []

        for pattern in PATTERNS:
            score = self._score_pattern(pattern, classes, all_packages, all_annotations, circular_count, dep_graph)
            scores[pattern.name] = round(score, 2)
            if score > 0.3:
                detected_patterns.append({
                    "name": pattern.name,
                    "description": pattern.description,
                    "confidence": round(score, 2),
                })

        primary = max(scores, key=scores.get) if scores else "traditional_monolith"
        primary_score = scores.get(primary, 0)

        style = {
            "primary_style": primary,
            "primary_confidence": primary_score,
            "all_scores": scores,
            "detected_patterns": sorted(detected_patterns, key=lambda x: x["confidence"], reverse=True),
            "layered_evidence": self._layered_evidence(classes),
            "circular_dependencies_count": circular_count,
            "modularity_score": self._modularity_score(classes, dep_graph),
        }

        context.architecture_style = style
        context.architecture_scores = scores

        context.add_event(EventType.ARCHITECTURE_DETECTED.value, {"primary": primary, "confidence": primary_score})
        context.set_phase("architecture")

        logger.info("architecture_detected", primary=primary, confidence=primary_score, patterns=len(detected_patterns))
        return context

    def _score_pattern(self, pattern: ArchitecturePattern, classes, packages, annotations, circular_count, dep_graph) -> float:
        score = 0.0

        for indicator in pattern.indicators:
            matching_packages = [p for p in packages if indicator in p]
            if matching_packages:
                score += 0.15
            matching_annotations = [a for a in annotations if indicator.lower() in a.lower()]
            if matching_annotations:
                score += 0.10

        if pattern.name == "layered_architecture":
            has_controllers = any(c.is_controller for c in classes)
            has_services = any(c.is_service for c in classes)
            has_repositories = any(c.is_repository for c in classes)
            if has_controllers and has_services and has_repositories:
                score += 0.30
            if has_controllers and has_services:
                score += 0.15
            layered_pkgs = sum(1 for p in packages if any(x in p for x in ["controller", "service", "repository", "dao"]))
            if layered_pkgs >= 3:
                score += 0.15

        if pattern.name == "clean_architecture":
            domain_pkgs = sum(1 for p in packages if "domain" in p)
            if domain_pkgs > 0:
                score += 0.20

        if pattern.name == "hexagonal_architecture":
            port_pkgs = sum(1 for p in packages if "port" in p or "adapter" in p)
            if port_pkgs > 0:
                score += 0.25

        if pattern.name == "modular_monolith":
            module_pkgs = sum(1 for p in packages if "module" in p)
            if module_pkgs >= 2:
                score += 0.25
            if circular_count > 0:
                score -= 0.10

        if pattern.name == "traditional_monolith":
            unstructured = sum(1 for p in packages if not any(x in p for x in ["controller", "service", "repository", "model", "dto", "domain"]))
            if unstructured > len(packages) * 0.5:
                score += 0.40
            if circular_count > 2:
                score += 0.10

        return min(1.0, max(0.0, score))

    def _layered_evidence(self, classes) -> dict:
        return {
            "controllers": len([c for c in classes if c.is_controller]),
            "services": len([c for c in classes if c.is_service]),
            "repositories": len([c for c in classes if c.is_repository]),
            "entities": len([c for c in classes if c.is_entity]),
            "dtos": len([c for c in classes if c.is_dto]),
            "configurations": len([c for c in classes if c.is_configuration]),
        }

    def _modularity_score(self, classes, dep_graph) -> float:
        if not classes:
            return 0.0
        pkg_coupling = dep_graph.get("package_dependencies", {})
        coupled_pkgs = len([v for v in pkg_coupling.values() if v])
        total_pkgs = len(set(c.package for c in classes if c.package)) or 1
        return round(max(0, 100 - (coupled_pkgs / total_pkgs * 100)), 1)
