"""Sprint 5.6 tests — BENCHMARK Analysis Mode."""

from app.core.analysis_profile import (
    AnalysisMode,
    FAST_PROFILE,
    DEEP_PROFILE,
    AnalysisProfile,
    detect_model_capabilities,
    get_active_profile,
    _build_benchmark_profile,
    _normal_profile,
    clear_profile_cache,
)


class TestBenchmarkProfile:
    def teardown_method(self):
        clear_profile_cache()

    def test_benchmark_auto_detects_nova(self):
        profile = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="amazon.nova-pro-v1:0",
        )
        assert profile.name == "benchmark"
        assert profile.bedrock_max_tokens == 10_000
        assert profile.max_classes > 1000
        assert profile.classes_json_max_chars > 10_000

    def test_benchmark_auto_detects_claude(self):
        profile = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        )
        assert profile.name == "benchmark"
        assert profile.bedrock_max_tokens == 8192

    def test_benchmark_scales_down_for_small_model(self):
        profile = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="mistral.mixtral-8x7b-instruct-v0:1",
        )
        assert profile.name == "benchmark"
        assert profile.bedrock_max_tokens == 4096
        assert profile.prompt_max_tokens <= 30_000

    def test_benchmark_caches_by_model(self):
        p1 = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="amazon.nova-lite-v1:0",
        )
        p2 = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="amazon.nova-lite-v1:0",
        )
        assert p1 is p2

    def test_benchmark_differs_for_different_models(self):
        clear_profile_cache()
        p_nova = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="amazon.nova-pro-v1:0",
        )
        clear_profile_cache()
        p_claude = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        )
        assert p_nova.bedrock_max_tokens != p_claude.bedrock_max_tokens

    def test_benchmark_has_all_fields(self):
        profile = get_active_profile(
            analysis_mode=AnalysisMode.BENCHMARK,
            bedrock_model_id="amazon.nova-pro-v1:0",
        )
        assert profile.max_classes > 0
        assert profile.max_endpoints > 0
        assert profile.max_dependency_edges > 0
        assert profile.max_injection_deps > 0
        assert profile.max_circular_deps > 0
        assert profile.max_god_classes > 0
        assert profile.max_boundaries > 0
        assert profile.max_boundaries_for_adr > 0
        assert profile.max_boundaries_for_explain > 0
        assert profile.max_annotations_per_class > 0
        assert profile.max_deps_per_class > 0
        assert profile.classes_json_max_chars > 0
        assert profile.package_tree_json_max_chars > 0
        assert profile.endpoints_json_max_chars > 0
        assert profile.dependencies_json_max_chars > 0
        assert profile.circular_deps_json_max_chars > 0
        assert profile.injection_deps_json_max_chars > 0
        assert profile.god_classes_json_max_chars > 0
        assert profile.coupling_data_json_max_chars > 0
        assert profile.service_evidence_json_max_chars > 0
        assert profile.boundary_json_max_chars > 0
        assert profile.explain_boundary_json_max_chars > 0
        assert profile.codegen_boundary_json_max_chars > 0
        assert profile.compact_json_max_chars > 0
        assert profile.json_summary_max_chars > 0
        assert profile.bedrock_max_tokens > 0
        assert profile.prompt_max_tokens > 0
        assert profile.service_deps_json_max_chars > 0
        assert profile.readiness_json_max_chars > 0
        assert profile.rule_max_findings > 0
        assert profile.rule_max_affected_components > 0
        assert profile.rule_max_evidence_classes > 0
        assert profile.metrics_max_largest_classes > 0
        assert profile.metrics_max_long_methods > 0
        assert profile.graph_max_highly_coupled > 0
        assert profile.rec_max_highly_coupled > 0
        assert profile.rec_max_god_classes > 0
        assert profile.report_max_risk_findings > 0
        assert profile.report_max_circular_deps > 0
        assert profile.planner_max_low_risk > 0
        assert profile.planner_max_med_risk > 0
        assert profile.planner_max_high_risk > 0
        assert profile.report_max_god_classes > 0
        assert profile.report_max_circular_deps > 0
        assert profile.report_max_cycle_display > 0
        assert profile.report_max_dev_god_classes > 0
        assert profile.report_max_dev_circular_deps > 0
        assert profile.ai_max_classes > 0
        assert profile.ai_max_endpoints > 0
        assert profile.ai_max_risk_findings > 0
        assert profile.ai_max_circular_deps > 0
        assert profile.ai_max_candidate_services > 0
        assert profile.ai_max_affected_components > 0
        assert profile.orchestrator_max_classes > 0
        assert profile.orchestrator_max_endpoints > 0
        assert profile.orchestrator_max_business_caps > 0
        assert profile.memory_max_tokens > 0
        assert profile.memory_entry_max_chars > 0
        assert profile.memory_max_entries > 0
        assert profile.memory_summary_max_entries > 0
        assert profile.min_confidence >= 0
        assert profile.min_response_length >= 0


class TestDetectModelCapabilities:
    def test_exact_match(self):
        caps = detect_model_capabilities("amazon.nova-pro-v1:0")
        assert caps.max_input_context == 300_000
        assert caps.max_output_tokens == 10_000

    def test_unknown_model_gets_default(self):
        caps = detect_model_capabilities("amazon.nova-mega-v1:0")
        assert caps.max_input_context == 300_000
        assert caps.max_output_tokens == 10_000

    def test_empty_model_id(self):
        caps = detect_model_capabilities("")
        assert caps.max_input_context == 300_000
        assert caps.max_output_tokens == 10_000

    def test_unknown_amazon_model_falls_to_default(self):
        caps = detect_model_capabilities("amazon.unknown-v1:0")
        assert caps.max_input_context == 100_000
        assert caps.max_output_tokens == 4096

    def test_claude_unknown(self):
        caps = detect_model_capabilities("anthropic.claude-opus-5-v1:0")
        assert caps.max_input_context == 200_000
        assert caps.max_output_tokens == 8192


class TestProfilePurity:
    """NORMAL mode must remain byte-identical to original hardcoded values."""

    def test_normal_max_classes(self):
        p = _normal_profile()
        assert p.max_classes == 100

    def test_normal_class_limit(self):
        p = FAST_PROFILE
        assert p.max_classes == 50

    def test_normal_bedrock_tokens_default(self):
        p = _normal_profile()
        assert p.bedrock_max_tokens == 8000
        assert p.prompt_max_tokens == 7000

    def test_normal_bedrock_tokens_custom(self):
        p = _normal_profile(bedrock_max_tokens=9999, prompt_max_tokens=8888)
        assert p.bedrock_max_tokens == 9999
        assert p.prompt_max_tokens == 8888

    def test_deep_has_high_limits(self):
        assert DEEP_PROFILE.max_classes >= 1000
        assert DEEP_PROFILE.bedrock_max_tokens >= 10000

    def test_fast_is_lighter_than_normal(self):
        normal = _normal_profile()
        assert FAST_PROFILE.max_classes < normal.max_classes
        assert FAST_PROFILE.bedrock_max_tokens < normal.bedrock_max_tokens
        assert FAST_PROFILE.prompt_max_tokens < normal.prompt_max_tokens


class TestModelCapabilities:
    def test_all_registered_models_have_caps(self):
        from app.core.analysis_profile import _MODEL_CAPABILITIES
        for model_id, caps in _MODEL_CAPABILITIES.items():
            assert caps.model_id == model_id
            assert caps.max_input_context > 0
            assert caps.max_output_tokens > 0

    def test_nova_family_values(self):
        caps = detect_model_capabilities("amazon.nova-micro-v1:0")
        assert caps.max_output_tokens == 10_000

    def test_claude_family_values(self):
        caps = detect_model_capabilities("us.anthropic.claude-sonnet-4-20250514-v1:0")
        assert caps.max_output_tokens == 8192
