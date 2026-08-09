# Completed Sprints — EMIP

## Sprint 0 — Foundation

Initial repository setup and project scaffolding.

**Deliverables:**
- GitHub repository with CI structure
- Project architecture defined (`docs/01_ARCHITECTURE.md`, `docs/02_PIPELINE.md`)
- AWS SAM skeleton (`infrastructure/sam/`)
- Backend skeleton with FastAPI
- Frontend skeleton with Vite + React + TypeScript
- Development guidelines and coding standards

**Files created:**
- `backend/app/main.py` — FastAPI entry point
- `frontend/` — Vite + React + TS scaffold
- `docs/` — Architecture and design documents

---

## Sprint 1 — Infrastructure

AWS resource provisioning via SAM and CDK.

**Deliverables:**
- **Lambda Functions:** API handler (`handler.py`), Worker function (`worker_handler.py`)
- **API Gateway:** REST API with Lambda proxy integration
- **SQS + DLQ:** Analysis job queue with dead-letter queue
- **SNS:** Notification topic for job events
- **DynamoDB:** `emip-jobs` and `emip-analysis` tables (no GSI; `list_jobs` uses a Scan)
- **S3:** Artifact bucket with SSE encryption
- **IAM:** Least-privilege roles for Lambda, API Gateway, SQS, Bedrock
- **CloudWatch:** Log groups, metrics, alarms
- **X-Ray:** Tracing enabled on all Lambda functions

**Key files:**
- `infrastructure/sam/template.yaml` — SAM template
- `infrastructure/cdk/` — CDK stack
- `backend/handler.py` — API Lambda handler (Mangum adapter)
- `backend/worker_handler.py` — SQS-triggered Worker Lambda
- `backend/app/monitoring/` — Logging and middleware

---

## Sprint 2 — Pipeline Foundation

Core pipeline engine and static analysis.

**Deliverables:**
- **ZIP upload to S3** — `backend/app/routes/upload.py` → `S3Repository`
- **Codebase extraction** — Extracts and indexes uploaded projects
- **Static Java analyzer** — Regex-based detection in `backend/app/services/static_analyzer.py`
  - Package structure, class declarations, methods, annotations, imports
  - Dependency edges, circular dependencies
  - Injection dependencies (Spring `@Autowired`, `@Inject`)
  - God class detection, endpoint detection (`@RestController`, `@Controller`)
- **Artifact repository** — `backend/app/artifacts/repository.py` for storing/loading pipeline output
- **Pipeline engine** — `backend/app/pipeline/engine.py` — `PipelineEngine` orchestrator
- **State management** — `ConcurrentPipelineState` for tracking stage progress
- **Checkpointing** — `CheckpointManager` for pause/resume
- **Manifest generation** — Deployment manifest created by final pipeline stage
- **Pipeline context** — `PipelineContext` with shared data across stages
- **Stage dependency validation** — Prerequisites checking before execution

**Pipeline stages (all 12):**
1. `extraction` — Code extraction and project structure detection
2. `static_analysis` — Regex-based Java analysis
3. `enterprise_analysis` — Business capability detection
4. `ai_boundaries` — Microservice boundary identification
5. `ai_readiness` — Migration readiness scoring
6. `ai_adrs` — Architecture Decision Record generation
7. `ai_migration` — Migration wave planning
8. `ai_cost` — Cost estimation and ROI
9. `ai_explainability` — AI reasoning traceability
10. `results_assembly` — Result aggregation
11. `report_generation` — Developer and executive reports
12. `manifest` — Deployment manifest creation

**Tests:** Unit tests for pipeline state, stages, artifact repository.

---

## Sprint 3 — AI Layer

Amazon Bedrock integration with provider abstraction.

**Deliverables:**
- **Provider abstraction** — `backend/app/ai/provider/` — Abstract `AIProvider` base class
- **Amazon Nova integration** — `backend/app/ai/provider/nova.py` — Nova Pro/Lite/Micro adapters
- **Prompt registry** — Versioned prompt templates in `backend/app/prompts/`
- **AI contracts** — Input/output schemas for AI operations
- **Prompt builder** — `backend/app/ai/context/builder.py` with token budgeting
- **Guardrails** — `backend/app/ai/guardrails/` — Input validation and output sanitization
- **Recommendation engine** — `backend/app/analysis/recommendation/engine.py`
- **AI memory** — `backend/app/ai/memory/` — Context store, summary, history
- **Context builder** — `backend/app/ai/context/builder.py`
- **AI planner** — `backend/app/ai/planner/engine.py` — Migration wave planning
- **Discovery phase** — Enterprise capability discovery
- **ADR generation** — Architecture Decision Records via AI
- **Migration waves** — AI-planned phased migration
- **Cost estimation** — `backend/app/ai/reports/` — Executive and developer reports
- **Explainability** — AI reasoning traceability
- **Business capability detection** — `backend/app/analysis/scanner/detectors.py`
- **AI orchestration** — `backend/app/ai/orchestrator.py` — Multi-stage AI coordination
- **Fallback chain (2-step, in `BaseAIStage`):**
  1. AI succeeds → result used directly
  2. AI fails (exception or empty result) → single deterministic fallback, flagged `is_degraded=true`; manifest reports degraded stages
- **Deterministic fallback mode** — All AI stages can operate without Bedrock; `ai_readiness`, `ai_migration`, `ai_cost`, `ai_explainability` are deterministic-by-design (`sprint3-deterministic`)

**Tests:** AI provider tests, prompt builder tests, guardrail tests, fallback chain tests.

---

## Sprint 4 — Production Hardening

Reliability, security, and operational readiness.

**Deliverables:**
- **Resume from checkpoints** — `CheckpointManager` with S3-backed state
- **Artifact restoration** — `ArtifactRepository` versioned restore
- **Artifact compression** — Gzip compression for large artifacts
- **Schema versioning** — `schema_version` field on all artifacts
- **Correlation IDs** — `CorrelationMiddleware` for request tracing
- **Report builders** — `backend/app/reports/builders.py` — Structured report generation
- **BaseAIStage** — Eliminated duplicate `try/except` in all AI stages via template method pattern in `backend/app/pipeline/stages/base.py`
- **Integration tests** — End-to-end pipeline test suite
- **S3 SSE encryption** — Server-side encryption enabled on all S3 objects
- **X-Ray tracing** — AWS X-Ray active tracing on all Lambda functions
- **Pipeline reliability** — Retry logic, circuit breakers, degraded mode
- **Configurable analysis profiles** — Preliminary profiles before Sprint 5.6

**Tests:** `test_sprint4_pipeline.py`, `test_sprint4_1.py`, `test_sprint4_artifacts.py`, `test_sprint4_workers.py`, `test_sprint4_capabilities.py`.

---

## Sprint 5 — Parallel Execution

DAG-based parallel pipeline execution.

**Deliverables:**
- **DAG-based execution** — `backend/app/scheduling/dag.py` — `DAGBuilder` constructs execution DAG from stage dependencies
- **Parallel scheduler** — `backend/app/scheduling/parallel_scheduler.py` — Executes ready stages concurrently
- **Worker thread pool** — Thread-safe pool with configurable concurrency
- **Thread-safe state** — `ConcurrentPipelineState` with locks
- **Execution layers** — `ExecutionLayers` groups independent stages for parallel execution
- **Dependency graph** — Graph construction with adjacency lists
- **Cycle detection** — `CycleDetector` in `backend/app/scheduling/cycle_detection.py`
- **Strategy pattern** — Execution strategy selection (sequential vs. parallel)
- **Performance improvements** — 3-5x speedup on independent stages

**Tests:** `test_sprint5_parallel.py` (20+ tests), `test_sprint5_dag.py` (23 tests), `test_sprint5_performance.py` (9 tests), `test_sprint5_integration.py`.

---

## Sprint 5.5 — Validation

Comprehensive validation of infrastructure, API, and failure modes.

**Deliverables:**
- **Infrastructure validation** — 20+ AWS resources verified (Lambda, API Gateway, SQS, DynamoDB, S3, SNS, IAM, CloudWatch, X-Ray)
- **API validation** — All 13 endpoints tested for response format, status codes, error handling
- **Failure mode testing** — 8 scenarios: S3 down, DynamoDB throttling, Bedrock timeout, SQS failure, invalid ZIP, corrupt data, concurrent requests, stage failure
- **Performance testing** — Pipeline throughput, concurrent job handling
- **Pipeline verification** — All 12 stages execute correctly end-to-end
- **CloudWatch/X-Ray monitoring** — Log format verification, trace validation
- **3 bugs found and fixed:**
  1. Race condition in parallel scheduler's `_mark_completed` when stages complete simultaneously
  2. Jobs listing without a GSI — `list_jobs` ran a full Scan; added in-memory sorting on `created_at` (`backend/app/aws/dynamodb.py`)
  3. `CheckpointManager` cleared checkpoints on resume intent instead of after successful resume

**Tests:** 249+ tests total across all test suites.

---

## Sprint 5.6 — Benchmark Analysis Mode

Dynamic analysis profiles replacing hardcoded limits.

**Deliverables:**
- **FAST/NORMAL/DEEP/BENCHMARK modes** — `AnalysisMode` enum in `backend/app/core/analysis_profile.py`
- **Central analysis profiles** — `AnalysisProfile` dataclass with ~60 configurable fields
- **Model capability detection** — `detect_model_capabilities()` mapping model IDs to limits
- **Prompt statistics** — Logging of prompt token usage per stage
- **Dynamic token budgets** — BENCHMARK mode auto-scales to model limits
- **Proportional prompt compression** — Token budget distributed across sections
- **Removal of hardcoded limits** — All 15+ files migrated to `get_profile_for_settings()`
- **Benchmark logging** — Full prompt/response logging in BENCHMARK mode

**Tests:** `test_sprint5_6_benchmark.py` — 21 tests covering profile construction, model detection, limit verification.

## Bugs Fixed

| Bug | Sprint | Root Cause | File | Fix |
|---|---|---|---|---|
| Race condition in parallel scheduler | 5.5 | Non-atomic state check in `_mark_completed` | `backend/app/scheduling/parallel_scheduler.py` | Added lock around completion check |
| Jobs list without GSI | 5.5 | Jobs table had no `status-created_at-index`; `list_jobs` needed a Scan | `backend/app/aws/dynamodb.py` | Jobs table uses `job_id` PK; `list_jobs` uses a Scan with in-memory sort (no GSI exists in `infrastructure/template.yaml`) |
| Checkpoint cleared on resume intent | 5.5 | `clear_checkpoint()` called before resume validation | `backend/app/routes/analyze.py:57` | Moved clear after `has_checkpoint` check |
| Hardcoded limits across 15+ files | 5.6 | Limits defined as module-level constants | `backend/analysis/rules/*.py`, `backend/ai/*.py`, etc. | Replaced with `get_profile_for_settings()` |
| BENCHMARK mode didn't account for output tokens | 5.6 | `prompt_max_tokens` set to full context window | `backend/app/core/analysis_profile.py` | Reserved 2000 tokens for output |

## Test Counts Per Sprint

| Sprint | Test Files | Test Count (approx.) |
|---|---|---|
| Sprint 0 | — | — |
| Sprint 1 | — | — |
| Sprint 2 | `test_truncation_integration.py` | 6 |
| Sprint 3 | AI layer tests | ~30 |
| Sprint 4 | `test_sprint4_pipeline.py`, `test_sprint4_1.py`, `test_sprint4_artifacts.py`, `test_sprint4_workers.py`, `test_sprint4_capabilities.py` | ~80 |
| Sprint 5 | `test_sprint5_parallel.py`, `test_sprint5_dag.py`, `test_sprint5_performance.py`, `test_sprint5_integration.py` | ~100 |
| Sprint 5.5 | Validation and integration tests | ~40 |
| Sprint 5.6 | `test_sprint5_6_benchmark.py` | 21 |
| **Total** | **18 test files** | **~276+** |
