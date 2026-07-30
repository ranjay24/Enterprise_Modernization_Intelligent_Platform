"""Java source code parser — extracts classes, interfaces, enums, endpoints."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import structlog

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata, AnalyzerPhase
from app.analysis.contracts.context import AnalysisContext
from app.analysis.events.bus import EventType

logger = structlog.get_logger(__name__)

SPRING_ANNOTATIONS = {"Service", "Component", "Controller", "RestController", "Repository", "Configuration", "RestControllerAdvice", "ControllerAdvice"}
ENTITY_ANNOTATIONS = {"Entity", "Table", "Document"}
DTO_PACKAGES = {"dto", "model", "request", "response", "command", "query"}
EXCEPTION_SUFFIXES = ("Exception", "Error")
CONFIG_ANNOTATIONS = {"Configuration", "SpringBootApplication", "EnableAutoConfiguration"}


@dataclass
class ParsedClass:
    name: str
    package: str
    file_path: str
    class_type: str = "class"
    lines_of_code: int = 0
    method_count: int = 0
    method_lines: list = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    extends: str = ""
    implements: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    fields: list[dict] = field(default_factory=list)
    injected_fields: list[str] = field(default_factory=list)
    annotations_with_params: dict[str, str] = field(default_factory=dict)
    is_entity: bool = False
    is_controller: bool = False
    is_service: bool = False
    is_repository: bool = False
    is_interface: bool = False
    is_abstract: bool = False
    is_dto: bool = False
    is_exception: bool = False
    is_configuration: bool = False
    is_utility: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name, "package": self.package, "file_path": self.file_path,
            "class_type": self.class_type, "lines_of_code": self.lines_of_code,
            "method_count": self.method_count, "annotations": self.annotations,
            "imports": self.imports, "extends": self.extends, "implements": self.implements,
            "dependencies": self.dependencies, "injected_fields": self.injected_fields,
            "is_entity": self.is_entity, "is_controller": self.is_controller,
            "is_service": self.is_service, "is_repository": self.is_repository,
            "is_interface": self.is_interface, "is_abstract": self.is_abstract,
            "is_dto": self.is_dto, "is_exception": self.is_exception,
            "is_configuration": self.is_configuration, "is_utility": self.is_utility,
        }


@dataclass
class ParsedEndpoint:
    method: str
    path: str
    handler_class: str
    handler_method: str
    annotations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method, "path": self.path,
            "handler_class": self.handler_class, "handler_method": self.handler_method,
            "annotations": self.annotations,
        }


class JavaParser(Analyzer):
    """Parses Java source files into structured ParsedClass objects."""

    def metadata(self) -> AnalyzerMetadata:
        return AnalyzerMetadata(
            name="java_parser",
            version="1.0.0",
            phase=AnalyzerPhase.PARSER,
            description="Parses Java files into classes, interfaces, enums, endpoints",
            tags=["parser", "java", "static"],
        )

    def supports(self, context: AnalysisContext) -> bool:
        return len(context.parsed_classes) == 0 and context.class_count == 0

    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        logger.info("parsing_java_files", path=context.extracted_path)
        java_files = self._find_java_files(context.extracted_path)

        classes = []
        interfaces = []
        enums = []
        endpoints = []
        annotations_index: dict[str, list[str]] = {}

        for fp in java_files:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            parsed = self._parse_file(content, fp, context.extracted_path)
            if parsed is None:
                continue

            if parsed.is_interface:
                interfaces.append(parsed)
            elif parsed.class_type == "enum":
                enums.append(parsed)
            else:
                classes.append(parsed)

            for ann in parsed.annotations:
                annotations_index.setdefault(ann, []).append(parsed.name)

            file_endpoints = self._extract_endpoints(content, parsed.name)
            endpoints.extend(file_endpoints)

        context.parsed_classes = classes
        context.parsed_interfaces = interfaces
        context.parsed_enums = enums
        context.endpoints = endpoints
        context.annotations_index = annotations_index

        pkg_tree: dict[str, list[str]] = {}
        for c in classes + interfaces + enums:
            pkg = c.package or "default"
            pkg_tree.setdefault(pkg, []).append(c.name)

        context.project_metadata = context.project_metadata or {}
        context.project_metadata["package_hierarchy"] = pkg_tree
        context.project_metadata["total_java_files"] = len(java_files)

        context.add_event(EventType.PROJECT_PARSED.value, {
            "classes": len(classes), "interfaces": len(interfaces),
            "enums": len(enums), "endpoints": len(endpoints),
        })
        context.set_phase("parser")

        logger.info("parsing_complete", classes=len(classes), interfaces=len(interfaces), enums=len(enums), endpoints=len(endpoints))
        return context

    def _find_java_files(self, root: str) -> list[str]:
        files = []
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f.endswith(".java"):
                    files.append(os.path.join(dirpath, f))
        return files

    def _parse_file(self, content: str, file_path: str, base_path: str) -> ParsedClass | None:
        package_match = re.search(r"package\s+([\w.]+);", content)
        package = package_match.group(1) if package_match else ""

        class_match = re.search(r"(?:public\s+)?(?:abstract\s+)?(class|interface|enum)\s+(\w+)", content)
        if not class_match:
            return None

        class_type = class_match.group(1)
        name = class_match.group(2)
        lines = content.split("\n")
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("*")])

        imports = re.findall(r"import\s+([\w.*]+);", content)
        extends = ""
        em = re.search(r"extends\s+(\w+)", content)
        if em:
            extends = em.group(1)
        implements = []
        im = re.search(r"implements\s+([\w,\s]+?)(?:\s*\{)", content)
        if im:
            implements = [i.strip() for i in im.group(1).split(",")]

        annotations = re.findall(r"@(\w+)", content)
        annotations_with_params = {}
        for ann_m in re.finditer(r"@(\w+)\s*\(([^)]*)\)", content):
            annotations_with_params[ann_m.group(1)] = ann_m.group(2).strip()

        methods = re.findall(
            r"(?:public|protected|private|static|final|synchronized|abstract|native)\s+"
            r"(?:[\w<>\[\],\s?]+)\s+(\w+)\s*\([^)]*\)",
            content,
        )

        method_lines = []
        for m in methods:
            pattern = rf"(?:public|protected|private|static|final|synchronized|abstract|native)\s+(?:[\w<>\[\],\s?]+)\s+{re.escape(m)}\s*\([^)]*\)"
            match = re.search(pattern, content)
            if match:
                start_line = content[:match.start()].count("\n") + 1
                method_lines.append({"name": m, "start_line": start_line})

        injected_fields = []
        field_deps = []
        for inj in re.finditer(r"@(?:Autowired|Inject|Resource)\s+(?:private|protected|public)?\s*(\w+(?:<[\w,\s<>]+>)?)\s+(\w+);", content):
            inj_type = inj.group(1).split("<")[0].strip()
            injected_fields.append(inj_type)
            field_deps.append({"type": inj_type, "name": inj.group(2), "injection_type": "field"})

        for fm in re.finditer(r"(?:private|protected|public)\s+(?!static|final)(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*[=;]", content):
            f_type = fm.group(1).split("<")[0].strip()
            if f_type not in injected_fields and f_type != name:
                field_deps.append({"type": f_type, "name": fm.group(2), "injection_type": "declaration"})

        deps = list(set([imp.split(".")[-1] for imp in imports if imp.split(".")[-1] != "*"] + injected_fields))

        is_interface = class_type == "interface"
        is_abstract = bool(re.search(r"abstract\s+class\s+", content))
        is_entity = bool(re.search(r"@(?:Entity|Table|Document)", content))
        is_controller = bool(re.search(r"@(?:RestController|Controller)", content))
        is_service = bool(SPRING_ANNOTATIONS.intersection(annotations))
        is_repository = bool(re.search(r"@(?:Repository|CrudRepository|JpaRepository)", content))
        is_dto = (
            bool({"Data", "Builder", "Getter", "Setter", "AllArgsConstructor", "NoArgsConstructor"}.intersection(annotations))
            or is_entity
            or is_repository
            or (package and any(p in package.lower() for p in DTO_PACKAGES) and not injected_fields)
        )
        is_exception = name.endswith(EXCEPTION_SUFFIXES) or "Exception" in annotations
        is_configuration = bool(CONFIG_ANNOTATIONS.intersection(annotations))

        utility_methods = [m for m in methods]
        is_utility = (
            not is_interface
            and not is_abstract
            and not is_entity
            and not is_controller
            and not is_service
            and not is_repository
            and all(re.search(r"static", content[m.start():m.start()+50]) for m in re.finditer(r"(?:public|protected)\s+.*?\s+(\w+)\s*\(", content) if m.group(1) in utility_methods)
            and len(utility_methods) > 0
            and not injected_fields
        )

        return ParsedClass(
            name=name, package=package,
            file_path=os.path.relpath(file_path, base_path),
            class_type=class_type.lower(),
            lines_of_code=loc, method_count=len(methods),
            method_lines=method_lines, annotations=annotations,
            imports=imports, extends=extends, implements=implements,
            dependencies=deps, fields=field_deps,
            injected_fields=injected_fields,
            annotations_with_params=annotations_with_params,
            is_entity=is_entity, is_controller=is_controller,
            is_service=is_service, is_repository=is_repository,
            is_interface=is_interface, is_abstract=is_abstract,
            is_dto=is_dto, is_exception=is_exception,
            is_configuration=is_configuration, is_utility=is_utility,
        )

    def _extract_endpoints(self, content: str, class_name: str) -> list[ParsedEndpoint]:
        endpoints = []
        mapping = {"GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT", "DeleteMapping": "DELETE", "PatchMapping": "PATCH", "RequestMapping": "ALL"}
        for ann, method in mapping.items():
            for path_m in re.finditer(rf"@{ann}\s*\(\s*[\"']([^\"']+)[\"']\s*\)", content):
                func_m = re.search(rf"@{ann}.*?\n\s*(?:public|protected)\s+\S+\s+(\w+)\s*\(", content, re.DOTALL)
                endpoints.append(ParsedEndpoint(
                    method=method, path=path_m.group(1),
                    handler_class=class_name,
                    handler_method=func_m.group(1) if func_m else "unknown",
                    annotations=[ann],
                ))
        return endpoints
