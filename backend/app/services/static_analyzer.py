"""Static analysis engine for Java codebases."""

import os
import re
from dataclasses import dataclass, field

import structlog

from app.core.settings import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()


@dataclass
class JavaClass:
    name: str
    package: str
    file_path: str
    lines_of_code: int = 0
    method_count: int = 0
    method_lines: list = field(default_factory=list)
    annotations: list = field(default_factory=list)
    imports: list = field(default_factory=list)
    extends: str = ""
    implements: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    injected_fields: list = field(default_factory=list)
    is_entity: bool = False
    is_controller: bool = False
    is_service: bool = False
    is_repository: bool = False
    is_interface: bool = False
    is_abstract: bool = False
    annotations_with_params: dict = field(default_factory=dict)


@dataclass
class APIEndpoint:
    method: str
    path: str
    handler_class: str
    handler_method: str
    annotations: list = field(default_factory=list)


@dataclass
class StaticAnalysisResult:
    classes: list[JavaClass]
    endpoints: list[APIEndpoint]
    dependency_edges: list[dict]
    metrics: dict
    package_tree: dict


def analyze_java_codebase(extracted_path: str) -> StaticAnalysisResult:
    logger.info("starting_static_analysis", path=extracted_path)

    java_files = _find_java_files(extracted_path)
    logger.info("java_files_found", count=len(java_files))

    classes = []
    all_endpoints = []
    dependency_edges = []
    package_tree = {}
    class_contents = {}

    for file_path in java_files:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        cls = _parse_java_class(content, file_path, extracted_path)
        if cls:
            classes.append(cls)
            class_contents[cls.name] = content
            pkg = cls.package or "default"
            if pkg not in package_tree:
                package_tree[pkg] = []
            package_tree[pkg].append(cls.name)

            endpoints = _extract_endpoints(content, cls.name)
            all_endpoints.extend(endpoints)

    # Dependency edges only capture real intra-project dependencies. Imports of
    # external frameworks (java.*, spring, jakarta, etc.) are not code-level
    # coupling and must not distort cohesion/coupling metrics.
    project_class_names = {c.name for c in classes}
    for cls in classes:
        for dep in cls.dependencies:
            if dep not in project_class_names:
                continue
            dependency_edges.append(
                {"source": cls.name, "target": dep, "type": "injection"}
                if dep in cls.injected_fields
                else {"source": cls.name, "target": dep, "type": "import"}
            )

    metrics = _calculate_metrics(classes, class_contents, all_endpoints)

    logger.info(
        "static_analysis_complete",
        total_classes=len(classes),
        total_endpoints=len(all_endpoints),
        total_loc=metrics.get("total_lines", 0),
    )

    return StaticAnalysisResult(
        classes=classes,
        endpoints=all_endpoints,
        dependency_edges=dependency_edges,
        metrics=metrics,
        package_tree=package_tree,
    )


def _find_java_files(root: str) -> list[str]:
    java_files = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith(".java"):
                java_files.append(os.path.join(dirpath, f))
    return java_files


def _parse_java_class(content: str, file_path: str, base_path: str) -> JavaClass | None:
    package_match = re.search(r"package\s+([\w.]+);", content)
    package = package_match.group(1) if package_match else ""

    class_match = re.search(
        r"(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)", content
    )
    if not class_match:
        return None

    name = class_match.group(1)
    lines = content.split("\n")
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("*")])

    imports = re.findall(r"import\s+([\w.*]+);", content)

    extends = ""
    extends_match = re.search(r"extends\s+(\w+)", content)
    if extends_match:
        extends = extends_match.group(1)

    implements = []
    impl_match = re.search(r"implements\s+([\w,\s]+?)(?:\s*\{)", content)
    if impl_match:
        implements = [i.strip() for i in impl_match.group(1).split(",")]

    is_interface = bool(re.search(r"interface\s+\w+", content))
    is_abstract = bool(re.search(r"abstract\s+class\s+", content))

    annotations = re.findall(r"@(\w+)", content)

    annotations_with_params = {}
    for ann_match in re.finditer(r"@(\w+)\s*\(([^)]*)\)", content):
        ann_name = ann_match.group(1)
        ann_params = ann_match.group(2).strip()
        annotations_with_params[ann_name] = ann_params

    methods = re.findall(
        r"(?:public|protected|private|static|final|synchronized|abstract|native)\s+"
        r"(?:[\w<>\[\],\s?]+)\s+(\w+)\s*\([^)]*\)",
        content,
    )
    method_count = len(methods)

    method_lines = []
    for m in methods:
        pattern = r"(?:public|protected|private|static|final|synchronized|abstract|native)\s+"
        pattern += r"(?:[\w<>\[\],\s?]+)\s+" + re.escape(m) + r"\s*\([^)]*\)"
        match = re.search(pattern, content)
        if match:
            start_line = content[: match.start()].count("\n") + 1
            method_lines.append({"name": m, "start_line": start_line})

    injected_fields = []
    field_deps = []

    for inj_match in re.finditer(
        r"@(?:Autowired|Inject|Resource)\s+(?:private|protected|public)?\s*(\w+(?:<[\w,\s<>]+>)?)\s+(\w+);",
        content,
    ):
        inj_type = inj_match.group(1).split("<")[0].strip()
        inj_name = inj_match.group(2)
        injected_fields.append(inj_type)
        field_deps.append({"type": inj_type, "name": inj_name, "injection_type": "field"})

    for field_match in re.finditer(
        r"(?:private|protected|public)\s+(?!static|final)(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*[=;]",
        content,
    ):
        f_type = field_match.group(1).split("<")[0].strip()
        f_name = field_match.group(2)
        if f_type not in injected_fields and f_type not in [name]:
            field_deps.append({"type": f_type, "name": f_name, "injection_type": "declaration"})

    for const_match in re.finditer(
        r"(?:private|protected|public)\s+static\s+(?:final\s+)?(\w+(?:<[\w,\s<>]+>)?)\s+(\w+)\s*=[^;]+;",
        content,
    ):
        const_type = const_match.group(1).split("<")[0].strip()
        const_name = const_match.group(2)
        if const_type not in injected_fields and const_type not in [name]:
            field_deps.append({"type": const_type, "name": const_name, "injection_type": "constant"})

    deps = []
    for imp in imports:
        class_name = imp.split(".")[-1]
        if class_name != "*":
            deps.append(class_name)

    all_deps = list(set(deps + injected_fields))

    is_entity = bool(re.search(r"@(?:Entity|Table|Document)(?!\w)", content))
    is_controller = bool(re.search(r"@(?:RestController|Controller)(?!Advice)", content))
    is_service = bool(re.search(r"@(?:Service|Component)(?!\w)", content))
    is_repository = bool(
        re.search(r"@Repository(?!\w)", content)
        or re.search(r"extends\s+(?:JpaRepository|CrudRepository|PagingAndSortingRepository|JpaSpecificationExecutor|MongoRepository|ElasticsearchRepository)(?![a-zA-Z])", content)
    )

    return JavaClass(
        name=name,
        package=package,
        file_path=os.path.relpath(file_path, base_path),
        lines_of_code=loc,
        method_count=method_count,
        method_lines=method_lines,
        annotations=annotations,
        imports=imports,
        extends=extends,
        implements=implements,
        dependencies=all_deps,
        fields=field_deps,
        injected_fields=injected_fields,
        is_entity=is_entity,
        is_controller=is_controller,
        is_service=is_service,
        is_repository=is_repository,
        is_interface=is_interface,
        is_abstract=is_abstract,
        annotations_with_params=annotations_with_params,
    )


def _extract_endpoints(content: str, class_name: str) -> list[APIEndpoint]:
    endpoints = []

    mapping_annotations = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
        "RequestMapping": "ALL",
    }

    for ann, method in mapping_annotations.items():
        # Match the mapping annotation (string, named arg, or array of paths)
        # together with the handler method that immediately follows it
        # (allowing for intervening parameter annotations).
        pattern = re.compile(
            rf"@{ann}\s*\((?P<args>[^)]*)\)"
            rf"(?:\s*\n\s*@\w+(?:\([^)]*\))?)*"
            rf"\s*\n\s*(?:public|protected|private)\s+[\w<>\[\],\s?]+\s+(?P<handler>\w+)\s*\("
        )
        for match in pattern.finditer(content):
            paths = re.findall(r"[\"']([^\"']+)[\"']", match.group("args"))
            if not paths:
                continue
            for path in paths:
                endpoints.append(
                    APIEndpoint(
                        method=method,
                        path=path,
                        handler_class=class_name,
                        handler_method=match.group("handler"),
                        annotations=[ann],
                    )
                )

    return endpoints


def _calculate_metrics(classes: list[JavaClass], class_contents: dict | None = None, endpoints: list[APIEndpoint] | None = None) -> dict:
    total_classes = len(classes)
    total_methods = sum(c.method_count for c in classes)
    total_loc = sum(c.lines_of_code for c in classes)

    god_classes = [
        {
            "name": c.name,
            "package": c.package,
            "lines_of_code": c.lines_of_code,
            "method_count": c.method_count,
            "injected_dependencies": len(c.injected_fields),
            "reason": _god_class_reason(c),
        }
        for c in classes
        if _is_god_class(c)
    ]

    long_methods = []
    for c in classes:
        if not c.method_lines:
            continue
        for i, m in enumerate(c.method_lines):
            start = m["start_line"]
            end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
            method_len = end - start
            if method_len > 30:
                long_methods.append({
                    "class": c.name,
                    "method": m["name"],
                    "line": start,
                    "length": method_len,
                })

    all_complexities = []
    for c in classes:
        if not c.method_lines:
            continue
        for i, m in enumerate(c.method_lines):
            start = m["start_line"]
            end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
            all_complexities.append(end - start)
    avg_complexity = round(sum(all_complexities) / len(all_complexities), 1) if all_complexities else 0

    duplicate_count = 0
    total_method_lines = 0
    seen_method_bodies = {}
    for c in classes:
        if not c.method_lines:
            continue
        for i, m in enumerate(c.method_lines):
            start = m["start_line"]
            end = c.method_lines[i + 1]["start_line"] if i + 1 < len(c.method_lines) else c.lines_of_code
            body_len = end - start
            total_method_lines += body_len
            if body_len >= 5:
                key = f"{c.name}:{start}"
                if key in seen_method_bodies:
                    duplicate_count += body_len
                else:
                    seen_method_bodies[key] = True
    duplicate_lines_percent = round((duplicate_count / total_method_lines * 100), 1) if total_method_lines > 0 else 0.0

    import_only_cycles = _detect_import_only_cycles(classes)
    injection_cycles = _detect_injection_cycles(classes)

    dead_code_report = _detect_dead_code(
        classes, class_contents or {}, endpoints or []
    )

    shared_tables = _detect_shared_entities(classes)
    all_cycles = _dedup_cycles(import_only_cycles, injection_cycles)

    return {
        "total_files": total_classes,
        "total_lines": total_loc,
        "total_classes": total_classes,
        "total_methods": total_methods,
        "avg_cyclomatic_complexity": avg_complexity,
        "god_classes": god_classes,
        "duplicate_lines_percent": duplicate_lines_percent,
        "long_methods": long_methods,
        "circular_dependencies": all_cycles,
        "import_only_cycles": import_only_cycles,
        "injection_cycles": injection_cycles,
        "dead_code": dead_code_report["dead_classes"],
        "dead_code_report": dead_code_report,
        "shared_entities": shared_tables,
        "injection_dependencies": [
            {
                "source": c.name,
                "source_package": c.package,
                "target": inj,
                "type": "injection",
            }
            for c in classes
            for inj in c.injected_fields
        ],
    }


_DEAD_CODE_SPRING_ANNOTATIONS = {
    "Service", "Component", "Controller", "RestController", "Repository",
    "Configuration", "RestControllerAdvice", "ControllerAdvice",
    "Bean", "Scheduled", "EventListener", "Conditional", "ConditionalOnProperty",
}
_DEAD_CODE_ENTITY_ANNOTATIONS = {"Entity", "Embeddable", "MappedSuperclass", "Table", "Document"}
_DEAD_CODE_LOMBOK_ANNOTATIONS = {
    "Data", "Builder", "Getter", "Setter", "AllArgsConstructor",
    "NoArgsConstructor", "ToString", "EqualsAndHashCode", "RequiredArgsConstructor",
}
_DEAD_CODE_CALLBACK_METHODS = {
    "main", "run", "init", "destroy", "start", "stop",
    "afterPropertiesSet", "beforeDestroy", "toString", "hashCode",
    "equals", "finalize", "clone",
}


def _detect_dead_code(classes, class_contents, endpoints) -> dict:
    contents = dict(class_contents)
    project_names = {c.name for c in classes}
    class_map = {c.name: c for c in classes}

    endpoint_methods = {
        ep.handler_method for ep in endpoints if ep.handler_class
    }
    interface_methods = {
        (c.name, m["name"])
        for c in classes
        if c.is_interface
        for m in c.method_lines
    }

    def _count_references(name, exclude=None):
        pattern = re.compile(r"\b" + re.escape(name) + r"\b")
        total = 0
        for cname, content in contents.items():
            if cname == exclude:
                continue
            total += len(pattern.findall(content))
        return total

    def _outgoing_references(c):
        refs = set()
        for dep in c.dependencies:
            if dep in project_names and dep != c.name:
                refs.add(dep)
        if c.extends in project_names:
            refs.add(c.extends)
        for impl in c.implements:
            if impl in project_names:
                refs.add(impl)
        return refs

    def _ignore_reason(c):
        if ("test" in (c.file_path or "").lower()) or _is_test_class_name(c.name):
            return ("TEST_CLASS", f"{c.name} is a test class (excluded by convention)")
        if _is_configuration_class(c):
            return ("CONFIGURATION", f"{c.name} is a Spring configuration/application entry point")
        if c.is_repository:
            return ("SPRING_COMPONENT", f"{c.name} is a Spring Data repository")
        if c.is_controller:
            return ("SPRING_COMPONENT", f"{c.name} is a controller exposing HTTP endpoints")
        if _is_spring_managed(c) or _DEAD_CODE_SPRING_ANNOTATIONS.intersection(c.annotations):
            return ("SPRING_COMPONENT", f"{c.name} is a Spring-managed component")
        if c.is_entity or _DEAD_CODE_ENTITY_ANNOTATIONS.intersection(c.annotations):
            return ("ENTITY", f"{c.name} is a persistent entity (mapped to storage)")
        if _DEAD_CODE_LOMBOK_ANNOTATIONS.intersection(c.annotations) or _is_dto_or_model(c):
            return ("GENERATED", f"{c.name} uses Lombok/annotations or is a DTO (members are generated/managed)")
        if "Generated" in c.annotations or "generated" in (c.package or "").lower():
            return ("GENERATED", f"{c.name} is generated code")
        if _is_exception_class(c):
            return ("SPRING_COMPONENT", f"{c.name} is an exception/error type (part of the public API)")
        if c.is_interface or c.is_abstract:
            return ("GENERATED", f"{c.name} is a {'interface' if c.is_interface else 'abstract'} contract (excluded by convention)")
        return None

    class_ignore_types = {}
    ignored_items = []
    for c in classes:
        ignore = _ignore_reason(c)
        if ignore:
            class_ignore_types[c.name] = ignore[0]
            ignored_items.append({"name": c.name, "type": ignore[0], "reason": ignore[1]})

    dead_classes = []
    for c in classes:
        if c.name in class_ignore_types:
            continue
        if _count_references(c.name, exclude=c.name) > 0:
            continue
        out = _outgoing_references(c)
        dead_classes.append({
            "name": c.name,
            "package": c.package,
            "file": c.file_path,
            "line": _symbol_line(contents.get(c.name, ""), c.name),
            "type": "class",
            "reason": "Class is not referenced by any other class in the project",
            "incoming_references": 0,
            "outgoing_references": len(out),
            "confidence": 95,
            "safe_to_delete": True,
        })

    dead_class_names = {d["name"] for d in dead_classes}
    member_skip_types = {"TEST_CLASS", "CONFIGURATION", "ENTITY", "GENERATED"}
    dead_methods = []
    dead_fields = []

    for c in classes:
        if c.is_interface or c.is_abstract or c.name in dead_class_names:
            continue
        if class_ignore_types.get(c.name) in member_skip_types or _is_exception_class(c):
            continue
        content = contents.get(c.name, "")
        class_endpoint_methods = {ep.handler_method for ep in endpoints if ep.handler_class == c.name}
        override_names = set()
        for impl in c.implements:
            override_names.update(m for (iface, m) in interface_methods if iface == impl)
        parent = c
        while parent.extends and parent.extends in class_map:
            parent = class_map[parent.extends]
            override_names.update(m["name"] for m in parent.method_lines)
        method_starts = sorted(m["start_line"] for m in c.method_lines if m["start_line"])
        content_line_count = len(content.split("\n")) if content else c.lines_of_code

        def _method_loc(start_line):
            if start_line is None or start_line not in method_starts:
                return 0
            idx = method_starts.index(start_line)
            end = method_starts[idx + 1] if idx + 1 < len(method_starts) else content_line_count
            return max(0, end - start_line)

        for m in c.method_lines:
            mname = m["name"]
            if mname in _DEAD_CODE_CALLBACK_METHODS or mname in class_endpoint_methods:
                continue
            if mname in override_names or re.match(r"^(get|set|is|has)", mname):
                continue
            if _method_annotations(content, m["start_line"]) & {"Override", "Scheduled", "EventListener", "PostConstruct", "PreDestroy", "Bean", "ExceptionHandler"}:
                continue
            if m["start_line"] is None:
                continue
            total = _count_invocations(mname, contents)
            if total > 1:
                continue
            is_private = _is_private_line(content, m["start_line"])
            dead_methods.append({
                "name": mname,
                "class": c.name,
                "package": c.package,
                "file": c.file_path,
                "line": m["start_line"],
                "type": "method",
                "reason": "Method is not invoked from any code in the project",
                "incoming_references": total - 1,
                "outgoing_references": _method_loc(m["start_line"]),
                "confidence": 90 if is_private else 80,
                "safe_to_delete": is_private,
            })

        for f in c.fields:
            fname = f["name"]
            if f.get("injection_type") == "field":
                continue
            if fname == "serialVersionUID":
                continue
            total = _count_references(fname, contents)
            if total > 1:
                continue
            is_private = _field_is_private(content, fname)
            dead_fields.append({
                "name": fname,
                "class": c.name,
                "package": c.package,
                "file": c.file_path,
                "line": _symbol_line(content, fname),
                "type": "field",
                "reason": "Field is never referenced outside its own declaration",
                "incoming_references": total - 1,
                "outgoing_references": 0,
                "confidence": 90 if is_private else 80,
                "safe_to_delete": is_private,
            })

    ignored_test_classes = sum(1 for i in ignored_items if i["type"] == "TEST_CLASS")
    return {
        "dead_classes": dead_classes,
        "dead_methods": dead_methods,
        "dead_fields": dead_fields,
        "ignored_items": ignored_items,
        "summary": {
            "dead_classes": len(dead_classes),
            "dead_methods": len(dead_methods),
            "dead_fields": len(dead_fields),
            "ignored_framework_classes": len(ignored_items) - ignored_test_classes,
            "ignored_test_classes": ignored_test_classes,
        },
    }


def _is_test_class_name(name):
    return (
        name.endswith("Test") or name.endswith("Tests")
        or name.endswith("IntegrationTest")
        or (name.endswith("IT") and name != "IT")
    )


def _is_exception_class(c):
    return (
        c.name.endswith("Exception") or c.name.endswith("Exceptions")
        or c.name.endswith("Error") or c.name.endswith("Errors")
    )


def _count_invocations(name, contents, exclude=None):
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(")
    total = 0
    for cname, content in contents.items():
        if cname == exclude:
            continue
        total += len(pattern.findall(content))
    return total


def _method_annotations(content, start_line):
    annotations = set()
    if not content or not start_line:
        return annotations
    lines = content.split("\n")
    i = start_line - 2
    while i >= 0:
        stripped = lines[i].strip()
        if not stripped:
            break
        match = re.match(r"@(\w+)", stripped)
        if match:
            annotations.add(match.group(1))
            i -= 1
        else:
            break
    return annotations


def _is_private_line(content, start_line):
    if not content or not start_line:
        return False
    lines = content.split("\n")
    if start_line <= len(lines):
        return bool(re.search(r"\bprivate\b", lines[start_line - 1]))
    return False


def _field_is_private(content, fname):
    if not content:
        return False
    match = re.search(r"[^;\n]*\bprivate\b[^;\n]*\b" + re.escape(fname) + r"\b", content)
    return bool(match)


def _symbol_line(content, name):
    if not content:
        return None
    match = re.search(r"\b(?:class|interface|enum)\s+" + re.escape(name) + r"\b|\b" + re.escape(name) + r"\s+[A-Za-z_][A-Za-z0-9_]*\s*=|;\s*" + re.escape(name) + r"\b", content)
    if match:
        return content[:match.start()].count("\n") + 1
    match = re.search(r"\b" + re.escape(name) + r"\b", content)
    if match:
        return content[:match.start()].count("\n") + 1
    return None


def _is_dto_or_model(c: JavaClass) -> bool:
    lombook_annotations = {"Data", "Builder", "Getter", "Setter", "AllArgsConstructor", "NoArgsConstructor", "ToString", "EqualsAndHashCode", "RequiredArgsConstructor"}
    if lombook_annotations.intersection(c.annotations):
        return True
    if c.is_entity:
        return True
    if c.is_repository:
        return True
    if c.package and ("dto" in c.package.lower() or "model" in c.package.lower()):
        if not c.injected_fields:
            return True
    return False


def _is_spring_managed(c: JavaClass) -> bool:
    spring_annotations = {"Service", "Component", "Controller", "RestController", "Repository", "Configuration", "RestControllerAdvice", "ControllerAdvice"}
    return bool(spring_annotations.intersection(c.annotations))


def _is_configuration_class(c: JavaClass) -> bool:
    config_annotations = {"Configuration", "SpringBootApplication", "EnableAutoConfiguration", "TestConfiguration"}
    return bool(config_annotations.intersection(c.annotations))


def _is_god_class(c: JavaClass) -> bool:
    if _is_dto_or_model(c):
        return False
    if c.is_interface or c.is_abstract:
        return False
    if len(c.injected_fields) > 5:
        return True
    if c.lines_of_code > 500:
        return True
    if c.lines_of_code > 300 and c.method_count > 10 and len(c.injected_fields) > 0:
        return True
    if c.is_controller and c.method_count > 12:
        return True
    if c.method_count > 15 and len(c.dependencies) > 8:
        return True
    return False


def _god_class_reason(c: JavaClass) -> str:
    reasons = []
    if c.lines_of_code > 300:
        reasons.append(f"{c.lines_of_code} LOC (threshold: 300)")
    if c.method_count > 10:
        reasons.append(f"{c.method_count} methods (threshold: 10)")
    if len(c.injected_fields) > 5:
        reasons.append(f"{len(c.injected_fields)} injected dependencies (threshold: 5)")
    if c.is_controller and c.method_count > 12:
        reasons.append(f"{c.method_count} methods in controller (threshold: 12)")
    if c.method_count > 15 and len(c.dependencies) > 8:
        reasons.append(f"{c.method_count} methods with {len(c.dependencies)} dependencies")
    if not reasons:
        reasons.append("Exceeds complexity thresholds")
    return "; ".join(reasons)


def _dedup_cycles(import_cycles: list[dict], injection_cycles: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for cycle in import_cycles + injection_cycles:
        key = tuple(sorted(set(cycle["cycle"])))
        if key not in seen:
            seen.add(key)
            result.append(cycle)
    return result


def _detect_import_only_cycles(classes: list[JavaClass]) -> list[dict]:
    class_map = {c.name: c for c in classes}
    seen_cycles = set()
    result = []

    import_deps = {}
    for c in classes:
        import_only = set()
        for imp in c.imports:
            class_name = imp.split(".")[-1]
            if class_name != "*" and class_name in class_map:
                import_only.add(class_name)
        import_deps[c.name] = import_only

    def dfs(name, path, visiting):
        if name in visiting:
            idx = path.index(name)
            cycle = path[idx:] + [name]
            canonical = tuple(sorted(set(cycle)))
            if canonical not in seen_cycles:
                seen_cycles.add(canonical)
                result.append({"cycle": cycle, "type": "import"})
            return
        if name in path:
            return
        path.append(name)
        visiting.add(name)
        deps = import_deps.get(name, set())
        for dep in deps:
            if dep in class_map:
                dfs(dep, path, visiting)
        path.pop()
        visiting.remove(name)

    for c in classes:
        dfs(c.name, [], set())

    return result


def _detect_injection_cycles(classes: list[JavaClass]) -> list[dict]:
    class_map = {c.name: c for c in classes}
    seen_cycles = set()
    result = []

    def dfs(name, path, visiting):
        if name in visiting:
            idx = path.index(name)
            cycle = path[idx:] + [name]
            canonical = tuple(sorted(set(cycle)))
            if canonical not in seen_cycles:
                seen_cycles.add(canonical)
                result.append({"cycle": cycle, "type": "injection"})
            return
        if name in path:
            return
        path.append(name)
        visiting.add(name)
        cls = class_map.get(name)
        if cls:
            for inj in cls.injected_fields:
                if inj in class_map:
                    dfs(inj, path, visiting)
        path.pop()
        visiting.remove(name)

    for c in classes:
        dfs(c.name, [], set())

    return result


def _detect_shared_entities(classes: list[JavaClass]) -> list[dict]:
    entities = [c for c in classes if c.is_entity]
    if len(entities) < 2:
        return []

    entity_referencers = {}
    for entity in entities:
        referencers = set()
        for c in classes:
            if c.name == entity.name:
                continue
            if not c.is_service:
                continue
            if entity.name in c.dependencies or entity.name in c.injected_fields:
                referencers.add(c.name)
        entity_referencers[entity.name] = referencers

    shared = []
    for entity in entities:
        ref_services = entity_referencers.get(entity.name, set())
        if len(ref_services) > 1:
            shared.append({
                "entity": entity.name,
                "services": sorted(ref_services),
                "concern": f"Entity {entity.name} referenced by {len(ref_services)} different service classes",
            })

    return shared
