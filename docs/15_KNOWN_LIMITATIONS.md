# EMIP Known Limitations

This document catalogs the current limitations of the Enterprise Modernization Intelligence Platform. Use this as a reference when planning features, setting expectations with stakeholders, or debugging unexpected behavior. A concise, evaluator-facing summary lives at the repo root: [`KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md).

---

## AI Limitations

### Context Window Constraints

| Model | Max Input Context | Max Output Tokens |
|-------|------------------|-------------------|
| Amazon Nova Pro | 300,000 tokens | 10,000 tokens |
| Amazon Nova Lite | 300,000 tokens | 10,000 tokens |
| Amazon Nova Micro | 300,000 tokens | 10,000 tokens |
| Claude Sonnet 4 | 200,000 tokens | 8,192 tokens |
| Claude Haiku 4.5 | 200,000 tokens | 8,192 tokens |
| Claude Opus 4.5 | 200,000 tokens | 8,192 tokens |
| Mixtral 8x7B | 32,000 tokens | 4,096 tokens |
| Llama 3.2 90B | 128,000 tokens | 4,096 tokens |

The Claude/Mistral/Llama rows feed BENCHMARK profile capability detection only; only the three Nova models have a runtime adapter and can be invoked.

- **Prompt compression needed for large codebases** — codebases with >500 classes routinely exceed available context windows. The `AnalysisProfile` truncation limits (`classes_json_max_chars`, etc.) mitigate this by slicing data before prompt assembly.
- **BENCHMARK mode** detects model capabilities and sets limits accordingly, but very large monoliths (>1000 classes) will still be truncated in any mode.
- **Token counting** is approximate — actual token consumption can vary by 10-20% depending on content.

### Hallucination Risk

- **Service boundary hallucination**: The AI can invent or hallucinate service boundaries for very large monoliths (>500 classes), especially when data has been heavily truncated. The `confidence` score in boundary artifacts partially mitigates this but is not calibrated against ground truth.
- **Package-name bias**: Domain detection is biased by Java package naming conventions. Projects with non-standard package structures or flat namespace layouts produce less reliable domain decompositions.
- **Synthetic examples in prompts**: Some prompt templates include synthetic examples that may bias model responses toward those patterns, potentially reducing relevance for unique architectures.

### Cost Estimation

- **Hybrid pricing, not a quote**: `ai_cost` prices its assumed infrastructure footprint (EC2 `t3.medium`, RDS `db.t3.small`, gp3 storage) with **real AWS Pricing API on-demand rates** when `EMIP_AWS_PRICING_ENABLED=true` (requires AWS credentials, i.e. the Lambda worker) and the region is a known Pricing-API location. When the lookup is disabled/offline/unknown-region it falls back to fixed formulas (e.g. `$1.50/1000 LOC`, `$0.80/class`, fixed post-migration savings assumptions). `migration_impact.pricing_source` = `aws-pricing-api` or `estimate-formulas`. Figures are order-of-magnitude estimates, not quotes. They do not account for:
  - Enterprise discount programs (EDPs)
  - Reserved instance pricing
  - Savings plans
  - Spot instance availability
  - Data transfer costs across regions
  - Support plan costs
- **The footprint is assumed, not scanned**: the static analyzer reports no real instance inventory, so resource counts are derived from classes/LOC/service boundaries. Operations and maintenance remain fixed engineering-labor formulas.
- Estimates default to the region in `AWS_REGION`; other regions may have different rates. Unknown regions fall back to formulas.

### AI Response Consistency

- Model outputs are **non-deterministic by nature**. Even with `temperature=0.0`, the same input can produce different outputs across invocations.
- Response caching (`ai_response_cache_ttl`) reduces variability but adds staleness for long-running analyses.
- Guardrails catch some malformed responses, but schema validation is not exhaustive.

---

## Static Analysis Limitations

### Regex-Based Java Analysis

The static analyzer in `backend/app/services/static_analyzer.py` uses **regex-based parsing**, not an AST-based approach. This leads to:

| Issue | Impact |
|-------|--------|
| Complex generics | Wildcard types, bounded type parameters, and nested generics may be misparsed or skipped |
| Lambda expressions | Anonymous functions are not fully analyzed — inner references may be missed |
| Annotations | Complex annotation structures (nested, with values) may produce incomplete results |
| Inner/anonymous classes | May be inaccurately attributed to their enclosing class |
| Method references | `Class::method` syntax may not resolve correctly |
| Record types | Java 14+ records are not fully supported |
| Sealed classes/interfaces | Not detected — seals are treated as regular modifiers |
| Pattern matching | `instanceof` pattern matching, switch patterns not parsed |

### Missing Analysis Features

- **No call graph construction**: Method-level invocation chains are not tracked. This limits impact analysis and transitive dependency detection.
- **No data flow analysis**: Variable assignments, data propagation, and taint tracking are not implemented.
- **No bytecode analysis**: Only source code is analyzed — compiled class files, JARs, and dependencies are not inspected.

### False Positives

| Detection | False Positive Rate | Cause |
|-----------|-------------------|-------|
| Dead code detection | ~15% | Reflection-based usage, Spring autowiring, SPI/service loader patterns are not recognized |
| Unused imports | ~5% | Static imports, wildcard imports, and annotations may mask true usage |
| God class detection | ~10% | Framework-required base classes with many methods (controllers, services) flagged incorrectly |

### False Negatives

| Detection | False Negative Rate | Cause |
|-----------|-------------------|-------|
| Circular dependencies | ~20% | Runtime-only cycles via reflection, proxy objects, or AOP may not appear in import-level analysis |
| Dependency direction | ~10% | Bidirectional dependencies via interfaces/abstract classes may be missed |
| Injection point detection | ~15% | Constructor injection vs field injection, custom qualifiers, and programmatic lookups |

---

## Upload Security (external 47-item review fixes — 2026-08-09)

- **ZIP traversal + zip-bomb hardening is in place**: uploads are validated
  against path traversal (`..` members, absolute paths, drive letters) and
  size caps (`MAX_ZIP_ENTRY_SIZE_BYTES=100MB`, `MAX_ZIP_ENTRY_COUNT=10000`,
  `MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES=500MB`, `MAX_ZIP_COMPRESSION_RATIO=200`) in
  `app/utils/zip_utils.py` / `app/validators/zip_validator.py`; extraction is
  member-by-member with realpath checks and insecure `mktemp` call sites were
  replaced with `mkstemp`.
- **Remaining gaps acknowledged but deferred** (out of the security+correctness
  pass): SQS `enqueue_report` lacks `MessageGroupId` (#31), `TERMINAL_STATUSES`
  still includes `generating`/`paused` (#34), resume can set raw `uploaded`
  status strings (#32), `fallback()` is not guarded against empty AI output
  triggering it (#22), and some places still buffer large files with
  `file.read()` (#30). See `docs/19_CORRECTNESS_PLAN.md` Phase 9.

## Frontend Limitations

### Data Mocking

- **Demo mode data is static mock data**, not derived from real analysis. The architecture graph, metrics, and recommendations in demo mode are pre-defined samples.
- Mock data is embedded in frontend service files and may diverge from actual API response formats.

### Test Coverage

- **Playwright e2e smoke tests exist** (`tests/e2e/full-flow.spec.ts`, 13 tests — demo-mode dashboard/upload/jobs/results/navigation walkthrough) but there are **no frontend unit or integration tests** for components, hooks, or the API client.
- Component behavior is otherwise verified only through manual testing.

### Performance

- **Architecture graph (ReactFlow) layout** can be slow for >50 nodes. The force-directed layout algorithm has O(n²) complexity and may cause frame drops.
- Large analysis results (>10 MB) may cause slow rendering in the results view.
- No virtual scrolling is implemented for long lists (classes, endpoints, findings).

---

## Infrastructure Limitations

### CI/CD

- **No CI/CD pipeline** — deployment is manual via SAM CLI commands. CI/CD automation (lint, tests, build, deploy) is the active next work track.
- No automated testing in CI, no deployment gates, no canary deployments.

### Monitoring

- **No CloudWatch dashboards** are configured. Metrics exist in CloudWatch but are not aggregated into visual dashboards.
- **No auto-scaling alerts** — Lambda concurrency can be exhausted without notification.
- **No log-based alarms** — error rate increases may go undetected until reported manually.
- X-Ray tracing is disabled by default (controlled by `ENABLE_XRAY` environment variable).

### Multi-Region

- **No multi-region deployment** — all infrastructure is deployed to a single AWS region.
- No disaster recovery strategy, no cross-region replication for S3 or DynamoDB.

### Cold Start

| Function | Cold Start Latency | Mitigation |
|----------|-------------------|------------|
| API backend (FastAPI) | ~1.2 seconds | Keep warm with scheduled CloudWatch Events |
| Worker lambda | ~250ms | Acceptable for async processing |
| Frontend (CloudFront/S3) | None | Static files served from CDN |

---

## Platform Limitations

### Authentication

- **Single-user system** — no multi-tenant support, no user management, no role-based access control.
- Authentication is limited to a static API key (`X-API-Key` header) configured via environment variable.
- No OAuth, no SSO, no JWT-based authentication.

### Language Support

- **Java-only analysis** — the static analyzer, AI prompts, and analysis rules are designed exclusively for Java/Spring Boot applications.
- No support for: .NET, Python, Node.js, Go, Rust, or other JVM languages (Kotlin, Scala).
- Plan analysis is not available for any language.

### Knowledge Base

- **Knowledge base is empty** — the `knowledge-base/` directory exists but contains no reference architectures, migration patterns, or best practice documents.
- No RAG (Retrieval-Augmented Generation) is implemented — AI models rely entirely on prompt context.
- No domain-specific fine-tuning has been applied to AI models.

### Code Generation

- **Code generation works but is not deployed end-to-end**: the agentic codegen loop (architecture → plan → generate → review, max 3 iterations) produces deployable Spring Boot 3 + Java 17 microservice scaffolds via Bedrock with deterministic fallbacks. It runs **in-process in the backend Lambda** — the codegen worker/SQS Lambda path is **not deployed** in the SAM template.
- Generated services cover core scaffolding (pom, config, controllers, services, repositories, entities, tests) with Kafka/RabbitMQ listener wiring and Feign clients; they are a starting point, not a finished production service.
- No API Gateway route wiring, no database migration scripts, no deployment manifests are generated.

### Reports

- The `reports/` directory is **scaffolding only** — report generation via `backend/app/reports/builders.py` produces structured data but no formatted documents (PDF, HTML, DOCX).
- Executive summaries, developer reports, and ADR documents exist only as JSON artifacts.
- No visualization library (charts, diagrams) is integrated into report output.

---

## Performance Expectations

| Project Size | Classes | Static Analysis | AI Analysis | Total Pipeline (seq.) | Total Pipeline (parallel) |
|-------------|---------|-----------------|-------------|----------------------|--------------------------|
| Small | <50 | ~5s | ~30s | ~60s | ~35s |
| Medium | 50-200 | ~15s | ~90s | ~180s | ~100s |
| Large | 200-500 | ~45s | ~240s | ~480s | ~260s |
| Very Large | >500 | ~120s | ~600s+ | ~900s+ | ~500s+ |

Times are estimates based on Nova Pro model with NORMAL profile. Actual performance varies with model choice, profile mode, and concurrent invocation limits.

---

## What to Expect

- **For projects <200 classes**: EMIP provides high-quality service boundaries, ADRs, and migration plans with confidence scores typically >0.7.
- **For projects 200-500 classes**: Results are good but may require human review. Service boundaries may need refinement. Confidence scores typically range 0.4-0.7.
- **For projects >500 classes**: Significant truncation occurs. Results should be treated as recommendations requiring substantial human validation. Confidence scores typically <0.5.
- **Edge cases**: Projects with non-standard frameworks, mixed languages, or extensive reflection/bytecode manipulation will produce less reliable results.
