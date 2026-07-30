"""AI Capability Registry — extensible system for registering AI capabilities.

Each capability represents a distinct AI-powered analysis function
(migration, architecture, security, performance, cost, documentation, optimization).

New capabilities can be registered without modifying the orchestration layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CapabilityCategory(str, Enum):
    MIGRATION = "migration"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COST = "cost"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"


@dataclass
class CapabilityMetadata:
    """Metadata for a registered capability."""
    capability_id: str = ""
    name: str = ""
    description: str = ""
    category: CapabilityCategory = CapabilityCategory.ARCHITECTURE
    version: str = "1.0.0"
    enabled: bool = True
    priority: int = 100
    required_context: list[str] = field(default_factory=list)
    output_type: str = "dict"

    def to_dict(self) -> dict:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "enabled": self.enabled,
            "priority": self.priority,
            "required_context": self.required_context,
        }


class AICapability(ABC):
    """Abstract base for an AI capability.

    Each capability implements execute() which takes an AIContext
    and returns a result dict (or typed contract).
    """

    @abstractmethod
    def metadata(self) -> CapabilityMetadata:
        """Return capability metadata."""
        ...

    @abstractmethod
    def execute(self, ai_context: Any, **kwargs) -> Any:
        """Execute this capability with the given AI context."""
        ...

    def supports(self, ai_context: Any) -> bool:
        """Check if this capability can run with the given context."""
        return True

    def validate_prerequisites(self, ai_context: Any) -> list[str]:
        """Validate that prerequisites are met. Returns list of unmet requirements."""
        return []


class CapabilityRegistry:
    """Central registry for AI capabilities.

    Capabilities register themselves and are invoked by the orchestration
    layer based on category and priority.

    Adding a new capability:
    1. Create a class implementing AICapability
    2. Register it with this registry
    3. No changes needed in the orchestration layer
    """

    def __init__(self):
        self._capabilities: dict[str, AICapability] = {}
        self._category_index: dict[CapabilityCategory, list[str]] = {
            cat: [] for cat in CapabilityCategory
        }

    def register(self, capability: AICapability):
        """Register an AI capability."""
        meta = capability.metadata()
        self._capabilities[meta.capability_id] = capability
        self._category_index[meta.category].append(meta.capability_id)
        logger.info(
            "capability_registered",
            capability_id=meta.capability_id,
            name=meta.name,
            category=meta.category.value,
        )

    def register_many(self, capabilities: list[AICapability]):
        """Register multiple capabilities."""
        for cap in capabilities:
            self.register(cap)

    def get(self, capability_id: str) -> AICapability | None:
        """Get a capability by ID."""
        return self._capabilities.get(capability_id)

    def get_by_category(self, category: CapabilityCategory) -> list[AICapability]:
        """Get all enabled capabilities for a category, sorted by priority."""
        ids = self._category_index.get(category, [])
        capabilities = []
        for cid in ids:
            cap = self._capabilities.get(cid)
            if cap and cap.metadata().enabled:
                capabilities.append(cap)
        return sorted(capabilities, key=lambda c: c.metadata().priority)

    def execute_capability(self, capability_id: str, ai_context: Any, **kwargs) -> Any:
        """Execute a specific capability."""
        cap = self._capabilities.get(capability_id)
        if cap is None:
            raise ValueError(f"Capability not found: {capability_id}")

        meta = cap.metadata()
        if not meta.enabled:
            raise ValueError(f"Capability disabled: {capability_id}")

        unmet = cap.validate_prerequisites(ai_context)
        if unmet:
            raise ValueError(f"Unmet prerequisites for {capability_id}: {unmet}")

        if not cap.supports(ai_context):
            raise ValueError(f"Capability {capability_id} does not support this context")

        return cap.execute(ai_context, **kwargs)

    def execute_category(self, category: CapabilityCategory, ai_context: Any, **kwargs) -> dict:
        """Execute all enabled capabilities for a category."""
        results = {}
        capabilities = self.get_by_category(category)
        for cap in capabilities:
            meta = cap.metadata()
            try:
                result = cap.execute(ai_context, **kwargs)
                results[meta.capability_id] = {"success": True, "result": result}
            except Exception as exc:
                logger.error("capability_execution_failed", capability_id=meta.capability_id, error=str(exc))
                results[meta.capability_id] = {"success": False, "error": str(exc)}
        return results

    def list_all(self) -> list[dict]:
        """List all registered capabilities."""
        return [cap.metadata().to_dict() for cap in self._capabilities.values()]

    def list_categories(self) -> dict[str, list[str]]:
        """List capabilities by category."""
        return {
            cat.value: [cid for cid in ids if self._capabilities.get(cid) and self._capabilities[cid].metadata().enabled]
            for cat, ids in self._category_index.items()
        }

    def enable(self, capability_id: str):
        cap = self._capabilities.get(capability_id)
        if cap:
            cap.metadata().enabled = True

    def disable(self, capability_id: str):
        cap = self._capabilities.get(capability_id)
        if cap:
            cap.metadata().enabled = False
