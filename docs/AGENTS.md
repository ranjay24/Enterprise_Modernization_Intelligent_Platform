# AGENTS.md — OpenCode Context for EMIP

## Project
Enterprise Modernization Intelligence Platform (EMIP) — analyzes legacy Java (Spring Boot) applications and produces AI-driven recommendations for migrating to AWS microservices architecture.

## Stack
- **Backend**: Python 3.14, FastAPI, Mangum (Lambda adapter)
- **Frontend**: React 18 + TypeScript + Vite 5 + Tailwind CSS v3
- **Infra**: AWS (S3, DynamoDB, Bedrock, SQS, SNS, Lambda, API Gateway, EventBridge)
- **AI**: Amazon Bedrock (Nova Pro, Nova Lite, Nova Micro)

## Key Directories
```
backend/
  app/
    pipeline/stages/   ← 12 pipeline stages
    ai/                ← AI orchestration (service.py, engine.py, provider/)
    services/          ← Static analyzer, analysis engine, orchestrator
    aws/               ← S3, DynamoDB, SQS, Bedrock, SNS clients
    routes/            ← FastAPI routes (upload, analyze, results, jobs, deploy)
    artifacts/         ← Artifact storage & versioning
    scheduling/        ← DAG, executor, worker pool, cycle detection
    reports/           ← Report builders
    analysis/          ← Sprint 2 plugin-based analysis engine
    prompts/           ← AI prompt templates (versioned)
    models/            ← Pydantic schemas
    core/              ← Settings, constants, analysis profiles
    validators/        ← Input validation
    exceptions/        ← EMIP exception hierarchy
    monitoring/        ← structlog, correlation middleware
frontend/
  src/
    pages/             ← 9 pages
    components/        ← ~95 UI/card/chart/dashboard/results components
    hooks/             ← React hooks
    services/          ← API client (Axios)
    data/              ← Mock data (demo mode)
    store/             ← Zustand store
    types/             ← TypeScript definitions
    utils/             ← Formatters, constants
```

## Pipeline Stages (in order)
1. extraction → 2. static_analysis → 3. enterprise_analysis →
4. ai_boundaries → 5. ai_readiness → 6. ai_adrs →
7. ai_migration → 8. ai_cost → 9. ai_explainability →
10. results_assembly → 11. report_generation → 12. manifest

## Key Rules
- No code changes outside assigned spec files
- Always read the spec file before making changes
- Update progress files after completing tasks
- Do not push to GitHub without explicit approval
- All AI prompts go through BaseAIStage template method
- Never modify artifact schemas without versioning
- Never modify API contracts (request/response models)
- Never remove fallback paths from AI stages

## How to Start
1. Read your assigned spec file from docs/specs/
2. Read docs/design/architecture.md and docs/design/workflow.md
3. Mark task as started in docs/progress/in-progress.md
4. Implement changes
5. Run tests: cd backend && python -m pytest tests/
6. Mark as complete in docs/progress/completed.md
