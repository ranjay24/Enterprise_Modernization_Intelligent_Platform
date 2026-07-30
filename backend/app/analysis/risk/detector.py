"""Risk Detector — orchestrates the rule engine to detect migration risks."""

from __future__ import annotations

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.analysis.rules.circular_dependency_rule import CircularDependencyRule
from app.analysis.rules.engine import RuleEngine, Severity
from app.analysis.rules.god_class_rule import GodClassRule
from app.analysis.rules.hardcoded_config_rule import HardcodedConfigRule
from app.analysis.rules.long_method_rule import LongMethodRule
from app.analysis.rules.unused_code_rule import UnusedCodeRule

logger = structlog.get_logger(__name__)


class RiskDetector(Analyzer):
    def __init__(self) -> None:
        self._rule_engine = RuleEngine()
        self._rule_engine.register_many([
            GodClassRule(),
            CircularDependencyRule(),
            LongMethodRule(),
            HardcodedConfigRule(),
            UnusedCodeRule(),
        ])

    @property
    def rule_engine(self) -> RuleEngine:
        return self._rule_engine

    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="risk_detector", version="1.0.0", phase=AnalyzerPhase.RISK,
            description="Detects migration risks using a pluggable rule engine",
            tags=["risk", "rules", "quality"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return len(context.risk_findings) == 0

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        logger.info("running_risk_detection")
        findings = self._rule_engine.execute(context)

        severity_counts = {s.value: 0 for s in Severity}
        for f in findings:
            severity_counts[f.severity.value] += 1

        summary = {
            "total_findings": len(findings),
            "by_severity": severity_counts,
            "critical_count": severity_counts["critical"],
            "high_count": severity_counts["high"],
            "medium_count": severity_counts["medium"],
            "low_count": severity_counts["low"],
            "categories": list(set(f.category for f in findings)),
            "rules_evaluated": len(self._rule_engine.rules),
        }

        context.risk_findings = [f.to_dict() for f in findings]
        context.risk_summary = summary

        context.add_event(EventType.RISKS_DETECTED.value, {"total": len(findings), "critical": severity_counts["critical"]})
        context.set_phase("risk")

        logger.info("risk_detection_complete", total=len(findings), critical=severity_counts["critical"])
        return context
