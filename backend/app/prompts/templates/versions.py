"""Prompt version registry — tracks prompt template versions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptVersion:
    """Version metadata for a prompt template."""
    prompt_id: str = ""
    version: str = "1.0.0"
    model_id: str = ""
    analysis_version: str = "1.0.0"
    description: str = ""
    author: str = "emip"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "model_id": self.model_id,
            "analysis_version": self.analysis_version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
        }


class VersionManager:
    """Manages prompt template versions.

    Supports:
    - Version registration and lookup
    - Version compatibility checks
    - Version history tracking
    """

    def __init__(self):
        self._versions: dict[str, list[PromptVersion]] = {}

    def register(self, version: PromptVersion):
        """Register a prompt version."""
        if version.prompt_id not in self._versions:
            self._versions[version.prompt_id] = []
        self._versions[version.prompt_id].append(version)

    def get_latest(self, prompt_id: str) -> PromptVersion | None:
        """Get the latest version of a prompt."""
        versions = self._versions.get(prompt_id, [])
        return versions[-1] if versions else None

    def get_version(self, prompt_id: str, version: str) -> PromptVersion | None:
        """Get a specific version of a prompt."""
        for v in self._versions.get(prompt_id, []):
            if v.version == version:
                return v
        return None

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        """List all versions of a prompt."""
        return list(self._versions.get(prompt_id, []))

    def list_all(self) -> dict[str, list[PromptVersion]]:
        """List all registered prompt versions."""
        return dict(self._versions)

    def is_compatible(self, prompt_id: str, min_version: str = "1.0.0") -> bool:
        """Check if the latest version meets minimum version requirement."""
        latest = self.get_latest(prompt_id)
        if not latest:
            return False
        return self._version_gte(latest.version, min_version)

    @staticmethod
    def _version_gte(v1: str, v2: str) -> bool:
        """Check if v1 >= v2 using semantic versioning."""
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        return parts1 >= parts2
