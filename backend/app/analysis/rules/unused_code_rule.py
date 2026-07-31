"""Rule: Detects potentially unused classes (dead code)."""

from app.analysis.contracts.context import AnalysisContext
from app.analysis.rules.engine import RiskFinding, Rule, Severity
from app.core.analysis_profile import get_profile_for_settings


class UnusedCodeRule(Rule):
    def rule_id(self) -> str:
        return "RISK-005"

    def evaluate(self, context: AnalysisContext) -> list[RiskFinding]:
        classes = context.parsed_classes
        class_names = {c.name for c in classes}
        all_field_types = set()
        for c in classes:
            for f in c.fields:
                all_field_types.add(f.get("type", ""))
            all_field_types.update(c.injected_fields)

        used = set()
        for c in classes:
            used.update(c.dependencies)
            if c.extends:
                used.add(c.extends)
            used.update(c.implements)

        unused = [
            c for c in classes
            if c.name not in used and c.name not in all_field_types
            and not c.is_interface and not c.is_abstract
            and not c.is_dto and not c.is_exception
            and not c.is_configuration and not c.is_utility
            and not _is_spring_managed(c)
        ]

        if not unused:
            return []

        profile = get_profile_for_settings()
        return [RiskFinding(
            rule_id=self.rule_id(),
            title=f"Potentially Unused Code: {len(unused)} classes",
            severity=Severity.LOW if len(unused) < 5 else Severity.MEDIUM,
            category="unused_code",
            description=f"{len(unused)} classes appear to be unreferenced",
            impact="Increases codebase size, maintenance burden, and confusion",
            recommended_fix="Verify usage and remove confirmed dead code",
            confidence=0.60,
            affected_components=[c.name for c in unused[:profile.rule_max_affected_components]],
            evidence={"unused_count": len(unused), "classes": [c.name for c in unused[:profile.rule_max_evidence_classes]]},
        )]


def _is_spring_managed(c) -> bool:
    spring = {"Service", "Component", "Controller", "RestController", "Repository", "Configuration", "RestControllerAdvice", "ControllerAdvice"}
    return bool(spring.intersection(c.annotations))
