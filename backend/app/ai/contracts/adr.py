"""AI Architecture Decision Record contract — strongly typed ADR model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ADRStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclass
class ADROption:
    """An option considered in an ADR."""
    name: str = ""
    description: str = ""
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "pros": self.pros,
            "cons": self.cons,
        }


@dataclass
class ADRTradeoff:
    """Tradeoffs of the chosen decision."""
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"pros": self.pros, "cons": self.cons}


@dataclass
class ADRConsequence:
    """Consequences of the chosen decision."""
    positive: list[str] = field(default_factory=list)
    negative: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "positive": self.positive,
            "negative": self.negative,
            "risks": self.risks,
        }


@dataclass
class AIDecisionRecord:
    """An AI-generated Architecture Decision Record."""
    adr_id: str = field(default_factory=lambda: f"ADR-{uuid.uuid4().hex[:6].upper()}")
    title: str = ""
    status: ADRStatus = ADRStatus.PROPOSED
    context: str = ""
    problem: str = ""
    decision: str = ""
    options: list[ADROption] = field(default_factory=list)
    tradeoffs: ADRTradeoff | None = None
    consequences: ADRConsequence | None = None
    confidence: float = 0.5
    migration_impact: dict = field(default_factory=dict)
    related_recommendations: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_id: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "adr_id": self.adr_id,
            "id": self.adr_id,
            "title": self.title,
            "status": self.status.value,
            "context": self.context,
            "problem": self.problem,
            "decision": self.decision,
            "options": [o.to_dict() for o in self.options],
            "tradeoffs": self.tradeoffs.to_dict() if self.tradeoffs else {"pros": [], "cons": []},
            "consequences": self.consequences.to_dict() if self.consequences else {"positive": [], "negative": [], "risks": []},
            "confidence": self.confidence,
            "migration_impact": self.migration_impact,
            "related_recommendations": self.related_recommendations,
            "created_at": self.created_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AIDecisionRecord:
        options = [ADROption(**o) for o in data.get("options", [])]
        tradeoffs = None
        if data.get("tradeoffs"):
            tradeoffs = ADRTradeoff(**data["tradeoffs"])
        consequences = None
        if data.get("consequences"):
            consequences = ADRConsequence(**data["consequences"])

        return cls(
            adr_id=data.get("adr_id", data.get("id", f"ADR-{uuid.uuid4().hex[:6].upper()}")),
            title=data.get("title", ""),
            status=ADRStatus(data.get("status", "proposed")),
            context=data.get("context", ""),
            problem=data.get("problem", ""),
            decision=data.get("decision", ""),
            options=options,
            tradeoffs=tradeoffs,
            consequences=consequences,
            confidence=data.get("confidence", 0.5),
            migration_impact=data.get("migration_impact", {}),
            related_recommendations=data.get("related_recommendations", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            model_id=data.get("model_id", ""),
            prompt_version=data.get("prompt_version", ""),
        )
