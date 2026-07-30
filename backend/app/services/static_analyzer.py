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

    for file_path in java_files:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        cls = _parse_java_class(content, file_path, extracted_path)
        if cls:
            classes.append(cls)
            pkg = cls.package or "default"
            if pkg not in package_tree:
                package_tree[pkg] = []
            package_tree[pkg].append(cls.name)

            endpoints = _extract_endpoints(content, cls.name)
            all_endpoints.extend(endpoints)

            for dep in cls.dependencies:
                dependency_edges.append(
                    {"source": cls.name, "target": dep, "type": "injection"}
                    if dep in cls.injected_fields
                    else {"source": cls.name, "target": dep, "type": "import"}
                )

    metrics = _calculate_metrics(classes)

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

    deps = []
    for imp in imports:
        class_name = imp.split(".")[-1]
        if class_name != "*":
            deps.append(class_name)

    all_deps = list(set(deps + injected_fields))

    is_entity = bool(re.search(r"@(?:Entity|Table|Document)", content))
    is_controller = bool(re.search(r"@(?:RestController|Controller)", content))
    is_service = bool(re.search(r"@(?:Service|Component)", content))
    is_repository = bool(re.search(r"@(?:Repository|CrudRepository|JpaRepository)", content))

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
        pattern = rf"@{ann}\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
        matches = re.findall(pattern, content)
        for path in matches:
            func_match = re.search(
                rf"@{ann}.*?\n\s*(?:public|protected)\s+\S+\s+(\w+)\s*\(",
                content,
                re.DOTALL,
            )
            handler_method = func_match.group(1) if func_match else "unknown"
            endpoints.append(
                APIEndpoint(
                    method=method,
                    path=path,
                    handler_class=class_name,
                    handler_method=handler_method,
                    annotations=[ann],
                )
            )

    return endpoints


def _calculate_metrics(classes: list[JavaClass]) -> dict:
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

    all_class_names = {c.name for c in classes}
    used_classes = set()
    for c in classes:
        used_classes.update(c.dependencies)
        if c.extends:
            used_classes.add(c.extends)
        used_classes.update(c.implements)

    all_field_types = set()
    for c in classes:
        for f in c.fields:
            all_field_types.add(f["type"])
        for inj in c.injected_fields:
            all_field_types.add(inj)

    dead_code = [
        {
            "name": c.name,
            "package": c.package,
            "reason": "Not referenced by any other class and not a Spring-managed component",
            "is_deprecated": "Deprecated" in c.annotations,
        }
        for c in classes
        if c.name not in used_classes
        and c.name not in all_field_types
        and not c.is_interface
        and not c.is_abstract
        and not _is_dto_or_model(c)
        and not _is_spring_managed(c)
        and not _is_configuration_class(c)
        and not c.name.endswith("Exception")
        and not c.name.endswith("Error")
        and "Exception" not in c.annotations
    ]

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
        "dead_code": dead_code,
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
    return False


def _god_class_reason(c: JavaClass) -> str:
    reasons = []
    if c.lines_of_code > 300:
        reasons.append(f"{c.lines_of_code} LOC (threshold: 300)")
    if c.method_count > 10:
        reasons.append(f"{c.method_count} methods (threshold: 10)")
    if len(c.injected_fields) > 5:
        reasons.append(f"{len(c.injected_fields)} injected dependencies (threshold: 5)")
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

    class_map = {c.name: c for c in classes}
    entity_referencers = {}
    for entity in entities:
        referencers = set()
        for c in classes:
            if c.name == entity.name:
                continue
            if entity.name in c.dependencies or entity.name in c.injected_fields:
                referencers.add(c.package)
        entity_referencers[entity.name] = referencers

    shared = []
    for entity in entities:
        ref_packages = entity_referencers.get(entity.name, set())
        if len(ref_packages) > 1:
            shared.append({
                "entity": entity.name,
                "packages": list(ref_packages),
                "concern": f"Entity {entity.name} referenced by classes in {len(ref_packages)} different packages",
            })

    return shared
