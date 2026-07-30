"""AI Orchestrator — replaces direct bedrock_analyzer calls in the analysis pipeline.

Integrates with the existing orchestrator.py while providing the new AI layer
capabilities. Maintains backward compatibility with existing API contracts.
"""

from __future__ import annotations

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


def analyze_service_boundaries(analysis_data: dict) -> dict:
    """Analyze service boundaries — drop-in replacement for bedrock_analyzer."""
    service = get_ai_service()
    discovery, metadata = service.discover_services(analysis_data)

    # Build a class lookup for enriching boundaries
    all_classes = analysis_data.get("classes", [])
    class_by_name = {c.get("name", ""): c for c in all_classes}
    all_endpoints = analysis_data.get("endpoints", [])

    services = []
    candidate_list = discovery.get("candidate_services", [])
    # Ensure it's a list (Sprint 2 may return a single dict)
    if isinstance(candidate_list, dict):
        candidate_list = [candidate_list]

    for svc in candidate_list:
        if not isinstance(svc, dict):
            continue
        # Resolve class names to full class data
        class_names = svc.get("classes", []) or []
        resolved_classes = []
        packages = set()
        endpoints = []
        db_tables = []

        for cn in class_names:
            cls = class_by_name.get(cn, {})
            if cls:
                resolved_classes.append(cn)
                pkg = cls.get("package", "")
                if pkg:
                    packages.add(pkg)
                # Find endpoints for this class
                for ep in all_endpoints:
                    if ep.get("handler_class") == cn or cn in str(ep.get("handler_class", "")):
                        endpoints.append({
                            "method": ep.get("method", "GET"),
                            "path": ep.get("path", "/"),
                            "handler_class": cn,
                            "handler_method": ep.get("handler_method", "handle"),
                        })
                # Check if entity with tables
                if cls.get("is_entity"):
                    table_name = cn.replace("Entity", "").replace("Model", "").lower() + "s"
                    db_tables.append(table_name)

        # If no classes resolved from AI, use all classes from matching packages
        if not resolved_classes:
            svc_packages = svc.get("packages", []) or []
            for pkg_name in svc_packages:
                for cn, cls in class_by_name.items():
                    if cls.get("package", "").startswith(pkg_name):
                        resolved_classes.append(cn)
                        packages.add(pkg_name)
                        for ep in all_endpoints:
                            if cn in str(ep.get("handler_class", "")):
                                endpoints.append({
                                    "method": ep.get("method", "GET"),
                                    "path": ep.get("path", "/"),
                                    "handler_class": cn,
                                    "handler_method": ep.get("handler_method", "handle"),
                                })

        confidence = svc.get("confidence", 0.5)
        confidence_pct = confidence * 100 if confidence <= 1 else confidence

        services.append({
            "name": svc.get("name", "Unknown"),
            "description": svc.get("description", ""),
            "cohesion_score": svc.get("cohesion_score", 50) if svc.get("cohesion_score", 50) <= 100 else confidence_pct,
            "coupling_score": svc.get("coupling_score", 50) if svc.get("coupling_score", 50) <= 100 else 100 - confidence_pct,
            "classes": resolved_classes,
            "packages": list(packages),
            "api_endpoints": endpoints,
            "database_tables": db_tables,
            "confidence": confidence_pct,
            "readiness": svc.get("readiness", "yellow"),
            "risk_level": svc.get("risk_level", "medium"),
            "business_capability": svc.get("business_capability", ""),
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
            "business_capability": "Core Application",
        })

    return {
        "services": services,
        "total_services": len(services),
        "business_capabilities": discovery.get("business_capabilities", []),
    }


def generate_readiness_scores(analysis_data: dict) -> dict:
    """Generate readiness scores — maps Sprint 2 data to frontend dimensions."""
    ctx = get_ai_service().engine.build_context(analysis_data)
    sprint2_ready = ctx.readiness_summary

    # Sprint 2 generates: compute, database, networking, configuration, security, container, cicd, observability
    # Frontend expects: code_quality, architecture, cloud_readiness, service_separation, database_coupling, documentation
    # Map them intelligently based on actual analysis data
    metrics = analysis_data.get("metrics", {})
    sprint2 = analysis_data.get("sprint2_analysis", {})
    arch = sprint2.get("architecture_summary", {})
    quality = sprint2.get("quality_metrics", {})
    coupling_analysis = sprint2.get("coupling_analysis", {})
    god_classes = metrics.get("god_classes", [])
    circular_deps = metrics.get("circular_dependencies", [])
    total_classes = metrics.get("total_classes", 0)

    # Code quality: based on maintainability, god classes, complexity
    maintainability = quality.get("maintainability_score", 50)
    god_penalty = min(30, len(god_classes) * 10)
    code_quality_score = max(10, min(100, maintainability - god_penalty))
    code_quality_evidence = f"Maintainability: {maintainability}/100"
    if god_classes:
        code_quality_evidence += f", {len(god_classes)} god classes detected"

    # Architecture: based on pattern score, circular deps, modularity
    arch_score = arch.get("score", 50)
    modularity = arch.get("modularity_score", 50)
    circular_penalty = min(30, len(circular_deps) * 5)
    architecture_score = max(10, min(100, (arch_score + modularity) // 2 - circular_penalty))
    architecture_evidence = f"Pattern score: {arch_score}/100, Modularity: {modularity}/100"
    if circular_deps:
        architecture_evidence += f", {len(circular_deps)} circular dependencies"

    # Cloud readiness: from Sprint 2 compute/container scores
    compute_r = sprint2_ready.get("compute", 50) if isinstance(sprint2_ready.get("compute"), (int, float)) else 50
    container_r = sprint2_ready.get("container", 50) if isinstance(sprint2_ready.get("container"), (int, float)) else 50
    cloud_readiness_score = (compute_r + container_r) // 2

    # Service separation: based on package structure, dependency edges
    dep_edges = len(analysis_data.get("dependency_edges", []))
    packages = set()
    for c in analysis_data.get("classes", []):
        pkg = c.get("package", "")
        if pkg:
            packages.add(pkg)
    separation_score = min(100, max(20, 80 - dep_edges * 2 + len(packages) * 5)) if packages else 40
    separation_evidence = f"{len(packages)} packages, {dep_edges} dependency edges"

    # Database coupling: from Sprint 2 database readiness + entity sharing
    db_r = sprint2_ready.get("database", 50) if isinstance(sprint2_ready.get("database"), (int, float)) else 50
    entities = [c for c in analysis_data.get("classes", []) if c.get("is_entity", False)]
    db_coupling_score = max(10, min(100, db_r - len(entities) * 3))
    db_evidence = f"{len(entities)} entities, DB readiness: {db_r}/100"

    # Documentation: based on total classes vs methods ratio, code comments
    total_methods = metrics.get("total_methods", 0)
    doc_score = min(80, max(20, 60 + (total_classes * 2 if total_classes < 20 else 0)))
    doc_evidence = f"{total_classes} classes, {total_methods} methods analyzed"

    overall = sprint2_ready.get("overall", 50) if isinstance(sprint2_ready.get("overall"), (int, float)) else 50
    confidence = sprint2_ready.get("confidence", 0.6) if isinstance(sprint2_ready.get("confidence"), (int, float)) else 0.6

    return {
        "code_quality": {"score": code_quality_score, "evidence": code_quality_evidence},
        "architecture": {"score": architecture_score, "evidence": architecture_evidence},
        "cloud_readiness": {"score": cloud_readiness_score, "evidence": f"Compute: {compute_r}/100, Container: {container_r}/100"},
        "service_separation": {"score": separation_score, "evidence": separation_evidence},
        "database_coupling": {"score": db_coupling_score, "evidence": db_evidence},
        "documentation": {"score": doc_score, "evidence": doc_evidence},
        "overall": overall,
        "confidence": confidence,
        "summary": sprint2_ready.get("summary", "Analysis complete with moderate readiness assessment"),
    }


def generate_adrs(analysis_data: dict, boundaries: list[dict]) -> dict:
    """Generate ADRs — AI-powered with fallback."""
    service = get_ai_service()
    adrs, metadata = service.generate_adrs(analysis_data)
    return {"adrs": [a.to_dict() for a in adrs]}


def generate_migration_waves(boundaries: list[dict], readiness: dict) -> dict:
    """Generate migration waves — uses actual service boundary data."""
    if not boundaries:
        return {"waves": [], "total_weeks": 0, "recommended_order": []}

    # Sort by confidence (highest first = easiest to extract)
    sorted_svcs = sorted(boundaries, key=lambda b: b.get("confidence", 50), reverse=True)

    waves = []
    week_counter = 1
    for i, svc in enumerate(sorted_svcs):
        confidence = svc.get("confidence", 50)
        classes = svc.get("classes", [])
        num_classes = len(classes) if isinstance(classes, list) else 0
        complexity = "low" if confidence >= 80 else "medium" if confidence >= 60 else "high"

        timeline_weeks = max(2, min(12, num_classes // 3 + 2))
        engineers = max(2, min(8, num_classes // 4 + 2))

        # Risk level based on coupling and confidence
        coupling = svc.get("coupling_score", 50)
        if coupling > 70 or confidence < 40:
            risk = "critical"
        elif coupling > 50 or confidence < 60:
            risk = "high"
        elif coupling > 30:
            risk = "medium"
        else:
            risk = "low"

        dependencies = []
        if i > 0:
            dependencies.append(f"wave-{i}")

        wave_name = f"Wave {i + 1}: Extract {svc.get('name', f'Service {i + 1}')}"
        waves.append({
            "wave_number": i + 1,
            "name": wave_name,
            "services": [svc.get("name", f"Service {i + 1}")],
            "timeline_weeks": timeline_weeks,
            "estimated_engineers": engineers,
            "dependencies": dependencies,
            "risk_level": risk,
            "migration_complexity": complexity,
        })
        week_counter += timeline_weeks

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
    current_monthly = base_infra + ops_cost

    # Post-migration: infrastructure goes down (serverless/containers), ops stays similar
    post_infra = base_infra * 0.55  # 45% infra savings from microservices
    post_ops = ops_cost * 0.75  # 25% ops savings from independent deployment
    post_monthly = post_infra + post_ops

    savings = max(0, current_monthly - post_monthly)

    # One-time migration cost based on complexity
    complexity_factor = god_classes * 500 + circular_deps * 300 + num_services * 1000
    one_time_cost = max(5000, complexity_factor + num_services * 2000)

    payback_months = max(1, round(one_time_cost / savings)) if savings > 0 else 24

    return {
        "current_monthly": round(current_monthly, 2),
        "post_migration_monthly": round(post_monthly, 2),
        "monthly_savings": round(savings, 2),
        "annual_savings": round(savings * 12, 2),
        "one_time_cost": round(one_time_cost, 2),
        "payback_months": payback_months,
        "breakdown_current": {
            "compute": round(base_infra * 0.5, 2),
            "storage": round(base_infra * 0.15, 2),
            "networking": round(base_infra * 0.1, 2),
            "operations": round(ops_cost * 0.7, 2),
            "licensing": round(ops_cost * 0.3, 2),
        },
        "breakdown_post": {
            "compute": round(post_infra * 0.5, 2),
            "storage": round(post_infra * 0.15, 2),
            "networking": round(post_infra * 0.1, 2),
            "operations": round(post_ops * 0.7, 2),
            "licensing": round(post_ops * 0.3, 2),
        },
        "migration_impact": {
            "total_services": num_services,
            "total_waves": num_services,
            "estimated_timeline_weeks": sum(max(2, len(b.get("classes", [])) // 3 + 2) for b in boundaries),
            "total_engineers_needed": max(2, num_services * 2),
            "risk_summary": f"{god_classes} god classes, {circular_deps} circular dependencies need resolution",
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
                "low_coupling": f"Coupling: {coupling}%",
                "database_independence": f"{len(b.get('database_tables', []))} shared tables",
            },
            "migration_complexity": "low" if confidence >= 80 else "moderate" if confidence >= 60 else "high",
        })

    # Extract business capabilities from the analysis
    business_caps = []
    sprint2 = analysis_data.get("sprint2_analysis", {})
    bounded_contexts = sprint2.get("bounded_contexts", [])
    for bc in bounded_contexts:
        if isinstance(bc, dict):
            business_caps.append(bc.get("name", bc.get("capability", "")))
        elif isinstance(bc, str):
            business_caps.append(bc)

    return {
        "recommendations": recommendations,
        "business_capabilities": [c for c in business_caps if c][:_profile().orchestrator_max_business_caps],
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
