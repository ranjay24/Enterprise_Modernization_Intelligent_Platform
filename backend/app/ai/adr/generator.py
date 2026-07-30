"""AI ADR Generator — generates Architecture Decision Records."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext
from app.ai.contracts.adr import (
    ADRConsequence,
    ADROption,
    ADRStatus,
    ADRTradeoff,
    AIDecisionRecord,
)

logger = structlog.get_logger(__name__)


class AIADRGenerator:
    """Generates AI-powered Architecture Decision Records."""

    def generate(self, ai_context: AIContext, parsed_response: dict) -> list[AIDecisionRecord]:
        """Generate ADRs from parsed AI response."""
        adrs = []
        for adr_data in parsed_response.get("adrs", []):
            try:
                adr = self._build_adr(adr_data)
                adrs.append(adr)
            except Exception as exc:
                logger.warning("adr_build_failed", error=str(exc))
        return adrs

    def generate_deterministic(self, ai_context: AIContext) -> list[AIDecisionRecord]:
        """Generate ADRs without AI — fallback."""
        adrs = []
        god_classes = ai_context.god_classes
        circular = ai_context.circular_dependencies

        if god_classes:
            adrs.append(AIDecisionRecord(
                title="Decompose God Classes",
                status=ADRStatus.PROPOSED,
                context=f"Analysis identified {len(god_classes)} god classes exceeding complexity thresholds.",
                problem="God classes violate single responsibility and impede microservice extraction.",
                decision="Decompose god classes into focused services following domain boundaries.",
                tradeoffs=ADRTradeoff(
                    pros=["Better maintainability", "Easier testing", "Enables microservice extraction"],
                    cons=["Requires significant refactoring", "Risk of introducing bugs", "Team training needed"],
                ),
                consequences=ADRConsequence(
                    positive=["Improved code quality", "Easier onboarding"],
                    negative=["Short-term velocity decrease", "Increased test surface"],
                    risks=["Decomposition may break hidden dependencies"],
                ),
                confidence=0.8,
            ))

        if circular:
            adrs.append(AIDecisionRecord(
                title="Break Circular Dependencies",
                status=ADRStatus.PROPOSED,
                context=f"Analysis identified {len(circular)} circular dependency chains.",
                problem="Circular dependencies create tight coupling and prevent independent deployment.",
                decision="Introduce event-driven communication or shared kernel pattern to break cycles.",
                tradeoffs=ADRTradeoff(
                    pros=["Enables independent deployment", "Reduces coupling", "Clearer boundaries"],
                    cons=["Introduces eventual consistency", "Requires messaging infrastructure"],
                ),
                confidence=0.85,
            ))

        return adrs

    def _build_adr(self, data: dict) -> AIDecisionRecord:
        options = [
            ADROption(
                name=o.get("name", ""),
                description=o.get("description", ""),
                pros=o.get("pros", []),
                cons=o.get("cons", []),
            )
            for o in data.get("options", [])
        ]

        tradeoffs = None
        if data.get("tradeoffs"):
            tradeoffs = ADRTradeoff(**data["tradeoffs"])

        consequences = None
        if data.get("consequences"):
            consequences = ADRConsequence(**data["consequences"])

        return AIDecisionRecord(
            adr_id=data.get("adr_id", data.get("id", "")),
            title=data.get("title", ""),
            status=ADRStatus(data.get("status", "proposed")),
            context=data.get("context", ""),
            problem=data.get("problem", ""),
            decision=data.get("decision", ""),
            options=options,
            tradeoffs=tradeoffs,
            consequences=consequences,
            confidence=float(data.get("confidence", 0.5)),
            migration_impact=data.get("migration_impact", {}),
        )
