"""AI Microservice Discovery — discovers candidate microservices from analysis."""

from __future__ import annotations

import structlog

from app.ai.context.builder import AIContext

logger = structlog.get_logger(__name__)


class AIMicroserviceDiscovery:
    """Discovers candidate microservices using Sprint 2 analysis data + AI insights.

    Generates:
    - Candidate Microservices with suggested APIs
    - Suggested Database Ownership
    - Shared Components
    - Communication Style
    - Migration Order
    - Dependencies
    """

    def discover(self, ai_context: AIContext, parsed_response: dict = None) -> dict:
        """Discover microservices from AI-enhanced response or fallback to static analysis."""
        if parsed_response and parsed_response.get("services"):
            return self._build_from_ai(ai_context, parsed_response)
        return self._discover_from_analysis(ai_context)

    def _build_from_ai(self, ai_context: AIContext, parsed_response: dict) -> dict:
        services = []
        for svc in parsed_response.get("services", []):
            services.append({
                "name": svc.get("name", ""),
                "description": svc.get("description", ""),
                "classes": svc.get("classes", []),
                "packages": svc.get("packages", []),
                "api_endpoints": svc.get("api_endpoints", []),
                "database_tables": svc.get("database_tables", []),
                "confidence": svc.get("confidence", 0.5),
                "readiness": svc.get("readiness", "yellow"),
                "risk_level": svc.get("risk_level", "medium"),
                "business_capability": svc.get("business_capability", ""),
                "communication_style": "sync",
                "shared_components": [],
            })

        return {
            "candidate_services": services,
            "total_services": len(services),
            "business_capabilities": parsed_response.get("business_capabilities", []),
            "migration_order": [s["name"] for s in sorted(services, key=lambda x: x.get("confidence", 0), reverse=True)],
            "dependency_map": self._build_dependency_map(services, ai_context),
        }

    def _discover_from_analysis(self, ai_context: AIContext) -> dict:
        """Discover services from Sprint 2 analysis without AI."""
        services = []
        raw_candidates = ai_context.candidate_services

        # Handle both list of services and single recommendation dict
        candidates_list = []
        if isinstance(raw_candidates, list):
            candidates_list = raw_candidates
        elif isinstance(raw_candidates, dict) and raw_candidates.get("title"):
            # Single recommendation — extract package-based services
            candidates_list = [raw_candidates]

        for svc in candidates_list:
            if not isinstance(svc, dict):
                continue
            name = svc.get("name", "")
            # If no name, try to extract from title or description
            if not name:
                title = svc.get("title", "")
                if "Extract" in title and "as Microservice" in title:
                    # "Extract com.enterprise.hospital.controller as Microservice"
                    parts = title.split("Extract ")
                    if len(parts) > 1:
                        pkg = parts[1].split(" as ")[0].strip()
                        name = pkg.split(".")[-1].capitalize() + "Service"
                elif "Package" in svc.get("description", ""):
                    desc = svc.get("description", "")
                    pkg_part = desc.split("Package ")[1].split(" ")[0] if "Package " in desc else ""
                    if pkg_part:
                        name = pkg_part.split(".")[-1].capitalize() + "Service"
                else:
                    name = "Service"

            description = svc.get("description", "")
            classes = svc.get("classes", [])
            packages = svc.get("packages", [])
            evidence = svc.get("evidence", [])

            # Extract package from evidence if not in packages
            if not packages and evidence:
                for ev in evidence:
                    if isinstance(ev, str) and ev.startswith("Package:"):
                        pkg = ev.replace("Package:", "").strip()
                        packages.append(pkg)

            confidence = svc.get("confidence", 0.5)
            if confidence <= 1:
                confidence_pct = confidence * 100
            else:
                confidence_pct = confidence

            services.append({
                "name": name,
                "description": description,
                "classes": classes,
                "packages": packages,
                "api_endpoints": svc.get("api_endpoints", []),
                "database_tables": svc.get("database_tables", []),
                "confidence": confidence_pct,
                "readiness": svc.get("readiness", "yellow"),
                "risk_level": svc.get("risk_level", "medium"),
                "communication_style": "sync",
                "shared_components": [],
            })

        return {
            "candidate_services": services,
            "total_services": len(services),
            "business_capabilities": ai_context.bounded_contexts,
            "migration_order": [s["name"] for s in services],
            "dependency_map": {},
        }

    def _build_dependency_map(self, services: list[dict], ai_context: AIContext) -> dict:
        dep_map = {}
        class_to_service = {}
        for svc in services:
            for cls in svc.get("classes", []):
                class_to_service[cls] = svc["name"]

        for svc in services:
            deps = set()
            for cls in svc.get("classes", []):
                for finding in ai_context.risk_findings:
                    if cls in finding.get("affected_components", []):
                        pass
            dep_map[svc["name"]] = list(deps)

        return dep_map
