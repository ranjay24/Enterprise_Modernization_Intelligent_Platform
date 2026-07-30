"""Rule: Detects god classes — overly large classes with too many responsibilities."""

from app.analysis.contracts.context import AnalysisContext
from app.analysis.rules.engine import RiskFinding, Rule, Severity


class GodClassRule(Rule):
    def rule_id(self) -> str:
        return "RISK-001"

    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]:
        findings = []
        for c in context.parsed_classes:
            if c.is_dto or c.is_interface or c.is_abstract:
                continue
            reasons = []
            if c.lines_of_code > 500:
                reasons.append(f"{c.lines_of_code} lines of code (threshold: 500)")
            if c.method_count > 20:
                reasons.append(f"{c.method_count} methods (threshold: 20)")
            if len(c.injected_fields) > 5:
                reasons.append(f"{len(c.injected_fields)} injected dependencies (threshold: 5)")
            if c.lines_of_code > 300 and c.method_count > 10 and c.injected_fields:
                reasons.append("High LOC + methods + dependencies compound")

            if reasons:
                severity = Severity.CRITICAL if c.lines_of_code > 1000 or c.method_count > 30 else Severity.HIGH
                findings.append(RiskFinding(
                    rule_id=self.rule_id(),
                    title=f"God Class: {c.name}",
                    severity=severity,
                    category="god_class",
                    description=f"Class {c.name} exceeds complexity thresholds",
                    impact="Increases maintenance cost, testing difficulty, and migration risk",
                    recommended_fix=f"Decompose {c.name} into smaller, focused classes",
                    confidence=min(1.0, (c.lines_of_code / 500) * 0.5 + (c.method_count / 20) * 0.3 + (len(c.injected_fields) / 5) * 0.2),
                    affected_components=[c.name],
                    evidence={"loc": c.lines_of_code, "methods": c.method_count, "injections": len(c.injected_fields)},
                ))
        return findings
