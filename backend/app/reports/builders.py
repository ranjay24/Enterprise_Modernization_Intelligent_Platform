"""Shared report builders — single source of truth for all report generation."""

from __future__ import annotations

from app.core.analysis_profile import get_profile_for_settings


def build_executive_summary(results: dict) -> dict:
    """Build executive summary from assembled results."""
    metrics = results.get("metrics", {})
    readiness = results.get("readiness", {})
    cost = results.get("cost_comparison", {})
    services = results.get("service_boundaries", [])
    sprint2 = results.get("sprint2_analysis", {}) or {}
    project_name = (
        (sprint2.get("project_summary", {}) or {}).get("project_name")
        or results.get("project_name")
        or results.get("job_id", "Unknown")
    )

    return {
        "title": "Executive Summary — Monolith to Microservices Migration",
        "project_name": project_name,
        "overall_score": readiness.get("overall", 0),
        "risk_level": _derive_risk_level(readiness),
        "recommended_services": len(services),
        "estimated_monthly_savings": cost.get("monthly_savings", 0),
        "estimated_annual_savings": cost.get("annual_savings", 0),
        "estimated_payback_months": cost.get("payback_months", 0),
        "key_findings": [
            f"Detected {metrics.get('total_classes', 0)} classes across {len(services)} potential services",
            f"Overall modernization readiness: {readiness.get('overall', 0)}/100",
            f"Estimated monthly savings post-migration: ${cost.get('monthly_savings', 0):,.2f}",
        ],
        "recommendation": _derive_recommendation(readiness),
    }


def build_developer_report(results: dict) -> dict:
    """Build developer-focused technical report."""
    metrics = results.get("metrics", {})
    services = results.get("service_boundaries", [])
    adrs = results.get("adrs", [])

    return {
        "title": "Developer Report — Technical Analysis",
        "codebase_metrics": {
            "total_classes": metrics.get("total_classes", 0),
            "total_lines": metrics.get("total_lines", 0),
            "total_methods": metrics.get("total_methods", 0),
            "god_classes": len(metrics.get("god_classes", [])),
            "circular_dependencies": len(metrics.get("circular_dependencies", [])),
        },
        "services": [
            {
                "name": s.get("name", ""),
                "classes": len(s.get("classes", [])),
                "coupling_score": s.get("coupling_score", 0),
                "risk_level": s.get("risk_level", "medium"),
            }
            for s in services
        ],
        "adr_count": len(adrs),
        "priority_actions": [
            "Decompose god classes before service extraction",
            "Break circular dependency chains",
            "Establish API contracts between services",
        ],
    }


def build_risk_analysis(results: dict) -> dict:
    """Build risk analysis report."""
    metrics = results.get("metrics", {})
    services = results.get("service_boundaries", [])
    risk_findings = results.get("sprint2_analysis", {}).get("risk_report", {}).get("findings", [])

    profile = get_profile_for_settings()
    return {
        "title": "Risk Analysis",
        "total_risks": len(risk_findings),
        "critical_risks": len([r for r in risk_findings if r.get("severity") == "critical"]),
        "high_risks": len([r for r in risk_findings if r.get("severity") == "high"]),
        "findings": risk_findings[:profile.report_max_risk_findings],
        "high_risk_services": [
            s.get("name", "") for s in services if s.get("risk_level") in ("high", "critical")
        ],
        "god_classes": [g.get("name", "") for g in metrics.get("god_classes", [])],
        "circular_dependencies": [
            c.get("cycle", []) for c in metrics.get("circular_dependencies", [])[:profile.report_max_circular_deps]
        ],
    }


def build_architecture_report(results: dict) -> dict:
    """Build architecture analysis report."""
    services = results.get("service_boundaries", [])
    readiness = results.get("readiness", {})

    return {
        "title": "Architecture Report",
        "detected_style": "modular_monolith",
        "recommended_style": "microservices",
        "service_count": len(services),
        "readiness_scores": readiness,
        "services": [
            {
                "name": s.get("name", ""),
                "confidence": s.get("confidence", 0),
                "cohesion_score": s.get("cohesion_score", 0),
                "coupling_score": s.get("coupling_score", 0),
                "readiness": s.get("readiness", "yellow"),
            }
            for s in services
        ],
    }


def build_migration_roadmap(results: dict) -> dict:
    """Build migration roadmap report."""
    waves = results.get("migration_waves", [])
    return {
        "title": "Migration Roadmap",
        "total_waves": len(waves),
        "waves": waves,
        "estimated_total_weeks": sum(w.get("timeline_weeks", 4) for w in waves),
    }


def build_all_reports(results: dict) -> dict[str, dict]:
    """Build all five reports from assembled results."""
    return {
        "executive_summary": build_executive_summary(results),
        "developer_report": build_developer_report(results),
        "risk_analysis": build_risk_analysis(results),
        "architecture_report": build_architecture_report(results),
        "migration_roadmap": build_migration_roadmap(results),
    }


def _derive_risk_level(readiness: dict) -> str:
    overall = readiness.get("overall", 50)
    if overall >= 70:
        return "low"
    if overall >= 40:
        return "medium"
    return "high"


def _derive_recommendation(readiness: dict) -> str:
    overall = readiness.get("overall", 50)
    if overall >= 70:
        return "Proceed with migration — codebase is reasonably ready"
    if overall >= 40:
        return "Proceed with caution — address key risks first"
    return "Significant refactoring needed before migration"
