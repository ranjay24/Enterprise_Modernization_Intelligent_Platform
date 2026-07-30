"""Cloud Readiness dimension scorers — each returns 0-100."""

from __future__ import annotations

from typing import Any


def score_compute_readiness(metrics: dict, classes: list) -> dict[str, Any]:
    score = 50
    reasons = []
    total_loc = metrics.get("total_lines", 0)
    god_classes = len(metrics.get("god_classes", []))
    if total_loc < 50000:
        score += 15; reasons.append("Moderate codebase size")
    elif total_loc > 200000:
        score -= 15; reasons.append("Very large codebase")
    if god_classes == 0:
        score += 10; reasons.append("No god classes detected")
    elif god_classes > 3:
        score -= 20; reasons.append(f"{god_classes} god classes need decomposition")
    avg_complexity = metrics.get("avg_cyclomatic_complexity", 0)
    if avg_complexity < 15:
        score += 5; reasons.append("Low average complexity")
    elif avg_complexity > 30:
        score -= 10; reasons.append("High average complexity")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_database_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 50
    reasons = []
    shared_entities = metrics.get("shared_entities", [])
    entities = [c for c in context.parsed_classes if c.is_entity]
    if not entities:
        score += 10; reasons.append("No JPA entities detected — may use external DB")
    elif len(shared_entities) == 0:
        score += 15; reasons.append("No shared entity coupling detected")
    else:
        score -= len(shared_entities) * 10; reasons.append(f"{len(shared_entities)} shared entities found")
    repositories = [c for c in context.parsed_classes if c.is_repository]
    if repositories:
        score += 5; reasons.append(f"{len(repositories)} repository interfaces found")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_networking_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 60
    reasons = []
    endpoints = context.endpoints
    if len(endpoints) > 0:
        score += 10; reasons.append(f"{len(endpoints)} API endpoints identified")
    rest_endpoints = [e for e in endpoints if hasattr(e, "method") and e.method != "ALL"]
    if rest_endpoints:
        score += 5; reasons.append("REST-style endpoints detected")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_configuration_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 50
    reasons = []
    metadata = context.project_metadata or {}
    configs = metadata.get("config_files", [])
    if configs:
        score += 10; reasons.append(f"{len(configs)} configuration files found")
    has_application_yml = any("application.yml" in c or "application.yaml" in c for c in configs)
    has_properties = any("application.properties" in c for c in configs)
    if has_application_yml:
        score += 10; reasons.append("Uses YAML config (cloud-friendly)")
    elif has_properties:
        score += 5; reasons.append("Uses properties config (consider migrating to YAML)")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_security_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 50
    reasons = []
    risk_findings = context.risk_findings or []
    hardcoded = [r for r in risk_findings if r.get("category", "").startswith("hardcoded")]
    if hardcoded:
        score -= len(hardcoded) * 10; reasons.append(f"{len(hardcoded)} hardcoded config/secret risks")
    else:
        score += 10; reasons.append("No hardcoded secrets detected")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_container_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 55
    reasons = []
    metadata = context.project_metadata or {}
    build_tool = metadata.get("build_tool", "unknown")
    if build_tool in ("maven", "gradle"):
        score += 10; reasons.append(f"{build_tool.title()} build detected — containerizable")
    classes = context.parsed_classes
    has_main = any(c.name == "Application" or "main" in c.name.lower() for c in classes)
    if has_main:
        score += 5; reasons.append("Entry point class detected")
    avg_loc = metrics.get("avg_class_size", 0)
    if avg_loc < 200:
        score += 5; reasons.append("Reasonable average class size")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_cicd_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 40
    reasons = []
    metadata = context.project_metadata or {}
    build_tool = metadata.get("build_tool", "unknown")
    if build_tool == "maven":
        score += 15; reasons.append("Maven — mature CI/CD ecosystem")
    elif build_tool == "gradle":
        score += 15; reasons.append("Gradle — good CI/CD support")
    configs = metadata.get("config_files", [])
    has_docker = any("dockerfile" in c.lower() or "docker-compose" in c.lower() for c in configs)
    if has_docker:
        score += 15; reasons.append("Docker configuration found")
    else:
        reasons.append("No Docker configuration detected")
    return {"score": max(0, min(100, score)), "reasons": reasons}


def score_observability_readiness(metrics: dict, context: Any) -> dict[str, Any]:
    score = 35
    reasons = []
    classes = context.parsed_classes
    has_logging = any("log" in c.name.lower() or "Logger" in str(c.annotations) for c in classes)
    if has_logging:
        score += 10; reasons.append("Logging patterns detected")
    else:
        reasons.append("No explicit logging patterns found")
    has_monitoring = any("metrics" in c.name.lower() or "health" in c.name.lower() for c in classes)
    if has_monitoring:
        score += 10; reasons.append("Health/metrics classes found")
    else:
        reasons.append("No health check or metrics classes detected")
    return {"score": max(0, min(100, score)), "reasons": reasons}
