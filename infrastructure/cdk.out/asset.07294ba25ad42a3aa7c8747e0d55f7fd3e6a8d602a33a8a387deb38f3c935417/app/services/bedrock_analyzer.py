import json
import os
import re
from ..utils.aws import get_bedrock_client
from ..utils.config import (
    BEDROCK_MODEL_PRIMARY,
    BEDROCK_MODEL_FALLBACK,
    MAX_TOKENS_HAIKU,
)


def analyze_service_boundaries(analysis_data: dict) -> dict:
    prompt = _build_boundary_prompt(analysis_data)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_readiness_scores(analysis_data: dict) -> dict:
    prompt = _build_readiness_prompt(analysis_data)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_adrs(analysis_data: dict, boundaries: list[dict]) -> dict:
    prompt = _build_adr_prompt(analysis_data, boundaries)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_migration_waves(boundaries: list[dict], readiness: dict) -> dict:
    prompt = _build_wave_prompt(boundaries, readiness)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_cost_comparison(analysis_data: dict, boundaries: list[dict]) -> dict:
    prompt = _build_cost_prompt(analysis_data, boundaries)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_explainability(
    boundaries: list[dict], readiness: dict, analysis_data: dict
) -> dict:
    prompt = _build_explainability_prompt(boundaries, readiness, analysis_data)
    response = _invoke_bedrock(prompt, max_tokens=MAX_TOKENS_HAIKU)
    return _parse_json_response(response)


def generate_service_code(
    service_name: str,
    boundary: dict,
    analysis_data: dict,
) -> dict:
    prompt = _build_codegen_prompt(service_name, boundary, analysis_data)
    from ..utils.config import BEDROCK_MODEL_CODEGEN

    response = _invoke_bedrock(
        prompt, max_tokens=MAX_TOKENS_HAIKU, model_id=BEDROCK_MODEL_CODEGEN
    )
    return _parse_json_response(response)


def _invoke_bedrock(
    prompt: str, max_tokens: int = 4096, model_id: str | None = None
) -> str:
    client = get_bedrock_client()
    model = model_id or BEDROCK_MODEL_PRIMARY

    try:
        response = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.0},
        )
        output = response["output"]["message"]["content"]
        return output[0]["text"]
    except Exception:
        if model != BEDROCK_MODEL_FALLBACK:
            return _invoke_bedrock(prompt, max_tokens, BEDROCK_MODEL_FALLBACK)
        raise


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


def _build_boundary_prompt(data: dict) -> str:
    classes = data.get("classes", [])
    package_tree = data.get("package_tree", {})
    endpoints = data.get("endpoints", [])
    dependencies = data.get("dependency_edges", [])

    classes_summary = []
    for c in classes[:100]:
        classes_summary.append(
            {
                "name": c["name"],
                "package": c["package"],
                "loc": c["lines_of_code"],
                "methods": c["method_count"],
                "annotations": c.get("annotations", [])[:5],
                "deps": c.get("dependencies", [])[:10],
            }
        )

    return f"""You are an expert software architect specializing in Domain-Driven Design and microservices.

Analyze the following monolithic Java application and identify optimal microservice boundaries.

CLASSES ({len(classes)} total):
{json.dumps(classes_summary, indent=2)[:6000]}

PACKAGE TREE:
{json.dumps(package_tree, indent=2)[:2000]}

API ENDPOINTS ({len(endpoints)}):
{json.dumps(endpoints[:30], indent=2)[:2000]}

DEPENDENCY EDGES ({len(dependencies)}):
{json.dumps(dependencies[:50], indent=2)[:2000]}

For each recommended microservice, provide:
1. name: Service name (PascalCase)
2. description: What this service does (1 sentence)
3. cohesion_score: 0-100 (how cohesive are the classes)
4. coupling_score: 0-100 (lower = less coupled to others)
5. classes: List of class names assigned to this service
6. packages: List of Java packages
7. api_endpoints: List of endpoints this service owns
8. database_tables: List of tables (inferred from class names)
9. confidence: 0-100 (how confident you are in this boundary)
10. readiness: "green", "yellow", or "red"
11. risk_level: "low", "medium", "high", or "critical"

Apply DDD principles:
- Group by business domain, not technical layer
- Minimize inter-service dependencies
- Each service should own its data
- Start with the most isolated, low-coupling services first

Return JSON: {{"services": [list of service objects], "total_services": N}}"""


def _build_readiness_prompt(data: dict) -> str:
    metrics = data.get("metrics", {})
    classes = data.get("classes", [])
    endpoints = data.get("endpoints", [])

    return f"""You are a cloud architecture readiness assessor.

Score the following monolith for microservices migration readiness.

METRICS:
- Total classes: {metrics.get('total_classes', 0)}
- Total LOC: {metrics.get('total_lines', 0)}
- Total methods: {metrics.get('total_methods', 0)}
- God classes: {len(metrics.get('god_classes', []))}
- Circular dependencies: {len(metrics.get('circular_dependencies', []))}
- Dead code classes: {len(metrics.get('dead_code', []))}
- Duplicate lines: {metrics.get('duplicate_lines_percent', 0)}%
- API endpoints: {len(endpoints)}

GOD CLASSES:
{json.dumps(metrics.get('god_classes', [])[:10], indent=2)[:2000]}

CIRCULAR DEPS:
{json.dumps(metrics.get('circular_dependencies', [])[:10], indent=2)[:1000]}

Score each dimension 0-100:
1. code_quality: Method count, complexity, duplication (weight 25%)
2. architecture: Cohesion, coupling, layering (weight 20%)
3. cloud_readiness: Statelessness, 12-factor compliance (weight 20%)
4. service_separation: Data isolation, API boundaries (weight 20%)
5. database_coupling: Shared tables, transaction scope (weight 10%)
6. documentation: JavaDoc, README, comments (weight 5%)

Calculate overall as weighted average.
Provide confidence % with evidence.

Return JSON:
{{
  "code_quality": {{"score": N, "evidence": "..."}},
  "architecture": {{"score": N, "evidence": "..."}},
  "cloud_readiness": {{"score": N, "evidence": "..."}},
  "service_separation": {{"score": N, "evidence": "..."}},
  "database_coupling": {{"score": N, "evidence": "..."}},
  "documentation": {{"score": N, "evidence": "..."}},
  "overall": N,
  "confidence": N,
  "summary": "..."
}}"""


def _build_adr_prompt(data: dict, boundaries: list) -> str:
    return f"""You are a software architect generating Architecture Decision Records (ADRs).

Generate an ADR for each recommended microservice extraction.

SERVICES TO EXTRACT:
{json.dumps(boundaries[:10], indent=2)[:5000]}

For each service, generate an ADR with:
- id: "ADR-NNN"
- title: "Extract {{ServiceName}}"
- status: "Recommended" | "Accepted" | "Superseded"
- context: Why this extraction is needed (2-3 paragraphs)
- decision: What was decided and why
- alternatives: List of alternatives considered with rejection reasons
- tradeoffs: {{"pros": [...], "cons": [...]}}
- consequences: {{"positive": [...], "negative": [...], "risks": [...]}}
- confidence: 0-100

Order ADRs by extraction priority (first service to extract = ADR-001).

Return JSON: {{"adrs": [list of ADR objects]}}"""


def _build_wave_prompt(boundaries: list, readiness: dict) -> str:
    return f"""You are a migration planning expert.

Create a phased migration plan for extracting these microservices.

SERVICES:
{json.dumps(boundaries[:10], indent=2)[:5000]}

READINESS:
{json.dumps(readiness, indent=2)[:2000]}

Create 3 waves:
- Wave 1 (Foundation): Low-risk, low-complexity services that unblock others
- Wave 2 (Core): Medium-complexity core business services
- Wave 3 (Advanced): High-complexity, high-risk services

For each wave provide:
- wave_number: 1, 2, or 3
- name: Descriptive name
- services: List of service names
- timeline_weeks: Estimated duration
- estimated_engineers: Team size needed
- dependencies: What must complete before this wave
- risk_level: Overall risk

Return JSON: {{"waves": [list of wave objects], "total_weeks": N}}"""


def _build_cost_prompt(data: dict, boundaries: list) -> str:
    metrics = data.get("metrics", {})
    return f"""You are an AWS cost optimization expert.

Estimate the cost comparison between the current monolith and the proposed microservices architecture.

MONOLITH:
- LOC: {metrics.get('total_lines', 0)}
- Classes: {metrics.get('total_classes', 0)}
- Endpoints: {len(data.get('endpoints', []))}

PROPOSED SERVICES: {len(boundaries)} microservices

Estimate monthly AWS costs for:
1. Current: EC2, RDS, ALB, data transfer, operations
2. Post-migration: ECS Fargate, DynamoDB, Lambda, SQS, ALB, CloudWatch

Provide detailed breakdown and ROI analysis.

Return JSON:
{{
  "current_monthly": N,
  "post_migration_monthly": N,
  "monthly_savings": N,
  "annual_savings": N,
  "one_time_cost": N,
  "payback_months": N,
  "breakdown_current": {{"infrastructure": N, "operations": N, "development": N}},
  "breakdown_post": {{"infrastructure": N, "operations": N, "development_savings": N}}
}}"""


def _build_explainability_prompt(boundaries, readiness, data) -> str:
    return f"""You are an AI explainability expert.

For each service recommendation, provide detailed reasoning.

RECOMMENDATIONS:
{json.dumps(boundaries[:5], indent=2)[:4000]}

For each service, explain:
1. Why this service was recommended (primary, secondary reasons)
2. Evidence from code analysis supporting this recommendation
3. What scores contributed to the decision
4. Why other services were NOT recommended first
5. Confidence breakdown by factor

Return JSON:
{{
  "recommendations": [
    {{
      "service": "ServiceName",
      "confidence": N,
      "primary_reason": "...",
      "secondary_reasons": ["...", "..."],
      "evidence": {{"code_isolation": "...", "low_coupling": "...", "...": "..."}},
      "why_not_others": {{"ServiceA": "reason", "ServiceB": "reason"}},
      "confidence_factors": {{"factor": weight*score}}
    }}
  ]
}}"""


def _build_codegen_prompt(service_name, boundary, data) -> str:
    return f"""You are a Java Spring Boot expert generating production-ready microservice code.

Generate complete code for: {service_name}

BOUNDARY:
{json.dumps(boundary, indent=2)[:3000]}

ENDPOINTS:
{json.dumps(boundary.get('api_endpoints', [])[:10], indent=2)[:2000]}

Generate these files:
1. Controller class (REST endpoints)
2. Service class (business logic)
3. Repository class (data access)
4. Model/Entity class
5. DTO classes (request/response)
6. Exception classes
7. Dockerfile (multi-stage build)
8. pom.xml (Spring Boot 3.x dependencies)
9. application.yml (config)
10. CDK stack (Python) for ECS + DynamoDB deployment
11. OpenAPI 3.0 spec
12. buildspec.yml (CodeBuild)

Follow Spring Boot 3.x conventions. Use proper packages:
- com.enterprise.{service_name.lower()}.controller
- com.enterprise.{service_name.lower()}.service
- com.enterprise.{service_name.lower()}.repository
- com.enterprise.{service_name.lower()}.model
- com.enterprise.{service_name.lower()}.dto
- com.enterprise.{service_name.lower()}.exception

Return JSON:
{{
  "files": [
    {{"path": "src/main/java/.../Xxx.java", "content": "..."}},
    {{"path": "Dockerfile", "content": "..."}},
    {{"path": "pom.xml", "content": "..."}},
    {{"path": "cdk_stack.py", "content": "..."}},
    {{"path": "openapi.yaml", "content": "..."}},
    ...
  ],
  "compilation_notes": "...",
  "deployment_notes": "..."
}}"""
