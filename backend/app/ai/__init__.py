"""Enterprise AI Intelligence Layer — Sprint 3.

Provides AI-powered modernization analysis, recommendations, ADRs,
migration planning, executive summaries, and developer reports.

Architecture:
- Provider layer: model adapters, factory, registry
- Guardrails: prompt validation, policy enforcement, data redaction
- Pipeline: explicit stage-based orchestration
- Contracts: strongly typed output models
- Context builder: transforms Sprint 2 data into AI-ready context
- Prompt registry: versioned template loading and rendering
- Cost tracking: token usage and estimated inference costs
- Observability: latency, success rates, failure tracking
- Memory: architecture preparation for future conversational support

NOTE: Imports are lazy to avoid circular dependency issues at module load time.
Access the engine/service via get_ai_engine() / get_ai_service() functions.
"""


def get_ai_engine():
    from app.ai.engine import AIEngine
    from app.ai.service import get_ai_engine as _get
    return _get()


def get_ai_service():
    from app.ai.service import get_ai_service as _get
    return _get()


def analyze_service_boundaries(analysis_data: dict) -> dict:
    from app.ai.orchestrator import analyze_service_boundaries as _fn
    return _fn(analysis_data)


def generate_readiness_scores(analysis_data: dict) -> dict:
    from app.ai.orchestrator import generate_readiness_scores as _fn
    return _fn(analysis_data)


def generate_adrs(analysis_data: dict, boundaries: list[dict]) -> dict:
    from app.ai.orchestrator import generate_adrs as _fn
    return _fn(analysis_data, boundaries)


def generate_migration_waves(boundaries: list[dict], readiness: dict) -> dict:
    from app.ai.orchestrator import generate_migration_waves as _fn
    return _fn(boundaries, readiness)


def generate_cost_comparison(analysis_data: dict, boundaries: list[dict]) -> dict:
    from app.ai.orchestrator import generate_cost_comparison as _fn
    return _fn(analysis_data, boundaries)


def generate_explainability(boundaries: list[dict], readiness: dict, analysis_data: dict) -> dict:
    from app.ai.orchestrator import generate_explainability as _fn
    return _fn(boundaries, readiness, analysis_data)


def generate_service_code(service_name: str, boundary: dict, analysis_data: dict) -> dict:
    from app.ai.orchestrator import generate_service_code as _fn
    return _fn(service_name, boundary, analysis_data)
