# KNOWN_LIMITATIONS.md

Honest account of what EMIP does and does not do today. Read this before
trusting any marketing in the other docs. Last verified: 2026-08-09.

## External 47-item code review — status (2026-08-09)

An externally-supplied 47-item EMIP review was independently re-verified and all
P0/P1 security and correctness findings were **fixed** (uncommitted):

- **ZIP uploads are now safe against traversal and zip-bombs**: member-by-member
  extraction with realpath checks, `..`/absolute-path rejection at validation
  time, and caps (100MB/entry, 10,000 entries, 500MB uncompressed total,
  200:1 ratio). Insecure `tempfile.mktemp` call sites replaced with `mkstemp`.
- **Timing-safe API-key comparison** (`hmac.compare_digest`).
- **Pause/cancel now persists a checkpoint** so a paused job resumes from the
  last completed stage instead of restarting.
- **Resume no longer fabricates COMPLETED stages** and artifacts are counted
  once (was triple-counted); executor error entries carry `timestamp`.
- **Nova adapter sends the system prompt and honors explicit `temperature=0.0`**;
  the AI cost tracker receives `job_id` and `estimate_cost` honors updated
  cost profiles; `get_result_data` returns a deep copy.
- **Metrics are honest**: `avg_cyclomatic_complexity` now counts real decision
  points (was avg method line-span), duplication detection actually dedupes by
  body hash (was always 0), and constructor-injection regex no longer matches
  `new Foo(...)` instantiations.
- Regression suite: **424 passed** (`backend/tests/test_code_review_fixes.py`,
  25 tests), frontend `npm run build` green.

**Deferred (out of scope for this pass):** resilience items (#9/#10/#22/#29/
#31/#32/#34 — SQS `MessageGroupId`, `TERMINAL_STATUSES`, raw status strings,
`fallback()` guard, big `file.read()`, resume status), dead-code removal (#33),
frontend polish (#6/#47 — the AIChat `dangerouslySetInnerHTML` is latent today
because its content is a trusted static mock, not model output), and eslint
setup (#48).

## AI capabilities (what actually calls Bedrock)

- **Only two pipeline stages invoke Amazon Bedrock:** `ai_boundaries` (service
  boundary detection) and `ai_adrs` (Architecture Decision Records).
- The other four `ai_*` stages — `ai_readiness`, `ai_migration`, `ai_cost`,
  `ai_explainability` — are **deterministic by design**. They run rule/score
  logic and report model id `sprint3-deterministic` (or
  `sprint3-deterministic-empty` when they return a safe default). They are
  labeled "AI" for historical reasons; they never call a foundation model.
- Every AI-capable stage has a **single deterministic fallback** implemented in
  `BaseAIStage` (`backend/app/pipeline/stages/base.py`): if `execute_ai()`
  raises or returns an empty result, the stage emits its deterministic
  `fallback()` result, sets `is_degraded=true`, and the pipeline continues. The
  manifest lists degraded stages. This is a 2-step chain (AI → fallback), not a
  4-level chain.
- **Codegen** (Modernization Studio / Architecture page) uses an agentic loop
  (architecture → plan → generate → review, max 3 iterations) that DOES call
  Bedrock, with deterministic fallbacks per agent. Prompt wiring for this was
  broken until the P2.1 fix.

## Cost estimation

- `ai_cost` prices its assumed infrastructure footprint (EC2 t3.medium,
  RDS db.t3.small, gp3 storage) with **real AWS Pricing API on-demand rates**
  when enabled (`EMIP_AWS_PRICING_ENABLED=true`, requires AWS credentials, so
  it activates in the Lambda worker) and the region is known. Operations and
  maintenance remain fixed engineering-labor formulas — the Pricing API cannot
  price those. When the lookup is disabled, offline, or the region is unknown,
  it falls back to the fixed formulas (`$1.50/1000 LOC`, `$0.80/class`).
  `migration_impact.pricing_source` reports which path ran. It never calls a
  foundation model — the stage stays deterministic
  (`sprint3-deterministic`).
- **The footprint itself is assumed, not scanned**: the static analyzer reports
  no real infrastructure inventory, so instance counts are derived from
  classes/LOC/service boundaries and priced with default instance types.
  Treat every number as an order-of-magnitude estimate, not a quote.
- The analysis manifest reports real **Bedrock token usage and estimated
  inference cost** per job via the AI cost tracker; when a job never reaches
  Bedrock (fallback/demo), those fields are 0.

## Static analysis

- Java static analysis is **regex-based, not AST-based** (`static_analyzer.py`).
  No call-graph construction, no data-flow/taint analysis, no bytecode analysis.
- Known false-positive/false-negative rates for dead code (~15%), god classes
  (~10%), circular deps (~20%), etc. — see `docs/15_KNOWN_LIMITATIONS.md`.
- Java/Spring Boot only. No Kotlin, Scala, .NET, Python, Node.js, Go, Rust.

## Frontend

- **Demo mode** (`emip-demo` localStorage flag) renders **static mock data**,
  not live analysis. The UI shows an honest "Demo Mode is on" banner on the
  dashboard, jobs, upload, and results pages.
- A Playwright demo-mode smoke walkthrough exists (`tests/e2e/full-flow.spec.ts`,
  13 tests) but there are **no frontend unit/integration tests**.
- Without a live backend, uploads fail with an honest error banner (no fake
  success). No backend → no real analysis.

## Deployment & operations

- **SAM is the supported deployment path** (`infrastructure/template.yaml`):
  API + backend Lambda, SQS worker + DLQ, DynamoDB, S3, Bedrock permissions,
  EventBridge rule → SNS topic, and an email subscription only when the
  `NotificationEmail` parameter is set. The legacy CDK/ECS path was removed.
- **The codegen worker Lambda path is NOT deployed** — code generation runs
  in-process in the backend Lambda (the SQS codegen trigger and its resources
  are not wired into the deployed template).
- **API auth is disabled by default** — the `ApiKey` parameter defaults to
  empty, so `X-API-Key` is not enforced unless configured.
- The Jobs table has **no GlobalSecondaryIndex** — `list_jobs` uses a full Scan
  and sorts in memory. Fine for demos, not for high-volume production.
- **Progress is in-memory** between polls; a Lambda cold start during analysis
  loses transient progress (checkpoints resume the pipeline, but live progress
  reporting is not durable).
- **No CI/CD pipeline** yet — deploys are manual SAM commands. CI/CD
  automation is the active next work track.
- No CloudWatch dashboards, no auto-scaling alerts, no log-based alarms.
  X-Ray is off by default.
- Single AWS region; no multi-region / DR story.
- Cold start: backend ~1.2s, worker ~250ms.

## Platform scope

- Single-user, no multi-tenant, no RBAC, no OAuth/SSO. Optional static API key
  only.
- Knowledge base directory exists but is **empty** — no RAG, no fine-tuning.
- Reports are structured JSON artifacts; no rendered PDF/HTML/DOCX.
- No model-parameter tuning UI; all AI tuning is via `AnalysisProfile`.

## Context window

- Codebases > ~500 classes routinely exceed model context; `AnalysisProfile`
  truncation mitigates but loses fidelity. BENCHMARK mode detects model limits.
- Token counts are approximate (±10–20%).
