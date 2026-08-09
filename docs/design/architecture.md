# Architecture Design — EMIP

## High-Level System Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React 18 + Vite 5 + TypeScript)"]
        Pages["9 Pages<br/>Dashboard, Upload, Results, Jobs,<br/>Architecture, Migration, Reports, Settings"]
        Components["95+ Components<br/>UI, Cards, Charts, Dashboard Sections,<br/>Results Sections, Upload Flow, Jobs"]
        State["Zustand Store +<br/>TanStack React Query"]
    end

    subgraph Gateway["API Gateway"]
        API["13 REST Endpoints<br/>/api/upload, /api/analyze, /api/results,<br/>/api/jobs, /api/deploy, /api/capabilities"]
    end

    subgraph Backend["Backend Lambda (FastAPI + Mangum)"]
        Routes["Routes Layer<br/>upload.py, analyze.py, results.py,<br/>jobs.py, deploy.py"]
        Services["Services Layer<br/>orchestrator.py, analysis_engine.py,<br/>events.py, notifications.py, checkpoint.py"]
        AWS_Clients["AWS Clients<br/>clients.py, s3.py, dynamodb.py,<br/>sqs.py, sns.py, eventbridge.py, bedrock.py"]
    end

    subgraph Queue["SQS Queue"]
        AnalysisQueue["emip-analysis-queue-dev"]
        DLQ["emip-analysis-dlq-dev"]
    end

    subgraph Worker["Worker Lambda (2048MB, 600s)"]
        PipelineEngine["PipelineEngine<br/>Sequential or DAG-based"]
        Stages["12 Pipeline Stages<br/>Extraction → Static Analysis → Enterprise Analysis →<br/>AI Boundaries → AI Readiness → AI ADRs →<br/>AI Migration → AI Cost → AI Explainability →<br/>Results Assembly → Report Generation → Manifest"]
        AI["AI Layer<br/>Nova Pro/Lite/Micro<br/>2-step fallback (AI → deterministic)"]
    end

    subgraph Storage["AWS Storage"]
        S3["S3 Buckets<br/>emip-code-dev (uploads)<br/>emip-artifacts-dev (artifacts)"]
        DynamoDB["DynamoDB<br/>emip-jobs-dev<br/>emip-analysis-dev"]
    end

    subgraph Analytics["AWS Analytics & Monitoring"]
        CloudWatch["CloudWatch<br/>Logs + Metrics + X-Ray"]
        EventBridge["EventBridge<br/>Pipeline Events"]
        SNS["SNS<br/>Notifications"]
    end

    Frontend -->|HTTP| Gateway
    Gateway -->|proxy| Backend
    Backend -->|enqueue| AnalysisQueue
    AnalysisQueue -->|trigger| Worker
    AnalysisQueue -->|redrive after 3| DLQ
    Worker --> PipelineEngine
    PipelineEngine --> Stages
    Stages --> AI
    Stages -->|artifacts| S3
    Stages -->|metadata| DynamoDB
    Worker --> CloudWatch
    Worker --> EventBridge
    Worker --> SNS
    Backend -->|read/write| S3
    Backend -->|read/write| DynamoDB
```

## Component Diagram

```mermaid
graph LR
    subgraph Frontend
        Pages
        Components
        Hooks
        Services
        Store
    end

    subgraph "API Layer"
        UploadRoute["POST /api/upload"]
        AnalyzeRoute["POST /api/analyze/{id}"]
        ResultsRoute["GET /api/results/{id}"]
        JobsRoute["POST/DELETE /api/jobs/{id}"]
    end

    subgraph "Pipeline Engine"
        PipelineContext["PipelineContext<br/>Thread-safe shared state"]
        Stage["PipelineStage<br/>Abstract Base Class"]
        BaseAI["BaseAIStage<br/>execute() → execute_ai() → fallback()"]
        Executor["SequentialExecutor / ParallelExecutor"]
        DAG["DAGBuilder<br/>StageNode, CycleValidator"]
    end

    subgraph "AI Provider Layer"
        Adapter["AIModelAdapter<br/>Abstract"]
        Nova["NovaAdapter<br/>Amazon Nova Pro/Lite/Micro"]
        Factory["ProviderFactory"]
        Guardrails["PromptValidator<br/>Policy Enforcement"]
    end

    subgraph "Analysis Engine"
        Scanner["ProjectScanner"]
        Parser["JavaParser"]
        Metrics["CodeMetricsAnalyzer<br/>QualityMetricsAnalyzer"]
        DepGraph["DependencyGraphAnalyzer"]
        Architecture["ArchitectureDetector"]
        Risk["RiskDetector"]
        Readiness["CloudReadinessAnalyzer"]
        Rules["RuleEngine<br/>GodClass, LongMethod, CircularDep,<br/>UnusedCode, HardcodedConfig"]
    end

    subgraph "AWS Services"
        S3_["S3"]
        DynamoDB_["DynamoDB"]
        SQS_["SQS"]
        Bedrock["Bedrock"]
    end

    Frontend --> UploadRoute
    UploadRoute --> S3_
    UploadRoute --> DynamoDB_
    AnalyzeRoute --> SQS_
    SQS_ -->|trigger| PipelineEngine
    PipelineEngine --> Stage
    Stage --> BaseAI
    BaseAI --> Adapter
    Adapter --> Nova
    Nova --> Bedrock
    Stage --> AnalysisEngine
    AnalysisEngine --> Scanner
    AnalysisEngine --> Parser
    AnalysisEngine --> Metrics
    AnalysisEngine --> DepGraph
    AnalysisEngine --> Architecture
    AnalysisEngine --> Risk
    AnalysisEngine --> Readiness
    AnalysisEngine --> Rules
    PipelineEngine --> Executor
    PipelineEngine --> DAG
    ResultsRoute --> DynamoDB_
    ResultsRoute --> S3_
```

## Key Design Patterns

1. **Artifact-First Pipeline**: Every stage produces a versioned Artifact. Stages communicate through artifacts only, not shared memory.

2. **Plugin-Based Analysis**: The Sprint 2 analysis engine uses a plugin architecture where Analyzers are registered by phase and executed in order.

3. **Degraded Mode**: If an AI stage fails, the pipeline continues. The final manifest reports which stages were degraded. No hard failures.

4. **Checkpoint/Resume**: Pipeline state is checkpointed after each stage. Jobs can be paused, cancelled, and resumed from the last checkpoint.

5. **Dual AI Path**: The orchestrator can use either the Sprint 3 AI intelligence layer or fall back to direct Bedrock calls.

6. **DAG-Based Parallel Execution**: Stages with explicit dependencies can run in parallel when the DAG executor is enabled.

7. **2-Step Fallback Chain** (in `BaseAIStage`): AI succeeds → result used; AI fails or returns empty → single deterministic fallback with `is_degraded=true`; pipeline continues and the manifest reports degraded stages.

## Data Flow

1. **Upload**: User uploads ZIP → POST /api/upload → S3 jobs/{id}/raw/ → DynamoDB job record → Response: job_id
2. **Trigger**: POST /api/analyze/{id} → Backend enqueues to SQS → Response: 202 Accepted
3. **Worker**: SQS triggers Worker Lambda → Builds pipeline context → Executes 12 stages (sequential or DAG)
4. **Artifacts**: Each stage writes an Artifact via ArtifactRepository → S3 + DynamoDB metadata
5. **Polling**: Frontend polls GET /api/results/{id} → Displays real-time progress
6. **Completion**: Pipeline completes → EventBridge event → SNS terminal notification (email when `NotificationEmail` is set); the frontend picks up finished results by polling
