"""Rule: Detects excessively long methods."""

from app.analysis.contracts.context import AnalysisContext
from app.analysis.rules.engine import RiskFinding, Rule, Severity
from app.core.analysis_profile import get_profile_for_settings


class LongMethodRule(Rule):
    def rule_id(self) -> str:
        return "RISK-003"

    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]:
        findings = []
        for c in context.parsed_classes:
            if not c.method_lines:
                continue
            for i, m in enumerate(c.method_lines):
                start = m["start_line"]
                end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
                length = end - start
                if length > 50:
                    severity = Severity.HIGH if length > 100 else Severity.MEDIUM
                    findings.append(RiskFinding(
                        rule_id=self.rule_id(),
                        title=f"Long Method: {c.name}.{m['name']}",
                        severity=severity,
                        category="long_method",
                        description=f"Method {m['name']} is {length} lines long",
                        impact="Reduces readability, increases defect risk, complicates testing",
                        recommended_fix=f"Extract {m['name']} into smaller methods",
                        confidence=0.90,
                        affected_components=[c.name],
                        evidence={"method": m["name"], "length": length, "start_line": start},
                    ))
        profile = get_profile_for_settings()
        return findings[:profile.rule_max_findings]
