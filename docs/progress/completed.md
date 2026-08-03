# Completed Tasks

| Task | Assignee | Date | Spec |
|---|---|---|---|
| Sprint 0 - Project Foundation | Team | - | - |
| Sprint 1 - Infrastructure | Team | - | - |
| Sprint 2 - Pipeline Foundation | Team | - | - |
| Sprint 3 - AI Layer | Team | - | - |
| Sprint 4 - Production Hardening | Team | - | - |
| Sprint 5 - Parallel Execution | Team | - | - |
| Sprint 5.5 - Validation | Team | 2026-07-29 | - |
| Sprint 5.6 - Benchmark Analysis Mode | Team | - | - |
| Business Capability Detection | Abhijeet | 2026-07-31 | specs/01-business-capability-detection.md |
| Service Boundary Detection (DDD) | Abhijeet | 2026-07-31 | specs/02-service-boundary-detection.md |
| Migration Roadmap | Abhijeet | 2026-07-31 | specs/03-migration-roadmap.md |
| ADR Generation | Abhijeet | 2026-07-31 | specs/04-adr-generation.md |
| Business Context Understanding | Abhijeet | 2026-07-31 | specs/05-business-context-understanding.md |
| Readiness Scoring with Evidence | Abhijeet | 2026-07-31 | specs/06-readiness-scoring.md |
| Cloud Readiness Breakdown | Abhijeet | 2026-07-31 | specs/07-cloud-readiness.md |
| Cohesion/Coupling Integration Fix | Abhijeet | 2026-07-31 | specs/02-service-boundary-detection.md |
| Results Accuracy Fix (job 5e529ab8) | Abhijeet | 2026-07-31 | specs/02-service-boundary-detection.md |
| Single-File Monolith Parsing Fix | Abhijeet | 2026-08-02 | specs/02-service-boundary-detection.md |

## Results Accuracy Fix — Changes (2026-07-31)
- **Parser/static analyzer flags**: `is_controller` excludes `@ControllerAdvice`; `is_repository` catches `extends CrudRepository` (and JPA/Paging/Mongo/Elasticsearch interfaces); `is_dto` excludes entities/repos/controllers/services; Lombok annotations recognized; `Exceptions` suffix no longer flagged as exception class.
- **Endpoint extraction**: bounded mapping-annotation regex + immediately-following handler method (param annotations allowed); `OrderController` correctly yields 0 endpoints; real count = 26 (Admin 15, Home 5, Product 3, User 3).
- **Dependency edges**: project-only filtering — 130 fabricated edges → 34 real intra-project edges; dead-code rule keeps Spring-managed types (incl. `@ControllerAdvice`).
- **Metrics**: `total_classes`/`total_files`/`avg_cyclomatic_complexity`/`class_type_counts` computed over classes+interfaces+enums (23 = top-level, was 19).
- **Quality**: cohesion/coupling grounded in real intra-project edges (package-level); layered monolith correctly reports ~0/100 instead of fabricated 94.2/8.7.
- **Graph**: class map/edges include interfaces+enums; `coupling_analysis`/highly-coupled counts only project deps.
- **Project scanner**: `_find_project_root` walks below extraction root for `pom.xml` → name `Business_Management_Project-master`, maven, Java 17, Spring Boot 3.1.3 (was `tmp8i07y4zn`/unknown).
- **Boundaries**: `_resolve_class_ownership` (dedupe), `_merge_singleton_boundaries` (HomeController → ProductService), `_assign_unassigned_classes` (100% coverage, 23/23, no dupes); `database_tables` only real `@Table` names (none fabricated); risk/readiness derived from grounded coupling; `business_capabilities` rebuilt from final boundaries.
- **Cost**: `migration_impact` derived from the real wave plan (2 waves/11wk/5 eng for the 4-boundary set); breakdown sums match totals (300/185).
- **ADR prompt**: rule 2 no longer forces god-class/circular-dependency mentions; ADRs grounded in real metrics (0 god classes, 0 circular).
- **Explainability**: evidence labels corrected (`coupling_analysis`, `database_ownership`); `migration_complexity` from grounded coupling; capabilities from final boundaries.
- Tests: 258 passed, 17 failed — all failures are pre-existing environment issues (S3 `NoSuchBucket` in pipeline/executor tests, Windows timer resolution in `test_timer_context_manager`); none in changed modules.

## Single-File Monolith Parsing Fix — Changes (2026-08-02)
- **Problem**: `static_analyzer.py` only parsed top-level classes, so single-file monoliths (one 982-line file with ~36 nested/package-private classes) yielded 2 classes (both dropped as infra) → empty AI boundaries/migration/cost output despite real Bedrock calls.
- **`_parse_java_classes`**: detects every class (multiple top-level + nested/inner) via masked-text declaration scan + brace matching; returns `(JavaClass, source_segment)`; computes file-relative `end_line` and `segment_start_line`.
- **`_mask_code`**: blanks comments/string/char literals preserving newlines (so brace matching and reference counting ignore doc text).
- **`_find_class_declarations`**: handles all modifiers + `class|interface|enum|record`, skips `@interface`.
- **`_annotation_block_start`**: rewritten to backtrack over annotation names/params so `@SpringBootApplication` (and other class annotations) are captured; config classes now correctly ignored as CONFIGURATION.
- **`_parse_java_class`**: class regex includes all modifiers/`record`; method `start_line` offset for file-relative lines; field/`@Autowired` regexes allow `final`; constructor-injection parsing captures Spring ctor params as dependencies (`injection_type: "constructor"`).
- **Dead code**: `class_contents` now stores per-class masked segments (comments never count as references); `_method_annotations`/`_is_private_line` convert file→segment lines; `_symbol_line` outputs file-relative.
- **`_calculate_metrics`/`_detect_dead_code`**: bound last-method end by `end_line` (not file length) — fixes long-method/complexity numbers.
- **Result on `training-certificate-monolith.zip`** (39 classes, 196 methods, 744 LOC): god class `EnrollmentManagementService` (7 injected deps), long methods `UserService.registerUser` (33) + `EnrollmentManagementService.processEnrollmentAndIssuance` (46), dead classes `BaseEntity`/`LegacyPaperCertificatePrinter`/`OldGradeCalculator`, 6 real endpoints; `ai_boundaries` artifact now non-empty (1 service, 37 classes, 10 tables) with `model_id: amazon.nova-pro-v1:0`, 5.4s duration.
- Tests: benchmark (20), sprint3 AI layer (10), sprint4 pipeline (72), capabilities/artifacts/DAG (61), static-analyzer subset (5) all pass.
- **Still open** (deferred, not part of this fix): other stages (`ai_adrs`, `ai_migration`, `ai_cost`, `ai_explainability`, `ai_readiness`) still label `model_id` as `sprint3-deterministic`; cost stage returns `sprint3-deterministic-pricing-unavailable` (IAM lacks `pricing:GetProducts`).

## Deep-Dive Accuracy Fix — training-certificate-monolith.zip (2026-08-03)
Deep-dive on the single-file monolith exposed 1 collapsed "UserService" (39 classes, cohesion=100/coupling=0), 6/9 endpoints, and dishonest model metadata. All issues fixed except Bedrock usage (per request). Verified on fresh job `8702d873-b94d-4837-9fb8-36b0af6c74b2`.
- **RC-1 — collapsed boundaries** (`backend/app/ai/orchestrator.py`):
  - `_assign_unassigned_classes`: score is now `(-dep_overlap, -reverse, -pkg_frac, len(names))` with `pkg_frac` normalized by boundary size; ties break toward the SMALLEST boundary → support/shared classes spread across boundaries instead of all dumping into the first one.
  - `_deterministic_recluster` `_affinity`: normalized `(dep_overlap*3 + reverse*2 + pkg_overlap)/len(names)` — kills the rich-get-richer attractor that previously collapsed everything into one boundary.
  - `analyze_service_boundaries`: `_deterministic_recluster` now runs **only when `not domains`** (AI-candidate fallback). Domain-derived boundaries keep their full DDD chains (C→S→R→E), so `_merge_singleton_boundaries` no longer folds them into a single service.
  - Result: **10 services** (User, Course, CourseModule, Enrollment, Certificate, Assessment, CoursePayment, Notification, StudentProfile, ComplianceAudit) with real coupling/risk — UserService high/red, EnrollmentService critical/red, AssessmentService low/green — no more blanket cohesion=100/coupling=0.
- **RC-2 — missing endpoints** (`backend/app/services/static_analyzer.py`): `_extract_endpoints` regex required `@(Get|Post|…)Mapping\s*\(args\)`, silently dropping bare `@GetMapping`/`@PostMapping`. Added `_class_mapping_path`/`_join_endpoint_path`; fallback prefix is the class-level mapping (or path). Result: **9 endpoints** (was 6): `GET /users/{id}`, `POST /users/register`, `GET /courses`, `GET /courses/{id}`, `POST /courses`, `POST /enrollments`, `POST /enrollments/{id}/complete`, `GET /certificates/verify/{code}`, `GET /certificates/student/{studentId}`. Metrics dict now includes `total_endpoints`.
- **RC-3/4 — cost/readiness labels**: investigated, no code change needed — `pricing-unavailable` label was a docs-only artifact; `AICostStage`/`ai_migration`/`ai_explainability`/`ai_readiness` are honestly deterministic (no Bedrock call, `sprint3-deterministic` model).
- **RC-5 — dishonest model metadata** (`backend/app/ai/orchestrator.py`, `ai_boundaries.py`, `ai_adrs.py`): added `_resolved_model_id(metadata, default="deterministic-fallback")` (returns `default` when `used_fallback`/`error`, else the real Bedrock model). `analyze_service_boundaries` returns the resolved id; `generate_adrs` sets `adr.model_id` per record and returns `_model_id`. Stage defaults changed `sprint3-deterministic` → `deterministic-fallback`. Result: `ai_boundaries`/`ai_adrs` report `amazon.nova-pro-v1:0` (real 18s Bedrock call), deterministic stages report `sprint3-deterministic`.
- **Validation framework** (`backend/app/services/static_analyzer.py`): `endpoint_totals` check compared against `metrics["total_endpoints"]` which was never populated (always 0 → auto-pass). Metrics dict now emits `total_endpoints`; check is meaningful (expected=9 actual=9). `class_ownership`/`entity_table_ownership`/`boundary_completeness` expected/actual 0/0 is a real metric-vs-boundary check, kept as-is.
- **Downstream effects verified**: migration 6 waves/21 weeks/20 engineers (was 1 wave/12 weeks); cost $3,300 → $1,385 (was $800 → $385); readiness "10 business domains detected; Well-separated" consistent with 10 boundaries.
- Tests: `python -m pytest tests/ --ignore=test_sprint5_6_benchmark.py` → **255 passed**. (Full suite's benchmark file requires live model-detection and exceeds local timeout.)
