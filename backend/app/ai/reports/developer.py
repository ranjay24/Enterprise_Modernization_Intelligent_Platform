"""AI Developer Report Generator — generates detailed engineering reports."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext
from app.ai.contracts.developer import (
    AIDeveloperReport,
    ArchitectureFinding,
    CodeQualityAssessment,
    DependencyAnalysis,
)
from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


class AIDeveloperReportGenerator:
    """Generates AI-powered developer reports."""

    def generate(self, ai_context: AIContext, parsed_response: dict) -> AIDeveloperReport:
        """Generate developer report from parsed AI response."""
        arch_findings = []
        for f in parsed_response.get("architecture_findings", []):
            arch_findings.append(ArchitectureFinding(
                finding_id=f.get("finding_id", ""),
                category=f.get("category", ""),
                title=f.get("title", ""),
                description=f.get("description", ""),
                affected_components=f.get("affected_components", []),
                severity=f.get("severity", "info"),
                recommendation=f.get("recommendation", ""),
            ))

        dep_analysis = None
        if parsed_response.get("dependency_analysis"):
            dep_data = parsed_response["dependency_analysis"]
            dep_analysis = DependencyAnalysis(
                total_dependencies=dep_data.get("total_dependencies", 0),
                circular_dependencies=dep_data.get("circular_dependencies", 0),
                highly_coupled_classes=dep_data.get("highly_coupled_classes", []),
                coupling_hotspots=dep_data.get("coupling_hotspots", []),
                recommendations=dep_data.get("recommendations", []),
            )

        code_quality = None
        if parsed_response.get("code_quality"):
            cq = parsed_response["code_quality"]
            code_quality = CodeQualityAssessment(
                overall_score=cq.get("overall_score", 0),
                maintainability_score=cq.get("maintainability_score", 0),
                complexity_score=cq.get("complexity_score", 0),
                technical_debt_hours=cq.get("technical_debt_hours", 0),
                duplication_percent=cq.get("duplication_percent", 0),
                god_class_count=cq.get("god_class_count", 0),
                long_method_count=cq.get("long_method_count", 0),
                issues=cq.get("issues", []),
            )

        return AIDeveloperReport(
            project_name=ai_context.project_name,
            architecture_findings=arch_findings,
            dependency_analysis=dep_analysis,
            code_quality=code_quality,
            key_findings=parsed_response.get("key_findings", []),
        )

    def generate_deterministic(self, ai_context: AIContext) -> AIDeveloperReport:
        profile = get_profile_for_settings()
        findings = []
        for i, gc in enumerate(ai_context.god_classes[:profile.report_max_dev_god_classes]):
            findings.append(ArchitectureFinding(
                finding_id=f"AF-{i+1:03d}",
                category="architecture",
                title=f"God Class: {gc.get('name', '')}",
                description=f"Class with {gc.get('loc', 0)} LOC and {gc.get('methods', 0)} methods",
                affected_components=[gc.get("name", "")],
                severity="high",
                recommendation="Decompose into smaller, focused classes",
            ))

        for i, cd in enumerate(ai_context.circular_dependencies[:profile.report_max_dev_circular_deps]):
            findings.append(ArchitectureFinding(
                finding_id=f"AF-{len(findings)+1:03d}",
                category="dependency",
                title="Circular Dependency Chain",
                description=f"Cycle: {' -> '.join(cd.get('cycle', [])[:profile.report_max_cycle_display])}",
                affected_components=cd.get("cycle", []),
                severity="high",
                recommendation="Break cycle using event-driven pattern or shared interface",
            ))

        dep_analysis = DependencyAnalysis(
            total_dependencies=ai_context.dependency_summary.get("total_edges", 0),
            circular_dependencies=ai_context.dependency_summary.get("circular_count", 0),
            coupling_hotspots=ai_context.dependency_summary.get("high_coupling_count", []),
        )

        quality = ai_context.quality_summary
        code_quality = CodeQualityAssessment(
            overall_score=quality.get("overall_quality", 50),
            maintainability_score=quality.get("maintainability_score", 50),
            complexity_score=quality.get("complexity_score", 50),
            technical_debt_hours=quality.get("technical_debt_hours", 0),
            god_class_count=len(ai_context.god_classes),
            long_method_count=ai_context.metrics_summary.get("long_method_count", 0),
        )

        return AIDeveloperReport(
            project_name=ai_context.project_name,
            architecture_findings=findings,
            dependency_analysis=dep_analysis,
            code_quality=code_quality,
            key_findings=[
                f"Identified {len(ai_context.god_classes)} god classes requiring decomposition",
                f"Found {len(ai_context.circular_dependencies)} circular dependency chains",
                f"Overall code quality score: {quality.get('overall_quality', 50)}/100",
            ],
        )
