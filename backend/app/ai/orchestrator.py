"""AI Orchestrator — replaces direct bedrock_analyzer calls in the analysis pipeline.

Integrates with the existing orchestrator.py while providing the new AI layer
capabilities. Maintains backward compatibility with existing API contracts.
"""

from __future__ import annotations

import re
from collections import Counter

import structlog

from app.ai.service import AIService
from app.core.analysis_profile import get_active_profile
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


def _profile():
    s = get_settings()
    return get_active_profile(s.analysis_mode, s.bedrock_max_tokens, s.ai_prompt_max_tokens)

_service: AIService | None = None


def get_ai_service() -> AIService:
    """Get or create the singleton AI service."""
    global _service
    if _service is None:
        _service = AIService()
    return _service


def _resolved_model_id(metadata: dict, default: str = "deterministic-fallback") -> str:
    """Report which model actually produced a result.

    AI metadata carries the real model id only when a provider invocation
    succeeded. When the pipeline fell back to deterministic logic (provider
    error or no model), claiming the model id would mislabel the output, so
    the deterministic label is used instead.
    """
    if metadata.get("used_fallback") or metadata.get("error"):
        return default
    return metadata.get("model_id") or default


def _apply_graph_boundary_metrics(services: list[dict], edges: list[dict]) -> None:
    """Overwrite AI/provided cohesion & coupling with graph-grounded values.

    For each resolved boundary, cohesion is the share of dependency edges
    that stay inside the boundary (intra) and coupling is the share that
    cross it (inter). Falls back to the existing values when no edge touches
    the boundary (graph is silent for that slice).
    """
    if not edges:
        return
    class_to_service: dict[str, str] = {}
    for svc in services:
        for name in svc.get("classes", []) or []:
            class_to_service[name] = svc["name"]

    for svc in services:
        names = set(svc.get("classes", []) or [])
        intra = 0
        inter = 0
        for e in edges:
            source = e.get("source")
            target = e.get("target")
            s_in = source in names
            t_in = target in names
            if s_in and t_in:
                intra += 1
            elif s_in or t_in:
                inter += 1
        total = intra + inter
        if total > 0:
            svc["cohesion_score"] = round(intra / total * 100)
            svc["coupling_score"] = round(inter / total * 100)


        total = intra + inter
        if total > 0:
            svc["cohesion_score"] = round(intra / total * 100)
            svc["coupling_score"] = round(inter / total * 100)


def _ai_candidate_base_name(candidate: dict) -> str:
    """Strip a framework suffix from an AI service candidate name."""
    cname = (candidate.get("name") or "").strip()
    if not cname:
        return ""
    for suffix in ("Service", "Controller", "Repository", "Api"):
        if cname.endswith(suffix) and len(cname) > len(suffix):
            return cname[: -len(suffix)]
    return cname


def _match_ai_service_name(dom: dict, ai_candidates: list[dict]) -> str:
    """Pick a stable, human service name for a domain from AI candidates.

    Prefers an exact capability match (so "Sales Management" keeps the name
    "EmpSalesInfoService"), then a name/entity base match ("Orders" domain →
    "OrdersService"). Returns "" when no candidate fits.
    """
    dname = dom.get("name", "")
    entity = dom.get("entity", "")
    for s in ai_candidates:
        if isinstance(s, dict) and s.get("business_capability") == dname and s.get("name"):
            return s["name"]
    for s in ai_candidates:
        if not isinstance(s, dict):
            continue
        cbase = _ai_candidate_base_name(s)
        if entity and cbase and (cbase == entity or cbase in entity or entity in cbase):
            return s["name"]
    return ""


def _entity_service_name(entity: str) -> str:
    """Derive a service name from a domain root entity."""
    return f"{entity}Service" if entity else "Service"


def _build_boundaries_from_domains(
    domains: list[dict],
    ai_candidates: list[dict],
    class_by_name: dict,
    all_endpoints: list[dict],
) -> list[dict]:
    """Build service boundaries from the deterministic business domains.

    Each domain (controller → service → repository → entity chain) becomes one
    boundary, so membership is always grounded in the dependency graph instead
    of the AI's (sometimes hallucinated) class lists. Classes shared by several
    domains (e.g. a controller injecting services from two domains) are given
    to the domain whose exclusive classes they depend on most, so every class
    belongs to exactly one boundary. AI candidates only contribute service
    names and confidence.
    """
    class_sets = [set(d.get("classes", []) or []) for d in domains]
    owners: dict[str, list[int]] = {}
    for idx, s in enumerate(class_sets):
        for cn in s:
            owners.setdefault(cn, []).append(idx)

    counts = Counter(cn for s in class_sets for cn in s)
    exclusive = [{cn for cn in s if counts[cn] == 1} for s in class_sets]

    final: list[set[str]] = [set(e) for e in exclusive]
    for cn, idxs in owners.items():
        if len(idxs) == 1:
            continue
        cls = class_by_name.get(cn, {})
        deps = set(cls.get("dependencies", []) or [])
        deps.update(cls.get("injected_fields", []) or [])
        deps = {d for d in deps if d in class_by_name}

        def _score(i: int) -> tuple:
            ent = domains[i].get("entity", "")
            stem_match = 1 if (ent and (cn == ent or cn.startswith(ent) or ent in cn)) else 0
            return (
                stem_match,
                len(deps & exclusive[i]),
                len(deps & class_sets[i]),
                domains[i].get("confidence", 0),
                -len(class_sets[i]),
                domains[i].get("name", ""),
            )

        pick = max(idxs, key=_score)
        final[pick].add(cn)

    services: list[dict] = []
    used_names: set[str] = set()
    for idx, dom in enumerate(domains):
        classes = sorted(final[idx])
        if not classes:
            continue
        name = _match_ai_service_name(dom, ai_candidates)
        if not name or name in used_names:
            name = _entity_service_name(dom.get("entity", ""))
            if name in used_names:
                name = dom.get("name", "Service")
        used_names.add(name)
        dom_classes = set(classes)
        endpoints = [
            {
                "method": e.get("method", "GET"),
                "path": e.get("path", "/"),
                "handler_class": e.get("handler_class", ""),
                "handler_method": e.get("handler_method", "handle"),
            }
            for e in all_endpoints
            if e.get("handler_class", "") in dom_classes
        ]
        services.append({
            "name": name,
            "description": dom.get("description", ""),
            "cohesion_score": 50,
            "coupling_score": 50,
            "classes": classes,
            "packages": [],
            "api_endpoints": endpoints,
            "database_tables": dom.get("database_tables", []),
            "confidence": dom.get("confidence", 55),
            "readiness": "yellow",
            "risk_level": "medium",
            "business_capability": dom.get("name", name),
        })
    return services


def _build_boundaries_from_ai_candidates(
    candidate_list: list,
    class_by_name: dict,
    all_endpoints: list[dict],
    all_classes: list[dict],
    capability_names: list[str],
) -> list[dict]:
    """Fallback boundary builder when no business domain could be detected.

    Uses the AI candidate service lists directly, resolving class names to the
    static analysis data and falling back to package matching when the AI names
    do not resolve.
    """
    services = []
    for svc in candidate_list:
        if not isinstance(svc, dict):
            continue
        class_names = svc.get("classes", []) or []
        resolved_classes = []
        for cn in class_names:
            if class_by_name.get(cn):
                resolved_classes.append(cn)
        if not resolved_classes:
            svc_packages = svc.get("packages", []) or []
            for pkg_name in svc_packages:
                for cn, cls in class_by_name.items():
                    if cls.get("package", "").startswith(pkg_name):
                        resolved_classes.append(cn)
        resolved_classes = list(dict.fromkeys(resolved_classes))

        confidence = svc.get("confidence", 0.5)
        confidence_pct = confidence * 100 if confidence <= 1 else confidence

        services.append({
            "name": svc.get("name", "Unknown"),
            "description": svc.get("description", ""),
            "cohesion_score": svc.get("cohesion_score", 50) if svc.get("cohesion_score", 50) <= 100 else confidence_pct,
            "coupling_score": svc.get("coupling_score", 50) if svc.get("coupling_score", 50) <= 100 else 100 - confidence_pct,
            "classes": resolved_classes,
            "packages": [],
            "api_endpoints": [],
            "database_tables": [],
            "confidence": confidence_pct,
            "readiness": svc.get("readiness", "yellow"),
            "risk_level": svc.get("risk_level", "medium"),
            "business_capability": svc.get("business_capability", "") or "",
        })

    # If still no services, create one from all classes
    if not services and all_classes:
        all_class_names = [c.get("name", "") for c in all_classes if c.get("name")]
        all_pkgs = list(set(c.get("package", "") for c in all_classes if c.get("package")))
        all_eps = [{
            "method": e.get("method", "GET"),
            "path": e.get("path", "/"),
            "handler_class": e.get("handler_class", ""),
            "handler_method": e.get("handler_method", "handle"),
        } for e in all_endpoints]
        p = _profile()
        services.append({
            "name": "MonolithService",
            "description": f"Entire monolith application with {len(all_class_names)} classes across {len(all_pkgs)} packages",
            "cohesion_score": 40,
            "coupling_score": 60,
            "classes": all_class_names[:p.orchestrator_max_classes],
            "packages": all_pkgs,
            "api_endpoints": all_eps[:p.orchestrator_max_endpoints],
            "database_tables": [],
            "confidence": 65,
            "readiness": "yellow",
            "risk_level": "medium",
            "business_capability": capability_names[0] if capability_names else "Core Application",
        })
    return services


def _is_infra_class(name: str, cls: dict) -> bool:
    """Config entry points, tests and exceptions are not domain code."""
    annotations = set(cls.get("annotations", []) or [])
    if annotations & {"Test", "SpringBootTest", "RunWith", "SpringBootApplication", "Configuration", "EnableAutoConfiguration", "ComponentScan"}:
        return True
    if name.endswith("Tests") or name.endswith("Test") or (name.endswith("IT") and name != "IT"):
        return True
    if name.endswith("Exception") or name.endswith("Exceptions") or name.endswith("Error") or name.endswith("Errors"):
        return True
    return False


def _drop_infra_classes(services: list[dict], class_by_name: dict) -> None:
    """Remove config entry points, tests and exceptions from every boundary.

    These classes are infrastructure, not domain code: the application entry
    point and its test bootstrap do not belong to any microservice and would
    distort the cohesion of whichever boundary contained them. They stay
    covered by the static analysis/dead-code artifacts instead.
    """
    for cn in list(class_by_name):
        if not _is_infra_class(cn, class_by_name[cn]):
            continue
        for svc in services:
            classes = svc.get("classes", []) or []
            if cn in classes:
                classes.remove(cn)
    services[:] = [s for s in services if s.get("classes", []) or []]


def analyze_service_boundaries(analysis_data: dict) -> dict:
    """Analyze service boundaries — drop-in replacement for bedrock_analyzer."""
    from app.ai.context.domains import detect_business_domains

    service = get_ai_service()
    discovery, metadata = service.discover_services(analysis_data)

    # Business domains are the deterministic source of truth for boundary
    # membership (Spec 01/02). AI discovery only contributes service names and
    # confidence; when no domain can be detected the AI candidate list is used
    # verbatim as a fallback.
    domains = detect_business_domains(analysis_data)
    capability_names = [d["name"] for d in domains]

    # Build a class lookup for enriching boundaries
    all_classes = analysis_data.get("classes", [])
    class_by_name = {c.get("name", ""): c for c in all_classes}
    all_endpoints = analysis_data.get("endpoints", [])

    candidate_list = discovery.get("candidate_services", [])
    # Ensure it's a list (Sprint 2 may return a single dict)
    if isinstance(candidate_list, dict):
        candidate_list = [candidate_list]

    if domains:
        services = _build_boundaries_from_domains(
            domains, candidate_list, class_by_name, all_endpoints
        )
        detected = capability_names
    else:
        services = _build_boundaries_from_ai_candidates(
            candidate_list, class_by_name, all_endpoints, all_classes, capability_names
        )
        detected = discovery.get("business_capabilities", []) or []
        if isinstance(detected, list) and detected:
            detected = [c for c in detected if c]
        if not detected:
            detected = capability_names

    # Guarantee 100% class coverage: any class the discovery omitted is
    # assigned to the boundary whose code it actually depends on. AI discovery
    # may also duplicate classes across boundaries or strand a class in its
    # own single-class boundary — resolve both deterministically so each class
    # belongs to exactly one boundary and none are fabricated or dropped.
    _assign_unassigned_classes(services, class_by_name)
    _resolve_class_ownership(services, class_by_name)
    # Re-cluster every class onto the dependency-grounded boundary it actually
    # belongs to; the AI's class lists are only used to seed the boundaries.
    # This repair is only meaningful when boundaries came from AI candidates —
    # domain-derived boundaries already carry full DDD chains grounded in the
    # dependency graph, and re-running it on them collapses single-package
    # monoliths into one service (the reassignment cascade favours the
    # largest boundary).
    if not domains:
        _deterministic_recluster(services, class_by_name)
    _merge_singleton_boundaries(services, class_by_name)
    # Config/test/exception classes are not domain code; exclude them from the
    # service boundaries so no domain is polluted by infrastructure.
    _drop_infra_classes(services, class_by_name)
    _merge_singleton_boundaries(services, class_by_name)
    # Derive packages, endpoints and database tables from the resolved classes
    # (exact handler_class matching only — no endpoint bleed between classes).
    _attach_boundary_details(services, class_by_name, all_endpoints)

    # Ground boundary cohesion/coupling in the dependency graph so migration
    # wave ordering and readiness scoring use real values, not 50/50 defaults.
    _apply_graph_boundary_metrics(services, analysis_data.get("dependency_edges", []))

    # Derive risk level and readiness from the grounded coupling/confidence so
    # the boundaries agree with the migration waves (which already use them).
    for svc in services:
        risk = _risk_level(svc)
        svc["risk_level"] = risk
        svc["readiness"] = "red" if risk in ("critical", "high") else "yellow" if risk == "medium" else "green"

    # Rebuild the capability list from the final boundaries so it never
    # mentions a capability whose boundary was merged away.
    final_caps = list(dict.fromkeys(
        s.get("business_capability", "") for s in services if s.get("business_capability")
    ))
    if not final_caps:
        final_caps = detected

    return {
        "services": services,
        "total_services": len(services),
        "business_capabilities": final_caps[: _profile().orchestrator_max_business_caps],
        "_model_id": _resolved_model_id(metadata),
    }


def _entity_tables(cls: dict) -> list[str]:
    """Resolve database table names from explicit @Table annotations or JPA default naming."""
    annotations = set(cls.get("annotations", []) or [])
    if "Table" in annotations:
        params = (cls.get("annotations_with_params") or {}).get("Table", "") or ""
        match = re.search(r"name\s*=\s*[\"']([^\"']+)[\"']", params)
        return [match.group(1)] if match else [cls.get("name", "")]
    if "Entity" in annotations or cls.get("is_entity"):
        name = cls.get("name", "")
        if name:
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            return [snake]
    return []


def _assign_unassigned_classes(services: list[dict], class_by_name: dict) -> None:
    """Assign classes the discovery omitted to the boundary that uses them.

    A leftover class joins the boundary with the most dependency overlap with
    its own dependencies (ties broken by package overlap), so storefront or
    support classes land next to the code they actually reference.
    """
    covered = {cn for svc in services for cn in svc.get("classes", []) or []}
    leftovers = [cn for cn in class_by_name if cn not in covered]
    if not leftovers:
        return

    for cn in leftovers:
        cls = class_by_name.get(cn, {})
        deps = set(cls.get("dependencies", []) or [])
        deps.update(cls.get("injected_fields", []) or [])
        deps = {d for d in deps if d in class_by_name}
        pkg = cls.get("package", "")

        # Maximise dependency affinity, then break ties by the SMALLEST
        # boundary so support/framework classes (which often have no project
        # deps at all) are spread across boundaries instead of all piling into
        # the first one and turning it into a gravity well for later reclustering.
        def _score(svc: dict) -> tuple:
            names = set(svc.get("classes", []) or [])
            dep_overlap = len(deps & names)
            reverse = sum(1 for n in names if cn in _class_deps(class_by_name[n]))
            pkg_frac = (
                sum(1 for n in names if class_by_name.get(n, {}).get("package", "") == pkg)
                / max(1, len(names))
            )
            return (-dep_overlap, -reverse, -pkg_frac, len(names))

        best = min(services, key=_score) if services else None

        if best is None:
            best = next((s for s in services if s.get("name") == "CommonService"), None)
        if best is None:
            best = services[0] if services else None
        if best is None:
            return
        if cn not in best.get("classes", []):
            best.setdefault("classes", []).append(cn)


def _resolve_class_ownership(services: list[dict], class_by_name: dict) -> None:
    """Give each class to exactly one boundary.

    AI discovery may assign a class to several boundaries. Resolve by keeping
    the class in the boundary whose existing classes overlap its dependencies
    the most (ties broken by package overlap, then boundary size) and dropping
    it from every other boundary.
    """
    owners: dict[str, list[str]] = {}
    for svc in services:
        for name in svc.get("classes", []) or []:
            if name not in class_by_name:
                continue
            owners.setdefault(name, [])
            if svc["name"] not in owners[name]:
                owners[name].append(svc["name"])

    for name, claiming in owners.items():
        if len(claiming) <= 1:
            continue
        cls = class_by_name[name]
        deps = set(cls.get("dependencies", []) or [])
        deps.update(cls.get("injected_fields", []) or [])
        pkg = cls.get("package", "")

        def _score(svc_name: str) -> tuple:
            names = {
                c for s in services if s["name"] == svc_name
                for c in s.get("classes", []) or []
            }
            return (
                len(deps & names),
                sum(1 for n in names if class_by_name.get(n, {}).get("package", "") == pkg),
                -len(names),
            )

        keep = max(claiming, key=_score)
        for svc in services:
            if svc["name"] == keep:
                continue
            if name in svc.get("classes", []):
                svc["classes"].remove(name)

    services[:] = [s for s in services if s.get("classes", []) or []]


def _has_ddd_chain(svc: dict, class_by_name: dict) -> bool:
    """Check if a service boundary has a valid DDD chain or multiple DDD roles."""
    classes = set(svc.get("classes", []) or [])
    has_ctrl = any(class_by_name.get(c, {}).get("is_controller") for c in classes)
    has_svc = any(class_by_name.get(c, {}).get("is_service") for c in classes)
    has_repo = any(
        class_by_name.get(c, {}).get("is_repository")
        or (class_by_name.get(c, {}).get("name", "").endswith("Repository"))
        for c in classes
    )
    has_entity = any(class_by_name.get(c, {}).get("is_entity") for c in classes)
    role_count = sum([has_ctrl, has_svc, has_repo, has_entity])
    return role_count >= 2


def _merge_singleton_boundaries(services: list[dict], class_by_name: dict) -> None:
    """Merge single-class boundaries into the boundary that uses that class.

    Boundaries that have a distinct DDD role structure are preserved.
    """
    while True:
        singleton = next(
            (s for s in services if len(s.get("classes", []) or []) == 1 and not _has_ddd_chain(s, class_by_name)),
            None,
        )
        if singleton is None:
            break
        name = singleton["classes"][0]
        cls = class_by_name.get(name, {})
        deps = set(cls.get("dependencies", []) or [])
        deps.update(cls.get("injected_fields", []) or [])
        pkg = cls.get("package", "")

        best = None
        best_score = (-1, -1)
        for other in services:
            if other is singleton:
                continue
            names = set(other.get("classes", []) or [])
            score = (
                len(deps & names),
                sum(1 for n in names if class_by_name.get(n, {}).get("package", "") == pkg),
            )
            if score > best_score:
                best, best_score = other, score

        if best is None:
            break
        if name not in best["classes"]:
            best["classes"].append(name)
        services.remove(singleton)


def _boundary_anchor(svc: dict, class_by_name: dict) -> str | None:
    """Pick the representative class that anchors a boundary in place.

    Prefers the service class whose name matches the boundary name (so the
    AI's names/capabilities stay authoritative), then a controller, then any
    service layer class already assigned to the boundary. Returns None when
    the boundary has no classes at all.
    """
    names = svc.get("classes", []) or []
    if not names:
        return None
    base = svc.get("name", "")
    if base.endswith("Service"):
        base = base[: -len("Service")]
    for cn in names:
        cls_base = cn
        if cls_base.endswith("Service"):
            cls_base = cls_base[: -len("Service")]
        if base and cls_base and (cls_base.startswith(base) or base.startswith(cls_base)):
            return cn
    for cn in names:
        if (class_by_name.get(cn, {}).get("type") or "").lower() == "controller":
            return cn
    for cn in names:
        cls_type = (class_by_name.get(cn, {}).get("type") or "").lower()
        if cls_type == "service":
            return cn
    return names[0]


def _deterministic_recluster(services: list[dict], class_by_name: dict) -> None:
    """Re-cluster classes onto boundaries from the dependency graph.

    AI discovery may dump a coherent group of classes into a single boundary
    (e.g. user/repository/service code landing in FollowUpsService) that
    local ownership resolution cannot repair. Each boundary is anchored on its
    representative class and every other class is then re-assigned to the
    boundary it has the strongest dependency affinity to — the boundary whose
    classes it references most, that references it most, and that shares its
    package. Anchors are pinned; iteration continues until the assignment is
    stable so every class lands exactly once and none are invented.
    """
    if len(services) <= 1:
        return

    all_types = {cn: class_by_name.get(cn, {}).get("type", "") for cn in class_by_name}

    pinned: dict[str, int] = {}
    for idx, svc in enumerate(services):
        anchor = _boundary_anchor(svc, class_by_name)
        if anchor is None:
            continue
        pinned[anchor] = idx
        for j, other in enumerate(services):
            if j == idx:
                continue
            if anchor in (other.get("classes", []) or []):
                other["classes"].remove(anchor)
        if anchor not in svc["classes"]:
            svc["classes"].append(anchor)

    def _class_deps_of(cn: str) -> set[str]:
        cls = class_by_name.get(cn, {})
        deps = set(cls.get("dependencies", []) or [])
        deps.update(cls.get("injected_fields", []) or [])
        return {d for d in deps if d in class_by_name}

    def _affinity(cn: str, idx: int) -> float:
        names = set(services[idx].get("classes", []) or [])
        names.discard(cn)
        if not names:
            return 0.0
        deps = _class_deps_of(cn)
        dep_overlap = len(deps & names)
        reverse = sum(
            1 for n in names if cn in _class_deps_of(n)
        )
        pkg = class_by_name.get(cn, {}).get("package", "")
        pkg_overlap = sum(1 for n in names if class_by_name.get(n, {}).get("package", "") == pkg)
        # Normalise by boundary size so a large boundary cannot out-attract
        # classes from smaller ones just by having more members (this is what
        # collapsed single-package monoliths into one all-encompassing service).
        return (dep_overlap * 3 + reverse * 2 + pkg_overlap) / len(names)

    for _ in range(10):
        moved = 0
        for cn in list(class_by_name):
            if cn in pinned:
                continue
            current = next(
                (i for i, svc in enumerate(services) if cn in (svc.get("classes", []) or [])),
                None,
            )
            if current is None:
                continue
            best_idx = current
            best_score = _affinity(cn, current)
            for idx in range(len(services)):
                score = _affinity(cn, idx)
                if score > best_score:
                    best_score, best_idx = score, idx
            if best_idx == current:
                continue
            for svc in services:
                if cn in (svc.get("classes", []) or []):
                    svc["classes"].remove(cn)
            services[best_idx].setdefault("classes", []).append(cn)
            moved += 1
        if moved == 0:
            break

    # Config/test classes have no dependency ties to a domain cluster; park
    # them in the smallest boundary so they do not pollute a domain's cohesion.
    infra_types = {"configuration", "test", "exception"}
    for cn in list(class_by_name):
        if cn in pinned:
            continue
        if (all_types.get(cn) or "").lower() not in infra_types:
            continue
        owner = next(
            (i for i, svc in enumerate(services) if cn in (svc.get("classes", []) or [])),
            None,
        )
        target = min(
            range(len(services)),
            key=lambda i: len(services[i].get("classes", []) or []),
        )
        if owner is None:
            services[target].setdefault("classes", []).append(cn)
        elif owner != target:
            services[owner]["classes"].remove(cn)
            services[target].setdefault("classes", []).append(cn)

    services[:] = [s for s in services if s.get("classes", []) or []]


def _attach_boundary_details(services: list[dict], class_by_name: dict, all_endpoints: list[dict]) -> None:
    """Derive packages, endpoints and database tables per boundary class."""
    endpoints_by_handler: dict[str, list[dict]] = {}
    for ep in all_endpoints:
        handler = ep.get("handler_class", "")
        endpoints_by_handler.setdefault(handler, []).append({
            "method": ep.get("method", "GET"),
            "path": ep.get("path", "/"),
            "handler_class": handler,
            "handler_method": ep.get("handler_method", "handle"),
        })

    for svc in services:
        classes = svc.get("classes", []) or []
        packages: list[str] = []
        endpoints: list[dict] = []
        db_tables: list[str] = []
        seen_endpoints: set[tuple] = set()

        for cn in classes:
            cls = class_by_name.get(cn, {})
            pkg = cls.get("package", "")
            if pkg and pkg not in packages:
                packages.append(pkg)
            for ep in endpoints_by_handler.get(cn, []):
                key = (ep["method"], ep["path"], ep["handler_class"])
                if key not in seen_endpoints:
                    seen_endpoints.add(key)
                    endpoints.append(ep)
            if cls.get("is_entity"):
                for table in _entity_tables(cls):
                    if table not in db_tables:
                        db_tables.append(table)

        svc["classes"] = classes
        svc["packages"] = packages
        svc["api_endpoints"] = endpoints
        if db_tables:
            svc["database_tables"] = db_tables


_SESSION_DEPS = {"HttpSession", "SessionStatus", "SessionAttributes", "SessionAttribute"}
_FILESYSTEM_DEPS = {"File", "Files", "Paths", "Path", "MultipartFile", "FileInputStream",
                    "FileOutputStream", "FileWriter", "FileReader", "Filesystems"}
_EXTERNAL_SDK_MARKERS = ("razorpay", "aws", "stripe", "twilio", "sendgrid",
                         "okhttp", "gson", "commons", "apache", "slack")


def _class_deps(cls: dict) -> set[str]:
    return set(cls.get("dependencies", [])) | set(cls.get("injected_fields", []))


def _build_cloud_readiness_categories(analysis_data: dict, sprint2_ready: dict) -> list[dict]:
    """Per-category cloud readiness breakdown (Spec 07)."""
    classes = analysis_data.get("classes", []) or []
    total = max(1, len(classes))

    session_users = [c for c in classes if _class_deps(c) & _SESSION_DEPS]
    filesystem_users = [c for c in classes if _class_deps(c) & _FILESYSTEM_DEPS]
    entities = [c for c in classes if c.get("is_entity", False)]
    repos = [c for c in classes if c.get("is_repository", False)]
    hardcoded = [c for c in classes if "@Value" in (c.get("annotations", []) or [])]

    external_deps = set()
    for c in classes:
        for d in _class_deps(c):
            low = d.lower()
            if any(m in low for m in _EXTERNAL_SDK_MARKERS):
                external_deps.add(d)

    compute_r = sprint2_ready.get("compute", 50) if isinstance(sprint2_ready.get("compute"), (int, float)) else 50
    db_r = sprint2_ready.get("database", 50) if isinstance(sprint2_ready.get("database"), (int, float)) else 50
    container_r = sprint2_ready.get("container", 50) if isinstance(sprint2_ready.get("container"), (int, float)) else 50
    config_r = sprint2_ready.get("configuration", 50) if isinstance(sprint2_ready.get("configuration"), (int, float)) else 50

    session_names = sorted(c["name"] for c in session_users)[:3]
    filesystem_names = sorted(c["name"] for c in filesystem_users)[:3]

    categories = [
        {
            "category": "Statelessness",
            "score": max(10, 100 - len(session_users) * 12),
            "evidence": (
                f"{len(session_users)} class(es) use session state "
                f"({', '.join(session_names) or 'none'})"
            ),
        },
        {
            "category": "File System Usage",
            "score": max(10, 100 - len(filesystem_users) * 20),
            "evidence": (
                f"{len(filesystem_users)} class(es) access the file system "
                f"({', '.join(filesystem_names) or 'none'})"
            ),
        },
        {
            "category": "Session Management",
            "score": max(10, 100 - len(session_users) * 12),
            "evidence": (
                f"Session state found in {len(session_users)} class(es); "
                f"requires sticky sessions or Redis session store"
            ),
        },
        {
            "category": "External Dependencies",
            "score": max(10, 100 - len(external_deps) * 12),
            "evidence": (
                f"{len(external_deps)} external SDK(s) detected "
                f"({', '.join(sorted(external_deps)[:3]) or 'none'})"
            ),
        },
        {
            "category": "Database Readiness",
            "score": max(10, db_r + (15 if entities else 0)),
            "evidence": (
                f"{len(entities)} entities, {len(repos)} repositories, "
                f"DB readiness: {db_r}/100"
            ),
        },
        {
            "category": "Container Readiness",
            "score": max(10, container_r),
            "evidence": f"Container readiness: {container_r}/100",
        },
        {
            "category": "Configuration Management",
            "score": max(10, config_r - len(hardcoded) * 10),
            "evidence": (
                f"{len(hardcoded)} class(es) with hardcoded configuration, "
                f"config readiness: {config_r}/100"
            ),
        },
    ]
    # Provide compute readiness as additional context.
    categories.append({
        "category": "Compute & Runtime",
        "score": max(10, compute_r),
        "evidence": f"Compute readiness: {compute_r}/100",
    })
    return categories


def generate_readiness_scores(analysis_data: dict) -> dict:
    """Generate readiness scores — maps Sprint 2 data to frontend dimensions.

    Each dimension now carries an evidence trail (bullets) and the cloud
    readiness dimension includes a per-category breakdown (Spec 06/07).
    """
    ctx = get_ai_service().engine.build_context(analysis_data)
    sprint2_ready = ctx.readiness_summary

    # Sprint 2 generates: compute, database, networking, configuration, security, container, cicd, observability
    # Frontend expects: code_quality, architecture, cloud_readiness, service_separation, database_coupling, documentation
    # Map them intelligently based on actual analysis data
    metrics = analysis_data.get("metrics", {})
    sprint2 = analysis_data.get("sprint2_analysis", {})
    arch = sprint2.get("architecture_summary", {})
    quality = sprint2.get("quality_metrics", {})
    god_classes = metrics.get("god_classes", [])
    long_methods = metrics.get("long_methods", [])
    circular_deps = metrics.get("circular_dependencies", [])
    import_cycles = metrics.get("import_only_cycles", [])
    injection_cycles = metrics.get("injection_cycles", [])
    dead_code = metrics.get("dead_code", 0)
    dead_code_count = len(dead_code) if isinstance(dead_code, list) else int(dead_code)
    shared_entities = metrics.get("shared_entities", [])
    total_classes = metrics.get("total_classes", 0)
    avg_complexity = metrics.get("avg_cyclomatic_complexity", 0)
    duplicate_pct = metrics.get("duplicate_lines_percent", 0)

    # Code quality: based on maintainability, god classes, complexity
    maintainability = quality.get("maintainability_score", 50)
    god_penalty = min(30, len(god_classes) * 10)
    code_quality_score = max(10, min(100, maintainability - god_penalty))
    code_quality_bullets = [
        f"Maintainability score: {maintainability}/100",
        f"Average cyclomatic complexity: {avg_complexity}",
    ]
    if god_classes:
        code_quality_bullets.append(f"{len(god_classes)} god class(es) detected")
    if long_methods:
        code_quality_bullets.append(f"{len(long_methods)} long method(s) detected")
    if dead_code_count:
        code_quality_bullets.append(f"{dead_code_count} dead code item(s) found")
    if duplicate_pct:
        code_quality_bullets.append(f"Duplicate lines: {duplicate_pct}%")
    code_quality_evidence = "; ".join(code_quality_bullets)

    # Architecture: based on pattern score, circular deps, modularity
    arch_score = arch.get("score", 50)
    modularity = arch.get("modularity_score", 50)
    circular_penalty = min(30, len(circular_deps) * 5)
    architecture_score = max(10, min(100, (arch_score + modularity) // 2 - circular_penalty))
    architecture_bullets = [
        f"Pattern score: {arch_score}/100",
        f"Modularity: {modularity}/100",
    ]
    if circular_deps:
        architecture_bullets.append(f"{len(circular_deps)} circular dependency cycle(s)")
    if import_cycles:
        architecture_bullets.append(f"{len(import_cycles)} import-only cycle(s)")
    if injection_cycles:
        architecture_bullets.append(f"{len(injection_cycles)} injection cycle(s)")
    if not (circular_deps or import_cycles or injection_cycles):
        architecture_bullets.append("No circular dependencies detected")
    architecture_evidence = "; ".join(architecture_bullets)

    # Cloud readiness: from Sprint 2 compute/container scores + category breakdown
    compute_r = sprint2_ready.get("compute", 50) if isinstance(sprint2_ready.get("compute"), (int, float)) else 50
    container_r = sprint2_ready.get("container", 50) if isinstance(sprint2_ready.get("container"), (int, float)) else 50
    cloud_readiness_score = (compute_r + container_r) // 2
    cloud_categories = _build_cloud_readiness_categories(analysis_data, sprint2_ready)
    cloud_bullets = [
        f"Compute: {compute_r}/100",
        f"Container: {container_r}/100",
    ]
    for cat in cloud_categories[:3]:
        cloud_bullets.append(f"{cat['category']}: {cat['score']}/100")
    cloud_readiness_evidence = "; ".join(cloud_bullets)

    # Service separation: based on package structure, dependency edges, domains
    dep_edges = len(analysis_data.get("dependency_edges", []))
    packages = set()
    for c in analysis_data.get("classes", []):
        pkg = c.get("package", "")
        if pkg:
            packages.add(pkg)
    domain_count = 0
    try:
        from app.ai.context.domains import detect_business_domains
        domain_count = len(detect_business_domains(analysis_data))
    except Exception:
        domain_count = 0
    # Coupling per class: high edge density drags the score down; domains raise it
    avg_edges = dep_edges / max(1, len(analysis_data.get("classes", [])))
    separation_score = 85 - min(60, avg_edges * 8)
    separation_score = min(100, separation_score + min(20, domain_count * 2)) if domain_count else separation_score
    separation_score = max(20, min(100, round(separation_score)))
    separation_bullets = [
        f"{len(packages)} packages, {dep_edges} dependency edges",
        f"{domain_count} business domains detected",
    ]
    if separation_score >= 60:
        separation_bullets.append("Well-separated business domains")
    elif separation_score >= 40:
        separation_bullets.append("Moderate separation — some cross-domain coupling")
    else:
        separation_bullets.append("Heavy coupling — consider merging services")
    separation_evidence = "; ".join(separation_bullets)

    # Database coupling: from Sprint 2 database readiness + entity sharing
    db_r = sprint2_ready.get("database", 50) if isinstance(sprint2_ready.get("database"), (int, float)) else 50
    entities = [c for c in analysis_data.get("classes", []) if c.get("is_entity", False)]
    db_coupling_score = max(10, min(100, db_r - len(entities) * 3))
    db_bullets = [
        f"{len(entities)} entities, DB readiness: {db_r}/100",
    ]
    if shared_entities:
        shared_noun = "entity" if len(shared_entities) == 1 else "entities"
        db_bullets.append(f"{len(shared_entities)} shared {shared_noun} across services")
    else:
        db_bullets.append("No shared entities detected")
    db_evidence = "; ".join(db_bullets)

    # Documentation: based on total classes vs methods ratio, code comments
    total_methods = metrics.get("total_methods", 0)
    doc_score = min(80, max(20, 60 + (total_classes * 2 if total_classes < 20 else 0)))
    doc_evidence = f"{total_classes} classes, {total_methods} methods analyzed"

    overall = sprint2_ready.get("overall", 50) if isinstance(sprint2_ready.get("overall"), (int, float)) else 50
    confidence = sprint2_ready.get("confidence", 0.6) if isinstance(sprint2_ready.get("confidence"), (int, float)) else 0.6

    return {
        "code_quality": {"score": code_quality_score, "evidence": code_quality_evidence,
                         "evidence_bullets": code_quality_bullets},
        "architecture": {"score": architecture_score, "evidence": architecture_evidence,
                         "evidence_bullets": architecture_bullets},
        "cloud_readiness": {"score": cloud_readiness_score, "evidence": cloud_readiness_evidence,
                            "evidence_bullets": cloud_bullets,
                            "categories": cloud_categories},
        "service_separation": {"score": separation_score, "evidence": separation_evidence,
                               "evidence_bullets": separation_bullets},
        "database_coupling": {"score": db_coupling_score, "evidence": db_evidence,
                              "evidence_bullets": db_bullets},
        "documentation": {"score": doc_score, "evidence": doc_evidence,
                          "evidence_bullets": [doc_evidence]},
        "overall": overall,
        "confidence": confidence,
        "summary": sprint2_ready.get("summary", "Analysis complete with moderate readiness assessment"),
    }


def generate_adrs(analysis_data: dict, boundaries: list[dict]) -> dict:
    """Generate ADRs — AI-powered with fallback.

    Feeds the actual detected service boundaries (with classes, endpoints,
    capabilities) into the ADR prompt so records reference real code. The
    resolved model id is returned via ``_model_id`` so callers can label the
    records honestly (AI model vs deterministic fallback).
    """
    service = get_ai_service()
    if boundaries:
        analysis_data = dict(analysis_data)
        analysis_data["candidate_services"] = boundaries
    adrs, metadata = service.generate_adrs(analysis_data)
    model_id = _resolved_model_id(metadata)
    for adr in adrs:
        adr.model_id = model_id
    return {"adrs": [a.to_dict() for a in adrs], "_model_id": model_id}


def _risk_level(svc: dict, default_confidence: float = 50) -> str:
    confidence = svc.get("confidence", default_confidence)
    coupling = svc.get("coupling_score", 50)
    if coupling > 70 or confidence < 40:
        return "critical"
    if coupling > 50 or confidence < 60:
        return "high"
    if coupling > 30:
        return "medium"
    return "low"


def _complexity(svc: dict, default_confidence: float = 50) -> str:
    confidence = svc.get("confidence", default_confidence)
    coupling = svc.get("coupling_score", 50)
    if coupling > 70:
        return "high"
    if coupling > 50:
        return "medium"
    if confidence >= 80:
        return "low"
    if confidence >= 60:
        return "medium"
    return "high"


def _complexity_rank(level: str) -> int:
    return {"low": 0, "moderate": 1, "medium": 1, "high": 2}.get(level, 1)


def generate_migration_waves(
    boundaries: list[dict], readiness: dict, analysis_data: dict | None = None
) -> dict:
    """Generate migration waves with business + technical justification.

    Waves are ordered by the service dependency graph (a service cannot ship
    before the services it depends on), then by risk/coupling. Each wave
    carries an explicit justification (Spec 03).
    """
    from app.ai.context.domains import build_service_dependency_graph

    if not boundaries:
        return {"waves": [], "total_weeks": 0, "recommended_order": []}

    dep_map = {}
    if analysis_data:
        dep_map = build_service_dependency_graph(boundaries, analysis_data)
    else:
        for svc in boundaries:
            dep_map[svc.get("name", "")] = svc.get("dependencies", [])

    by_name = {b.get("name", ""): b for b in boundaries}
    _risk_priority = {"critical": 3, "high": 2, "medium": 1, "low": 0}

    def _sort_key(svc: dict):
        name = svc.get("name", "")
        return (
            _risk_priority.get(_risk_level(svc), 1),
            -float(svc.get("confidence", 50)),
            len(svc.get("classes", []) or []),
            name,
        )

    # Topological wave assignment: process services whose dependencies are
    # already placed first, at most 2 per wave, lowest risk first.
    placed: set[str] = set()
    remaining = list(boundaries)
    wave_groups: list[list[dict]] = []
    while remaining:
        ready = [
            s for s in remaining
            if all(d in placed for d in dep_map.get(s.get("name", ""), []) if d != s.get("name"))
        ]
        if not ready:
            ready = remaining
        ready.sort(key=_sort_key)
        group = ready[:2]
        wave_groups.append(group)
        for svc in group:
            placed.add(svc.get("name", ""))
            remaining.remove(svc)

    waves = []
    wave_number = 1
    for group in wave_groups:
        service_names = [s.get("name", f"Service {i + 1}") for i, s in enumerate(group)]
        total_classes = sum(len(s.get("classes", []) or []) for s in group)
        timeline_weeks = max(2, min(12, total_classes // 3 + 2))
        engineers = max(2, min(8, total_classes // 4 + 2))

        wave_dep_numbers = set()
        justification: list[str] = []
        for svc in group:
            name = svc.get("name", "")
            cap = svc.get("business_capability") or name
            coupling = svc.get("coupling_score", 50)
            confidence = svc.get("confidence", 50)
            risk = _risk_level(svc)
            justification.append(
                f"{name} ({cap}): coupling {coupling}%, confidence {confidence}%, "
                f"risk {risk}"
            )
            for dep in dep_map.get(name, []):
                for prev_idx, prev_group in enumerate(wave_groups[: wave_number - 1]):
                    if any(p.get("name") == dep for p in prev_group):
                        wave_dep_numbers.add(prev_idx + 1)

        if not justification:
            justification = ["Foundational extraction with no upstream dependencies"]

        risk_level = "medium"
        complexity = "moderate"
        for svc in group:
            svc_risk = _risk_level(svc)
            svc_complexity = _complexity(svc)
            if _risk_priority.get(svc_risk, 1) > _risk_priority.get(risk_level, 1):
                risk_level = svc_risk
            if _complexity_rank(svc_complexity) > _complexity_rank(complexity):
                complexity = svc_complexity

        waves.append({
            "wave_number": wave_number,
            "name": f"Wave {wave_number}: {service_names[0]}",
            "services": service_names,
            "timeline_weeks": timeline_weeks,
            "estimated_engineers": engineers,
            "dependencies": sorted(wave_dep_numbers),
            "risk_level": risk_level,
            "migration_complexity": complexity,
            "justification": justification,
        })
        wave_number += 1

    total_weeks = sum(w.get("timeline_weeks", 0) for w in waves)

    return {
        "waves": waves,
        "total_weeks": total_weeks,
        "recommended_order": [w["name"] for w in waves],
    }


def generate_cost_comparison(analysis_data: dict, boundaries: list[dict]) -> dict:
    """Generate cost comparison — deterministic estimate based on actual metrics."""
    metrics = analysis_data.get("metrics", {})
    total_loc = metrics.get("total_lines", 0)
    total_classes = metrics.get("total_classes", 0)
    num_services = max(1, len(boundaries))
    god_classes = len(metrics.get("god_classes", []))
    circular_deps = len(metrics.get("circular_dependencies", []))

    # Base cost on actual codebase size: $1.50 per 1000 LOC/month for infrastructure
    base_infra = max(200, total_loc / 1000 * 1.5) if total_loc > 0 else 500
    # Operations cost: $0.80 per class/month
    ops_cost = max(100, total_classes * 0.8) if total_classes > 0 else 200
    # Maintenance engineering dominates legacy spend and grows with the number
    # of services the team must keep supporting independently.
    maintenance = max(500, num_services * 300)
    current_monthly = base_infra + ops_cost + maintenance

    # Post-migration: infrastructure goes down (serverless/containers), ops
    # stays similar and the maintenance burden drops sharply.
    post_infra = base_infra * 0.55  # 45% infra savings from microservices
    post_ops = ops_cost * 0.75  # 25% ops savings from independent deployment
    post_maintenance = maintenance * 0.4
    post_monthly = post_infra + post_ops + post_maintenance

    savings = max(0, current_monthly - post_monthly)

    # One-time migration cost based on complexity
    complexity_factor = god_classes * 500 + circular_deps * 300 + num_services * 1000
    one_time_cost = max(5000, complexity_factor + num_services * 2000)

    payback_months = max(1, round(one_time_cost / savings)) if savings > 0 else 24

    # The UI breaks costs into 5 categories; scale them so the lines always
    # sum to the monthly totals shown (maintenance is distributed across them).
    current_cats = base_infra + ops_cost
    post_cats = post_infra + post_ops
    current_scale = current_monthly / current_cats if current_cats > 0 else 1
    post_scale = post_monthly / post_cats if post_cats > 0 else 1

    # Reuse the actual migration wave plan so cost estimates never contradict
    # the roadmap (same wave count, timeline and team size).
    wave_result = generate_migration_waves(boundaries, {}, analysis_data)
    waves = wave_result.get("waves", [])
    total_weeks = wave_result.get("total_weeks", 0)
    peak_engineers = max((w.get("estimated_engineers", 2) for w in waves), default=2)

    return {
        "current_monthly": round(current_monthly, 2),
        "post_migration_monthly": round(post_monthly, 2),
        "monthly_savings": round(savings, 2),
        "annual_savings": round(savings * 12, 2),
        "one_time_cost": round(one_time_cost, 2),
        "payback_months": payback_months,
        "breakdown_current": {
            "compute": round(base_infra * 0.6 * current_scale, 2),
            "storage": round(base_infra * 0.2 * current_scale, 2),
            "networking": round(base_infra * 0.2 * current_scale, 2),
            "operations": round(ops_cost * 0.6 * current_scale, 2),
            "licensing": round(ops_cost * 0.4 * current_scale, 2),
        },
        "breakdown_post": {
            "compute": round(post_infra * 0.6 * post_scale, 2),
            "storage": round(post_infra * 0.2 * post_scale, 2),
            "networking": round(post_infra * 0.2 * post_scale, 2),
            "operations": round(post_ops * 0.6 * post_scale, 2),
            "licensing": round(post_ops * 0.4 * post_scale, 2),
        },
        "migration_impact": {
            "total_services": num_services,
            "total_waves": len(waves) or num_services,
            "estimated_timeline_weeks": total_weeks,
            "total_engineers_needed": peak_engineers,
            "risk_summary": f"{god_classes} god classes, {circular_deps} circular dependencies detected",
        },
    }


def generate_explainability(boundaries: list[dict], readiness: dict, analysis_data: dict) -> dict:
    """Generate explainability data — based on actual boundary analysis."""
    recommendations = []
    for b in boundaries:
        name = b.get("name", "Unknown")
        confidence = b.get("confidence", 50)
        classes = b.get("classes", [])
        packages = b.get("packages", [])
        cohesion = b.get("cohesion_score", 50)
        coupling = b.get("coupling_score", 50)

        # Build evidence from actual data
        evidence_parts = []
        if classes:
            evidence_parts.append(f"{len(classes)} classes identified")
        if packages:
            evidence_parts.append(f"From {', '.join(packages[:3])} packages")
        if cohesion > 70:
            evidence_parts.append(f"High cohesion ({cohesion}%)")
        if coupling < 30:
            evidence_parts.append(f"Low coupling ({coupling}%)")

        primary_reason = f"Service boundary detected with {confidence}% confidence"
        if evidence_parts:
            primary_reason += f" — {', '.join(evidence_parts)}"

        recommendations.append({
            "service": name,
            "confidence": confidence,
            "primary_reason": primary_reason,
            "secondary_reasons": [
                f"Cohesion score: {cohesion}",
                f"Coupling score: {coupling}",
                f"{len(classes)} classes across {len(packages)} packages",
            ],
            "evidence": {
                "code_isolation": f"Based on {len(classes)} classes in {', '.join(packages[:2]) or 'unknown packages'}",
                "coupling_analysis": f"Coupling: {coupling}%",
                "database_ownership": f"{len(b.get('database_tables', []))} table(s) owned",
            },
            "migration_complexity": _complexity(b),
        })

    # Business capabilities come from the actual resolved boundaries (deduped —
    # a capability never appears twice even if two boundaries share the label).
    business_caps = list(dict.fromkeys(
        b.get("business_capability", "") for b in boundaries if b.get("business_capability")
    ))

    return {
        "recommendations": recommendations,
        "business_capabilities": business_caps[: _profile().orchestrator_max_business_caps],
        "risk_heatmap": [],
    }


def generate_service_code(service_name: str, boundary: dict, analysis_data: dict) -> dict:
    """Generate service code — placeholder for Sprint 4."""
    return {"files": [], "compilation_notes": "Code generation not yet implemented", "deployment_notes": ""}


# =============================================================================
# Sprint 4 Extension Hooks — NOT IMPLEMENTED
# Reserve architecture for:
#   - Amazon SQS async analysis
#   - Amazon EventBridge event publishing
#   - AWS Step Functions workflow state
#   - Long-running analysis with heartbeat
#   - Workflow retries with exponential backoff
#   - Email notifications on completion
#   - Report generation pipeline
# =============================================================================

# TODO: Sprint 4 — SQS async analysis
# async def enqueue_analysis_job(job_id: str, analysis_data: dict) -> str:
#     """Send analysis job to SQS for async processing."""
#     raise NotImplementedError("SQS async analysis - Sprint 4")

# TODO: Sprint 4 — EventBridge event publishing
# async def publish_analysis_event(event_type: str, job_id: str, data: dict) -> str:
#     """Publish analysis event to EventBridge."""
#     raise NotImplementedError("EventBridge events - Sprint 4")

# TODO: Sprint 4 — Step Functions workflow
# async def start_workflow(job_id: str) -> str:
#     """Start a Step Functions workflow for long-running analysis."""
#     raise NotImplementedError("Step Functions workflow - Sprint 4")

# TODO: Sprint 4 — Email notifications
# async def send_completion_notification(job_id: str, status: str, recipient: str = "") -> None:
#     """Send email notification when analysis completes."""
#     raise NotImplementedError("Email notifications - Sprint 4")

# TODO: Sprint 4 — Report generation pipeline
# async def generate_report(job_id: str, report_type: str = "full") -> dict:
#     """Generate comprehensive report and store in S3."""
#     raise NotImplementedError("Report generation pipeline - Sprint 4")
