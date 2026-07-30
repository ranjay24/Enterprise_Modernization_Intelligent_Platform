"""Project metadata data model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectMetadata:
    name: str = ""
    build_tool: str = "unknown"
    java_version: str = "unknown"
    spring_boot_version: str = "unknown"
    base_package: str = ""
    modules: list[str] = field(default_factory=list)
    source_folders: list[str] = field(default_factory=list)
    resource_folders: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    build_files: list[str] = field(default_factory=list)
    total_java_files: int = 0
    package_hierarchy: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "build_tool": self.build_tool,
            "java_version": self.java_version,
            "spring_boot_version": self.spring_boot_version,
            "base_package": self.base_package,
            "modules": self.modules,
            "source_folders": self.source_folders,
            "resource_folders": self.resource_folders,
            "config_files": self.config_files,
            "build_files": self.build_files,
            "total_java_files": self.total_java_files,
            "package_hierarchy": self.package_hierarchy,
        }
