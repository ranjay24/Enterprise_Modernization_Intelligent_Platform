"""Rule: Detects circular dependencies."""

from app.analysis.contracts.context import AnalysisContext
from app.analysis.rules.engine import RiskFinding, Rule, Severity


class CircularDependencyRule(Rule):
    def rule_id(self) -> str:
        return "RISK-002"

    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]:
        findings = []
        cycles = context.circular_dependencies or []
        for cycle_info in cycles:
            cycle = cycle_info.get("cycle", [])
            cycle_type = cycle_info.get("type", "unknown")
            findings.append(RiskFinding(
                rule_id=self.rule_id(),
                title=f"Circular Dependency ({cycle_type})",
                severity=Severity.HIGH if len(cycle) <= 3 else Severity.CRITICAL,
                category="circular_dependency",
                description=f"Circular {cycle_type} dependency detected: {' -> '.join(cycle)}",
                impact="Prevents independent deployment, increases coupling, complicates testing",
                recommended_fix="Introduce interfaces or events to break the dependency cycle",
                confidence=0.95,
                affected_components=cycle,
                evidence={"cycle": cycle, "type": cycle_type, "length": len(cycle)},
            ))
        return findings
