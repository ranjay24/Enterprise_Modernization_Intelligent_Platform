"""Integration layer — bridges Sprint 2 AnalysisEngine with existing orchestrator."""

from __future__ import annotations

import structlog

from app.analysis.architecture.detector import ArchitectureDetector
from app.analysis.contracts.context import AnalysisContext
from app.analysis.dependency.graph import DependencyGraphAnalyzer
from app.analysis.engine import AnalysisEngine
from app.analysis.exporters.json_exporter import JSONExporter
from app.analysis.graph.generator import GraphGenerator
from app.analysis.metrics.code_metrics import CodeMetricsAnalyzer
from app.analysis.metrics.quality import QualityMetricsAnalyzer
from app.analysis.parser.java_parser import JavaParser
from app.analysis.readiness.engine import CloudReadinessAnalyzer
from app.analysis.recommendation.engine import RecommendationEngine
from app.analysis.risk.detector import RiskDetector
from app.analysis.scanner.project_scanner import ProjectScanner

logger = structlog.get_logger(__name__)


def create_engine() -> AnalysisEngine:
    """Create and configure a fully wired AnalysisEngine."""
    engine = AnalysisEngine()
    engine.register_many([
        ProjectScanner(),
        JavaParser(),
        CodeMetricsAnalyzer(),
        QualityMetricsAnalyzer(),
        DependencyGraphAnalyzer(),
        ArchitectureDetector(),
        RiskDetector(),
        CloudReadinessAnalyzer(),
        RecommendationEngine(),
        GraphGenerator(),
    ])
    return engine


def run_analysis(job_id: str, extracted_path: str) -> dict:
    """Run the full Sprint 2 analysis pipeline. Returns dict for storage."""
    engine = create_engine()
    context = AnalysisContext(job_id=job_id, extracted_path=extracted_path)
    result = engine.analyze(context)

    exporter = JSONExporter()
    return exporter.export_dict(result)
