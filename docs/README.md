# EMIP — Enterprise Modernization Intelligence Platform Documentation

## Docs Structure

```
docs/
├── README.md                 ← Overview (this file)
├── AGENTS.md                 ← OpenCode context
├── CLAUDE.md                 ← AI assistant context (root)
├── 00_PROJECT_OVERVIEW.md    ← What EMIP is and why it exists
├── 01_ARCHITECTURE.md        ← System architecture & component diagram
├── 02_PIPELINE.md            ← 12-stage pipeline deep dive
├── 03_AWS_INFRASTRUCTURE.md  ← AWS services, deployment, env vars
├── 04_AI_SYSTEM.md           ← AI layer, providers, prompts, fallbacks
├── 05_ARTIFACT_SYSTEM.md     ← Artifact schemas, versioning, checkpoint
├── 06_API_REFERENCE.md       ← All 13 REST endpoints with examples
├── 07_FRONTEND_ARCHITECTURE.md ← React app structure, components, state
├── 08_DATABASE.md            ← DynamoDB tables, schemas, access patterns
├── 09_ANALYSIS_PROFILES.md   ← FAST/NORMAL/DEEP/BENCHMARK modes
├── 10_COMPLETED_SPRINTS.md   ← History of all 7 completed sprints
├── 11_REMAINING_ROADMAP.md   ← Planned sprints 6-10
├── 12_CODING_GUIDELINES.md   ← Standards, conventions, rules
├── 13_TESTING_GUIDE.md       ← Test suites, running, validating
├── 14_DEPLOYMENT.md          ← SAM/CDK deployment instructions
├── 15_KNOWN_LIMITATIONS.md   ← Current limitations and tradeoffs
├── 16_BENCHMARK_GUIDE.md     ← How to benchmark EMIP
├── 17_AI_AGENT_GUIDE.md      ← MUST READ for AI coding assistants
├── specs/                    ← 14 issue spec files
│   ├── 01-business-capability-detection.md
│   ├── 02-service-boundary-detection.md
│   ├── 03-migration-roadmap.md
│   ├── 04-adr-generation.md
│   ├── 05-business-context-understanding.md
│   ├── 06-readiness-scoring.md
│   ├── 07-cloud-readiness.md
│   ├── 08-cost-estimation.md
│   ├── 09-explainability.md
│   ├── 10-business-capability-map.md
│   ├── 11-domain-relationships.md
│   ├── 12-microservice-recommendations.md
│   ├── 13-confidence-calculation.md
│   └── 14-ai-reasoning-layer.md
├── design/
│   ├── architecture.md       ← Architecture diagrams & patterns
│   └── workflow.md           ← Upload & pipeline workflows
└── progress/
    ├── completed.md           ← Completed tasks log
    ├── in-progress.md         ← Currently assigned tasks
    └── backlog.md             ← Full task backlog with priorities
```

## Quick Start for Developers

1. Read docs/00_PROJECT_OVERVIEW.md (5-minute overview)
2. Read your assigned spec in docs/specs/
3. Read docs/01_ARCHITECTURE.md and docs/02_PIPELINE.md
4. Read docs/12_CODING_GUIDELINES.md
5. Mark task as started in docs/progress/in-progress.md
6. Implement changes
7. Run tests: `cd backend && python -m pytest tests/ -v`
8. Mark as complete in docs/progress/completed.md
