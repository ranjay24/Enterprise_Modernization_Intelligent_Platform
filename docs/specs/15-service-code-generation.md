# Service Code Generation — Agentic Microservice Build

## Problem
The 12-stage analysis pipeline produces solid artifacts (service boundaries, migration waves,
ADRs, cost), but no runnable microservice code. The legacy single-shot `generate_service_code`
placeholder (`ai/orchestrator.py:1294`) returns an empty files list.

## Goal
Convert the analyzed monolith into production-ready Spring Boot 3 + Java 17 + Maven
microservices using a **multi-agent loop driven by Amazon Bedrock (Nova)**:

```
analysis artifacts
   │
   ▼
architectureDesignerAgent ──► architecture_design (graph, broker topology, resilience matrix)
   │
   ▼
servicePlannerAgent       ──► codegen_plan (build waves, per-service order, gateway routes)
   │  per wave → per service
   ▼
codeGenerationAgent       ──► service_code_<svc> (full Spring Boot projects)
   │
   ▼
reviewAgent               ──► review_report (findings + approve/reject)
   │  rejected → planner revises → regenerate (max 3 iterations)
   ▼
final bundle + Bedrock-driven architecture graph
```

## Agents
Four agent definitions live in `backend/app/agents/definitions/*.md` and are executed by
runtime classes in `backend/app/agents/`:

| Agent | Definition | Runtime | Output artifact | Model |
|---|---|---|---|---|
| Architecture Designer | `architectureDesignerAgent.md` | `agents/architecture.py` | `architecture_design` | `bedrock_model_primary` |
| Service Planner | `servicePlannerAgent.md` | `agents/planner.py` | `codegen_plan` | `bedrock_model_primary` |
| Code Generator | `codeGenerationAgent.md` | `agents/generator.py` | `service_code_<svc>` | `bedrock_model_codegen` |
| Reviewer | `reviewAgent.md` | `agents/reviewer.py` | `review_report` | `bedrock_model_primary` |

All agents invoke Bedrock via `AIEngine.invoke_ai_with_fallback()` (project rules 6, 7, 10)
and store results as versioned artifacts via `ArtifactRepository`.

## Generated code must include
- Spring Cloud Gateway routes (API gateway)
- Resilience4j: retry, circuit breaker, rate limiter, time limiter, bulkhead (`resilience4j.yml`)
- OpenFeign clients with circuit-breaker fallbacks for sync inter-service calls
- Kafka and/or RabbitMQ integration selected per service by the Architecture Designer
- `pom.xml`, `application.yml`, `Dockerfile`, `docker-compose.yml`, OpenAPI spec
- Controller / Service / Repository / Entity / DTO layers mapping real boundary classes
- A smoke test per service

## Kafka vs RabbitMQ decision
The Architecture Designer classifies every service's broker role from the data-flow signals
in the analysis artifacts (sync endpoints, shared entities, event/cron patterns, coupling):
- `kafka` — streaming/event backbone, high-volume events, fan-out, CDC
- `rabbitmq` — point-to-point commands, task queues, request-reply
- `both` — consumes event streams AND dispatches commands
- `none` — purely synchronous request/response

## Files to modify
- backend/app/agents/__init__.py (new)
- backend/app/agents/base.py (new) — Agent base class
- backend/app/agents/registry.py (new)
- backend/app/agents/runtime.py (new) — AgentRuntime loop orchestrator
- backend/app/agents/architecture.py (new)
- backend/app/agents/planner.py (new)
- backend/app/agents/generator.py (new)
- backend/app/agents/reviewer.py (new)
- backend/app/agents/definitions/architectureDesignerAgent.md (new)
- backend/app/agents/definitions/servicePlannerAgent.md (new)
- backend/app/agents/definitions/codeGenerationAgent.md (new)
- backend/app/agents/definitions/reviewAgent.md (new)
- backend/app/codegen/models.py (new)
- backend/app/codegen/orchestrator.py (new) — CodeGenOrchestrator
- backend/app/codegen/project_builder.py (new)
- backend/app/codegen/prompts/*.txt (new) — agent prompt templates
- backend/app/codegen/templates/* (new) — code scaffolding templates
- backend/app/routes/codegen.py (new) — start/status/architecture/code/review endpoints
- backend/app/main.py (modify) — register codegen router
- frontend/src/services/jobService.ts (modify) — codegen API client
- frontend/src/pages/ModernizationStudioPage.tsx (new)
- frontend/src/pages/ArchitecturePage.tsx (modify) — render Bedrock architecture graph
- frontend/src/App.tsx (modify) — add route
- docs/progress/in-progress.md / completed.md / backlog.md (modify)
- docs/AGENTS.md (modify)

## Acceptance Criteria
- [ ] A user can start code generation for a completed analysis job (separate action).
- [ ] Architecture Designer returns a Bedrock-generated graph (gateway/services/dbs/brokers
      + typed edges) that the Architecture page renders.
- [ ] Planner returns ordered build waves; generator builds one service per wave step.
- [ ] Generated services are complete Spring Boot 3 + Java 17 + Maven projects including
      Feign, Resilience4j (retry/circuit/rate-limit/time-limit/bulkhead), Gateway routes,
      and Kafka/RabbitMQ config where the architecture prescribes it.
- [ ] Reviewer returns findings; blocking findings trigger planner → regenerate (max 3 iterations).
- [ ] Everything is surfaced in the Modernization Studio UI with code explorer + review panel.
- [ ] New versioned artifacts: `codegen_plan`, `architecture_design`, `service_code_<svc>`,
      `review_report`.

## Estimated Effort
2-3 weeks
