# EMIP Testing Guide

## Test Framework

EMIP uses **pytest** with standard conventions. All tests live under `backend/tests/` and follow the structure:

```
backend/tests/
├── __init__.py
├── controller/
├── integration/
├── repository/
├── service/
├── unit/
├── test_sprint3_ai_layer.py
├── test_sprint4_1.py
├── test_sprint4_artifacts.py
├── test_sprint4_capabilities.py
├── test_sprint4_pipeline.py
├── test_sprint4_workers.py
├── test_sprint5_6_benchmark.py
├── test_sprint5_ai_analysis*.py
├── test_sprint5_dag.py
├── test_sprint5_integration.py
├── test_sprint5_parallel.py
├── test_sprint5_performance.py
└── test_truncation_integration.py
```

- One test file per module or feature area.
- Classes group related tests with descriptive names.
- Plain `assert` statements — no `unittest.TestCase`.
- Fixtures in `conftest.py` at the appropriate directory level.

## Running Tests

### Complete Regression Suite

```powershell
cd backend
python -m pytest tests/ -v
```

### Run with Warnings and Coverage

```powershell
python -m pytest tests/ -v --tb=short -W ignore::DeprecationWarning
```

### Run Specific Test Files

```powershell
python -m pytest tests/test_sprint5_6_benchmark.py -v
python -m pytest tests/test_sprint3_ai_layer.py -v
python -m pytest tests/test_truncation_integration.py -v
```

### Run Specific Test Classes or Methods

```powershell
python -m pytest tests/test_sprint5_6_benchmark.py::TestBenchmarkProfile -v
python -m pytest tests/test_sprint4_pipeline.py::TestPipelineEngine -v
```

### Run with Parallel Execution (if pytest-xdist is installed)

```powershell
python -m pytest tests/ -n 4 -v
```

## Test Suites and Their Files

| Suite | File(s) | Approx. Count | What It Tests |
|-------|---------|---------------|---------------|
| Sprint 3 AI Layer | `test_sprint3_ai_layer.py` | ~30 | AI engine, service, provider integration, prompt rendering |
| Sprint 4 DAG | `test_sprint4_*.py` + `test_sprint5_dag.py` | ~15 | DAG scheduling, dependency resolution, parallel execution |
| Sprint 4 Deployment | `test_sprint4_workers.py`, `test_sprint4_pipeline.py` | ~15 | Worker lambda logic, checkpoint/resume, pipeline state |
| Sprint 4 Comprehensive | `test_sprint4_*` combined | ~90 | Artifacts, capabilities, pipeline, workers — dual mode testing |
| Sprint 5 Integration | `test_sprint5_integration.py` | ~20 | End-to-end pipeline flow, stage chaining, artifact propagation |
| Sprint 5 Benchmark | `test_sprint5_6_benchmark.py` | ~40 | BENCHMARK profile, model auto-detection, prompt statistics |
| Sprint 5 AI Analysis | `test_sprint5_ai_analysis*.py` | ~25 | AI analysis stages, boundary detection, cost estimation |
| Sprint 5.6 Regression | All sprint 5/6 tests | 141 | Full regression against sprint 5 and 6 functionality |
| Truncation | `test_truncation_integration.py` | ~10 | Prompt truncation logic, long-context handling |
| **Total** | All files | **249+** | — |

## Testing Coverage Areas

### API Endpoints
- Request validation, response formats, error codes, authentication middleware.
- Test files: `tests/controller/`, `tests/service/`.

### Pipeline Stages
- Each stage produces the correct `Artifact` type.
- Stages execute in order, prerequisites are validated.
- Test files: `test_sprint4_pipeline.py`, `test_sprint5_integration.py`.

### DAG Scheduling
- Dependency graph resolves correctly.
- Parallel execution produces same results as sequential.
- Test files: `test_sprint5_dag.py`, `test_sprint5_parallel.py`.

### AI Prompts
- Prompt templates render correctly with context variables.
- Template versioning works as expected.
- Test files: `test_sprint3_ai_layer.py`.

### Truncation
- Content is truncated to fit profile limits.
- Truncation preserves JSON structure where possible.
- Test files: `test_truncation_integration.py`.

### Failure Modes
- AI stage fallback triggers on Bedrock errors.
- Pipeline continues with degraded artifacts.
- Checkpoint and resume work after interruptions.
- Test files: `test_sprint4_pipeline.py`.

### Parallel Execution
- DAG-based parallel execution is deterministic.
- Artifact ordering is preserved.
- Test files: `test_sprint5_parallel.py`.

### Analysis Modes
- FAST, NORMAL, DEEP, and BENCHMARK profiles work correctly.
- Profile switching changes behavior appropriately.
- Test files: `test_sprint5_6_benchmark.py`.

### Static Analyzer Edge Cases
- Empty projects, single-file projects, malformed Java.
- Edge cases in regex-based parsing.
- Test files: `tests/service/`.

## Benchmark Mode Testing

The `test_sprint5_6_benchmark.py` suite validates the benchmark infrastructure:

- **Profile construction** — BENCHMARK profile scales limits based on model capabilities.
- **Model capability auto-detection** — Nova, Claude Sonnet, Mistral, and Llama capability metadata is detected correctly (profile scaling; only Nova is runtime-wired).
- **Cache behavior** — Profile is cached per model ID; different models get different profiles.
- **Field completeness** — Every profile field is populated with sensible values.
- **Fallback behavior** — Unknown models get conservative defaults.

Run benchmark tests specifically:

```powershell
python -m pytest tests/test_sprint5_6_benchmark.py -v --tb=short
```

### Prompt Statistics

When running in BENCHMARK mode, prompt statistics are captured as artifacts:
- Token counts per prompt
- Character counts per JSON block
- Truncation events
- Model response timing

These are stored as artifacts retrievable via `ArtifactRepository` for analysis and reporting.

## How to Validate Changes

1. **Run the full test suite** — ensure no regressions:
   ```powershell
   cd backend
   python -m pytest tests/ -v --tb=short
   ```

2. **Check test count** — verify expected number of tests execute:
   ```
   = 249 passed in 12.34s =
   ```

3. **Run benchmark tests** if modifying profiles or AI stages:
   ```powershell
   python -m pytest tests/test_sprint5_6_benchmark.py -v
   ```

4. **Verify pipeline end-to-end** — the integration tests validate the full pipeline flow:
   ```powershell
   python -m pytest tests/test_sprint5_integration.py -v
   ```

5. **Check for warnings** — address any DeprecationWarnings or PendingDeprecationWarnings.

## Testing with AWS

### Mock Strategy

- All tests use **mocked AWS clients** — no real AWS calls.
- S3 operations are mocked via `unittest.mock.patch` on `app.aws.s3.S3Repository`.
- Bedrock calls are mocked at the `AIProvider` level.
- DynamoDB operations are mocked at the repository level.
- The `clear_profile_cache()` function resets the analysis profile singleton between tests.

```python
from unittest.mock import patch

@patch("app.aws.s3.S3Repository.put_object")
def test_artifact_saved_to_s3(mock_put):
    repo = ArtifactRepository()
    repo.save(job_id, stage_name, artifact)
    assert mock_put.called
```

### LocalStack vs Real AWS

- LocalStack is **not currently used** — all tests are fully mocked.
- Integration tests that validate AWS behavior use mock assertions rather than actual calls.
- This ensures tests run offline, fast, and without AWS costs.
- If adding tests that interact with real AWS, guard them with a `@pytest.mark.skipif` that checks `EMIP_ENV` or a feature flag.

## Adding New Tests

### Where to Add

- **Unit tests**: `backend/tests/unit/` — one file per module under test.
- **Integration tests**: `backend/tests/integration/` — cross-module and pipeline tests.
- **Feature/sprint tests**: Prefixed files at `backend/tests/` root (e.g., `test_sprint6_*.py`).

### Conventions

1. Create a test class with a descriptive name.
2. Use `def teardown_method(self)` to reset singletons if needed.
3. Name test methods `test_<what_is_being_tested>`.
4. Use descriptive assert messages for complex conditions.
5. Mock external services (AWS, network) — never depend on real infrastructure.
6. Keep tests fast — aim for <100ms per test.
7. Add docstrings to test classes explaining what they cover.

```python
class TestMyNewStage:
    """Tests for MyNewStage pipeline stage."""

    def test_execute_returns_artifact(self):
        stage = MyNewStage()
        context = PipelineContext(job_id="test-123", project_name="test")
        artifact = stage.execute(context)
        assert artifact.metadata.artifact_type == "my_new_stage"
        assert not artifact.metadata.is_degraded

    def test_fallback_on_ai_failure(self):
        stage = MyNewStage()
        context = PipelineContext(job_id="test-123", project_name="test")
        with patch.object(stage, "execute_ai", side_effect=Exception("AI failed")):
            artifact = stage.execute(context)
            assert artifact.metadata.is_degraded
            assert "fallback" in artifact.content
```

### What to Test

- **Happy path**: The stage/module produces correct output with valid input.
- **Error handling**: Exceptions are caught and handled gracefully.
- **Edge cases**: Empty input, very large input, missing data.
- **Fallback paths**: AI stages produce fallback output on failure.
- **Profile limits**: Behavior changes appropriately with different `AnalysisProfile` values.
- **State changes**: Pipeline state transitions are correct.
