"""Analysis Mode profiles — centralised limits for FAST, NORMAL, DEEP, and BENCHMARK modes.

Every limit that controls how much data is sent to Bedrock lives here.
NORMAL mode preserves byte-for-byte identical behaviour to pre-deep-mode.
BENCHMARK mode auto-detects the active Bedrock model and configures the
maximum safe limits supported by that model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class AnalysisMode(str, Enum):
    FAST = "fast"
    NORMAL = "normal"
    DEEP = "deep"
    BENCHMARK = "benchmark"


# ---------------------------------------------------------------------------
# Model capability registry — single source of truth for model limits.
# Add new models here when they are supported.
# ---------------------------------------------------------------------------
@dataclass
class ModelCapabilities:
    model_id: str
    max_input_context: int       # tokens
    max_output_tokens: int       # tokens
    provider: str = "bedrock"

_MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    # Amazon Nova
    "amazon.nova-pro-v1:0": ModelCapabilities(
        model_id="amazon.nova-pro-v1:0", max_input_context=300_000, max_output_tokens=10_000,
    ),
    "amazon.nova-lite-v1:0": ModelCapabilities(
        model_id="amazon.nova-lite-v1:0", max_input_context=300_000, max_output_tokens=10_000,
    ),
    "amazon.nova-micro-v1:0": ModelCapabilities(
        model_id="amazon.nova-micro-v1:0", max_input_context=300_000, max_output_tokens=10_000,
    ),

    # Anthropic Claude (cross-region inference)
    "anthropic.claude-sonnet-4-20250514-v1:0": ModelCapabilities(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),
    "anthropic.claude-haiku-4-5-20251001-v1:0": ModelCapabilities(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),
    "anthropic.claude-opus-4-5-20250929-v1:0": ModelCapabilities(
        model_id="anthropic.claude-opus-4-5-20250929-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),

    # US-region Claude
    "us.anthropic.claude-sonnet-4-20250514-v1:0": ModelCapabilities(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": ModelCapabilities(
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),
    "us.anthropic.claude-opus-4-5-20250929-v1:0": ModelCapabilities(
        model_id="us.anthropic.claude-opus-4-5-20250929-v1:0", max_input_context=200_000, max_output_tokens=8192,
    ),

    # Mistral
    "mistral.mixtral-8x7b-instruct-v0:1": ModelCapabilities(
        model_id="mistral.mixtral-8x7b-instruct-v0:1", max_input_context=32_000, max_output_tokens=4096,
    ),

    # Llama
    "meta.llama3-2-90b-instruct-v1:0": ModelCapabilities(
        model_id="meta.llama3-2-90b-instruct-v1:0", max_input_context=128_000, max_output_tokens=4096,
    ),
}


def detect_model_capabilities(model_id: str) -> ModelCapabilities:
    """Return known capabilities for *model_id*, or a safe conservative default."""
    if not model_id:
        logger.warning("no_model_id_configured_using_nova_defaults")
        return ModelCapabilities(model_id="unknown", max_input_context=300_000, max_output_tokens=10_000)

    # Exact match
    if model_id in _MODEL_CAPABILITIES:
        return _MODEL_CAPABILITIES[model_id]

    # Partial match (e.g. "anthropic.claude-sonnet-4" matches any Claude Sonnet 4 variant)
    for known_id, caps in _MODEL_CAPABILITIES.items():
        if model_id.startswith(known_id.split("-v")[0]) or known_id.startswith(model_id):
            logger.info("model_matched_by_prefix", model_id=model_id, matched=known_id)
            return caps

    # Unknown model — use safe default based on provider
    if "claude" in model_id:
        caps = ModelCapabilities(model_id=model_id, max_input_context=200_000, max_output_tokens=8192)
    elif "nova" in model_id:
        caps = ModelCapabilities(model_id=model_id, max_input_context=300_000, max_output_tokens=10_000)
    else:
        caps = ModelCapabilities(model_id=model_id, max_input_context=100_000, max_output_tokens=4096)

    logger.warning("unknown_model_using_safe_defaults", model_id=model_id,
                   max_input_context=caps.max_input_context, max_output_tokens=caps.max_output_tokens)
    return caps


# ---------------------------------------------------------------------------
@dataclass
class AnalysisProfile:
    """All configurable limits for a single analysis mode."""

    name: str

    # ---- List-slice limits (number of items to include) ----
    max_classes: int
    max_endpoints: int
    max_dependency_edges: int
    max_injection_deps: int
    max_circular_deps: int
    max_god_classes: int
    max_boundaries: int
    max_boundaries_for_adr: int
    max_boundaries_for_explain: int
    max_annotations_per_class: int
    max_deps_per_class: int

    # ---- Character-truncation limits for JSON blocks embedded in prompts ----
    classes_json_max_chars: int
    package_tree_json_max_chars: int
    endpoints_json_max_chars: int
    dependencies_json_max_chars: int
    circular_deps_json_max_chars: int
    injection_deps_json_max_chars: int
    god_classes_json_max_chars: int
    coupling_data_json_max_chars: int
    service_evidence_json_max_chars: int
    boundary_json_max_chars: int
    explain_boundary_json_max_chars: int
    codegen_boundary_json_max_chars: int
    compact_json_max_chars: int
    json_summary_max_chars: int

    # ---- Token / budget limits ----
    bedrock_max_tokens: int
    prompt_max_tokens: int

    # ---- AI context builder (ai/context/builder.py) ----
    ai_max_classes: int
    ai_max_endpoints: int
    ai_max_risk_findings: int
    ai_max_circular_deps: int
    ai_max_candidate_services: int
    ai_max_affected_components: int

    # ---- AI orchestrator fallback (ai/orchestrator.py) ----
    orchestrator_max_classes: int
    orchestrator_max_endpoints: int
    orchestrator_max_business_caps: int

    # ---- Memory context (ai/memory/context.py) ----
    memory_max_tokens: int
    memory_entry_max_chars: int
    memory_max_entries: int

    # ---- Analysis rules (analysis/rules/) ----
    rule_max_findings: int = 20
    rule_max_affected_components: int = 10
    rule_max_evidence_classes: int = 20

    # ---- Analysis metrics (analysis/metrics/) ----
    metrics_max_largest_classes: int = 10
    metrics_max_long_methods: int = 20

    # ---- Dependency graph (analysis/dependency/) ----
    graph_max_highly_coupled: int = 20

    # ---- Recommendation engine (analysis/recommendation/) ----
    rec_max_highly_coupled: int = 5
    rec_max_god_classes: int = 5

    # ---- Report builders (reports/) ----
    report_max_risk_findings: int = 20
    report_max_circular_deps: int = 10

    # ---- AI planner fallback (ai/planner/) ----
    planner_max_low_risk: int = 2
    planner_max_med_risk: int = 2
    planner_max_high_risk: int = 2

    # ---- AI reports fallback (ai/reports/) ----
    report_max_god_classes: int = 3
    ai_report_max_circular_deps: int = 3
    report_max_cycle_display: int = 4
    report_max_dev_god_classes: int = 5
    report_max_dev_circular_deps: int = 5

    # ---- Memory summary (ai/memory/) ----
    memory_summary_max_entries: int = 100

    # ---- Validation (ai/validation/) ----
    min_confidence: float = 0.3
    min_response_length: int = 50

    # ---- Miscellaneous ----
    service_deps_json_max_chars: int = 2000
    readiness_json_max_chars: int = 2000


# ---------------------------------------------------------------------------
# NORMAL  — exactly matches current hardcoded behaviour.
#           bedrock_max_tokens / prompt_max_tokens are filled from settings
#           so that existing env vars still work.
# ---------------------------------------------------------------------------
def _normal_profile(bedrock_max_tokens: int = 8000, prompt_max_tokens: int = 7000) -> AnalysisProfile:
    return AnalysisProfile(
        name="normal",

        max_classes=100,
        max_endpoints=30,
        max_dependency_edges=50,
        max_injection_deps=30,
        max_circular_deps=15,
        max_god_classes=10,
        max_boundaries=10,
        max_boundaries_for_adr=10,
        max_boundaries_for_explain=5,
        max_annotations_per_class=5,
        max_deps_per_class=10,

        classes_json_max_chars=6000,
        package_tree_json_max_chars=2000,
        endpoints_json_max_chars=2000,
        dependencies_json_max_chars=2000,
        circular_deps_json_max_chars=3000,
        injection_deps_json_max_chars=2000,
        god_classes_json_max_chars=2000,
        coupling_data_json_max_chars=5000,
        service_evidence_json_max_chars=6000,
        boundary_json_max_chars=4000,
        explain_boundary_json_max_chars=4000,
        codegen_boundary_json_max_chars=3000,
        compact_json_max_chars=4000,
        json_summary_max_chars=6000,

        bedrock_max_tokens=bedrock_max_tokens,
        prompt_max_tokens=prompt_max_tokens,

        ai_max_classes=20,
        ai_max_endpoints=15,
        ai_max_risk_findings=10,
        ai_max_circular_deps=10,
        ai_max_candidate_services=5,
        ai_max_affected_components=5,

        orchestrator_max_classes=50,
        orchestrator_max_endpoints=20,
        orchestrator_max_business_caps=10,

        memory_max_tokens=4000,
        memory_entry_max_chars=500,
        memory_max_entries=10,

        rule_max_findings=20,
        rule_max_affected_components=10,
        rule_max_evidence_classes=20,
        metrics_max_largest_classes=10,
        metrics_max_long_methods=20,
        graph_max_highly_coupled=20,
        rec_max_highly_coupled=5,
        rec_max_god_classes=5,
        report_max_risk_findings=20,
        report_max_circular_deps=10,
        planner_max_low_risk=2,
        planner_max_med_risk=2,
        planner_max_high_risk=2,
        report_max_god_classes=3,
        ai_report_max_circular_deps=3,
        report_max_cycle_display=4,
        report_max_dev_god_classes=5,
        report_max_dev_circular_deps=5,
        memory_summary_max_entries=100,

        service_deps_json_max_chars=2000,
        readiness_json_max_chars=2000,
        min_confidence=0.3,
        min_response_length=50,
    )


# ---------------------------------------------------------------------------
# FAST  — lightweight profile for quick demos and upload validation.
# ---------------------------------------------------------------------------
FAST_PROFILE = AnalysisProfile(
    name="fast",

    max_classes=50,
    max_endpoints=15,
    max_dependency_edges=25,
    max_injection_deps=15,
    max_circular_deps=8,
    max_god_classes=5,
    max_boundaries=5,
    max_boundaries_for_adr=5,
    max_boundaries_for_explain=3,
    max_annotations_per_class=3,
    max_deps_per_class=5,

    classes_json_max_chars=3000,
    package_tree_json_max_chars=1000,
    endpoints_json_max_chars=1000,
    dependencies_json_max_chars=1000,
    circular_deps_json_max_chars=1500,
    injection_deps_json_max_chars=1000,
    god_classes_json_max_chars=1000,
    coupling_data_json_max_chars=2500,
    service_evidence_json_max_chars=3000,
    boundary_json_max_chars=2000,
    explain_boundary_json_max_chars=2000,
    codegen_boundary_json_max_chars=2000,
    compact_json_max_chars=2000,
    json_summary_max_chars=3000,

    bedrock_max_tokens=4000,
    prompt_max_tokens=4000,

    ai_max_classes=10,
    ai_max_endpoints=8,
    ai_max_risk_findings=5,
    ai_max_circular_deps=5,
    ai_max_candidate_services=3,
    ai_max_affected_components=3,

    orchestrator_max_classes=25,
    orchestrator_max_endpoints=10,
    orchestrator_max_business_caps=5,

    memory_max_tokens=2000,
    memory_entry_max_chars=250,
    memory_max_entries=5,

    rule_max_findings=10,
    rule_max_affected_components=5,
    rule_max_evidence_classes=10,
    metrics_max_largest_classes=5,
    metrics_max_long_methods=10,
    graph_max_highly_coupled=10,
    rec_max_highly_coupled=3,
    rec_max_god_classes=3,
    report_max_risk_findings=10,
    report_max_circular_deps=5,
    planner_max_low_risk=1,
    planner_max_med_risk=1,
    planner_max_high_risk=1,
    report_max_god_classes=2,
    ai_report_max_circular_deps=2,
    report_max_cycle_display=3,
    report_max_dev_god_classes=3,
    report_max_dev_circular_deps=3,
    memory_summary_max_entries=20,

    service_deps_json_max_chars=1000,
    readiness_json_max_chars=1000,
    min_confidence=0.3,
    min_response_length=50,
)


# ---------------------------------------------------------------------------
# DEEP  — benchmarking / validation profile.
#         High effective limits (not truly unlimited) to avoid pathological
#         cases on giant enterprise codebases.
# ---------------------------------------------------------------------------
DEEP_PROFILE = AnalysisProfile(
    name="deep",

    max_classes=1000,
    max_endpoints=1000,
    max_dependency_edges=1000,
    max_injection_deps=1000,
    max_circular_deps=500,
    max_god_classes=500,
    max_boundaries=500,
    max_boundaries_for_adr=500,
    max_boundaries_for_explain=100,
    max_annotations_per_class=5,
    max_deps_per_class=10,

    classes_json_max_chars=50000,
    package_tree_json_max_chars=10000,
    endpoints_json_max_chars=10000,
    dependencies_json_max_chars=10000,
    circular_deps_json_max_chars=10000,
    injection_deps_json_max_chars=10000,
    god_classes_json_max_chars=10000,
    coupling_data_json_max_chars=15000,
    service_evidence_json_max_chars=15000,
    boundary_json_max_chars=10000,
    explain_boundary_json_max_chars=10000,
    codegen_boundary_json_max_chars=10000,
    compact_json_max_chars=15000,
    json_summary_max_chars=20000,

    bedrock_max_tokens=10000,
    prompt_max_tokens=30000,

    ai_max_classes=200,
    ai_max_endpoints=100,
    ai_max_risk_findings=50,
    ai_max_circular_deps=50,
    ai_max_candidate_services=50,
    ai_max_affected_components=10,

    orchestrator_max_classes=500,
    orchestrator_max_endpoints=200,
    orchestrator_max_business_caps=50,

    memory_max_tokens=8000,
    memory_entry_max_chars=2000,
    memory_max_entries=50,

    rule_max_findings=100,
    rule_max_affected_components=50,
    rule_max_evidence_classes=100,
    metrics_max_largest_classes=100,
    metrics_max_long_methods=100,
    graph_max_highly_coupled=100,
    rec_max_highly_coupled=20,
    rec_max_god_classes=20,
    report_max_risk_findings=100,
    report_max_circular_deps=50,
    planner_max_low_risk=10,
    planner_max_med_risk=10,
    planner_max_high_risk=10,
    report_max_god_classes=20,
    ai_report_max_circular_deps=20,
    report_max_cycle_display=8,
    report_max_dev_god_classes=20,
    report_max_dev_circular_deps=20,
    memory_summary_max_entries=200,

    service_deps_json_max_chars=10000,
    readiness_json_max_chars=10000,
    min_confidence=0.3,
    min_response_length=50,
)


# ---------------------------------------------------------------------------
# BENCHMARK  — built at runtime using detected model capabilities.
#              Uses the absolute maximum safe values for the active model.
# ---------------------------------------------------------------------------
def _build_benchmark_profile(model_id: str, model_caps: ModelCapabilities) -> AnalysisProfile:
    """Construct a profile that pushes the active model to its limits."""
    input_budget_tokens = min(model_caps.max_input_context - 2000, 50_000)  # leave room for output
    output_tokens = model_caps.max_output_tokens

    big_char_limit = input_budget_tokens * 4  # ~4 chars per token

    logger.info("building_benchmark_profile",
                model_id=model_id,
                max_input_context=model_caps.max_input_context,
                max_output_tokens=model_caps.max_output_tokens,
                prompt_token_budget=input_budget_tokens,
                output_token_limit=output_tokens)

    return AnalysisProfile(
        name="benchmark",

        max_classes=5000,
        max_endpoints=5000,
        max_dependency_edges=5000,
        max_injection_deps=5000,
        max_circular_deps=5000,
        max_god_classes=5000,
        max_boundaries=5000,
        max_boundaries_for_adr=5000,
        max_boundaries_for_explain=1000,
        max_annotations_per_class=10,
        max_deps_per_class=20,

        classes_json_max_chars=big_char_limit,
        package_tree_json_max_chars=big_char_limit // 5,
        endpoints_json_max_chars=big_char_limit // 4,
        dependencies_json_max_chars=big_char_limit // 4,
        circular_deps_json_max_chars=big_char_limit // 5,
        injection_deps_json_max_chars=big_char_limit // 5,
        god_classes_json_max_chars=big_char_limit // 5,
        coupling_data_json_max_chars=big_char_limit // 3,
        service_evidence_json_max_chars=big_char_limit // 3,
        boundary_json_max_chars=big_char_limit // 4,
        explain_boundary_json_max_chars=big_char_limit // 4,
        codegen_boundary_json_max_chars=big_char_limit // 5,
        compact_json_max_chars=big_char_limit // 3,
        json_summary_max_chars=big_char_limit // 2,

        bedrock_max_tokens=output_tokens,
        prompt_max_tokens=input_budget_tokens,

        ai_max_classes=5000,
        ai_max_endpoints=5000,
        ai_max_risk_findings=5000,
        ai_max_circular_deps=5000,
        ai_max_candidate_services=5000,
        ai_max_affected_components=100,

        orchestrator_max_classes=5000,
        orchestrator_max_endpoints=5000,
        orchestrator_max_business_caps=5000,

        memory_max_tokens=output_tokens,
        memory_entry_max_chars=5000,
        memory_max_entries=500,

        rule_max_findings=5000,
        rule_max_affected_components=5000,
        rule_max_evidence_classes=5000,
        metrics_max_largest_classes=5000,
        metrics_max_long_methods=5000,
        graph_max_highly_coupled=5000,
        rec_max_highly_coupled=5000,
        rec_max_god_classes=5000,
        report_max_risk_findings=5000,
        report_max_circular_deps=5000,
        planner_max_low_risk=5000,
        planner_max_med_risk=5000,
        planner_max_high_risk=5000,
        report_max_god_classes=5000,
        ai_report_max_circular_deps=5000,
        report_max_cycle_display=20,
        report_max_dev_god_classes=5000,
        report_max_dev_circular_deps=5000,
        memory_summary_max_entries=5000,

        service_deps_json_max_chars=big_char_limit // 4,
        readiness_json_max_chars=big_char_limit // 4,
        min_confidence=0.3,
        min_response_length=50,
    )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------
_active_profile: AnalysisProfile | None = None
_benchmark_model_id: str | None = None


def get_active_profile(analysis_mode: AnalysisMode | None = None,
                       bedrock_max_tokens: int = 8000,
                       prompt_max_tokens: int = 7000,
                       bedrock_model_id: str | None = None) -> AnalysisProfile:
    """Return the profile for the given (or cached) analysis mode.

    For BENCHMARK mode, *bedrock_model_id* is used to detect model limits.
    If not provided it is read from ``app.core.settings.get_settings()``.
    """
    global _active_profile, _benchmark_model_id

    if analysis_mode is None:
        if _active_profile is not None:
            return _active_profile
        analysis_mode = AnalysisMode.NORMAL

    if analysis_mode == AnalysisMode.FAST:
        profile = FAST_PROFILE
    elif analysis_mode == AnalysisMode.DEEP:
        profile = DEEP_PROFILE
    elif analysis_mode == AnalysisMode.BENCHMARK:
        if _active_profile is not None and _benchmark_model_id == bedrock_model_id:
            return _active_profile
        if bedrock_model_id is None:
            try:
                from app.core.settings import get_settings
                _s = get_settings()
                bedrock_model_id = _s.bedrock_model_primary
            except Exception:
                bedrock_model_id = "amazon.nova-pro-v1:0"
        caps = detect_model_capabilities(bedrock_model_id)
        profile = _build_benchmark_profile(bedrock_model_id, caps)
        _benchmark_model_id = bedrock_model_id
    else:
        profile = _normal_profile(bedrock_max_tokens, prompt_max_tokens)

    _active_profile = profile
    logger.info("analysis_profile_active", profile=profile.name,
                max_classes=profile.max_classes,
                bedrock_max_tokens=profile.bedrock_max_tokens)
    return profile


def get_profile_for_settings() -> AnalysisProfile:
    """One-liner convenience — reads settings and returns the active profile."""
    from app.core.settings import get_settings
    s = get_settings()
    return get_active_profile(
        analysis_mode=s.analysis_mode,
        bedrock_max_tokens=s.bedrock_max_tokens,
        prompt_max_tokens=s.ai_prompt_max_tokens,
        bedrock_model_id=s.bedrock_model_primary,
    )


def clear_profile_cache():
    """Clear the cached profile (useful for tests)."""
    global _active_profile, _benchmark_model_id
    _active_profile = None
    _benchmark_model_id = None
