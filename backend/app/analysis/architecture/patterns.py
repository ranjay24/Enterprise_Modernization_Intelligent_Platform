"""Architecture pattern definitions and detection heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ArchitecturePattern:
    name: str
    description: str
    indicators: list[str] = field(default_factory=list)
    anti_indicators: list[str] = field(default_factory=list)
    confidence_boost: float = 0.0
    confidence_penalty: float = 0.0


PATTERNS: list[ArchitecturePattern] = [
    ArchitecturePattern(
        name="layered_architecture",
        description="Traditional N-tier layered architecture with controller/service/repository layers",
        indicators=["controller", "service", "repository", "entity"],
        anti_indicators=[],
        confidence_boost=0.15,
    ),
    ArchitecturePattern(
        name="clean_architecture",
        description="Uncle Bob's Clean Architecture with domain, use case, and adapter layers",
        indicators=["domain", "usecase", "adapter", "infrastructure", "application"],
        anti_indicators=[],
        confidence_boost=0.20,
    ),
    ArchitecturePattern(
        name="hexagonal_architecture",
        description="Ports and Adapters architecture with clear inbound/outbound boundaries",
        indicators=["port", "adapter", "input", "output", "primary", "secondary"],
        anti_indicators=[],
        confidence_boost=0.20,
    ),
    ArchitecturePattern(
        name="modular_monolith",
        description="Module-based monolith with strong module boundaries",
        indicators=["module"],
        anti_indicators=["circular"],
        confidence_boost=0.15,
    ),
    ArchitecturePattern(
        name="traditional_monolith",
        description="Unstructured or loosely structured monolithic application",
        indicators=[],
        anti_indicators=[],
        confidence_boost=0.0,
    ),
]
