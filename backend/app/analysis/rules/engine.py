"""Rule Engine — executes registered rules against the AnalysisContext."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from app.analysis.contracts.context import AnalysisContext

logger = structlog.get_logger(__name__)


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFinding:
    rule_id: str
    title: str
    severity: Severity
    category: str
    description: str
    impact: str
    recommended_fix: str
    confidence: float
    affected_components: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id, "title": self.title,
            "severity": self.severity.value, "category": self.category,
            "description": self.description, "impact": self.impact,
            "recommended_fix": self.recommended_fix, "confidence": self.confidence,
            "affected_components": self.affected_components, "evidence": self.evidence,
        }


class Rule(ABC):
    @abstractmethod
    def rule_id(self) -> str: ...

    @abstractmethod
    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]: ...

    def supports(self, context: AnalysisContext) -> bool:
        return True


class RuleEngine:
    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def register_many(self, rules: list[Rule]) -> None:
        self._rules.extend(rules)

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    def execute(self, context: AnalysisContext) -> list[RiskFinding]:
        findings: list[RiskFinding] = []
        for rule in self._rules:
            if not rule.supports(context):
                continue
            try:
                rule_findings = rule.evaluate(context)
                findings.extend(rule_findings)
            except Exception as exc:
                logger.warning("rule_failed", rule_id=rule.rule_id(), error=str(exc))
        return findings
