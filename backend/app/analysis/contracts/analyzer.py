"""Base Analyzer interface — all analysis modules implement this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AnalyzerPhase(str, Enum):
    SCANNER = "scanner"
    PARSER = "parser"
    METRICS = "metrics"
    DEPENDENCY = "dependency"
    ARCHITECTURE = "architecture"
    RISK = "risk"
    READINESS = "readiness"
    RECOMMENDATION = "recommendation"
    GRAPH = "graph"


@dataclass(frozen=True)
class AnalyzerMetadata:
    """Immutable metadata about an analyzer."""
    name: str
    version: str
    phase: AnalyzerPhase
    description: str = ""
    tags: list[str] = field(default_factory=list)


class Analyzer(ABC):
    """Base interface every analysis plugin must implement."""

    @abstractmethod
    def metadata(self) -> AnalyzerMetadata:
        """Return static metadata about this analyzer."""
        ...

    @abstractmethod
    def analyze(self, context: "AnalysisContext") -> "AnalysisContext":
        """Run analysis, enrich the context, and return it."""
        ...

    @abstractmethod
    def supports(self, context: "AnalysisContext") -> bool:
        """Return True if this analyzer can run given the current context state."""
        ...

    def validate_prerequisites(self, context: "AnalysisContext") -> list[str]:
        """Return list of unmet prerequisites (empty = all met)."""
        return []
