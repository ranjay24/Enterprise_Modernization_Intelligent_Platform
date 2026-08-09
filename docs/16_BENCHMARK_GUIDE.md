# EMIP Benchmark Guide

## Purpose

The EMIP benchmark system measures analysis quality and performance across different monolith types, analysis modes, and AI models. Use benchmarking to:

- Validate service boundary quality against known reference architectures
- Measure pipeline execution performance (sequential vs parallel)
- Detect regressions after code changes
- Compare Nova model performance (Pro vs Lite vs Micro). Capability metadata exists for Claude/Mistral/Llama, but only Nova has a runtime adapter — those models cannot be invoked
- Generate prompt statistics for cost optimization
- Calibrate confidence scores against ground truth

## Reference Monoliths

Three test Java/Spring Boot projects are used for benchmarking:

### 1. Insurance Monolith

- **Size**: 200+ classes
- **Architecture**: Large, organically grown Spring Boot application
- **Domains**: Claims processing, policy management, payments, customer management, underwriting, reporting
- **Characteristics**:
  - Mixed concerns within packages
  - Circular dependencies between domains
  - Several god classes (>2000 lines)
  - Framework heavy (Spring Data, Spring Security, Spring MVC)
  - Some test coverage, inconsistent patterns
- **Expected difficulty**: Hard — domain boundaries are blurred

### 2. Modern Monolith

- **Size**: ~80 classes
- **Architecture**: Well-structured Spring Boot with clean package boundaries
- **Domains**: Orders, inventory, shipping, billing, notifications
- **Characteristics**:
  - Clear package-by-feature organization
  - Minimal circular dependencies
  - Consistent coding patterns
  - Good separation of concerns
  - Well-named packages and classes
- **Expected difficulty**: Easy — domains map closely to package structure

### 3. Hybrid Monolith

- **Size**: ~150 classes
- **Architecture**: Mixed architecture — some modular services, some shared code
- **Domains**: User management, content management, analytics, search, messaging
- **Characteristics**:
  - Several clearly separable modules
  - One large shared library with mixed concerns
  - Some API-based internal communication
  - Partial migration already in progress
- **Expected difficulty**: Medium — mixed signals with clear extraction candidates

## What to Measure

### Pipeline Execution Time

| Metric | Description |
|--------|-------------|
| Total pipeline duration | Wall clock time from start to completion |
| Per-stage duration | Time spent in each stage (Including AI invocation) |
| Parallel speedup | `T_seq / T_par` ratio |
| Idle time | Time spent waiting for dependencies in parallel mode |

### AI Stage Latency

| Stage | Typical Duration (NORMAL) | Typical Duration (DEEP) |
|-------|--------------------------|------------------------|
| Static Analysis | 5-30s | 5-120s |
| AI Boundaries | 15-45s | 30-180s |
| AI ADRs | 10-30s | 20-120s |
| AI Cost | 8-20s | 15-60s |
| AI Migration | 10-25s | 20-90s |
| AI Readiness | 8-20s | 15-60s |
| AI Explainability | 10-30s | 20-100s |

### Artifact Quality Scoring

Scores range from 0.0 to 1.0:

- **Boundary relevance**: Do the detected service boundaries match the reference decomposition?
- **ADR specificity**: Are ADRs actionable with specific implementation details?
- **Cost estimation accuracy**: How close are estimates to actual AWS pricing?
- **Confidence calibration**: Is the model's confidence score correlated with actual accuracy?

### Service Boundary Relevance

Compare detected boundaries against the known reference decomposition using:

- **Precision**: `TP / (TP + FP)` — what fraction of detected boundaries are correct
- **Recall**: `TP / (TP + FN)` — what fraction of true boundaries were detected
- **F1 Score**: `2 * P * R / (P + R)` — harmonic mean of precision and recall

### ADR Specificity

- **Actionable items**: Count of specific implementation steps per ADR
- **Technology references**: Use of specific AWS services, patterns, and configurations
- **Risk assessment**: Whether risks are identified with concrete mitigations

### Cost Estimation Accuracy

- **Mean Absolute Percentage Error (MAPE)**: Average % deviation from actual pricing
- **Under/over estimation bias**: Systematic tendency to over- or under-estimate

## Using BENCHMARK Profile

The BENCHMARK profile (`AnalysisMode.BENCHMARK`) pushes the active AI model to its limits:

### Activation

```python
from app.core.analysis_profile import AnalysisMode, get_active_profile, clear_profile_cache

clear_profile_cache()
profile = get_active_profile(
    analysis_mode=AnalysisMode.BENCHMARK,
    bedrock_model_id="amazon.nova-pro-v1:0",
)
```

Or via environment variable:
```
ANALYSIS_MODE=benchmark
BEDROCK_MODEL_PRIMARY=amazon.nova-pro-v1:0
```

### Behavior

- **Maximum limits**: All slicing/truncation limits are set to the maximum safe values for the detected model.
- **Context-aware**: Prompt token budget is computed based on model's `max_input_context` minus 2000 tokens for output.
- **Output maximized**: `bedrock_max_tokens` is set to the model's `max_output_tokens`.
- **Auto-detection**: Model capabilities are matched by ID prefix — adding a new model only requires entries in `_MODEL_CAPABILITIES`.

### What Is Captured

When running in BENCHMARK mode, the following data is logged and stored as artifacts:

1. **Prompt statistics** (via `app.core.prompt_stats`):
   - Token count per prompt
   - Character count per JSON block before/after truncation
   - Number of truncation events per stage

2. **Stage timing**:
   - Per-stage wall clock time in milliseconds
   - AI invocation duration
   - Sequential vs parallel comparison

3. **Model responses**:
   - Raw response text
   - Parsed response structure
   - Confidence scores per recommendation

4. **Cost tracking**:
   - Token counts (input + output)
   - Estimated cost per invocation
   - Cumulative cost per job

### Running Benchmark Tests

```powershell
cd backend
python -m pytest tests/test_sprint5_6_benchmark.py -v --tb=short
```

This validates:
- BENCHMARK profile construction for each supported model
- Profile caching behavior
- Model auto-detection
- Fallback for unknown models

## Expected Findings

### Insurance Monolith

| Metric | Expected Range | Notes |
|--------|---------------|-------|
| F1 Score (boundaries) | 0.4 - 0.6 | Blurred domains reduce precision |
| ADR Actionability | 3-5 items/ADR | Some ADRs will be generic |
| Cost MAPE | 25-40% | Generic pricing limits accuracy |
| Confidence scores | 0.3 - 0.6 | Model appropriately uncertain |

### Modern Monolith

| Metric | Expected Range | Notes |
|--------|---------------|-------|
| F1 Score (boundaries) | 0.7 - 0.9 | Clean structure maps well |
| ADR Actionability | 5-8 items/ADR | Specific, actionable recommendations |
| Cost MAPE | 15-25% | Simpler architecture, better estimates |
| Confidence scores | 0.6 - 0.9 | Model correctly confident |

### Hybrid Monolith

| Metric | Expected Range | Notes |
|--------|---------------|-------|
| F1 Score (boundaries) | 0.5 - 0.7 | Mixed results across modules |
| ADR Actionability | 4-6 items/ADR | Some substance, some gaps |
| Cost MAPE | 20-35% | Partial migration complicates estimates |
| Confidence scores | 0.4 - 0.7 | Mixed confidence reflects mixed signals |

## Expected Scores

### Code Quality Scores

| Aspect | Insurance | Modern | Hybrid |
|--------|-----------|--------|--------|
| Maintainability | 0.3 - 0.5 | 0.7 - 0.9 | 0.4 - 0.6 |
| Test Coverage | 0.2 - 0.4 | 0.5 - 0.8 | 0.3 - 0.5 |
| Dependency Management | 0.3 - 0.5 | 0.7 - 0.9 | 0.4 - 0.7 |
| Documentation | 0.2 - 0.4 | 0.4 - 0.7 | 0.3 - 0.5 |
| **Overall** | **0.3 - 0.5** | **0.6 - 0.8** | **0.4 - 0.6** |

### Readiness Ranges

| Level | Insurance | Modern | Hybrid |
|-------|-----------|--------|--------|
| Migration Readiness | 0.2 - 0.4 | 0.5 - 0.7 | 0.3 - 0.5 |
| Service Extraction Readiness | 0.2 - 0.4 | 0.6 - 0.8 | 0.3 - 0.6 |
| Cloud Readiness | 0.3 - 0.5 | 0.5 - 0.7 | 0.3 - 0.5 |

### Confidence Score Ranges

| Score Range | Interpretation | Action Required |
|-------------|---------------|-----------------|
| 0.0 - 0.3 | Low confidence — results may be unreliable | Full human review required |
| 0.3 - 0.6 | Medium confidence — useful as input | Review and refine before acting |
| 0.6 - 0.8 | High confidence — results likely correct | Minimal review needed |
| 0.8 - 1.0 | Very high confidence — results strongly aligned | Can be actioned directly |

## Regression Testing

After any code changes, use BENCHMARK mode to detect regressions:

1. **Run the benchmark suite** against all three reference monoliths:
   ```powershell
   python -m pytest tests/test_sprint5_6_benchmark.py -v
   ```

2. **Compare results** against the baseline (stored in CI or documentation):
   - Check that F1 scores have not decreased
   - Verify ADR actionability has not regressed
   - Confirm cost MAPE has not increased significantly

3. **Check pipeline timing** for regressions:
   - Sequential execution time should not increase by >20%
   - Parallel speedup should not decrease by >20%

4. **Verify artifact completeness**:
   - All 12 pipeline stages produce valid artifacts
   - No stages fall back to degraded mode unexpectedly
   - Artifact schema versions are consistent

## Analyzing Results

### Prompt Statistics

Prompt statistics artifacts contain:

```json
{
  "stage": "ai_boundaries",
  "model_id": "amazon.nova-pro-v1:0",
  "total_prompt_tokens": 45231,
  "total_response_tokens": 2841,
  "json_blocks": {
    "classes_json": {"chars": 28000, "max_chars": 50000, "truncated": false},
    "package_tree_json": {"chars": 4200, "max_chars": 10000, "truncated": false}
  },
  "truncation_events": 0,
  "duration_ms": 28500
}
```

Use this to:
- Identify which stages are hitting truncation limits
- Calculate cost per stage and per job
- Optimize prompt template sizes

### Token Usage

Track token consumption per model:

| Model | Cost per 1K Input Tokens | Cost per 1K Output Tokens |
|-------|--------------------------|---------------------------|
| Nova Pro | $0.008 | $0.024 |
| Nova Lite | $0.002 | $0.006 |
| Claude Sonnet 4 | $0.015 | $0.075 |
| Claude Haiku 4.5 | $0.008 | $0.040 |

Reference prices for capability planning; the pipeline only invokes Nova models at runtime.

### Stage Timing

Export stage timing for analysis:

```json
{
  "total_duration_ms": 284500,
  "stages": {
    "extraction": {"duration_ms": 1200, "status": "completed"},
    "static_analysis": {"duration_ms": 18500, "status": "completed"},
    "enterprise_analysis": {"duration_ms": 3200, "status": "completed"},
    "ai_boundaries": {"duration_ms": 45200, "status": "completed"},
    "ai_adrs": {"duration_ms": 28500, "status": "completed"},
    "ai_cost": {"duration_ms": 18200, "status": "completed"},
    "ai_migration": {"duration_ms": 22300, "status": "completed"},
    "ai_readiness": {"duration_ms": 15800, "status": "completed"},
    "ai_explainability": {"duration_ms": 19500, "status": "completed"},
    "results_assembly": {"duration_ms": 800, "status": "completed"},
    "report_generation": {"duration_ms": 2500, "status": "completed"},
    "manifest": {"duration_ms": 400, "status": "completed"}
  }
}
```

## Reporting

Benchmark reports are generated by `backend/app/reports/builders.py`'s `build_all_reports()` function.

### Report Format

Reports are stored as artifacts containing:

1. **Summary statistics**: Total time, artifacts produced, stages completed/failed
2. **Per-stage breakdown**: Timing, token usage, model used, degraded flag
3. **Quality metrics**: Boundary F1 scores, ADR actionability scores, confidence calibration
4. **Cost analysis**: Real vs estimated costs, per-model breakdown
5. **Regression indicators**: Delta from baseline for each metric

### Generating a Report

```python
from app.reports.builders import build_all_reports
from app.artifacts.repository import ArtifactRepository

repo = ArtifactRepository()
manifest = repo.load_manifest(job_id)
reports = build_all_reports(manifest, job_id, repo)
```

### Interpreting Results

- **Green**: All metrics within expected range, no degradation from baseline.
- **Yellow**: Some metrics outside expected range but within 2x of baseline. Investigate.
- **Red**: Significant regression or unexpected behavior. Block deployment.

### Automating Benchmark Runs

```powershell
# Full benchmark pipeline
python -m pytest tests/test_sprint5_6_benchmark.py -v --tb=short
python -m pytest tests/test_sprint5_integration.py -v --tb=short
python -m pytest tests/test_sprint5_parallel.py -v --tb=short
```
