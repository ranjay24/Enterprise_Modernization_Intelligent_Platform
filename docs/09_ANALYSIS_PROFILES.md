# Analysis Profiles — EMIP

## What Are Profiles?

Analysis profiles centralize all configurable limits that control analysis behavior. They replace hardcoded constants with a single configuration object that flows through every stage of the pipeline. Every limit that governs how much data is sent to Bedrock lives in a profile.

**File:** `backend/app/core/analysis_profile.py`

**Core Class:** `AnalysisProfile` (line 115) — dataclass with ~60 configurable fields across these categories:

| Category | Fields | Affected Module |
|---|---|---|
| List-slice limits | `max_classes`, `max_endpoints`, `max_dependency_edges`, ... | Pipeline stage inputs |
| Character truncation | `classes_json_max_chars`, `compact_json_max_chars`, ... | Prompt builder |
| Token budgets | `bedrock_max_tokens`, `prompt_max_tokens` | AI invocation |
| AI context builder | `ai_max_classes`, `ai_max_endpoints`, `ai_max_risk_findings`, ... | `ai/context/builder.py` |
| AI orchestrator | `orchestrator_max_classes`, `orchestrator_max_business_caps`, ... | `ai/orchestrator.py` |
| Memory | `memory_max_tokens`, `memory_entry_max_chars`, `memory_max_entries` | `ai/memory/` |
| Analysis rules | `rule_max_findings`, `rule_max_affected_components` | `analysis/rules/` |
| Metrics | `metrics_max_largest_classes`, `metrics_max_long_methods` | `analysis/metrics/` |
| Dependency graph | `graph_max_highly_coupled` | `analysis/dependency/` |
| Reports | `report_max_risk_findings`, `report_max_god_classes`, ... | `reports/` |
| Validation | `min_confidence`, `min_response_length` | `ai/validation/` |

## The 4 Profiles

### FAST

Lightweight profile for rapid iteration and development feedback. Skips deep AI reasoning.

| Property | Value |
|---|---|
| `max_classes` | 50 |
| `max_endpoints` | 15 |
| `max_dependency_edges` | 25 |
| `bedrock_max_tokens` | 4,000 |
| `prompt_max_tokens` | 4,000 |
| `ai_max_classes` | 10 |
| `memory_max_tokens` | 2,000 |
| `min_confidence` | 0.3 |

**Use case:** Rapid feedback during development, quick demos, upload validation.

**Impact:** Reduced token budget means shorter prompts, smaller AI invocations, fewer stages receive full AI reasoning. Some stages may fall back to deterministic logic.

### NORMAL

Balanced profile that matches pre-deep-mode behavior. Default profile used when no explicit selection is made.

| Property | Value |
|---|---|
| `max_classes` | 100 |
| `max_endpoints` | 30 |
| `max_dependency_edges` | 50 |
| `bedrock_max_tokens` | 8,000 (configurable via env) |
| `prompt_max_tokens` | 7,000 (configurable via env) |
| `ai_max_classes` | 20 |
| `memory_max_tokens` | 4,000 |
| `min_confidence` | 0.3 |

**Use case:** Standard analysis runs.

**Impact:** All 12 pipeline stages execute. Deterministic fallback available for all AI stages. Token budgets match original hardcoded values.

### DEEP

Comprehensive profile for production migration planning. High effective limits for thorough analysis.

| Property | Value |
|---|---|
| `max_classes` | 1,000 |
| `max_endpoints` | 1,000 |
| `max_dependency_edges` | 1,000 |
| `bedrock_max_tokens` | 10,000 |
| `prompt_max_tokens` | 30,000 |
| `ai_max_classes` | 200 |
| `memory_max_tokens` | 8,000 |
| `min_confidence` | 0.3 |

**Use case:** Production migration planning, large enterprise codebases.

**Impact:** High token budgets allow full codebase representation in prompts. All AI stages execute with expanded context. Longer analysis time and higher Bedrock costs.

### BENCHMARK

Evaluation mode for testing AI output quality. Dynamically computed at runtime based on the active model's capabilities.

| Property | Value |
|---|---|
| `max_classes` | 5,000 |
| `max_endpoints` | 5,000 |
| `bedrock_max_tokens` | Model's `max_output_tokens` (up to 10,000) |
| `prompt_max_tokens` | Model's `max_input_context - 2000` (capped at 50,000) |
| `min_confidence` | 0.3 |

**Use case:** Validating AI output quality, regression testing, model comparison.

**Impact:** Pushes the active model to its limits. All prompts and responses are logged. Not suitable for production use — designed for evaluation and benchmarking only.

## Model Capability Detection

The `detect_model_capabilities()` function in `analysis_profile.py:84` maps model IDs to their known limits:

```python
_MODEL_CAPABILITIES = {
    "amazon.nova-pro-v1:0":   ModelCapabilities(max_input_context=300_000, max_output_tokens=10_000),
    "amazon.nova-lite-v1:0":  ModelCapabilities(max_input_context=300_000, max_output_tokens=10_000),
    "amazon.nova-micro-v1:0": ModelCapabilities(max_input_context=300_000, max_output_tokens=10_000),
    "anthropic.claude-sonnet-4-20250514-v1:0":  ModelCapabilities(max_input_context=200_000, max_output_tokens=8192),
    "anthropic.claude-haiku-4-5-20251001-v1:0": ModelCapabilities(max_input_context=200_000, max_output_tokens=8192),
    "anthropic.claude-opus-4-5-20250929-v1:0":  ModelCapabilities(max_input_context=200_000, max_output_tokens=8192),
    "mistral.mixtral-8x7b-instruct-v0:1":       ModelCapabilities(max_input_context=32_000,  max_output_tokens=4096),
    "meta.llama3-2-90b-instruct-v1:0":          ModelCapabilities(max_input_context=128_000, max_output_tokens=4096),
}
```

For unknown models, safe defaults are inferred from provider prefix:
- `claude` → 200K input / 8192 output
- `nova` → 300K input / 10K output
- Others → 100K input / 4096 output

## Token Budgets and Prompt Compression

Profiles control prompt construction through two mechanisms:

### 1. List-Slice Limits

Before building prompts, large lists are truncated:

```python
# Example: ai/context/builder.py
classes = all_classes[:profile.ai_max_classes]     # DEEP: 200, FAST: 10
endpoints = all_endpoints[:profile.ai_max_endpoints] # DEEP: 100, FAST: 8
```

### 2. JSON Character Truncation

JSON blocks within prompts are truncated proportionally based on profile limits. The `truncate_json_block()` utility in `backend/app/utils/validators.py` trims at newline boundaries:

```python
compact_json = truncate_json_block(json.dumps(data), profile.compact_json_max_chars)
```

This ensures prompts never exceed the model's context window.

### Proportional Compression

When `prompt_max_tokens` is insufficient for all sections, available tokens are distributed proportionally by section size:

```python
# Proportional allocation across sections
section_budgets = allocate_proportional(
    total_budget=profile.prompt_max_tokens,
    section_sizes=[len(section_a), len(section_b), ...]
)
```

## Impact on Pipeline Stages

All AI-dependent stages check the active profile. Key consumers:

| Stage / Module | Profile Impact | File |
|---|---|---|
| AI boundary detection | `ai_max_classes`, `ai_max_endpoints`, `ai_max_candidate_services` | `backend/app/ai/orchestrator.py` |
| ADR generation | `max_boundaries_for_adr` | `backend/app/ai/engine.py` |
| Migration planning | `planner_max_low/med/high_risk` | `backend/app/ai/planner/engine.py` |
| Cost estimation | `max_boundaries`, `boundary_json_max_chars` | `backend/app/ai/reports/` |
| Explainability | `max_boundaries_for_explain` | `backend/app/ai/memory/context.py` |
| Static analysis rules | `rule_max_findings`, `rule_max_evidence_classes` | `backend/app/analysis/rules/*.py` |
| Dependency graph | `graph_max_highly_coupled` | `backend/app/analysis/dependency/graph.py` |
| Recommendations | `rec_max_highly_coupled`, `rec_max_god_classes` | `backend/app/analysis/recommendation/engine.py` |
| Report builders | `report_max_risk_findings`, `report_max_god_classes` | `backend/app/reports/builders.py` |

## Expected Costs (AWS Bedrock)

Estimates based on Amazon Nova Pro pricing for a 100MB Java project:

| Profile | Input Tokens (est.) | Output Tokens (est.) | Est. Cost per Run |
|---|---|---|---|
| FAST | ~8,000 | ~2,000 | ~$0.05 |
| NORMAL | ~25,000 | ~8,000 | ~$0.20 |
| DEEP | ~80,000 | ~10,000 | ~$0.80 |
| BENCHMARK | ~50,000 | ~10,000 | ~$0.60 |

> Costs vary significantly by project size and number of AI stages invoked. Only `ai_boundaries` and `ai_adrs` call Bedrock; the per-run estimates above assume those two stages with Nova Pro.

## How Profiles Are Selected

The `get_active_profile()` function in `analysis_profile.py:554` resolves the profile:

```python
def get_active_profile(analysis_mode=None,
                       bedrock_max_tokens=8000,
                       prompt_max_tokens=7000,
                       bedrock_model_id=None) -> AnalysisProfile:
    if analysis_mode == AnalysisMode.FAST:
        return FAST_PROFILE
    elif analysis_mode == AnalysisMode.DEEP:
        return DEEP_PROFILE
    elif analysis_mode == AnalysisMode.BENCHMARK:
        caps = detect_model_capabilities(bedrock_model_id)
        return _build_benchmark_profile(bedrock_model_id, caps)
    else:
        return _normal_profile(bedrock_max_tokens, prompt_max_tokens)
```

**Convenience function:** `get_profile_for_settings()` (line 597) reads settings and returns the active profile in one call.

**Caching:** The active profile is cached in `_active_profile` to avoid repeated resolution. BENCHMARK profiles are cached per model ID.

**Profile enum:** `AnalysisMode` in `analysis_profile.py:20` — `FAST`, `NORMAL`, `DEEP`, `BENCHMARK`.

## Migration from Hardcoded Limits

Before Sprint 5.6, all limits were hardcoded as module-level constants across 15+ files. The profile system:

1. Centralized all limits into one file (`analysis_profile.py`)
2. Flagged every usage with a `get_profile_for_settings()` call
3. Added proportional prompt compression
4. Enabled dynamic model-aware limits (BENCHMARK)
5. Added prompt statistics logging for observability

## Fallback Chain

When an AI stage runs, the fallback path (`BaseAIStage` in `backend/app/pipeline/stages/base.py`) is:

```
1. AI invocation (Bedrock via profile limits) → success → result used directly
2. AI fails (exception) OR returns an empty result → single deterministic fallback, flagged is_degraded=true
3. Pipeline continues → manifest reports degraded stages + deterministic fallback count
```

This is a 2-step chain — there is no "retry with a lower profile" step. `BaseAIStage` is extended by the six `ai_*` pipeline stages (`ai_boundaries`, `ai_readiness`, `ai_adrs`, `ai_migration`, `ai_cost`, `ai_explainability`); the other six stages are non-AI and do not extend it.
