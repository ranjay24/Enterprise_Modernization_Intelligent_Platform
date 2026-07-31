"""Business domain graph — the shared foundation for capability detection.

Groups classes into business capabilities using the DDD chain:

    Controllers/APIs → Services → Repositories → Entities → Business Domain

This module powers:
- Spec 01: Business Capability Detection
- Spec 02: DDD Service Boundary Detection
- Spec 03: Migration Roadmap justification
- Spec 04: Project-specific ADR generation
- Spec 05: Business Context Understanding

It also produces token-budgeted graph sections that can be embedded directly
into AI prompts (classes, package tree, endpoints, dependency edges, injection
deps, god classes, circular deps, detected domains).
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from app.core.analysis_profile import AnalysisProfile, get_profile_for_settings

logger = structlog.get_logger(__name__)

_ENTITY_SUFFIXES = ("Entity", "Model")

# Display names for domain roots that need a business-friendly label.
_CAPABILITY_NAMES: dict[str, str] = {
    "Orders": "Order Management",
    "Order": "Order Management",
    "FollowUps": "Follow-Up Management",
    "Inquiry": "Inquiry Management",
    "Feedback": "Feedback Management",
    "Course": "Course Management",
    "Employee": "Employee Management",
    "EmpSalesInfo": "Sales Management",
    "EmployeeOrders": "Sales Management",
    "User": "User Management",
    "Customer": "Customer Management",
    "BannedUsers": "User Management",
}

# Non-core dependencies that should never count as domain coupling.
_INTERNAL_FRAMEWORK_DEPS = {
    "Entity", "Id", "GeneratedValue", "GenerationType", "Column", "Table",
    "Repository", "JpaRepository", "CrudRepository", "Service", "Controller",
    "RestController", "Autowired", "Component", "RequestMapping", "GetMapping",
    "PostMapping", "PutMapping", "DeleteMapping", "PathVariable", "RequestParam",
    "RequestBody", "ResponseEntity", "Model", "ModelAttribute", "SessionStatus",
    "SessionAttributes", "SessionAttribute", "HttpSession", "Pageable", "Page",
    "PageRequest", "RedirectAttributes", "List", "Set", "Map", "ArrayList",
    "Optional", "Stream", "Collectors", "Files", "Paths", "Path", "UUID",
    "DateTimeFormatter", "LocalDate", "LocalTime", "LocalDateTime", "MultipartFile",
    "JSONObject", "RequestParam", "SpringBootApplication", "SpringApplication",
    "SpringBootTest", "Test", "MockMvc", "BeforeEach", "AfterEach",
}


def _base_name(name: str) -> str:
    """Strip entity/model suffixes from a class name."""
    for suffix in _ENTITY_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _categorize(cls: dict) -> str:
    """Classify a class into a DDD role based on static analysis flags."""
    if cls.get("is_entity"):
        return "entity"
    if cls.get("is_repository"):
        return "repository"
    if cls.get("is_service"):
        return "service"
    if cls.get("is_controller"):
        return "controller"
    return "support"


def _capability_name(entity_name: str) -> str:
    """Human-friendly capability label for a domain root entity."""
    key = _base_name(entity_name)
    if key in _CAPABILITY_NAMES:
        return _CAPABILITY_NAMES[key]
    return f"{key.replace('_', ' ').title()} Management"


def _pluralize(entity_name: str) -> str:
    """Default JPA/Hibernate table name for an entity class.

    Hibernate's implicit naming strategy lower-cases the entity name and
    inserts underscores at camel-case boundaries (e.g. EmployeeOrders →
    employee_orders); it does not pluralise.
    """
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", _base_name(entity_name)).lower()
    return snake or entity_name.lower()


def _clean_deps(cls: dict) -> list[str]:
    """Dependencies that are project classes (not framework boilerplate)."""
    deps = set(cls.get("dependencies", []))
    deps.update(cls.get("injected_fields", []))
    return [d for d in deps if d and d not in _INTERNAL_FRAMEWORK_DEPS]


def _entity_of_repository(repo: dict, entities: list[dict]) -> str | None:
    """Resolve the entity a repository manages via name matching or deps."""
    stem = repo["name"]
    if stem.endswith("Repository"):
        stem = stem[: -len("Repository")]
    for ent in entities:
        if ent["name"] == stem or _base_name(ent["name"]) == _base_name(stem):
            return ent["name"]
    deps = set(repo.get("dependencies", []))
    deps.update(repo.get("implements", []))
    for ent in entities:
        if ent["name"] in deps:
            return ent["name"]
    return None


def _is_repo_like(cls: dict) -> bool:
    """Repository-like classes may omit the @Repository annotation."""
    if cls.get("is_repository"):
        return True
    deps = set(cls.get("dependencies", []))
    deps.update(cls.get("implements", []))
    return bool(deps & {"JpaRepository", "CrudRepository", "Repository", "MongoRepository"})


def detect_business_domains(analysis_data: dict) -> list[dict]:
    """Detect business domains from static analysis output.

    The detection is deterministic: it walks the DDD chain from controllers
    down to entities and clusters classes that participate in the same
    business workflow.
    """
    classes = analysis_data.get("classes", []) or []
    endpoints = analysis_data.get("endpoints", []) or []
    if not classes:
        return []

    by_name = {c.get("name", ""): c for c in classes}
    entities = [c for c in classes if c.get("is_entity")]
    services = [c for c in classes if c.get("is_service")]
    repo_like = [c for c in classes if _is_repo_like(c)]
    controllers = [c for c in classes if c.get("is_controller")]

    # 1. Repository -> managed entity.
    repo_to_entity = {
        r["name"]: _entity_of_repository(r, entities) for r in repo_like
    }

    # 2. Service -> managed entities (via injected repositories + entity deps).
    service_to_entities: dict[str, set[str]] = {}
    service_to_repos: dict[str, list[str]] = {}
    for s in services:
        sname = s["name"]
        sset: set[str] = set()
        srepos: list[str] = []
        injected = set(s.get("injected_fields", []))
        deps = set(s.get("dependencies", []))
        for rname, ent in repo_to_entity.items():
            if rname in injected or rname in deps:
                srepos.append(rname)
                if ent:
                    sset.add(ent)
        # Fallback: direct entity dependencies (e.g. service typed against entity).
        if not sset:
            for e in entities:
                if e["name"] in deps:
                    sset.add(e["name"])
        service_to_entities[sname] = sset
        service_to_repos[sname] = srepos

    # 3. Controller -> injected services.
    controller_to_services: dict[str, list[str]] = {}
    for c in controllers:
        injected = set(c.get("injected_fields", []))
        controller_to_services[c["name"]] = [
            s["name"] for s in services if s["name"] in injected
        ]

    # 4. Cluster per entity root.
    domain_roots: dict[str, dict[str, Any]] = {}
    for ent in entities:
        ename = ent["name"]
        d_services = set()
        for sname, eset in service_to_entities.items():
            if ename in eset:
                d_services.add(sname)
        d_repos = {r for r, e in repo_to_entity.items() if e == ename}
        d_controllers = {
            cname
            for cname, svcs in controller_to_services.items()
            if set(svcs) & d_services
        }
        if not (d_services or d_repos or d_controllers):
            continue
        domain_roots[ename] = {
            "entity": ename,
            "services": d_services,
            "repositories": d_repos,
            "controllers": d_controllers,
            "extra_classes": set(),
        }

    # 5. Fold orphan entities into a matching domain by name containment.
    orphan_entities = [e["name"] for e in entities if e["name"] not in domain_roots]
    for orphan in orphan_entities:
        base = _base_name(orphan)
        for ename in list(domain_roots):
            if base and (base in ename or ename in base):
                domain_roots[ename]["extra_classes"].add(orphan)
                break

    # 6. Materialise domains.
    domains: list[dict] = []
    for ename, root in domain_roots.items():
        classes_in_domain = {
            ename,
            *root["services"],
            *root["repositories"],
            *root["controllers"],
            *root["extra_classes"],
        }
        # Add support classes (dto/config) that only reference domain classes.
        for name, cls in by_name.items():
            if name in classes_in_domain:
                continue
            deps = set(_clean_deps(cls))
            if deps and all(d in classes_in_domain for d in deps) and deps & classes_in_domain:
                classes_in_domain.add(name)

        endpoints_for_domain = [
            {
                "method": ep.get("method", "GET"),
                "path": ep.get("path", "/"),
                "handler_class": ep.get("handler_class", ""),
                "handler_method": ep.get("handler_method", "handle"),
            }
            for ep in endpoints
            if ep.get("handler_class", "") in classes_in_domain
        ]

        chain_present = (
            bool(root["controllers"])
            and bool(root["services"])
            and bool(root["repositories"])
        )
        confidence = 55
        if chain_present:
            confidence += 25
        confidence += min(18, len(classes_in_domain) * 2)
        confidence = min(98, confidence)

        evidence: list[str] = [
            f"Domain root entity: {ename}",
            f"{len(root['controllers'])} controller(s), "
            f"{len(root['services'])} service(s), "
            f"{len(root['repositories'])} repository(ies) participate",
        ]
        if chain_present:
            controller = sorted(root["controllers"])[0]
            service = sorted(root["services"])[0]
            repository = sorted(root["repositories"])[0]
            evidence.append(
                f"Controller → Service → Repository → Entity chain: "
                f"{controller} → {service} → {repository} → {ename}"
            )
        if endpoints_for_domain:
            sample = endpoints_for_domain[0]
            evidence.append(
                f"API endpoints: {len(endpoints_for_domain)} "
                f"(e.g., {sample['method']} {sample['path']})"
            )

        domains.append({
            "name": _capability_name(ename),
            "entity": ename,
            "description": (
                f"Business capability rooted in the {ename} entity. "
                f"Handles {len(root['controllers'])} controllers, "
                f"{len(root['services'])} services and "
                f"{len(root['repositories'])} repositories."
            ),
            "confidence": confidence,
            "classes": sorted(classes_in_domain),
            "controllers": sorted(root["controllers"]),
            "services": sorted(root["services"]),
            "repositories": sorted(root["repositories"]),
            "entities": [ename],
            "api_endpoints": endpoints_for_domain,
            "database_tables": [_pluralize(ename)],
            "evidence": evidence,
            "shared_classes": [],
        })

    # 7. Domain dependency edges (cross-domain controller injections).
    _attach_domain_dependencies(domains, by_name, controller_to_services, service_to_entities)

    domains.sort(key=lambda d: -d["confidence"])
    logger.info(
        "business_domains_detected",
        domain_count=len(domains),
        domain_names=[d["name"] for d in domains],
    )
    return domains


def _attach_domain_dependencies(
    domains: list[dict],
    by_name: dict[str, dict],
    controller_to_services: dict[str, list[str]],
    service_to_entities: dict[str, set[str]],
) -> None:
    """Compute cross-domain dependency edges for each domain."""
    class_to_domains: dict[str, list[str]] = {}
    for d in domains:
        for name in d["classes"]:
            class_to_domains.setdefault(name, []).append(d["name"])

    for d in domains:
        deps: set[str] = set()
        for cname in d["controllers"]:
            for sname in controller_to_services.get(cname, []):
                for target in class_to_domains.get(sname, []):
                    if target != d["name"]:
                        deps.add(target)
        for sname in d["services"]:
            for ename in service_to_entities.get(sname, set()):
                for other in domains:
                    if other["name"] != d["name"] and ename in other["entities"]:
                        deps.add(other["name"])
        d["dependencies"] = sorted(deps)
        d["shared_classes"] = sorted(
            name for name, doms in class_to_domains.items() if len(doms) > 1
        )


def summarize_business_capabilities(analysis_data: dict) -> list[dict]:
    """Compact capability summary for result payloads and prompts."""
    domains = detect_business_domains(analysis_data)
    return [
        {
            "name": d["name"],
            "entity": d["entity"],
            "confidence": d["confidence"],
            "classes": len(d["classes"]),
            "services": d["services"],
            "api_endpoint_count": len(d["api_endpoints"]),
            "dependencies": d.get("dependencies", []),
        }
        for d in domains
    ]


# ---------------------------------------------------------------------------
# Token-budgeted graph sections for AI prompts (Spec 05 / Spec 14 support).
# ---------------------------------------------------------------------------
def _budget_json(data: Any, max_chars: int) -> str:
    result = json.dumps(data, default=str, ensure_ascii=False)
    if len(result) > max_chars:
        return result[:max_chars] + '..."'
    return result


def _classes_for_prompt(analysis_data: dict, profile: AnalysisProfile) -> list[dict]:
    classes = analysis_data.get("classes", []) or []
    max_deps = profile.max_deps_per_class
    out = []
    for c in classes[: profile.ai_max_classes]:
        out.append({
            "name": c.get("name", ""),
            "package": c.get("package", ""),
            "kind": _categorize(c),
            "loc": c.get("lines_of_code", 0),
            "methods": c.get("method_count", 0),
            "dependencies": (c.get("dependencies", []) or [])[:max_deps],
            "injected_fields": (c.get("injected_fields", []) or [])[:max_deps],
            "annotations": (c.get("annotations", []) or [])[: profile.max_annotations_per_class],
        })
    return out


def build_graph_prompt_sections(
    analysis_data: dict, profile: AnalysisProfile | None = None
) -> dict:
    """Build token-budgeted JSON graph sections for AI prompts.

    This is the fix for the root cause of the 14 issues: AI stages previously
    received only package names and counts. These sections carry the actual
    dependency graph, entities, endpoints and detected domains into prompts.
    """
    profile = profile or get_profile_for_settings()

    metrics = analysis_data.get("metrics", {}) or {}
    injection_deps = metrics.get("injection_dependencies", []) or []
    circular = metrics.get("circular_dependencies", []) or []
    god_classes = metrics.get("god_classes", []) or []

    domains = detect_business_domains(analysis_data)

    return {
        "classes_summary_json": _budget_json(
            _classes_for_prompt(analysis_data, profile), profile.classes_json_max_chars
        ),
        "package_tree_json": _budget_json(
            analysis_data.get("package_tree", {}) or {}, profile.package_tree_json_max_chars
        ),
        "endpoints_summary_json": _budget_json(
            (analysis_data.get("endpoints", []) or [])[: profile.ai_max_endpoints],
            profile.endpoints_json_max_chars,
        ),
        "dependency_edges_json": _budget_json(
            (analysis_data.get("dependency_edges", []) or [])[: profile.max_dependency_edges],
            profile.dependencies_json_max_chars,
        ),
        "injection_deps_json": _budget_json(
            injection_deps[: profile.max_injection_deps], profile.injection_deps_json_max_chars
        ),
        "circular_deps_json": _budget_json(
            circular[: profile.ai_max_circular_deps], profile.circular_deps_json_max_chars
        ),
        "god_classes_json": _budget_json(
            god_classes[: profile.max_god_classes], profile.god_classes_json_max_chars
        ),
        "domains_json": _budget_json(domains, profile.service_evidence_json_max_chars),
    }


def build_service_dependency_graph(
    services: list[dict], analysis_data: dict
) -> dict[str, list[str]]:
    """Build a service-level dependency graph from class-level dependencies."""
    classes = analysis_data.get("classes", []) or []
    by_name = {c.get("name", ""): c for c in classes}
    class_to_service: dict[str, str] = {}
    for svc in services:
        for cn in svc.get("classes", []) or []:
            class_to_service[cn] = svc.get("name", "")

    dep_map: dict[str, list[str]] = {}
    for svc in services:
        sname = svc.get("name", "")
        targets: set[str] = set()
        for cn in svc.get("classes", []) or []:
            cls = by_name.get(cn)
            if not cls:
                continue
            for dep in _clean_deps(cls):
                target = class_to_service.get(dep)
                if target and target != sname:
                    targets.add(target)
        dep_map[sname] = sorted(targets)
    return dep_map
