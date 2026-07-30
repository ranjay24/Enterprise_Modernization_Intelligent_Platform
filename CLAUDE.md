# EMIP — Enterprise Modernization Intelligence Platform

This file provides context to AI coding assistants (Claude, Gemini, etc.).

## Project Structure
- Backend: Python FastAPI in backend/
- Frontend: React + Vite + TypeScript in frontend/
- Infrastructure: AWS SAM/CDK in infrastructure/

## Critical Files
| File | Purpose |
|------|---------|
| backend/app/pipeline/stages/ | 12 pipeline stage implementations |
| backend/app/pipeline/engine.py | PipelineEngine orchestrator |
| backend/app/ai/service.py | AI service entry point |
| backend/app/ai/engine.py | AI engine with provider orchestration |
| backend/app/ai/provider/nova.py | Amazon Nova model adapter |
| backend/app/analysis/engine.py | Sprint 2 plugin-based analysis engine |
| backend/app/services/static_analyzer.py | Regex-based Java static analysis |
| backend/app/services/orchestrator.py | Full analysis coordination (legacy) |
| backend/app/aws/clients.py | AWS client factory |
| backend/app/artifacts/repository.py | Artifact persistence |
| backend/app/scheduling/dag.py | DAG builder for parallel execution |
| backend/app/routes/ | FastAPI route handlers |
| backend/app/core/analysis_profile.py | Profile configuration |
| frontend/src/pages/ | 9 page components |
| frontend/src/services/jobService.ts | API client |

## Architecture
React Frontend → API Gateway → Lambda Backend (FastAPI+Mangum) → SQS → Worker Lambda → Pipeline Engine (12 stages) → Artifacts (S3+DynamoDB)

## Rules for Development
1. Read the relevant spec file in docs/specs/ before making changes
2. Only modify files listed in the "Files to modify" section of your spec
3. Update progress files after completing tasks
4. Do NOT push to GitHub without approval
5. Keep AGENTS.md and progress files in sync
6. Never create boto3 clients directly — use app/aws/clients.py factory
7. Never bypass BaseAIStage — always use the execute() → execute_ai() → fallback() pattern
8. Never hardcode limits — always use AnalysisProfile
9. Never modify artifact schemas without incrementing version field
10. Always add fallback paths for AI stages

## Documentation
- Architecture: docs/01_ARCHITECTURE.md
- Pipeline: docs/02_PIPELINE.md
- AWS Infra: docs/03_AWS_INFRASTRUCTURE.md
- AI System: docs/04_AI_SYSTEM.md
- Artifact System: docs/05_ARTIFACT_SYSTEM.md
- API Reference: docs/06_API_REFERENCE.md
- Frontend: docs/07_FRONTEND_ARCHITECTURE.md
- Database: docs/08_DATABASE.md
- Analysis Profiles: docs/09_ANALYSIS_PROFILES.md
- Coding Guidelines: docs/12_CODING_GUIDELINES.md
- Testing Guide: docs/13_TESTING_GUIDE.md
- Known Limitations: docs/15_KNOWN_LIMITATIONS.md
- AI Agent Guide: docs/17_AI_AGENT_GUIDE.md

## How to Start
1. Read docs/17_AI_AGENT_GUIDE.md first
2. Read your assigned spec from docs/specs/
3. Read docs/01_ARCHITECTURE.md and docs/02_PIPELINE.md
4. Mark task as started in docs/progress/in-progress.md
5. Implement changes following docs/12_CODING_GUIDELINES.md
6. Run tests: cd backend && python -m pytest tests/ -v
7. Mark as complete in docs/progress/completed.md
