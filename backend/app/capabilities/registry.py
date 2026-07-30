"""Capability registry — extensible platform feature registry."""

from __future__ import annotations

from app.capabilities.models import Capability, CapabilityCategory


class CapabilityRegistry:
    """Registry of all platform capabilities.

    Exposes available AI features, supported reports, languages,
    frameworks, and cloud providers.
    """

    def __init__(self):
        self._capabilities: dict[str, Capability] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in platform capabilities."""
        # Analysis capabilities
        self.register(Capability(
            name="static_analysis",
            category=CapabilityCategory.ANALYSIS,
            description="Java static analysis — classes, methods, dependencies, metrics",
            version="2.0.0",
            is_enabled=True,
            requires_ai=False,
        ))
        self.register(Capability(
            name="dependency_graph",
            category=CapabilityCategory.ANALYSIS,
            description="Dependency graph generation and circular dependency detection",
            version="2.0.0",
            is_enabled=True,
            requires_ai=False,
        ))
        self.register(Capability(
            name="architecture_detection",
            category=CapabilityCategory.ANALYSIS,
            description="Architecture pattern detection (layered, MVC, hexagonal)",
            version="2.0.0",
            is_enabled=True,
            requires_ai=False,
        ))
        self.register(Capability(
            name="risk_analysis",
            category=CapabilityCategory.ANALYSIS,
            description="Rule-based risk detection (god classes, circular deps, hardcoded config)",
            version="2.0.0",
            is_enabled=True,
            requires_ai=False,
        ))
        self.register(Capability(
            name="quality_metrics",
            category=CapabilityCategory.ANALYSIS,
            description="Code quality metrics — maintainability, complexity, duplication",
            version="2.0.0",
            is_enabled=True,
            requires_ai=False,
        ))

        # AI capabilities
        self.register(Capability(
            name="service_boundary_detection",
            category=CapabilityCategory.AI,
            description="AI-powered microservice boundary detection",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))
        self.register(Capability(
            name="readiness_scoring",
            category=CapabilityCategory.AI,
            description="Migration readiness scoring across 6 dimensions",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))
        self.register(Capability(
            name="adr_generation",
            category=CapabilityCategory.AI,
            description="Architecture Decision Record generation",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))
        self.register(Capability(
            name="migration_planning",
            category=CapabilityCategory.AI,
            description="Wave-based migration plan generation",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))
        self.register(Capability(
            name="cost_analysis",
            category=CapabilityCategory.AI,
            description="Pre/post migration cost comparison",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))
        self.register(Capability(
            name="explainability",
            category=CapabilityCategory.AI,
            description="AI recommendation explainability with reasoning chains",
            version="3.0.0",
            is_enabled=True,
            requires_ai=True,
            supported_models=["amazon.nova-pro-v1:0", "amazon.nova-lite-v1:0"],
        ))

        # Report capabilities
        self.register(Capability(
            name="executive_summary",
            category=CapabilityCategory.REPORT,
            description="Executive summary report generation",
            version="4.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="developer_report",
            category=CapabilityCategory.REPORT,
            description="Developer-focused technical report",
            version="4.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="risk_report",
            category=CapabilityCategory.REPORT,
            description="Risk analysis report",
            version="4.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="architecture_report",
            category=CapabilityCategory.REPORT,
            description="Architecture analysis report",
            version="4.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="migration_roadmap",
            category=CapabilityCategory.REPORT,
            description="Migration wave roadmap report",
            version="4.0.0",
            is_enabled=True,
        ))

        # Language support
        self.register(Capability(
            name="java",
            category=CapabilityCategory.LANGUAGE,
            description="Java source code analysis",
            version="2.0.0",
            is_enabled=True,
        ))

        # Framework support
        self.register(Capability(
            name="spring_boot",
            category=CapabilityCategory.FRAMEWORK,
            description="Spring Boot annotation and dependency detection",
            version="2.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="maven",
            category=CapabilityCategory.FRAMEWORK,
            description="Maven project structure detection",
            version="2.0.0",
            is_enabled=True,
        ))
        self.register(Capability(
            name="gradle",
            category=CapabilityCategory.FRAMEWORK,
            description="Gradle project structure detection",
            version="2.0.0",
            is_enabled=True,
        ))

        # Cloud support
        self.register(Capability(
            name="aws",
            category=CapabilityCategory.CLOUD,
            description="Amazon Web Services deployment target",
            version="4.0.0",
            is_enabled=True,
        ))

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def list_all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def list_by_category(self, category: CapabilityCategory) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.category == category]

    def get_enabled(self) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.is_enabled]

    def get_ai_capabilities(self) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.requires_ai]

    def to_dict(self) -> dict:
        return {
            "capabilities": [c.to_dict() for c in self._capabilities.values()],
            "total": len(self._capabilities),
            "categories": {
                cat.value: len(self.list_by_category(cat))
                for cat in CapabilityCategory
            },
            "ai_models": list({
                m for c in self._capabilities.values()
                for m in c.supported_models
            }),
        }
