"""Bedrock AI analysis service — calls Amazon Nova for intelligent analysis."""

import json
import re
from pathlib import Path

import structlog

from app.aws.bedrock import BedrockRepository
from app.core.analysis_profile import get_active_profile
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()
profile = get_active_profile(settings.analysis_mode,
                              settings.bedrock_max_tokens,
                              settings.ai_prompt_max_tokens)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.warning("prompt_file_not_found", name=name)
    return ""


def _validate_boundaries(data: dict) -> dict:
    if "services" not in data:
        data["services"] = []
    for svc in data["services"]:
        svc.setdefault("name", "UnknownService")
        svc.setdefault("description", "")
        svc.setdefault("cohesion_score", 50)
        svc.setdefault("coupling_score", 50)
        svc.setdefault("classes", [])
        svc.setdefault("packages", [])
        svc.setdefault("api_endpoints", [])
        svc.setdefault("database_tables", [])
        svc.setdefault("confidence", 50)
        svc.setdefault("readiness", "yellow")
        svc.setdefault("risk_level", "medium")
        svc.setdefault("business_capability", "")
        if svc["readiness"] not in ("green", "yellow", "red"):
            svc["readiness"] = "yellow"
        if svc["risk_level"] not in ("low", "medium", "high", "critical"):
            svc["risk_level"] = "medium"
    data.setdefault("total_services", len(data["services"]))
    data.setdefault("business_capabilities", [])
    return data


def _validate_readiness(data: dict) -> dict:
    defaults = {
        "code_quality": {"score": 0, "evidence": "No data"},
        "architecture": {"score": 0, "evidence": "No data"},
        "cloud_readiness": {"score": 0, "evidence": "No data"},
        "service_separation": {"score": 0, "evidence": "No data"},
        "database_coupling": {"score": 0, "evidence": "No data"},
        "documentation": {"score": 0, "evidence": "No data"},
        "overall": 0,
        "confidence": 0,
        "summary": "Analysis incomplete",
    }
    for key, default_val in defaults.items():
        if key not in data:
            data[key] = default_val
    if not isinstance(data.get("overall"), (int, float)):
        data["overall"] = 0
    return data


def _validate_adrs(data: dict) -> dict:
    if "adrs" not in data:
        data["adrs"] = []
    for adr in data["adrs"]:
        adr.setdefault("id", "ADR-000")
        adr.setdefault("title", "Unknown Decision")
        adr.setdefault("status", "Recommended")
        adr.setdefault("context", "")
        adr.setdefault("decision", "")
        adr.setdefault("alternatives", [])
        adr.setdefault("tradeoffs", {"pros": [], "cons": []})
        adr.setdefault("consequences", {"positive": [], "negative": [], "risks": []})
        adr.setdefault("confidence", 50)
        adr.setdefault("migration_impact", {
            "complexity": "medium", "estimated_effort": "TBD",
            "team_size": 2, "risk_factors": []
        })
    return data


def _validate_waves(data: dict) -> dict:
    if "waves" not in data:
        data["waves"] = []
    for wave in data["waves"]:
        wave.setdefault("wave_number", 1)
        wave.setdefault("name", "Unknown Wave")
        wave.setdefault("services", [])
        wave.setdefault("timeline_weeks", 4)
        wave.setdefault("estimated_engineers", 2)
        wave.setdefault("dependencies", [])
        wave.setdefault("risk_level", "medium")
        wave.setdefault("migration_complexity", "moderate")
        if wave["risk_level"] not in ("low", "medium", "high", "critical"):
            wave["risk_level"] = "medium"
    data.setdefault("total_weeks", sum(w.get("timeline_weeks", 4) for w in data["waves"]))
    data.setdefault("recommended_order", [])
    return data


def _truncate_to_budget(sections: list[tuple[str, str]], total_budget: int | None = None) -> str:
    """Build prompt with proportional, JSON-safe truncation.

    Preserves every section by allocating budget proportionally.
    Truncates at newline boundaries to avoid breaking JSON mid-value.
    """
    if total_budget is None:
        total_budget = profile.prompt_max_tokens
    if not sections:
        return ""

    header = sections[0][1] if sections[0][0] == "header" else ""
    footer = sections[-1][1] if sections[-1][0] == "footer" else ""
    content_sections = [(name, text) for name, text in sections if name not in ("header", "footer")]
    if not content_sections:
        return header + footer

    available = total_budget - len(header) - len(footer)
    if available <= 0:
        return header + footer

    total_content_len = sum(len(text) for _, text in content_sections)
    if total_content_len <= available:
        return header + "\n".join(text for _, text in content_sections) + footer

    result = header
    for name, text in content_sections:
        proportional = max(50, int((len(text) / total_content_len) * available))
        if len(text) > proportional:
            truncated = _truncate_json_safe(text, proportional)
            result += truncated + f"\n... [truncated {name}]\n"
        else:
            result += text + "\n"
    result += footer
    return result


def _truncate_json_safe(text: str, limit: int) -> str:
    """Truncate text at a newline boundary to avoid breaking JSON."""
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last_newline = truncated.rfind("\n")
    if last_newline > limit // 2:
        return truncated[:last_newline]
    return truncated


def _get_output_tokens() -> int:
    return profile.bedrock_max_tokens


def _limit_list(items: list, limit: int) -> list:
    if limit < 0:
        return items
    return items[:limit]


def _limit_chars(text: str, limit: int) -> str:
    if limit < 0:
        return text
    return text[:limit]


def analyze_service_boundaries(analysis_data: dict) -> dict:
    prompt = _build_boundary_prompt(analysis_data)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    result = _parse_json_response(response)
    return _validate_boundaries(result)


def generate_readiness_scores(analysis_data: dict) -> dict:
    prompt = _build_readiness_prompt(analysis_data)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    result = _parse_json_response(response)
    return _validate_readiness(result)


def generate_adrs(analysis_data: dict, boundaries: list[dict]) -> dict:
    prompt = _build_adr_prompt(analysis_data, boundaries)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    result = _parse_json_response(response)
    return _validate_adrs(result)


def generate_migration_waves(boundaries: list[dict], readiness: dict) -> dict:
    prompt = _build_wave_prompt(boundaries, readiness)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    result = _parse_json_response(response)
    return _validate_waves(result)


def generate_cost_comparison(analysis_data: dict, boundaries: list[dict]) -> dict:
    prompt = _build_cost_prompt(analysis_data, boundaries)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    return _parse_json_response(response)


def generate_explainability(boundaries: list[dict], readiness: dict, analysis_data: dict) -> dict:
    prompt = _build_explainability_prompt(boundaries, readiness, analysis_data)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens())
    return _parse_json_response(response)


def generate_service_code(service_name: str, boundary: dict, analysis_data: dict) -> dict:
    prompt = _build_codegen_prompt(service_name, boundary, analysis_data)
    repo = BedrockRepository()
    response = repo.invoke(prompt, max_tokens=_get_output_tokens(), model_id=settings.bedrock_model_codegen)
    return _parse_json_response(response)


def _parse_json_response(response: str) -> dict:
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"raw_response": response, "parse_error": True}


def _build_sections_for_budget(sections: list[tuple[str, str]]) -> str:
    return _truncate_to_budget(sections, total_budget=profile.prompt_max_tokens)


def _build_boundary_prompt(data: dict) -> str:
    classes = data.get("classes", [])
    package_tree = data.get("package_tree", {})
    endpoints = data.get("endpoints", [])
    dependencies = data.get("dependency_edges", [])
    metrics = data.get("metrics", {})

    god_classes = metrics.get("god_classes", [])
    circular_deps = metrics.get("circular_dependencies", [])
    injection_deps = metrics.get("injection_dependencies", [])

    god_class_names = [g["name"] for g in god_classes]
    god_class_details = [f"- {g['name']}: {g['reason']}" for g in god_classes]

    classes_summary = []
    for c in _limit_list(classes, profile.max_classes):
        classes_summary.append({
            "name": c["name"],
            "package": c["package"],
            "loc": c["lines_of_code"],
            "methods": c["method_count"],
            "annotations": c.get("annotations", [])[:profile.max_annotations_per_class],
            "deps": c.get("dependencies", [])[:profile.max_deps_per_class],
            "injected_fields": c.get("injected_fields", []),
            "is_entity": c.get("is_entity", False),
            "is_controller": c.get("is_controller", False),
            "is_service": c.get("is_service", False),
            "is_god_class": c["name"] in god_class_names,
        })

    header = _load_prompt("architecture.txt")
    sections = [
        ("header", header),
        ("classes", f"CLASSES ({len(classes)} total):\n{_limit_chars(json.dumps(classes_summary, indent=2), profile.classes_json_max_chars)}"),
        ("packages", f"PACKAGE TREE:\n{_limit_chars(json.dumps(package_tree, indent=2), profile.package_tree_json_max_chars)}"),
        ("endpoints", f"API ENDPOINTS ({len(endpoints)}):\n{_limit_chars(json.dumps(_limit_list(endpoints, profile.max_endpoints), indent=2), profile.endpoints_json_max_chars)}"),
        ("dependencies", f"DEPENDENCY EDGES ({len(dependencies)}):\n{_limit_chars(json.dumps(_limit_list(dependencies, profile.max_dependency_edges), indent=2), profile.dependencies_json_max_chars)}"),
        ("god_classes", f"GOD CLASSES TO SPLIT (CRITICAL — must be decomposed):\n{chr(10).join(god_class_details) if god_class_details else 'None detected'}"),
        ("injection", f"INJECTION DEPENDENCIES ({len(injection_deps)}):\n{_limit_chars(json.dumps(_limit_list(injection_deps, profile.max_injection_deps), indent=2), profile.injection_deps_json_max_chars)}"),
        ("circular", f"CIRCULAR DEPENDENCIES ({len(circular_deps)} total — these chains MUST be broken during extraction):\n{_limit_chars(json.dumps(_limit_list(circular_deps, profile.max_circular_deps), indent=2), profile.circular_deps_json_max_chars)}"),
        ("footer", """
CRITICAL RULES:
1. USE ACTUAL CLASS NAMES: Name services using actual class names from the codebase.
2. GOD CLASSES MUST BE DECOMPOSED
3. Circular dependencies MUST be broken during extraction
4. Each service should own its database tables (no shared tables)
5. Group by BUSINESS DOMAIN, not technical layer
6. Services with LOW coupling scores should be extracted FIRST
7. MAP each service to specific source classes

Return JSON: {"services": [list], "total_services": N, "business_capabilities": [list]}"""),
    ]
    return _build_sections_for_budget(sections)


def _build_readiness_prompt(data: dict) -> str:
    metrics = data.get("metrics", {})
    god_classes = metrics.get("god_classes", [])
    circular_deps = metrics.get("circular_dependencies", [])
    dead_code = metrics.get("dead_code", [])
    shared_entities = metrics.get("shared_entities", [])

    circular_dep_descriptions = []
    for i, cd in enumerate(_limit_list(circular_deps, profile.max_circular_deps), 1):
        cycle = cd.get("cycle", [])
        cycle_type = cd.get("type", "import")
        chain = " -> ".join(cycle)
        circular_dep_descriptions.append(f"  {i}. [{cycle_type.upper()}] {chain}")

    circular_dep_text = "\n".join(circular_dep_descriptions) if circular_dep_descriptions else "  NONE DETECTED"
    num_circular = len(circular_deps)

    header = _load_prompt("summary.txt")
    sections = [
        ("header", header),
        ("metrics", f"""METRICS:
- Total classes: {metrics.get('total_classes', 0)}
- Total LOC: {metrics.get('total_lines', 0)}
- God classes: {len(god_classes)}
- Circular dependencies: {num_circular}
- Dead code: {len(dead_code)}
- Shared entities: {len(shared_entities)}"""),
        ("god_classes", f"GOD CLASSES:\n{_limit_chars(json.dumps(_limit_list(god_classes, profile.max_god_classes), indent=2), profile.god_classes_json_max_chars)}"),
        ("circular", f"CIRCULAR DEPENDENCY CHAINS ({num_circular} total):\n{circular_dep_text}"),
        ("footer", """
SCORING RULES:
- code_quality: If god classes exist, max 40. PatientService alone caps at 30.
- architecture: If circular deps exist, max 35.
- cloud_readiness: If god classes exist, max 35.
- service_separation: If circular deps exist, max 40.
- database_coupling: If shared entities exist, max 40.

ARCHITECTURE EVIDENCE MUST mention circular dependency chains by name.

Return JSON:
{
  "code_quality": {"score": N, "evidence": "..."},
  "architecture": {"score": N, "evidence": "MUST mention circular deps by name"},
  "cloud_readiness": {"score": N, "evidence": "..."},
  "service_separation": {"score": N, "evidence": "..."},
  "database_coupling": {"score": N, "evidence": "..."},
  "documentation": {"score": N, "evidence": "..."},
  "overall": N,
  "confidence": N,
  "summary": "..."
}"""),
    ]
    return _build_sections_for_budget(sections)


def _build_adr_prompt(data: dict, boundaries: list) -> str:
    metrics = data.get("metrics", {})
    god_classes = metrics.get("god_classes", [])
    circular_deps = metrics.get("circular_dependencies", [])

    service_evidence = []
    for s in _limit_list(boundaries, profile.max_boundaries_for_adr):
        svc_name = s.get("name", "")
        svc_classes = s.get("classes", [])
        affected_god_classes = [g for g in god_classes if g["name"] in svc_classes]
        affected_circular = [
            c for c in circular_deps
            if any(cls in svc_classes for cls in c.get("cycle", []))
        ]
        service_evidence.append({
            "service": svc_name,
            "classes": svc_classes,
            "coupling_score": s.get("coupling_score", 50),
            "risk_level": s.get("risk_level", "medium"),
            "god_classes_in_service": affected_god_classes,
            "circular_deps_involving": affected_circular,
        })

    header = _load_prompt("adr.txt")
    sections = [
        ("header", header),
        ("service_evidence", f"SERVICE EVIDENCE:\n{_limit_chars(json.dumps(service_evidence, indent=2), profile.service_evidence_json_max_chars)}"),
        ("footer", """
CRITICAL RULES:
1. Each ADR context MUST reference specific god classes or circular dependencies by name
2. Each ADR tradeoffs.cons MUST include 2+ service-specific risks
3. Do NOT use the same template for all ADRs

Return JSON: {"adrs": [list of ADR objects]}

"""),
    ]
    return _build_sections_for_budget(sections)


def _build_wave_prompt(boundaries: list, readiness: dict) -> str:
    coupling_data = sorted(boundaries, key=lambda x: x.get("coupling_score", 100))

    service_deps = {}
    service_names = {s["name"] for s in coupling_data}
    class_to_service = {}
    for s in coupling_data:
        for cls in s.get("classes", []):
            class_to_service[cls] = s["name"]

    for s in coupling_data:
        svc_name = s["name"]
        deps = set()
        for inj in s.get("injected_fields", []):
            if inj in class_to_service and class_to_service[inj] != svc_name:
                deps.add(class_to_service[inj])
        service_deps[svc_name] = list(deps)

    header = _load_prompt("migration.txt")
    sections = [
        ("header", header),
        ("coupling", f"SERVICES (sorted by coupling — LOWEST first = extract FIRST):\n{_limit_chars(json.dumps(coupling_data, indent=2), profile.coupling_data_json_max_chars)}"),
        ("service_deps", f"SERVICE DEPENDENCY GRAPH:\n{_limit_chars(json.dumps(service_deps, indent=2), profile.service_deps_json_max_chars)}"),
        ("readiness", f"READINESS:\n{_limit_chars(json.dumps(readiness, indent=2), profile.readiness_json_max_chars)}"),
        ("footer", """
WAVE PLANNING RULES:
1. Wave 1: LOWEST coupling (< 30), LOW risk. 1-2 services max.
2. Wave 2: Low-medium coupling (30-50). 1-2 services.
3. Wave 3: MEDIUM coupling (50-70). 1-2 services.
4. Wave 4: HIGHER coupling (>70) or CIRCULAR DEPENDENCIES.
5. Wave 5: GOD CLASS services needing decomposition.
6. Max 2 services per wave unless trivially simple.
7. Services with CIRCULAR DEPENDENCIES must be in consecutive waves.

Return JSON: {"waves": [list], "total_weeks": N, "recommended_order": [list]}

"""),
    ]
    return _build_sections_for_budget(sections)


def _build_cost_prompt(data: dict, boundaries: list) -> str:
    metrics = data.get("metrics", {})
    return f"""You are an AWS cost optimization expert.

Estimate cost comparison between monolith and proposed microservices.

MONOLITH:
- LOC: {metrics.get('total_lines', 0)}
- Classes: {metrics.get('total_classes', 0)}
- Endpoints: {len(data.get('endpoints', []))}

PROPOSED SERVICES: {len(boundaries)} microservices

Return JSON:
{{
  "current_monthly": N,
  "post_migration_monthly": N,
  "monthly_savings": N,
  "annual_savings": N,
  "one_time_cost": N,
  "payback_months": N,
  "breakdown_current": {{"infrastructure": N, "operations": N, "development": N}},
  "breakdown_post": {{"infrastructure": N, "operations": N, "development_savings": N}},
  "migration_impact": {{
    "total_services": N,
    "total_waves": N,
    "estimated_timeline_weeks": N,
    "total_engineers_needed": N,
    "risk_summary": "..."
  }}
}}"""


def _build_explainability_prompt(boundaries: list, readiness: dict, data: dict) -> str:
    sections = [
        ("header", "You are an AI explainability expert.\n\nFor each service recommendation, provide detailed reasoning.\n"),
        ("recommendations", f"RECOMMENDATIONS:\n{_limit_chars(json.dumps(_limit_list(boundaries, profile.max_boundaries_for_explain), indent=2), profile.explain_boundary_json_max_chars)}"),
        ("footer", """
For each service, explain:
1. Why this service was recommended
2. Evidence from code analysis
3. Confidence breakdown by factor

Return JSON:
{
  "recommendations": [
    {
      "service": "ServiceName",
      "confidence": N,
      "primary_reason": "...",
      "secondary_reasons": ["..."],
      "evidence": {"code_isolation": "..."},
      "migration_complexity": "simple|moderate|complex"
    }
  ],
  "business_capabilities": ["..."],
  "risk_heatmap": [{"service": "Name", "risk_level": "low|medium|high", "risk_factors": ["..."]}]
}

"""),
    ]
    return _build_sections_for_budget(sections)


def _build_codegen_prompt(service_name: str, boundary: dict, data: dict) -> str:
    sections = [
        ("header", f"You are a Java Spring Boot expert generating production-ready microservice code.\n\nGenerate complete code for: {service_name}\n"),
        ("boundary", f"BOUNDARY:\n{_limit_chars(json.dumps(boundary, indent=2), profile.codegen_boundary_json_max_chars)}"),
        ("footer", """
Generate these files:
1. Controller class
2. Service class
3. Repository class
4. Model/Entity class
5. DTO classes
6. Dockerfile
7. pom.xml
8. application.yml
9. CDK stack
10. OpenAPI 3.0 spec

Return JSON:
{
  "files": [{"path": "src/main/java/.../Xxx.java", "content": "..."}],
  "compilation_notes": "...",
  "deployment_notes": "..."
}

"""),
    ]
    return _build_sections_for_budget(sections)
