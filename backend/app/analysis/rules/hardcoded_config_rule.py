"""Rule: Detects hardcoded configuration values."""

from __future__ import annotations

import re

from app.analysis.contracts.context import AnalysisContext
from app.analysis.rules.engine import RiskFinding, Rule, Severity
from app.core.analysis_profile import get_profile_for_settings


class HardcodedConfigRule(Rule):
    def rule_id(self) -> str:
        return "RISK-004"

    PATTERNS = [
        (r'(?i)(password|secret|api[_-]?key|token)\s*=\s*"[^"]+"', "hardcoded_secret"),
        (r'(?i)(jdbc:|mysql:|postgres:|mongodb:|redis:)', "hardcoded_connection_string"),
        (r'(?i)(localhost|127\.0\.0\.1):\d+', "hardcoded_endpoint"),
    ]

    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]:
        findings = []
        for c in context.parsed_classes:
            for pattern, category in self.PATTERNS:
                try:
                    with open(c.file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append(RiskFinding(
                            rule_id=self.rule_id(),
                            title=f"Hardcoded Config in {c.name}: {category}",
                            severity=Severity.HIGH if "secret" in category else Severity.MEDIUM,
                            category=category,
                            description=f"Found {len(matches)} hardcoded values in {c.name}",
                            impact="Security risk, environment coupling, deployment difficulty",
                            recommended_fix="Externalize configuration to properties/environment variables",
                            confidence=0.85,
                            affected_components=[c.name],
                            evidence={"match_count": len(matches), "category": category},
                        ))
                except Exception:
                    continue
        profile = get_profile_for_settings()
        return findings[:profile.rule_max_findings]
