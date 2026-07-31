"""Project Scanner — detects build tool, Java version, Spring Boot, package hierarchy."""

from __future__ import annotations

import os

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType
from app.analysis.scanner.detectors import (
    detect_build_tool,
    detect_java_version,
    detect_modules,
    detect_spring_boot_version,
    find_config_files,
)
from app.analysis.scanner.metadata import ProjectMetadata

logger = structlog.get_logger(__name__)


class ProjectScanner(Analyzer):
    """Detects project type, structure, and metadata."""

    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="project_scanner",
            version="1.0.0",
            phase=AnalyzerPhase.SCANNER,
            description="Detects build tool, Java/Spring versions, package hierarchy",
            tags=["scanner", "project", "metadata"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return context.project_metadata is None

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        logger.info("scanning_project", path=context.extracted_path)

        project_root = self._find_project_root(context.extracted_path)
        build_tool = detect_build_tool(project_root)
        java_version = detect_java_version(project_root)
        spring_boot_version = detect_spring_boot_version(project_root)
        modules = detect_modules(project_root, build_tool)
        config_files = find_config_files(project_root)

        source_folders, resource_folders = self._find_folders(project_root)
        java_files = self._find_java_files(project_root)
        package_hierarchy = self._build_package_hierarchy(java_files, project_root)
        base_package = self._infer_base_package(package_hierarchy)

        metadata = ProjectMetadata(
            name=os.path.basename(project_root.rstrip("/\\")),
            build_tool=build_tool,
            java_version=java_version,
            spring_boot_version=spring_boot_version,
            base_package=base_package,
            modules=modules,
            source_folders=source_folders,
            resource_folders=resource_folders,
            config_files=config_files,
            build_files=self._find_build_files(project_root, build_tool),
            total_java_files=len(java_files),
            package_hierarchy=package_hierarchy,
        )

        context.project_metadata = metadata.to_dict()
        context.add_event(EventType.PROJECT_SCANNED.value, {"build_tool": build_tool, "java_version": java_version})
        context.set_phase("scanner")

        logger.info(
            "project_scanned",
            build_tool=build_tool,
            java_version=java_version,
            spring_boot=spring_boot_version,
            modules=len(modules),
            java_files=len(java_files),
        )
        return context

    def _find_project_root(self, path: str) -> str:
        """Locate the directory that owns the project's build definition.

        Extracted archives are often wrapped in a top-level folder, so the
        build file (pom.xml / build.gradle) can live one or more levels below
        the extraction root. Falling back to the extraction root keeps analysis
        working for repositories extracted without a wrapper folder.
        """
        build_files = ("pom.xml", "build.gradle", "build.gradle.kts", "build.xml")
        if any(os.path.exists(os.path.join(path, bf)) for bf in build_files):
            return path
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "target", ".metadata")]
            for bf in build_files:
                if bf in filenames:
                    return dirpath
        return path

    def _find_folders(self, path: str) -> tuple[list[str], list[str]]:
        source_folders = []
        resource_folders = []
        for dirpath, dirnames, filenames in os.walk(path):
            rel = os.path.relpath(dirpath, path)
            if "src" in rel:
                parts = rel.split(os.sep)
                if "main" in parts and "java" in parts:
                    source_folders.append(rel)
                elif "main" in parts and "resources" in parts:
                    resource_folders.append(rel)
        return source_folders or ["src/main/java"], resource_folders or ["src/main/resources"]

    def _find_java_files(self, path: str) -> list[str]:
        java_files = []
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                if f.endswith(".java"):
                    java_files.append(os.path.join(dirpath, f))
        return java_files

    def _build_package_hierarchy(self, java_files: list[str], base_path: str) -> dict[str, list[str]]:
        hierarchy: dict[str, list[str]] = {}
        for fp in java_files:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(2000)
                import re
                m = re.search(r"package\s+([\w.]+);", content)
                pkg = m.group(1) if m else "default"
                class_name = os.path.splitext(os.path.basename(fp))[0]
                hierarchy.setdefault(pkg, []).append(class_name)
            except Exception:
                continue
        return hierarchy

    def _infer_base_package(self, hierarchy: dict[str, list[str]]) -> str:
        if not hierarchy:
            return ""
        packages = [p for p in hierarchy if p != "default"]
        if not packages:
            return ""
        parts = packages[0].split(".")
        for i, part in enumerate(parts):
            count = sum(1 for p in packages if p.startswith(".".join(parts[: i + 1])))
            if count < len(packages) * 0.5:
                return ".".join(parts[:i])
        return packages[0]

    def _find_build_files(self, path: str, build_tool: str) -> list[str]:
        build_files = []
        if build_tool == "maven":
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    if f == "pom.xml":
                        build_files.append(os.path.relpath(os.path.join(dirpath, f), path))
        elif build_tool == "gradle":
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    if f in ("build.gradle", "build.gradle.kts", "settings.gradle"):
                        build_files.append(os.path.relpath(os.path.join(dirpath, f), path))
        return build_files
