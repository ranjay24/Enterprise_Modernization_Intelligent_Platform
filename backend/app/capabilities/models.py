"""Capability models — describes platform features."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapabilityCategory(str, Enum):
    ANALYSIS = "analysis"
    AI = "ai"
    REPORT = "report"
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    CLOUD = "cloud"
    EXPORT = "export"


@dataclass
class Capability:
    """A single platform capability."""
    name: str = ""
    category: CapabilityCategory = CapabilityCategory.ANALYSIS
    description: str = ""
    version: str = "1.0.0"
    is_enabled: bool = True
    requires_ai: bool = False
    supported_models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "is_enabled": self.is_enabled,
            "requires_ai": self.requires_ai,
            "supported_models": self.supported_models,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Capability:
        return cls(
            name=data.get("name", ""),
            category=CapabilityCategory(data.get("category", "analysis")),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            is_enabled=data.get("is_enabled", True),
            requires_ai=data.get("requires_ai", False),
            supported_models=data.get("supported_models", []),
        )
