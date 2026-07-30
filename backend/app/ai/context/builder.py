"""AI Context Builder — transforms Sprint 2 AnalysisContext into AI-ready context.

Optimizes for token efficiency — summarizes large data structures,
extracts key metrics, and prepares variables for prompt rendering.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import structlog

from app.core.analysis_profile import AnalysisProfile, get_profile_for_settings

logger = structlog.get_logger(__name__)


@dataclass
class AIContext:
    """AI-ready context assembled from Sprint 2 analysis results.

    Contains token-efficient summaries — NOT raw source code.
    Structured for direct use in prompt template rendering.
    """
    job_id: str = ""
    project_name: str = ""

    project_metadata: dict = field(default_factory=dict)
    architecture_summary: dict = field(default_factory=dict)
    metrics_summary: dict = field(default_factory=dict)
    quality_summary: dict = field(default_factory=dict)
    dependency_summary: dict = field(default_factory=dict)
    risk_summary: dict = field(default_factory=dict)
    readiness_summary: dict = field(default_factory=dict)
    candidate_services: list[dict] = field(default_factory=list)
    bounded_contexts: list[dict] = field(default_factory=list)
    risk_findings: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)

    classes_summary: list[dict] = field(default_factory=list)
    endpoints_summary: list[dict] = field(default_factory=list)
    god_classes: list[dict] = field(default_factory=list)
    circular_dependencies: list[dict] = field(default_factory=list)

    estimated_tokens: int = 0

    def to_template_variables(self) -> dict:
        """Convert to flat dict suitable for prompt template rendering."""
        return {
            "project_name": self.project_name,
            "job_id": self.job_id,
            "build_tool": self.project_metadata.get("build_tool", "unknown"),
            "java_version": self.project_metadata.get("java_version", "unknown"),
            "spring_boot_version": self.project_metadata.get("spring_boot_version", "unknown"),
            "architecture_style": self.architecture_summary.get("primary_style", "unknown"),
            "architecture_score": self.architecture_summary.get("score", 0),
            "total_classes": self.metrics_summary.get("total_classes", 0),
            "total_lines": self.metrics_summary.get("total_lines", 0),
            "total_methods": self.metrics_summary.get("total_methods", 0),
            "total_endpoints": self.metrics_summary.get("total_endpoints", 0),
            "god_class_count": self.metrics_summary.get("god_class_count", 0),
            "long_method_count": self.metrics_summary.get("long_method_count", 0),
            "circular_dep_count": self.dependency_summary.get("circular_count", 0),
            "dependency_edge_count": self.dependency_summary.get("total_edges", 0),
            "high_coupling_count": self.dependency_summary.get("high_coupling_count", 0),
            "risk_count": self.risk_summary.get("total_findings", 0),
            "critical_count": self.risk_summary.get("critical", 0),
            "high_count": self.risk_summary.get("high", 0),
            "medium_count": self.risk_summary.get("medium", 0),
            "low_count": self.risk_summary.get("low", 0),
            "readiness_score": self.readiness_summary.get("overall", 0),
            "compute_readiness": self.readiness_summary.get("compute_readiness", {}).get("score", 0),
            "security_readiness": self.readiness_summary.get("security_readiness", {}).get("score", 0),
            "container_readiness": self.readiness_summary.get("container_readiness", {}).get("score", 0),
            "candidate_service_count": len(self.candidate_services),
            "overall_risk": self.risk_summary.get("overall_risk", "medium"),
            "migration_complexity": "moderate",
        }

    def to_json_summary(self, max_chars: int | None = None) -> str:
        """JSON summary of key data for embedding in prompts."""
        if max_chars is None:
            _profile = get_profile_for_settings()
            max_chars = _profile.json_summary_max_chars
        data = {
            "classes": self.classes_summary,
            "god_classes": self.god_classes,
            "endpoints": self.endpoints_summary,
            "circular_dependencies": self.circular_dependencies,
            "risk_findings": self.risk_findings,
            "candidate_services": self.candidate_services,
            "architecture": self.architecture_summary,
            "metrics": {k: v for k, v in self.metrics_summary.items()
                        if k in ("total_classes", "total_lines", "god_class_count",
                                 "long_method_count", "avg_cyclomatic_complexity",
                                 "duplicate_lines_percent")},
            "readiness": self.readiness_summary,
        }
        result = json.dumps(data, default=str)
        if len(result) > max_chars:
            result = result[:max_chars] + '..."'
        return result


class AIContextBuilder:
    """Builds AIContext from Sprint 2 AnalysisContext.

    Key principle: summarizes aggressively for token efficiency.
    Never includes raw source code unless explicitly required.
    """

    def __init__(self, profile: AnalysisProfile | None = None):
        self._profile = profile

    def _get_profile(self) -> AnalysisProfile:
        if self._profile is not None:
            return self._profile
        return get_profile_for_settings()

    def build(self, analysis_context: dict, job_id: str = "") -> AIContext:
        """Build AIContext from a Sprint 2 analysis result dict.

        Accepts the dict form of AnalysisResult (after to_dict()).
        """
        ctx = AIContext(job_id=job_id)

        ctx.project_metadata = self._extract_project_metadata(analysis_context)
        ctx.project_name = ctx.project_metadata.get("project_name", "Unknown Project")

        ctx.architecture_summary = self._summarize_architecture(analysis_context)
        ctx.metrics_summary = self._summarize_metrics(analysis_context)
        ctx.quality_summary = self._summarize_quality(analysis_context)
        ctx.dependency_summary = self._summarize_dependencies(analysis_context)
        ctx.risk_summary = self._summarize_risks(analysis_context)
        ctx.readiness_summary = self._summarize_readiness(analysis_context)

        ctx.classes_summary = self._summarize_classes(analysis_context)
        ctx.endpoints_summary = self._summarize_endpoints(analysis_context)
        ctx.god_classes = self._extract_god_classes(analysis_context)
        ctx.circular_dependencies = self._extract_circular_deps(analysis_context)
        ctx.risk_findings = self._extract_risk_findings(analysis_context)
        ctx.candidate_services = analysis_context.get("candidate_services", [])
        ctx.bounded_contexts = analysis_context.get("bounded_contexts", [])
        ctx.recommendations = analysis_context.get("recommendations", [])

        ctx.estimated_tokens = len(json.dumps(ctx.to_template_variables(), default=str)) // 4

        logger.info(
            "ai_context_built",
            job_id=job_id,
            estimated_tokens=ctx.estimated_tokens,
            classes=len(ctx.classes_summary),
            endpoints=len(ctx.endpoints_summary),
        )

        return ctx

    def build_from_analysis_result(self, result_dict: dict) -> AIContext:
        """Build from the full analysis results stored in S3."""
        return self.build(result_dict, job_id=result_dict.get("job_id", ""))

    def _extract_project_metadata(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        project_summary = sprint2.get("project_summary", {})
        return {
            "project_name": project_summary.get("project_name", "Unknown"),
            "build_tool": project_summary.get("build_tool", "unknown"),
            "java_version": project_summary.get("java_version", "unknown"),
            "spring_boot_version": project_summary.get("spring_boot_version", "unknown"),
            "total_java_files": project_summary.get("total_java_files", 0),
            "base_package": project_summary.get("base_package", ""),
        }

    def _summarize_architecture(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        arch = sprint2.get("architecture_summary", {})
        return {
            "primary_style": arch.get("primary_style", "unknown"),
            "score": arch.get("score", 0),
            "evidence": arch.get("evidence", []),
            "modularity_score": arch.get("modularity_score", 0),
        }

    def _summarize_metrics(self, data: dict) -> dict:
        metrics = data.get("metrics", {})
        sprint2 = data.get("sprint2_analysis", {})
        sprint2_metrics = sprint2.get("metrics", {})
        return {
            "total_classes": metrics.get("total_classes", sprint2_metrics.get("total_classes", 0)),
            "total_lines": metrics.get("total_lines", sprint2_metrics.get("total_lines", 0)),
            "total_methods": metrics.get("total_methods", sprint2_metrics.get("total_methods", 0)),
            "total_endpoints": len(data.get("endpoints", [])),
            "god_class_count": len(metrics.get("god_classes", [])),
            "long_method_count": len(metrics.get("long_methods", [])),
            "avg_cyclomatic_complexity": metrics.get("avg_cyclomatic_complexity", 0),
            "duplicate_lines_percent": metrics.get("duplicate_lines_percent", 0),
        }

    def _summarize_quality(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        return {
            "maintainability_score": sprint2.get("quality_metrics", {}).get("maintainability_score", 50),
            "complexity_score": sprint2.get("quality_metrics", {}).get("complexity_score", 50),
            "technical_debt_hours": sprint2.get("quality_metrics", {}).get("technical_debt_hours", 0),
            "overall_quality": sprint2.get("quality_metrics", {}).get("overall_quality", 50),
        }

    def _summarize_dependencies(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        dep_graph = sprint2.get("dependency_graph", {})
        coupling = sprint2.get("coupling_analysis", {})
        circular = data.get("metrics", {}).get("circular_dependencies", [])
        return {
            "total_edges": len(data.get("dependency_edges", [])),
            "circular_count": len(circular),
            "high_coupling_count": coupling.get("highly_coupled_count", 0),
            "avg_dependencies": coupling.get("avg_dependencies", 0),
            "max_dependencies": coupling.get("max_dependencies", 0),
        }

    def _summarize_risks(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        risk_summary = sprint2.get("risk_summary", {})
        return {
            "total_findings": risk_summary.get("total_findings", 0),
            "critical": risk_summary.get("critical", 0),
            "high": risk_summary.get("high", 0),
            "medium": risk_summary.get("medium", 0),
            "low": risk_summary.get("low", 0),
            "overall_risk": risk_summary.get("overall_risk", "medium"),
        }

    def _summarize_readiness(self, data: dict) -> dict:
        sprint2 = data.get("sprint2_analysis", {})
        return sprint2.get("readiness_scores", {})

    def _summarize_classes(self, data: dict) -> list[dict]:
        classes = data.get("classes", [])
        limit = self._get_profile().ai_max_classes
        summaries = []
        for c in classes[:limit]:
            summaries.append({
                "name": c.get("name", ""),
                "package": c.get("package", ""),
                "loc": c.get("lines_of_code", 0),
                "methods": c.get("method_count", 0),
                "injections": len(c.get("injected_fields", [])),
                "is_controller": c.get("is_controller", False),
                "is_service": c.get("is_service", False),
                "is_entity": c.get("is_entity", False),
                "is_repository": c.get("is_repository", False),
            })
        return summaries

    def _summarize_endpoints(self, data: dict) -> list[dict]:
        endpoints = data.get("endpoints", [])
        limit = self._get_profile().ai_max_endpoints
        return [
            {
                "method": e.get("method", ""),
                "path": e.get("path", ""),
                "handler_class": e.get("handler_class", ""),
            }
            for e in endpoints[:limit]
        ]

    def _extract_god_classes(self, data: dict) -> list[dict]:
        metrics = data.get("metrics", {})
        return [
            {
                "name": g.get("name", ""),
                "loc": g.get("lines_of_code", 0),
                "methods": g.get("method_count", 0),
                "injections": g.get("injected_dependencies", 0),
                "reason": g.get("reason", ""),
            }
            for g in metrics.get("god_classes", [])
        ]

    def _extract_circular_deps(self, data: dict) -> list[dict]:
        circular = data.get("metrics", {}).get("circular_dependencies", [])
        limit = self._get_profile().ai_max_circular_deps
        return [
            {
                "cycle": c.get("cycle", []),
                "type": c.get("type", ""),
            }
            for c in circular[:limit]
        ]

    def _extract_risk_findings(self, data: dict) -> list[dict]:
        sprint2 = data.get("sprint2_analysis", {})
        findings = sprint2.get("risk_findings", [])
        risk_limit = self._get_profile().ai_max_risk_findings
        comp_limit = self._get_profile().ai_max_affected_components
        return [
            {
                "rule_id": f.get("rule_id", ""),
                "title": f.get("title", ""),
                "severity": f.get("severity", ""),
                "description": f.get("description", ""),
                "affected_components": f.get("affected_components", [])[:comp_limit],
            }
            for f in findings[:risk_limit]
        ]
