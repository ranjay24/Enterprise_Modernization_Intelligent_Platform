# EMIP Correctness & Refinement Plan (v1)

> Merged plan combining:
> - **A — my independent audit** (this session): verified by running the full backend suite (290 passed), a clean frontend production build, and live probes against the deployed staging API (`https://v8fgmnly4b.execute-api.us-east-1.amazonaws.com/staging`).
> - **B — the prior 4-agent code-level audit** you shared. Its three biggest claims were re-verified by me against the code (codegen prompt-loader bug, worker DLQ swallowing, compile-breaking Jinja2 templates) and confirmed.
>
> Source tags: `[A]` my audit · `[B]` prior audit · `[Both]` independently confirmed by both.
> The evaluation ZIP is already submitted; this plan targets the **repo** over the 3-day improvement buffer, ordered by evaluation impact.

---

## 0. Context — the real-world problem EMIP must credibly solve

Enterprise monoliths (banks, hospitals, insurers) need to migrate to AWS microservices, but nobody understands the 1M+ line codebase; consultants charge $200K–$500K to produce a guesswork assessment. EMIP automates the **discovery and planning** part: upload the monolith → evidence-based service boundaries → readiness → migration waves → cost → ADRs → even draft microservices.

**The credibility equation a judge applies:** every "AI" feature must actually call Bedrock (or honestly say it fell back); every doc claim must match code; every button must work; the whole thing must deploy from a fresh checkout.

---

## 1. Current verified state (baseline)

| Area | Status |
|---|---|
| Backend test suite | 290 passed (full, 2m23s) |
| Frontend build | Clean production build |
| Staging API (live) | `/health`, `/api/health`, `/api/jobs` all 200, `aws_connected: true` |
| Hosted frontend | 200, bundle `index-C2SAOeAT.js` → staging API; upload returns 200 |
| Full pipeline | Job `bacd42cc`: 12/12 stages, 14 services, codegen `finalize` (deterministic fallback) |
| Demo mode | Functional, persisted `emip-demo` |

---

## 2. Phases overview

| Phase | Theme | Goal | Effort |
|---|---|---|---|
| 1 | Demo correctness | No visible bug during any click-through | S |
| 2 | Real AI codegen | Headline feature actually uses Bedrock | M |
| 3 | Deployability & IaC | A fresh checkout deploys; one canonical story | M |
| 4 | Security & reliability | Auth, DLQ, encryption, least-privilege | M |
| 5 | CI/CD + observability | "0%" turns into checkboxes | S–M |
| 6 | Frontend truthfulness | No fake/dead UI an evaluator finds in 2 min | M |
| 7 | Test the real paths | Coverage beyond happy-path unit tests | M |
| 8 | Docs honesty | Every claim matches code | M |

---

## 3. Detailed items

### Phase 1 — Demo correctness (do first, lowest risk)

**P1.1 — Fix upload multipart bug** `[A][B]` · Priority: CRITICAL · Effort: S · Risk: none · ✅ DONE (2026-08-07)
- **Problem:** `frontend/src/services/jobService.ts:7-9` sends explicit `Content-Type: multipart/form-data`; browsers never append `boundary=`, so upload returns `400 {"detail":"Missing boundary in multipart."}`. Same bug in `frontend/src/utils/api.ts`.
- **Fix:** Remove the manual header (axios sets the correct `multipart/form-data; boundary=...` automatically). Also make `frontend/src/utils/constants.ts:1` read `import.meta.env.VITE_API_BASE || '/api'`.
- **Files:** `frontend/src/services/jobService.ts`, `frontend/src/utils/api.ts`, `frontend/src/utils/constants.ts`.
- **Verify:** `npm run build` + browser upload through dev proxy and against hosted API → `200` with `job_id`.

**P1.2 — Remove stale "analyzing" jobs from staging DB** `[A]` · Priority: HIGH · Effort: S · Risk: none · ✅ DONE (2026-08-07)
- **Problem:** Jobs `cdc9e123-…`, `5c155faa-…` stuck at `analyzing`/5% since 2026-08-05; they render as "running forever" on the demo Jobs page.
- **Fix:** `DELETE /api/jobs/{id}` for both (verify artifacts first via `/api/results/{id}/artifacts`).
- **Verify:** `/api/jobs` no longer returns them.

**P1.3 — JobsPage misclassifies codegen jobs as "Queued"** `[A]` · Priority: HIGH · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** `frontend/src/pages/JobsPage.tsx:32-82` status map omits `generating` and `generation_complete` → flagship job `bacd42cc` shows as Queued/"Waiting…".
- **Fix:** Add `generating` (running bucket) and `generation_complete`/`generation_with_warnings` (completed bucket); update `currentTask` mapping.
- **Verify:** JobsPage shows completed jobs under Completed.

**P1.4 — `generation_with_warnings` missing from `JobStatus` enum** `[A][B]` · Priority: HIGH · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** Backend writes it (`codegen.py:99-102` from summary.status), but `backend/app/models/schemas.py:6-16` lacks it → any `GET /results/{id}` on such a job raises pydantic `ValidationError` → 500.
- **Fix:** Add `GENERATION_WITH_WARNINGS = "generation_with_warnings"` to the enum. Frontend already expects it (`types/api.ts:9`).
- **Verify:** Unit test that a job with that status serializes through `JobResponse`.

**P1.5 — Dead duplicate route in results.py** `[A]` · Priority: MEDIUM · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** `results.py:65` `get_artifact` and `results.py:95` `download_artifact_file` share path `/results/{job_id}/artifacts/{x}`; the latter is unreachable (first match wins).
- **Fix:** Rename/merge — keep `get_artifact` (metadata) and give the file download a distinct path (e.g. `/results/{job_id}/artifacts/{name}/download`), or delete the dead one if unused.
- **Verify:** Both routes listed distinctly in OpenAPI `/docs`.

**P1.6 — Dashboard ignores real jobs in non-demo mode** `[A][B]` · Priority: MEDIUM · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** `DashboardPage.tsx:39-79` shows a static empty state when `demoMode=false`; never fetches `listJobs`. After a real analysis the home page still says "No analyses yet".
- **Fix:** In non-demo mode fetch jobs; show latest completed job's metrics (boundaries, readiness, cost) or a genuinely empty state; add a visible "Demo data" badge when `demoMode=true`.
- **Verify:** With a completed job present, dashboard shows real numbers.

**P1.7 — Phase vocabulary mismatch ("0 of 12 stages")** `[A]` · Priority: MEDIUM · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** `AnalysisPhase` enum (`schemas.py:19-31`) uses stale names (`upload`, `extracting`, …) never emitted by the worker; frontend `PipelineStages.tsx:68-71` only recognizes 3 terminal phases → real phases render "0 of 12 stages". `JobsPage.tsx:49` `BACKEND_PHASE_ORDER[12]` is out of bounds.
- **Fix:** Align `AnalysisPhase` with real stage names or stop using it in `analyze.py:64`; make `PipelineStages` compute index from `completed_phases`; guard the out-of-bounds read.
- **Verify:** Job mid-analysis shows correct "x of 12".

**P1.8 — Reports / Migration Planner pick `jobs[0]` with no selector** `[A][B]` · Priority: LOW · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** `ReportsPage.tsx:19-22`, `MigrationPlannerPage.tsx:42-45` silently use the first completed job (DynamoDB scan order, not guaranteed newest-first) — wrong job may display.
- **Fix:** Sort by `created_at` desc (backend already does) and add an explicit job selector.

**P1.9 — `useJobPolling` never stops** `[A][B]` · Priority: LOW · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** `frontend/src/hooks/useJobPolling.ts` polls forever on `paused`/`generating`/`generation_complete`.
- **Fix:** Stop on `paused`, `cancelled`, `generating`→codegen status, `generation_complete`, `generation_with_warnings`.

---

### Phase 2 — Make the headline feature real: AI codegen

**P2.1 — Fix the codegen prompt-loader wiring** `[B]` (verified) · Priority: CRITICAL · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** Agents declare `prompt_id = "codegen/architecture_designer|service_planner|code_generator|code_reviewer"` (`agents/architecture.py:25`, `planner.py:20`, `generator.py:21`, `reviewer.py:20`), but `app/prompts/` has no `codegen/` dir — the 4 prompt files live orphaned in `app/codegen/prompts/`. `AIEngine` → `PromptRenderer` → `PromptLoader` fails to resolve → **every agent always runs deterministic fallback** (`used_ai=False`). The "13 generated services" are generic Jinja2 scaffolds.
- **Fix:** Moved the 4 template files (`architecture_designer.txt`, `code_generator.txt`, `code_reviewer.txt`, `service_planner.txt`) from `app/codegen/prompts/` into `app/prompts/codegen/` (removed the now-empty orphan dir). Their `# prompt:codegen/*` headers match the agents' `prompt_id`s, so `PromptLoader._load_by_id` now resolves them. Added regression test `TestCodegenPrompts` in `tests/test_codegen_agents.py` asserting all four resolve + render with no unresolved vars.
- **Verify:** `PromptLoader` resolves all four; `render_safe` renders cleanly (0 missing vars); full suite 296 passed → 297 with the new test.

**P2.2 — Generated code must compile** `[B]` (verified) · Priority: HIGH · Effort: M · ✅ DONE (2026-08-07)
- **Problems:**
  - `kafka_listener.java.j2:29` `on{{topic}}()` and `rabbit_listener.java.j2:27` `on{{queue}}()` emit invalid Java identifiers for dashed names (`onOrder-created()`). → add a `sanitize_identifier`/camelCase filter.
  - `feign_client.java.j2:16` calls `/internal/{{resource_path}}` that no controller exposes → align resource paths with `controller.java.j2`.
  - Every service defaults to port 8080 → allocate unique ports.
  - `@SpringBootTest` smoke test requires a live Postgres → make it optional/`@Disabled` or use H2.
  - Wave-0 platform services (api-gateway, config-server, discovery) are declared in the plan but never generated → generate them or remove from plan.
- **Fix:** Template filters + plan alignment.
- **Verify:** `mvn compile` (or `mvn -q validate`) on one generated service; smoke test skips without DB.
- **Done:**
  - Added `sanitize`/`camel`/`pascal`/`method` Jinja filters in `project_builder._env()`; listener methods now use `{{ topic | method }}`/`{{ queue | method }}` → valid Java identifiers (`onOrderCreated`, `onOrderEmail`).
  - Fixed a real collision: `broker_role="both"` previously overwrote the Kafka listener with the Rabbit one (same class/path); now distinct `…KafkaEventListener`/`…RabbitEventListener` classes.
  - Feign client now calls `@GetMapping("/{{ resource_path }}")` (matches controller `@RequestMapping`), class name pascalized (fixes dashed interface + file-name mismatch), and URL uses the target service's allocated port.
  - Unique ports: `fallback_plan` assigns `8081 + i` per service (8080 reserved for the gateway); `orchestrator._ordered_services` back-fills missing `server_port` and patches feign `target_port` for AI-produced plans. Wave-0 platform services removed from `fallback_plan` and `service_planner.txt` (platform infra is deployment-level).
  - Smoke test uses H2 (datasource + dialect overridden) and disables Kafka/Rabbit listener auto-startup + `spring.rabbitmq.dynamic` so the context loads fully offline.
  - 7 new `TestScaffoldCompiles` tests in `tests/test_codegen_agents.py`.
  - **Verified live:** generated a `both`-broker service (dashed topics, feign + circuit-breaker) and ran `mvn compile` + `mvn test` with Maven 3.9.9 + JDK 17 → BUILD SUCCESS, SmokeTest passes with no DB/brokers.

**P2.3 — Make the review→replan loop provable** `[B]` · Priority: MEDIUM · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** `reviewAgent` always approves on iteration 1 because scaffolds always contain `.java` files; the rejection→replan→regenerate path (max 3) is untested.
- **Fix:** Unit test forcing a rejection and asserting replan; add a code-quality finding (e.g., missing repository layer) that genuinely fails review.
- **Verify:** New test `test_codegen_rejection_replan.py`.
- **Done:**
  - `fallback_review` now blocks on **critical OR major** findings (matches the `code_reviewer` prompt rule), and adds a genuine `no-repository` **major** finding when an entity layer exists without a matching `repository/` JpaRepository.
  - Found + fixed the real reason replan regeneration never worked: findings are keyed by file path (`src/main/java/com/emip/orderservice/…`) but the service id is dashed (`order-service`) and the package dotted (`com.emip.orderservice`) — neither matched the slash-form path. New `_finding_matches_service()` in `orchestrator.py` matches id, dotted package, AND slash-form package; used by both `_affected_service_ids` and the per-service regeneration filter.
  - New `tests/test_codegen_rejection_replan.py` (6 tests): reviewer approves good scaffolds / rejects missing repository; finding→service mapping; end-to-end orchestrator run that rejects on iter 1 → replans with feedback → regenerates → approves on iter 2; and the max-iterations-exhausted path (`generation_with_warnings`).
  - Full suite 304→309 (one unrelated flaky timing test `test_parallel_faster_diamond_dag` passed in isolation on re-run).

**P2.4 — Persist codegen progress (kill in-memory dict)** `[A][B]` · Priority: MEDIUM · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** `routes/codegen.py:21` `_active_generations` is in-process; dies on restart, breaks across Lambda instances. Lambda path explicitly raises "not deployed yet" (`codegen.py:83`).
- **Fix:** Persist progress to DynamoDB at each agent milestone; implement the SQS-backed codegen worker path OR document local-only explicitly.
- **Verify:** Studio status survives backend restart.
- **Done:**
  - `_active_generations` module dict deleted entirely — DynamoDB is now the single source of truth for codegen status.
  - New `codegen_stage` field on `JobDomain` (+ `to_dict`/`from_dict`); `JobRepository.update_job` accepts it. The orchestrator's `_report` milestone callback now persists `(progress, codegen_stage)` per agent milestone; `start` persists `generating/0/starting`; completion persists `generation_complete/100/finalize`; failures persist `failed` + error.
  - `codegen_status` reads `progress`/`current_stage` from the job record, so Studio status survives a backend restart mid-generation (job stays `generating` at last persisted milestone; re-running the job restarts generation).
  - Lambda path now raises an explicit message documenting that codegen is local/in-process only until the SQS worker is deployed (D3).
  - New `tests/test_codegen_route_persistence.py` (11 tests): model round-trip, start persists generating state, guards (non-analysis-complete, missing job), explicit local-only Lambda message, milestone persistence, sync success/failure persistence, status-after-restart reads persisted progress, complete-job status, missing-job fallbacks.
  - Full suite 309→321 passed (clean run, no flaky failures this time).

---

### Phase 3 — Deployability & infra consistency

**P3.1 — Rebuild Lambda layer for Linux; add `layers/requirements.txt`** `[A][B]` · Priority: CRITICAL (if redeploying) · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** `layers/dependencies/python/` is a Windows pip dump (`pydantic_core.cp314-win_amd64.pyd`, `uvicorn.exe`, …) committed to git — cannot import on Amazon Linux. `docs/14_DEPLOYMENT.md:124` references `layers/requirements.txt`, which does not exist.
- **Fix:** Create `layers/requirements.txt` (pinned); `pip download --only-binary=:all: --platform manylinux2014_x86_64 -d layers/dependencies/python -r layers/requirements.txt`; confirm `sam build && sam deploy` works; optionally remove binaries from git.
- **Verify:** Fresh `sam build` + a deployed smoke `/health`.
- **Done:**
  - New `layers/requirements.txt` pinned to the exact versions bundled in the layer (derived from `*.dist-info`), including **`jinja2`/`markupsafe` which were missing entirely from the layer** — codegen would have crashed with `ImportError` on Lambda.
  - AWS Lambda built-ins (`boto3`, `botocore`, `s3transfer`, `jmespath`, `urllib3`, `six`, `python-dateutil`) excluded from the layer per AWS best practice (avoids runtime version drift; also shrinks the layer).
  - Layer rebuilt via `pip download --only-binary=:all: --platform manylinux2014_x86_64 --python-version 3.14 --implementation cp --abi cp314` and unpacked into `layers/dependencies/python/`. All 7 native modules are now `cpython-314-x86_64-linux-gnu.so`; zero `.pyd` remain.
  - `sam build --template template.yaml` **Build Succeeded** (SAM CLI 1.161.1); `sam validate` reports a valid template. Linux `.so` files land in both `BackendFunction` and `WorkerFunction` build artifacts.
  - Updated `docs/14_DEPLOYMENT.md` "Build the Layer" to the real `dependencies/python/` layout + full `--python-version/--abi` flags (was `-d dependencies/` + a stale `zip` step).
  - Binaries kept in git since a redeploy is pending (plan's "optionally remove" not taken).

**P3.2 — Reconcile SAM vs CDK; one canonical story** `[A][B]` · Priority: HIGH · Effort: M · ✅ DONE (2026-08-07)
- **Problem:** SAM = Lambda+API GW+SQS+DLQ+SNS+EventBridge; CDK = ECS Fargate+ALB+VPC (no worker/DLQ/SNS/EventBridge, DESTROY bucket, HTTP-only). Root `package.json` deploys via CDK; docs/samconfig say SAM is primary. Two systems, no canonical answer.
- **Decision needed:** Keep SAM as canonical (matches live staging). Update package.json deploy scripts to SAM; mark CDK stack as experimental/remove; fix CDK `RemovalPolicy.DESTROY` + `auto_delete_objects` if it stays.
- **Verify:** One deployment path produces the documented architecture.
- **Done:**
  - Root `package.json` now deploys via SAM: `deploy` = `sam deploy --template template.yaml`, new `build:backend` = `sam build`, `validate` = `sam validate`; CDK `deploy`/`deploy:backend`/`synth` scripts removed.
  - CDK stack marked **experimental/legacy**: `app.py` module docstring + runtime warning; `backend_stack.py` header docstring. All `RemovalPolicy.DESTROY` + `auto_delete_objects=True` replaced with `RemovalPolicy.RETAIN` (bucket, both tables, log group) so nothing is ever deleted accidentally.
  - Docs updated to a single canonical story: `03_AWS_INFRASTRUCTURE.md`, `14_DEPLOYMENT.md`, `00_PROJECT_OVERVIEW.md` (3 spots), `17_AI_AGENT_GUIDE.md`, `docs/aws_map.json`.
  - Verified: `npm run validate` → valid template; `npm run build:backend` → **Build Succeeded**; CDK files pass `py_compile`.

**P3.3 — Document/deploy the staging environment in the repo** `[A]` · Priority: HIGH · Effort: S · ✅ DONE (2026-08-07)
- **Problem:** Live demo runs on `emip-*-staging-*` resources (Aug 5) but nothing in the repo deploys them (samconfig → dev; no `parameters/staging.json`; `.env` → CDK names).
- **Fix:** Add `parameters/staging.json`, a `samconfig` staging section, and `SETUP.md`/`.env.example` matching staging names.
- **Verify:** `sam deploy --config-env staging` targets existing resources.
- **Done:**
  - New `infrastructure/parameters/staging.json` (`Environment=staging`, `emip-jobs-staging`/`emip-analysis-staging`, LogLevel INFO).
  - `samconfig.toml` gains a `[staging.build.parameters]` + `[staging.deploy.parameters]` section (stack `emip-staging`, s3_prefix `emip/deploy-staging`, inline overrides mirroring `staging.json`).
  - New root `SETUP.md` — local dev, SAM deploy for dev & staging, environment table, layer note.
  - `backend/.env.example` gains a commented staging block (staging bucket/tables, account 479752407378); the deployed Lambda env comes from the SAM template, not `.env`.
  - `docs/14_DEPLOYMENT.md` shows `sam deploy --config-env staging`.
  - Verified: samconfig parses (staging section present), `sam build --config-env staging` → **Build Succeeded**, both parameter JSONs valid. Actual `sam deploy --config-env staging` is deferred to the end-of-changes redeploy.

**P3.4 — Settings defaults point at non-existent resources** `[A][B]` · Priority: HIGH · Effort: S
- **Problem:** `settings.py:23-45` defaults to `emip-artifacts`, `emip-jobs`, `emip-analysis-queue` — none exist → local start without env = `NoSuchBucket`.
- **Fix:** Either change defaults to a working dev set or fail fast with a clear error listing required env vars.
- **Verify:** Fresh `uvicorn app.main:app` without env prints actionable guidance, not a 400.
- **DONE (2026-08-08):** Both — `settings.py` defaults now use real `-dev` resource names (`emip-jobs-dev`, `emip-analysis-dev`, `emip-analysis-queue-dev`, `emip-analysis-dlq-dev`, `emip-notifications-dev`, `emip-events-dev`); new `Settings.aws_config_problems` flags any leftover placeholder/empty AWS resource values with actionable guidance; `startup.on_startup` fail-fasts locally with a RuntimeError listing problems (skipped under Lambda, which gets real values from the SAM template). Also fixed `backend/.env` to point at real staging resources (`emip-artifacts-staging-479752407378`, `emip-jobs-staging`, `emip-analysis-staging`) and updated the stale defaults in dead modules `app/utils/config.py` and `app/utils/aws.py`. Verified: `on_startup` raises with actionable message when unconfigured, passes with real names; full suite **329 passed** (`tests/test_settings_aws_config.py`, 8 tests).

**P3.5 — Fix `parameters/dev.json` table-name mismatch** `[A][B]` · Priority: MEDIUM · Effort: S
- **Problem:** `infrastructure/parameters/dev.json` uses non-suffixed `emip-jobs`/`emip-analysis` while the template defaults and the judge IAM policy use `emip-jobs-dev`/`emip-analysis-dev` → the judge user cannot access deployed tables.
- **Fix:** Align names; add a pre-deploy check.
- **DONE (2026-08-08):** `dev.json` now uses `emip-jobs-dev`/`emip-analysis-dev` (matching template defaults and `policies/iam-team-policy.json`); new `infrastructure/scripts/check_parameters.py` validates every `parameters/*.json` enforces `emip-jobs-<Environment>`/`emip-analysis-<Environment>` and rejects bare legacy names; wired into `npm run validate` (runs before `sam validate`). Verified: all 3 parameter files pass, `npm run validate` green, negative test flags the original `emip-jobs`/`emip-analysis` values.

**P3.6 — Runtime mismatch & pinned deps** `[A][B]` · Priority: MEDIUM · Effort: S
- **Problem:** `backend/Dockerfile` uses `python:3.12-slim`, Lambda runtime is 3.14; `requirements.txt` uses unpinned `>=`.
- **Fix:** Pin exact versions; align Dockerfile base image with the Lambda runtime.
- **DONE (2026-08-08):** `backend/Dockerfile` → `FROM python:3.14-slim` (matches Lambda `python3.14`); `backend/requirements.txt` fully pinned to the production layer versions (`fastapi==0.140.13`, `uvicorn[standard]==0.51.0`, `pydantic==2.13.4`, `boto3==1.43.49`, `mangum==0.21.0`, `jinja2==3.1.6`, etc.) — no more unpinned `>=`. Verified: `pip install --dry-run` resolves all pins; env aligned to fastapi 0.140.13; full suite **329 passed**.

---

### Phase 4 — Security & reliability

**P4.1 — Wire API authentication** `[A][B]` · Priority: HIGH · Effort: M
- **Problem:** `ApiKey` param declared in SAM but never injected (no env var, no UsagePlan); middleware bypasses when key empty (`EMIP_API_KEY` also doesn't bind to `api_key` in settings — pydantic expects `API_KEY`). API is effectively unauthenticated.
- **Fix:** Pass `EMIP_API_KEY` from the parameter into Lambda env; add API Gateway UsagePlan/API key; honor `API_KEY`/`EMIP_API_KEY` consistently; test 401 without key. If auth stays off, document it.
- **Verify:** Unauthenticated request → 401; with key → 200.
- **DONE (2026-08-08):** `settings.py` `api_key` now binds via `AliasChoices("EMIP_API_KEY", "API_KEY", "api_key")` (EMIP name wins); dead `app/middleware.py` deleted; `app/core/security.py` now returns `JSONResponse(401)` instead of raising `HTTPException` inside `BaseHTTPMiddleware` (which propagated as an exception instead of a 401). SAM template: `EMIP_API_KEY: !Ref ApiKey` in globals, `Conditions` guard on the API key, `GatewayApiKey` + `UsagePlan` + `UsagePlanKey` resources created only when the `ApiKey` parameter is non-empty (`sam validate` green — had to drop `Name` props; the SAM linter schema rejects them). Docs updated in `docs/14_DEPLOYMENT.md`. 9 tests in `tests/test_security.py` (5 env binding + 4 middleware).

**P4.2 — Restore the DLQ failure path** `[A][B]` (verified) · Priority: HIGH · Effort: S
- **Problem:** `worker_handler.py:45-54` catches all exceptions, appends `500` to a list, still returns `200` → SQS deletes the message; `maxReceiveCount: 3` redrive to DLQ never triggers.
- **Fix:** On failure return `{"statusCode": 500}` (or re-raise) so SQS retries then redrives to DLQ.
- **Verify:** Poison message lands in `emip-analysis-dlq-staging`; job marked failed.
- **DONE (2026-08-08):** `worker_handler.py` now raises `RuntimeError` when any record fails (missing job_id, unknown action, or exception) so SQS retries (`maxReceiveCount: 3`) then redrives to the DLQ; success path unchanged (`200`). Tests updated: 2 tests expect the raise + new `test_handler_failure_raises_for_sqs_retry`; `tests/test_sprint4_workers.py` 21 passed.

**P4.3 — Tighten CORS** `[A][B]` · Priority: MEDIUM · Effort: S
- **Problem:** `CORS_ORIGINS: "*"` (globals), API Gateway `AllowOrigin: "'*'"`, mock swagger.
- **Fix:** Restrict to the hosted frontend origin + localhost dev origins.
- **DONE (2026-08-08):** `settings.py` `cors_origins` now uses `Annotated[list[str], NoDecode]` + a `mode="before"` validator that accepts a JSON array string OR comma-separated origins (empty env → defaults, via `env_ignore_empty`); `settings.py` model_config gained `env_ignore_empty`. SAM template: new `CorsOrigins` parameter (default hosted frontend `http://emip-frontend-479752407378.s3-website-us-east-1.amazonaws.com` + localhost 5173/3000), globals `CORS_ORIGINS: !Ref CorsOrigins` (replaces `"*"`); API Gateway `Cors` narrowed to explicit methods/headers while `AllowOrigin '*'` remains for preflight only — FastAPI CORSMiddleware is the authoritative per-origin gate since API Gateway can only echo a single origin. `.env`/`.env.example` updated. 4 new parsing tests in `tests/test_security.py`.

**P4.4 — KMS encryption for SQS/DynamoDB** `[A][B]` · Priority: MEDIUM · Effort: S
- **Problem:** SQS queues and DynamoDB tables use default encryption; the repo's own `test-full.yaml` already shows `KmsMasterKeyId: alias/aws/sqs`. No DDB PITR on SAM tables.
- **Fix:** Add KMS keys + `sse_specification` to tables, `PointInTimeRecoverySpecification: true`.
- **DONE (2026-08-08):** `template.yaml` — `AnalysisDLQ`/`AnalysisQueue` get `KmsMasterKeyId: alias/aws/sqs`; `JobsTable`/`AnalysisTable` get `SSESpecification: {SSEEnabled: true, SSEType: KMS}` (AWS-managed key) + `PointInTimeRecoverySpecification: {PointInTimeRecoveryEnabled: true}`. `sam validate` green.

**P4.5 — Harden IAM** `[A][B]` · Priority: MEDIUM · Effort: S
- **Problem:** `policies/iam-team-policy.json` and Lambda policies grant Bedrock on `Resource: "*"`; `messaging-permissions.json` grants `sqs:*`/`sns:*`/`events:*` on `*`; `cdk-policy.json` is near-admin.
- **Fix:** Scope Bedrock to the 3 Nova model ARNs; remove or replace the wildcard messaging/cdk policies with least-privilege versions.
- **DONE (2026-08-08):** `template.yaml` Backend/Worker `bedrock:Converse` now scoped to the 3 Nova model ARNs (`amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-micro-v1:0`) via `!Sub`; `policies/iam-team-policy.json` BedrockAccess scoped to the same ARNs; `messaging-permissions.json` rewritten least-privilege — data-plane actions on `emip-*` resources (SQS `arn:aws:sqs:...:emip-*`, SNS `emip-*`, EventBridge `event-bus/emip-*` + `rule/emip-*`) with separate list-only statements on `*` (SQS ListQueues, SNS ListTopics, EB ListEventBuses require service-level resources); near-admin `cdk-policy.json` **deleted** (legacy CDK path, unreferenced). Policies verified valid JSON; `sam validate` green.

**P4.6 — EventBridge/SNS wiring** `[A]` · Priority: MEDIUM · Effort: S
- **Problem:** Bus and topic are created but have no rules/targets/subscriptions; the "event-driven, notification" architecture claim is not actually wired.
- **Fix:** Add EventBridge rule(s) → SNS; an SNS subscription (email/HTTP); at minimum document the intended wiring.
- **DONE (2026-08-08):** `template.yaml` — `PipelineEventRule` (`AWS::Events::Rule`) on the custom bus matches `source: emip.pipeline` + terminal/failure detail-types (`pipeline.completed`, `pipeline.failed`, `pipeline.stage.failed`) with `schema_version` prefix guard, target = `NotificationTopic`; `NotificationTopicPolicy` grants `events.amazonaws.com` `sns:Publish` scoped by `aws:SourceArn: !GetAtt EventsBus.Arn`; `NotificationEmailSubscription` created only when new `NotificationEmail` param is set. Docs: `docs/03_AWS_INFRASTRUCTURE.md` EventBridge/SNS sections and `docs/14_DEPLOYMENT.md` env/param table updated. `sam validate` green.

**P4.7 — Guard `fresh_start.py`** `[A]` · Priority: LOW · Effort: S
- **Problem:** `scripts/fresh_start.py` deletes all rows/keys with only a `yes` prompt; no `ENVIRONMENT != prod` guard.
- **Fix:** Refuse to run when `ENVIRONMENT in ("prod", "staging")` unless forced.
- **DONE (2026-08-08):** `scripts/fresh_start.py` now reads `settings.environment` and refuses (exit 1, actionable message) when `prod`/`staging` unless `--force`; argparse `--force` added; docstring updated. Verified: `ENVIRONMENT=staging` run refuses with exit=1.

**Cross-cutting fix (2026-08-08) — CodeGen "no Java sources generated":** reported live on the Modernization Studio; 8/11 services rejected by the review after ~15 min and progress oscillation. Root cause: truncated Bedrock output failed validation, but `AIEngine.invoke_ai` did not set `metadata["error"]`, so `invoke_ai_with_fallback` returned the `{"raw_response": ...}` garbage as valid AI output and the scaffold fallback never ran → `normalize_service_code` → `files: []`. Fixed in `app/ai/engine.py` (mark validation failure as error → fallback triggers) + `app/agents/generator.py` (`_is_complete_service` guard → scaffold on incomplete output). 8 regression tests; full suite **351 passed**; end-to-end loop now approves in 1 iteration with complete services.

**Cross-cutting fix (2026-08-08) — per-file Bedrock generation + fallback badge:** the whole-service prompt can still exceed the model's output-token budget, so `CodeGenerationAgent` now generates **one file per Bedrock call** (`prompt_id="codegen/code_generator_file"`, new template `backend/app/prompts/codegen/code_generator_file.txt`; parallelism bounded by new setting `codegen_parallel_files=3`). The deterministic scaffold is the authoritative file manifest and per-file fallback; the `_is_complete_service` guard remains the final whole-service gate. New `Agent.invoke(..., prompt_id=...)` param in `app/agents/base.py`. Orchestrator now records per-service provenance (`summary.service_origins`: `source` in `bedrock|mixed|scaffold`, `files_ai`, `files_scaffold`, `files_total`) and `GET /api/codegen/{job_id}/status` exposes it. Studio UI (`ModernizationStudioPage.tsx`) renders a **Bedrock / Mixed / Scaffold** badge per generated service. 5 new/updated tests (incl. prompt-variable render + mixed AI/scaffold aggregation); full suite **354 passed**; `npm run build` green; end-to-end run (real orchestrator + stub Bedrock truncating `pom.xml`/`openapi.yaml`) converged in 1 iteration, every service complete with correct `mixed` origins.

**Cross-cutting fix (2026-08-08) — cross-file name consistency gate:** a real run on the `OrderManagementApp` monolith produced a microservice that would not compile — each independently-generated file used different class names (`Order` vs `OrderServiceEntity`, `OrderDTO` vs `OrderServiceDto`, `OrderRepository` vs `OrderServiceRepository`), so 4 of 6 Java files imported types that were never generated. Two-part fix in `app/agents/generator.py` + `backend/app/prompts/codegen/code_generator_file.txt` (v1.1.0):
- **Canonical type manifest** — `_build_shared_types_manifest()` derives the exact type name/kind/package/path of every scaffold file and injects it as `shared_types_json` into **every** per-file prompt, with a rule to reference only those names. Deterministic, no extra Bedrock calls.
- **Import-consistency gate** — `_inconsistent_file_paths()` scans the assembled files: any file whose intra-service import references a type no generated file declares falls back to the deterministic scaffold file; if the whole service still has unresolved imports, the whole-service scaffold fallback engages. This turns the observed compile break into a scaffold fallback instead of persisted broken code.
- 5 new tests in `TestCodeGenerationAgentConsistencyGate` (manifest content, single broken file → scaffold, whole-project drift → consistent output, `_inconsistent_file_paths` positive/negative); full suite **358 passed** (only the pre-existing flaky `test_engine_parallel_vs_sequential` timing test failed under full-suite load — passes in isolation); end-to-end run reproducing the exact divergent-name failure converged in 1 iteration with an import-consistent, approved service.

**Cross-cutting fix (2026-08-09) — monotonic codegen progress + review status UX:** reported live on the Modernization Studio — the progress bar "gradually increases, then decreases and continues" oscillating (80 → 50 → 30..70 → 80 …), the review step stayed red `rejected` even after completion, and the hero showed a misleading "Review pending — findings fed back to Planner" warning post-completion. Root cause (oscillation): `CodeGenOrchestrator._report`/`run` overwrote progress with absolute per-iteration values — replan and each regeneration round restarted from a *lower* number. Fixes:
- **Backend** (`app/codegen/orchestrator.py`): `_report` now tracks a per-run high-water mark (`_max_progress`) and clamps so progress only ever increases within a run; the initial `progress=10` write is routed through the same monotonic reporter. Finalize still lands on exactly 100.
- **Frontend** (`ModernizationStudioPage.tsx`): defence-in-depth high-water mark via a `progressCeiling` ref so the bar never moves backwards mid-run (reset on each new run); `buildAgentSteps` now shows Review as `rejected`/`FEEDBACK` only while the loop is still running and `completed` once generation finishes (detail reflects blocking findings when the final review carried them); hero badges split into in-progress "Reviewing generated code — feeding findings to Planner" vs post-completion "Completed with review findings" / "Generation Complete".
- **Frontend presentation** (`AgentPipelineView.tsx`, `ReviewPanel.tsx`): `rejected` renders as amber `FEEDBACK` (not red danger); `ReviewPanel` header is "Needs Work" with a warning badge instead of a red "Review Rejected"/danger "NEEDS WORK".
- **Tests:** new `tests/test_codegen_progress_monotonic.py` (2 unit + 1 full-loop integration: rejection → replan → approve with non-decreasing progress ending at `(100, "finalize")`); full suite **427 passed**; `npm run build` (tsc + vite) green.

---

### Phase 5 — CI/CD + observability

**P5.1 — Add `.github/workflows/ci.yml`** `[A][B]` · Priority: HIGH · Effort: M
- **Problem:** `.github/workflows/` empty → "CI/CD 0%".
- **Fix:** Job 1 backend: `pip install -r requirements.txt` + `python -m pytest tests/` (offline-safe subset for CI). Job 2 frontend: `npm ci` + `tsc --noEmit` + `npm run build`. Trigger on PR + push.

**P5.2 — Linting** `[B]` · Priority: LOW · Effort: S
- **Fix:** `ruff` for backend, `eslint` for frontend (config files + one clean run).

**P5.3 — CloudWatch dashboard + alarms** `[B]` · Priority: MEDIUM · Effort: S
- **Fix:** One dashboard (Lambda errors/duration/memory, queue depth, DLQ count) + alarms (DLQ > 0, error rate threshold).

---

### Phase 6 — Frontend truthfulness & cleanup

**P6.1 — Label demo mode / make dashboard honest** `[A][B]` · Priority: HIGH · Effort: M · ✅ DONE (2026-08-08)
- **Problem:** Dashboard is mock-only with hardcoded numbers even in non-demo mode; the "Powered by Amazon Bedrock" chat is a 4-answer keyword matcher; fake validation/progress in `useUploadFlow.ts:34-91`.
- **Fix:** Show a persistent "Demo data" badge when `demoMode`; wire dashboard to real API in non-demo; relabel the chat "FAQ (demo)" or wire it to an endpoint; replace simulated validation/progress with real responses (or mark "simulated").
- **Done:** real client-side validation in `useUploadFlow.ts` (async ZIP-magic-byte read, ≤500MB, `.zip`, non-empty — no fake timers); real upload progress via axios `onUploadProgress`; demo banners (FlaskConical) on Dashboard/Jobs/Upload/Results; AIChat relabeled "Demo assistant · pre-written sample answers".

**P6.2 — Wire or disable dead buttons** `[B]` · Priority: MEDIUM · Effort: M · ✅ DONE (2026-08-08)
- **Problem:** Export "as PDF/JSON/MD" and artifact download cards have no `onClick`.
- **Fix:** Implement (data exists in the pages) or disable with a tooltip.
- **Done:** all dead actions disabled with `title="Coming soon"` (Button now allows tooltips via `disabled:cursor-not-allowed` instead of `pointer-events-none`); fabricated Sidebar "Recent" section and "John Doe/Enterprise Plan" profile removed.

**P6.3 — Fix Architecture page stale graph + `?tab=`** `[A][B]` · Priority: MEDIUM · Effort: S · ✅ DONE (2026-08-08)
- **Problem:** `useNodesState/useEdgesState` don't reset on job switch (`ArchitecturePage.tsx:393`); `window.location.href` (`:177`) full-reloads and the `?tab=plan` param is never read.
- **Fix:** `useEffect` to reset nodes/edges on job change; use `navigate()`; make `ModernizationStudioPage` read the initial tab from query params.
- **Done:** `CurrentFlow` now wires `onNodesChange/onEdgesChange` + `useEffect` sync, `key={activeJobId}` remounts the view, `navigate()` replaces `window.location.href`, `?tab=` drives the initial Studio tab.

**P6.4 — Migration Planner week cap** `[A]` · Priority: LOW · Effort: S · ✅ DONE (2026-08-08)
- **Problem:** `MigrationPlannerPage.tsx:116-123` clamps header to `min(maxWeek, 14)`; waves beyond week 14 overflow.
- **Fix:** Auto-scale the axis or add scroll.
- **Done:** timeline renders over `scaleMax = max(maxWeek, 1)` weeks (no 14-week clamp, no "..." truncation); horizontal scroll wrapper (`overflow-x-auto` + `min-w-[720px]`) for long plans.

**P6.5 — Dead code & dupes** `[A][B]` · Priority: MEDIUM · Effort: S · ✅ DONE (2026-08-08)
- **Fix:** Remove unused `utils/api.ts`, `hooks/useUpload.ts`, `data/mockDemoMode.ts`, `AgentRuntime` (raises `NotImplementedError`, never used), `jobService.deleteJob/deployService`, duplicate `/jobs/:jobId/studio` route (`App.tsx:37,40`), unused `Toaster` and deps (`react-table`, `react-virtual`, `cmdk`).
- **Done:** deleted all of the above (Toaster kept — rendered in `main.tsx`); removed the 3 unused deps from `package.json`; full pytest **359 passed** after `agents/runtime.py` deletion (only internal references remained).

**P6.6 — Reduce `any` usage** `[B]` · Priority: LOW · Effort: M · ✅ DONE (2026-08-08)
- **Fix:** Replace 51 `any` usages with types from `src/types/`.
- **Done:** converted the high-value call-sites to real types — new `types/metrics.ts` (`GodClassMetric`, `CircularDependencyMetric`, `DeadCodeMetric`, `ExplainabilityData`) used by `TechnicalDebtCenter`/`ArchitectureIntelligence`/`ExplainabilityCenter`; `JobResponse` in `StudioIndexPage`/`ArchitecturePage`; `CodeGenService`/`ArchitectureNode` in `ModernizationStudioPage`/`ArchitectureGraph`/`ArchitecturePage`; `PlannerWave extends MigrationWave` in `MigrationPlannerPage`; typed recharts tooltip props in `CostTrendChart`; `ServiceBoundary` gained optional `dependencies?: string[]`. Remaining `React.*` annotations are legitimate types. `npm run build` green.

**P6.7 — Fix mock status drift** `[A]` · Priority: LOW · Effort: S · ✅ DONE (2026-08-08)
- **Problem:** `data/mockJobs.ts:21,45` uses statuses that don't exist in the backend (`ai_processing`, `generating_report`, …).
- **Fix:** Align mock statuses with `JobStatus`.
- **Done:** `mockJobs.ts` fields renamed to real API shape (`name`/`filename`/`file_size`/`created_at`/`completed_at`/`error`/`current_phase`, readiness fallback); `useCompletedJobs.ts` `apiJobToDetail` maps real `JobResponse` fields; `jobs.ts`/`useJobPolling.ts` signatures updated to match.

---

### Phase 7 — Tests for the real paths

**P7.1 — Codegen orchestrator loop test** `[B]` · Priority: HIGH · Effort: M
- **Fix:** Unit test `CodeGenOrchestrator` architecture → plan → generate → review → replan (max 3 iterations) with mocked Bedrock + forced rejection.
- **✅ DONE (2026-08-08):** Covered by existing `tests/test_codegen_rejection_replan.py` — `test_rejection_forces_replan_and_regeneration` (reviewer rejection feeds back to the planner) and `test_max_iterations_exhausted_without_approval` (loop caps at 3 iterations) — running green in the full suite.

**P7.2 — AI fallback chain test** `[B]` · Priority: HIGH · Effort: S
- **Fix:** `BaseAIStage`: AI success / AI error → fallback / empty result; assert `is_degraded` + model id honesty.
- **✅ DONE (2026-08-08):** `tests/test_sprint4_1.py` `TestBaseAIStage.test_execute_ai_empty_result_triggers_fallback` now also asserts `artifact.metadata.model_id == "nova-pro-empty"` (model-id honesty on empty AI output).

**P7.3 — Worker DLQ test** `[B]` · Priority: HIGH · Effort: S
- **Fix:** Simulate worker exception → assert non-2xx return (message not silently consumed).
- **✅ DONE (2026-08-08):** Covered by existing `tests/test_sprint4_workers.py` — `test_handler_missing_job_id_redrives_to_dlq`, `test_handler_unknown_action_redrives_to_dlq`, and `test_handler_failure_raises_for_sqs_retry` (worker raises instead of returning 200, so SQS retries and `maxReceiveCount` redrives to the DLQ) — running green.

**P7.4 — Real AI stage tests (boundaries + ADRs)** `[B]` · Priority: MEDIUM · Effort: M
- **Fix:** Mocked Bedrock client; verify honest model id reporting and fallback.
- **✅ DONE (2026-08-08):** New `tests/test_ai_stage_execution.py` (8 passed): `TestAIBoundariesStage` asserts real model id, `_model_id` stripped from content, fallback on exception → `deterministic-fallback` + `is_degraded`, empty-result `nova-lite-empty` fallback, prerequisites require static + enterprise analysis. `TestAIADRStage` runs the same matrix through `app.ai.orchestrator.generate_adrs`.

**P7.5 — Static analyzer fixture test** `[A][B]` · Priority: MEDIUM · Effort: S
- **Fix:** Lock known-good output (e.g., `training-certificate-monolith`: 39 classes, 9 endpoints) as a regression fixture.
- **✅ DONE (2026-08-08):** New fixture `tests/fixtures/training-certificate-monolith/` (9 Java files) + `tests/service/test_static_analyzer_fixture.py` (8 passed). Baselines locked from a live run: 9 classes, 5 endpoints, 4 injection-only dependency edges, `package_tree = {"com.training": 9}`; no `java.*`/`jakarta.*`/`org.springframework` targets in edges; class-level `@RequestMapping("/api/certificates")` joins handler paths and bare mappings resolve to the prefix without doubling.

**P7.6 — Artifact versioning round-trip** `[B]` · Priority: LOW · Effort: S
- **Fix:** Save→load, gzip threshold, checksum, `is_degraded`, schema version.
- **✅ DONE (2026-08-08):** New `tests/repository/test_artifact_roundtrip.py` (6 passed): save→load preserves content/metadata/generator/model_id/artifact_id/`is_degraded`/version fields; checksum matches `ArtifactVersioner.compute_checksum`; content >10 KB gzips (magic bytes `\x1f\x8b`) and round-trips; load-missing returns `None`. Patches `S3Repository` at `app.artifacts.repository.S3Repository`.

**P7.7 — Frontend smoke test** `[A][B]` · Priority: MEDIUM · Effort: M
- **Fix:** Playwright walkthrough (upload → analysis → results in demo mode) asserting pages render; fix stale selectors in the existing `tests/e2e/full-flow.spec.ts`.
- **✅ DONE (2026-08-08):** Rewrote `tests/e2e/full-flow.spec.ts` as a 13-test hard-assertion demo-mode smoke walkthrough; all 13 pass against a fresh Vite server. Also fixed `playwright.config.ts` (webServer now runs in `frontend/` — the root `npm run dev` was the latent reason the old stale dev server was always reused). Selector lessons locked in: the demo banner is a plain-text `<p>` (no node-split issue), the file input is intentionally hidden so the drop zone (`role="button"` + `aria-label="Drop zone for ZIP files"`) is the picker surface, non-ZIP rejection is UploadZone's local `Only .zip files are supported`, and page headings must be scoped to `main` because the top bar renders a duplicate h2. Root-caused a stale-cache pitfall: a long-running dev server was serving pre-P6.1 transformed modules, which is why the banners were invisible to the first run.

---

### Phase 8 — Documentation honesty

**P8.1 — Known-limitations doc (root)** `[A][B]` · Priority: HIGH · Effort: S
- **Fix:** Root `KNOWN_LIMITATIONS.md`: AI-codegen fallback state, 4 deterministic "AI" stages, SAM layer Linux rebuild, API auth disabled by default, codegen Lambda path not deployed, in-memory progress. Own the gaps before an evaluator finds them.
- **✅ DONE (2026-08-08):** Created root `KNOWN_LIMITATIONS.md` (89 lines, last verified 2026-08-08) covering: only `ai_boundaries`+`ai_adrs` call Bedrock; the other 4 `ai_*` stages are deterministic (`sprint3-deterministic`); 2-step fallback chain (not 4-level); codegen agentic loop does call Bedrock with per-agent fallbacks; `ai_cost` fixed-formula estimates (no Pricing API); regex-based static analysis; demo mode = static mock data with honest banner; SAM = supported deploy path but codegen worker Lambda **not** deployed; API auth disabled by default; no GSI (`list_jobs` = Scan); in-memory progress; no CI/CD; no dashboards; single-region; no RBAC; empty knowledge base; context-window truncation. Also reconciled stale claims in `docs/15_KNOWN_LIMITATIONS.md`: cost section now says "fixed formula estimates, not a pricing API"; test-coverage section now reflects the Playwright e2e suite; CI/CD "Planned for Sprint 6+" → active work track; "no real code generation" → honest end-to-end codegen description; added cross-link to the root file.

**P8.2 — Fix false/overstated doc claims** `[A][B]` · Priority: HIGH · Effort: M
- **Examples:** `docs/10_COMPLETED_SPRINTS.md` claims a status-created-at GSI that doesn't exist; `PROJECT_STATUS.md` claims "production-ready" → soften to "validated demo/enterprise-grade prototype"; claims about EventBridge/SNS wiring; stage descriptions that say "AI-generated" for deterministic stages; "4-level fallback" vs actual single retry.
- **✅ DONE (2026-08-08):**
  - **4-level fallback → 2-step** everywhere: `PROJECT_STATUS.md` (failure-handling section, Sprint 3 deliverable row), `SPRINT5_5_REPORT.md`, `docs/04_AI_SYSTEM.md` (overview + Mermaid diagram + numbered list), `docs/09_ANALYSIS_PROFILES.md`, `docs/10_COMPLETED_SPRINTS.md`, `docs/11_REMAINING_ROADMAP.md`, `docs/design/architecture.md` (Mermaid + principle #7), `docs/01_ARCHITECTURE.md`, `docs/02_PIPELINE.md` (code sample relabeled Step 1/Step 2 + explicit "no retry-with-reduced-context step").
  - **GSI false claim removed:** `docs/08_DATABASE.md` (access-pattern section + index table now "no GSI"; `list_jobs` = Scan + in-memory sort) and `docs/10_COMPLETED_SPRINTS.md` (Sprint 5.5 deliverable + bugs table corrected).
  - **"production-ready" → "validated demo / enterprise-grade prototype"** (`PROJECT_STATUS.md`); "passing in production" → "covered by the backend test suite (381 passing)".
  - **SNS "pushes to frontend" fixed:** terminal SNS is an email notification only when `NotificationEmail` is set; the frontend always picks up results by polling (`PROJECT_STATUS.md`, `docs/00_PROJECT_OVERVIEW.md`, `docs/design/architecture.md`, `docs/06_API_REFERENCE.md`).
  - **"AI-generated migration waves/cost" → deterministic:** `PROJECT_STATUS.md` and `docs/00_PROJECT_OVERVIEW.md` now say "AI-generated service boundaries and ADRs, plus deterministic migration waves and cost estimates".
  - **Claude claims corrected to reality:** only `NovaAdapter` is registered (`factory.py: bedrock → NovaAdapter`); Claude/Mistral/Llama exist only as profile capability metadata. Fixed `PROJECT_STATUS.md` ("Claude compatibility layer ✅" → "Claude/Mistral/Llama capability metadata (profile scaling only — no runtime adapter)"), `docs/11_REMAINING_ROADMAP.md`, `docs/16_BENCHMARK_GUIDE.md` (purpose + pricing table note), `docs/15_KNOWN_LIMITATIONS.md` (capability-table note), `docs/13_TESTING_GUIDE.md`, `docs/17_AI_AGENT_GUIDE.md`, `docs/04_AI_SYSTEM.md` code-comment.
  - **Codegen progress bar:** `PROJECT_STATUS.md` `Code Generation 5% ❌ Stubbed only` → `100% ✅ Agentic codegen (Phase 3) — Lambda worker not deployed`; `Frontend Tests 10%` → `20% ✅ E2E smoke tests (13) — unit tests missing`.
  - **Stage table deps corrected** in `PROJECT_STATUS.md` to match the authoritative `docs/02_PIPELINE.md` dependencies.

**P8.3 — Reconcile AI claims** `[A][B]` · Priority: MEDIUM · Effort: S
- **Fix:** Docs must state: only `ai_boundaries` + `ai_adrs` call Bedrock; the other 4 are deterministic-by-design and honestly labeled `sprint3-deterministic`; codegen prompt wiring was broken until P2.1 (now fixed).
- **✅ DONE (2026-08-08):** `docs/04_AI_SYSTEM.md` overview now states only 2 stages invoke Bedrock and the other 4 report `sprint3-deterministic`. `docs/02_PIPELINE.md` per-stage `Requires AI` rows: stages 4/6 → "Yes — invokes Bedrock (Nova Pro)", stages 5/7/8/9 → "No — deterministic" with the exact model id; `ai_cost` row also notes no AWS Pricing call. `PROJECT_STATUS.md` stage table `Requires AI` column + `docs/design/workflow.md` and `docs/06_API_REFERENCE.md` sequence diagrams now show Bedrock only for boundaries/ADRs. Root `KNOWN_LIMITATIONS.md` records the P2.1 codegen prompt-wiring fix.

**P8.4 — Cost-model honesty** `[A][B]` · Priority: MEDIUM · Effort: S
- **Fix:** `ai_cost` uses fixed formulas (`$1.50/1000 LOC`, `$0.80/class`, …) — no AWS Pricing call. Document this as "estimate model", or wire AWS Pricing.
- **✅ DONE (2026-08-08):** Documented as an estimate model everywhere: `docs/02_PIPELINE.md` `ai_cost` row, `docs/15_KNOWN_LIMITATIONS.md` cost section, root `KNOWN_LIMITATIONS.md` cost section, and `docs/09_ANALYSIS_PROFILES.md` expected-cost note (only boundaries+ADRs consume tokens; per-run figures assume Nova Pro).
- **⬆️ EXTENDED (2026-08-08):** Wired the AWS Pricing API as the primary infra-rate source: new `backend/app/services/pricing_service.py` (`AwsPricingService`) looks up real on-demand rates (EC2 `t3.medium`, RDS `db.t3.small`, EBS gp3) per region with TTL cache and graceful `None` on any failure; `AWSClients` gains a `pricing` client; settings gain `EMIP_AWS_PRICING_ENABLED` (default off), `EMIP_AWS_PRICING_REGION`, `EMIP_AWS_PRICING_CACHE_TTL`. `generate_cost_comparison(..., pricing=...)` in `backend/app/ai/orchestrator.py` uses real rates for infrastructure when the lookup succeeds and otherwise keeps the formulas; `AICostStage` passes the provider only when the flag is on (offline-safe, still `sprint3-deterministic`, no Bedrock). `migration_impact.pricing_source` = `aws-pricing-api` | `estimate-formulas`; ops/maintenance stay engineering-labor formulas (not priceable via the API). New `tests/test_pricing_service.py` (12 tests): footprint scaling/cap, rate parsing + cache, missing-rate/API-error/unknown-region fallback, orchestrator formula vs real-rate paths, `pricing` client exposed.

**P8.5 — Add platform AWS-cost metric** `[B]` · Priority: LOW · Effort: M
- **Fix:** Manifest already tracks prompt tokens; add a cost-per-analysis metric (Bedrock tokens, Lambda, DDB on-demand, S3).
- **✅ DONE (2026-08-08):** `backend/app/pipeline/stages/manifest.py` now sources real per-job usage from the AI cost tracker singleton (`get_ai_engine().provider_registry.cost_tracker.get_job_usage(job_id)`, wrapped in try/except with `manifest_cost_tracker_unavailable` warning). Keeps the existing `ai_summary` key shape (`total_tokens_used`, `total_cost_estimate`, `deterministic_fallbacks`, `degraded_stages`) so no schema/API change; `deterministic_fallbacks` remains `len(degraded_stages)`. Previously the fields summed `stage_state.tokens_used`/`cost_estimate`, which are never populated → always 0. New `tests/test_manifest_cost_metric.py` (3 passed): real recorded usage appears (1000+500 Nova Pro tokens → 1500 tokens, ~$0.0016), no usage → 0, and degraded stages are listed.

---

### Phase 9 — External 47-item review: security & correctness (P0/P1)

**Scope selected (2026-08-09):** "Security + correctness first". An externally-supplied 47-item EMIP code-review report was independently re-verified; every P0/P1 security and correctness finding was fixed. Resilience/dead-code/frontend-polish items were deferred (see §4). All changes are **uncommitted** for review.

**Review findings verified TRUE (fixed):**

| Item | Finding | Fix |
|---|---|---|
| #1 | ZIP upload path traversal (`../` members, absolute paths) | `app/utils/zip_utils.py` rewritten — member-by-member `extract` + `_safe_member_path` realpath check; `validate_zip_safety` now also rejects traversal member names (defense-in-depth at upload) |
| #2 | No zip-bomb caps | New caps in `app/core/constants.py` (`MAX_ZIP_ENTRY_SIZE_BYTES=100MB`, `MAX_ZIP_ENTRY_COUNT=10000`, `MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES=500MB`, `MAX_ZIP_COMPRESSION_RATIO=200`) enforced in `validate_zip_safety` |
| #3 | `tempfile.mktemp` ×2 (insecure) | `extraction.py` + `orchestrator.py:218-241` now use `mkstemp`+`os.close`, apply zip-safety checks per member, remove temp zip in `finally` |
| #4 | `boundary_rules.py:188` SyntaxError (broken docstring) | Docstring restored; `python -m compileall -q app` passes |
| #5 | Non-constant-time API-key compare | `hmac.compare_digest` in `app/core/security.py` |
| #8 | Pause/cancel branch never saves checkpoint | `analysis_worker.py` saves checkpoint **before** pause/cancel handling |
| #11 | Validator `float(confidence)` crash on non-numeric | `_to_float()` helper in `app/ai/validation/validator.py` (returns `None`; no crash) |
| #13 | Nova dropped `system_prompt`; temp 0.0 bypassed | `adapter.py` `temperature: float | None`; `nova.py` sends `system` message + resolves temperature from request when set, else config |
| #14 | Cost tracker never receives `job_id`; `estimate_cost` ignored updated profiles | `registry.invoke` passes `request.metadata["job_id"]` into `record_usage`; `update_cost_profile` now mutates module-level `_DEFAULT_COSTS` |
| #16 | `get_result_data` returned live reference | Returns `copy.deepcopy(artifact.content)` |
| #18 | Executor error entries missing `timestamp`; progress counted failed/skipped | All 4 error appends use `{"stage","error","timestamp"}` |
| #19 | Resume fabricated phantom COMPLETED; triple artifact counting | `mark_completed`/`mark_cached` only count artifacts when status wasn't already COMPLETED/CACHED; resume loop no longer fabricates COMPLETED or double-loads artifacts |
| #23 | "avg_cyclomatic_complexity" was avg method line-span | Real cyclomatic counting (`_DECISION_PATTERN`); per-method `start_line`/`end_line`/`body_hash`; new `avg_method_length` scalar |
| #27 | Constructor regex matched `new Foo(...)` anywhere | Class-body scoped regex (`_extract_class_body`) + requires `{` after signature |
| #28 | Dedup key always unique → `dup_lines` always 0 | Dedup by whitespace-normalized `body_hash`, min body length 5 |
| #20 | `mkdtemp` leak + oracle `mktemp` | Temp dirs cleaned on failure; temp zip removed in `finally` |

**Verified NOT a bug / already guarded:** #12 (guards present), #17 (guarded), #44 (`MigrationPlanner` has `|| 12` fallbacks). **Partial:** #33 — `confidence.py`/`orphan_detector.py`/`architecture_smells.py` truly unreferenced, but `graph_exporter.py` **is** exported via `exporters/__init__.py`.

**Tests:** new `backend/tests/test_code_review_fixes.py` (25 regression tests) covering zip traversal/bombs, deep-copy isolation, idempotent artifact counting, validator tolerance, cost-tracker wiring, Nova system-prompt/temperature passthrough (mocked Bedrock), parser complexity/line-span/body-hash, duplication detection, static-analyzer constructor scoping, boundary-rules import, worker checkpoint ordering, executor error schema. Full suite: **424 passed** (was 398 + 1 environmental flake). Frontend `npm run build` green (no frontend code changed in this scope).

**Deferred (out of scope):** #9/#10/#22/#29/#31/#32/#34 (resilience), #33 dead-code removal, #6/#47 (frontend — `AIChat` innerHTML currently latent: content is trusted static mock), #48 (eslint setup).

---

## 4. Execution order & dependencies

```
Phase 1 (P1.1→P1.9)   — ✅ COMPLETE (2026-08-07); every fix is isolated
   ↓
Phase 2 (P2.1→P2.4)   — ✅ P2.1+P2.2+P2.3+P2.4 DONE (2026-08-07) — **Phase 2 complete**
   ↓
Phase 3 (P3.1–P3.6)   — ✅ P3.1+P3.2+P3.3 DONE (2026-08-07); P3.4+P3.5+P3.6 DONE (2026-08-08) — **Phase 3 complete**
   ↓
Phase 4 (P4.1→P4.7)   — security pass
   ↓
Phase 5 (P5.1→P5.3)   — CI can run from here on
   ↓
Phase 6 (P6.1→P6.7)   — ✅ P6.1+P6.2+P6.3+DONE (2026-08-08); P6.4+P6.5+P6.6+P6.7 DONE (2026-08-08) — **Phase 6 complete**
   ↓
Phase 7 (P7.1→P7.7)   — ✅ P7.1+P7.2+P7.3 covered/verified (2026-08-08); P7.4+P7.5+P7.6+P7.7 DONE (2026-08-08) — **Phase 7 complete** (backend 381 passed, frontend build green, 13/13 e2e)
   ↓
Phase 8 (P8.1→P8.5)   — ✅ P8.1+P8.2+P8.3+P8.4+P8.5 DONE (2026-08-08) — **Phase 8 complete** (docs reconciled; manifest cost metric wired; 3 new tests green)
    ↓
Phase 9 (47-item review) — ✅ security+correctness scope DONE (2026-08-09, uncommitted) — 25 new regression tests; full suite 424 passed
```

**Golden rule:** after every change, `cd backend && python -m pytest tests/` (296 baseline) and `cd frontend && npm run build`. Any PR that drops the suite below baseline must be fixed before the next item.

---

## 5. Definition of done (overall)

1. `GET /api/jobs`, `/api/results/{id}/analysis`, `/api/codegen/{id}/status` return correct data for a real job — no 4xx/5xx.
2. A fresh upload → analysis → codegen run completes; codegen artifacts report a real Bedrock model id.
3. One canonical deploy path (SAM) works from a clean checkout; staging env is documented.
4. API auth on; CORS tightened; DLQ proven (poison message lands in DLQ).
5. CI workflow green; tests cover codegen loop, AI fallback, worker DLQ.
6. No fake UI (dashboard/chat/progress/buttons) without an explicit "demo/simulated" label.
7. Docs and code agree on every claim.

---

## 6. Decisions to confirm

| # | Decision | Options | Blocking |
|---|---|---|---|
| D1 | Canonical IaC | SAM (recommended) vs CDK | P3.2 |
| D2 | API auth | On (UsagePlan+key) vs documented-off | P4.1 |
| D3 | Codegen worker path | Implement SQS-backed vs document local-only | P2.4 |
| D4 | Commit policy | Commit each fix separately vs batch per phase | all |
| D5 | Scope this buffer | Phase 1–2 only vs full plan | effort estimate |
| D6 | Update progress docs | Update `docs/progress/` per item (repo convention) | all |
