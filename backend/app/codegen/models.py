"""CodeGen models — lightweight validators and normalizers for agent outputs.

Agent outputs are stored as versioned artifacts (raw JSON). These helpers
normalize and sanity-check the agent JSON so downstream stages and the UI
can rely on stable shapes even when Bedrock returns partial content.
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)

VALID_BROKER_ROLES = {"kafka", "rabbitmq", "both", "none"}
VALID_RESILIENCE = {"retry", "circuit-breaker", "rate-limiter", "time-limiter", "bulkhead"}
VALID_SEVERITIES = {"critical", "major", "minor", "info"}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_service_list(plan: dict) -> list[dict]:
    """Return the list of service plans from a codegen_plan artifact."""
    services = plan.get("services") or plan.get("service_plans") or []
    if isinstance(services, dict):
        services = list(services.values())
    return _as_list(services)


def normalize_waves(plan: dict) -> list[dict]:
    waves = _as_list(plan.get("waves"))
    return [w for w in waves if isinstance(w, dict)]


def normalize_service_id(entry: dict, fallback: str = "service") -> str:
    return str(entry.get("id") or entry.get("name") or fallback).strip()


def broker_role_of(entry: dict) -> str:
    role = str(entry.get("broker_role", "none")).strip().lower()
    if role not in VALID_BROKER_ROLES:
        role = "none"
    return role


def resilience_of(entry: dict) -> list[str]:
    resilience = entry.get("resilience", [])
    if isinstance(resilience, dict):
        resilience = list(resilience.keys())
    return [r for r in _as_list(resilience) if r in VALID_RESILIENCE]


def normalize_architecture(design: dict) -> dict:
    """Normalize an architecture_design artifact for the UI graph renderer."""
    nodes = _as_list(design.get("nodes"))
    edges = _as_list(design.get("edges"))
    services = _as_list(design.get("services"))
    by_id = {}
    for svc in services:
        svc_id = normalize_service_id(svc)
        if svc_id:
            by_id[svc_id] = svc
    for node in nodes:
        node_id = str(node.get("id", ""))
        if node_id and node_id in by_id:
            svc = by_id[node_id]
            node.setdefault("broker_role", broker_role_of(svc))
            node.setdefault("resilience", resilience_of(svc))
            node.setdefault("tech_stack", _as_list(svc.get("tech_stack")))
    return {
        "version": design.get("version", "1.0.0"),
        "services": services,
        "nodes": nodes,
        "edges": edges,
        "message_topology": design.get("message_topology", {}),
    }


def normalize_service_code(code: dict) -> dict:
    """Normalize a service_code_<svc> artifact."""
    files = _as_list(code.get("files"))
    valid = []
    seen = set()
    for f in files:
        if not isinstance(f, dict):
            continue
        path = str(f.get("path", "")).strip()
        if not path or path in seen:
            continue
        seen.add(path)
        valid.append({"path": path, "content": str(f.get("content", ""))})
    return {
        "service_id": code.get("service_id", ""),
        "base_package": code.get("base_package", ""),
        "language": code.get("language", "java"),
        "build_tool": code.get("build_tool", "maven"),
        "files": valid,
        "compilation_notes": code.get("compilation_notes", ""),
        "deployment_notes": code.get("deployment_notes", ""),
    }


def normalize_findings(report: dict) -> list[dict]:
    findings = _as_list(report.get("findings"))
    cleaned = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        severity = str(f.get("severity", "info")).lower()
        if severity not in VALID_SEVERITIES:
            severity = "info"
        cleaned.append({
            "id": str(f.get("id", "")),
            "severity": severity,
            "category": str(f.get("category", "general")),
            "file": str(f.get("file", "")),
            "finding": str(f.get("finding", "")),
            "recommendation": str(f.get("recommendation", "")),
        })
    return cleaned


def blocking_findings(report: dict) -> list[dict]:
    """Findings that force a regeneration round."""
    return [f for f in normalize_findings(report) if f["severity"] in ("critical", "major")]


def is_approved(report: dict) -> bool:
    approved = report.get("approved")
    if isinstance(approved, bool):
        return approved
    return not blocking_findings(report)


def summarize_findings(report: dict) -> dict:
    findings = normalize_findings(report)
    counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    return counts
