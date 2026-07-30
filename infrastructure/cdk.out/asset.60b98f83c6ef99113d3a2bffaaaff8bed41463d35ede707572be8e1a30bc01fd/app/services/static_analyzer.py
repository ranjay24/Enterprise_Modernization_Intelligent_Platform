import re
import os
from dataclasses import dataclass, field


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
    java_files = _find_java_files(extracted_path)
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
                    {"source": cls.name, "target": dep, "type": "import"}
                )

    metrics = _calculate_metrics(classes)
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
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])

    imports = re.findall(r"import\s+([\w.*]+);", content)

    extends = ""
    extends_match = re.search(r"extends\s+(\w+)", content)
    if extends_match:
        extends = extends_match.group(1)

    implements = []
    impl_match = re.search(r"implements\s+([\w,\s]+?)(?:\s*\{)", content)
    if impl_match:
        implements = [i.strip() for i in impl_match.group(1).split(",")]

    annotations = re.findall(r"@(\w+)", content)

    methods = re.findall(
        r"(?:public|protected|private|static|final|synchronized|abstract|native)\s+"
        r"(?:[\w<>\[\],\s?]+)\s+(\w+)\s*\([^)]*\)",
        content,
    )
    method_count = len(methods)

    method_lines = []
    for m in methods:
        pattern = rf"(?:public|protected|private|static|final|synchronized|abstract|native)\s+"
        pattern += r"(?:[\w<>\[\],\s?]+)\s+" + re.escape(m) + r"\s*\([^)]*\)"
        match = re.search(pattern, content)
        if match:
            start_line = content[: match.start()].count("\n") + 1
            method_lines.append({"name": m, "start_line": start_line})

    deps = []
    for imp in imports:
        class_name = imp.split(".")[-1]
        if class_name != "*":
            deps.append(class_name)

    cls = JavaClass(
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
        dependencies=deps,
    )
    return cls


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
            "lines_of_code": c.lines_of_code,
            "method_count": c.method_count,
        }
        for c in classes
        if c.lines_of_code > 500 or c.method_count > 20
    ]

    long_methods = []
    avg_complexity = 0

    circular_deps = _detect_circular_dependencies(classes)

    all_class_names = {c.name for c in classes}
    used_classes = set()
    for c in classes:
        used_classes.update(c.dependencies)
        if c.extends:
            used_classes.add(c.extends)
        used_classes.update(c.implements)

    dead_code = [
        {"name": c.name, "package": c.package}
        for c in classes
        if c.name not in used_classes
        and not any(a in c.annotations for a in ["SpringBootApplication", "Configuration"])
    ]

    return {
        "total_files": total_classes,
        "total_lines": total_loc,
        "total_classes": total_classes,
        "total_methods": total_methods,
        "avg_cyclomatic_complexity": avg_complexity,
        "god_classes": god_classes,
        "duplicate_lines_percent": 0.0,
        "long_methods": long_methods,
        "circular_dependencies": circular_deps,
        "dead_code": dead_code,
    }


def _detect_circular_dependencies(classes: list[JavaClass]) -> list[dict]:
    class_map = {c.name: c for c in classes}
    circular = []
    visited = set()
    path = set()

    def dfs(name):
        if name in path:
            circular.append({"cycle": list(path) + [name]})
            return
        if name in visited:
            return
        visited.add(name)
        path.add(name)
        cls = class_map.get(name)
        if cls:
            for dep in cls.dependencies:
                if dep in class_map:
                    dfs(dep)
        path.remove(name)

    for c in classes:
        dfs(c.name)

    return circular
