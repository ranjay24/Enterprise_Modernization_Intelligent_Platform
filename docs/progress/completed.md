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
