# Workflow Design — EMIP

## Upload Workflow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Backend API
    participant S3
    participant DB as DynamoDB

    User->>Frontend: Select ZIP file
    Frontend->>Frontend: Validate file type & size
    Frontend->>API: POST /api/upload (multipart)
    API->>API: Validate ZIP content (non-empty)
    API->>S3: Upload to jobs/{id}/raw/
    API->>DB: Create job record (status: uploaded)
    API-->>Frontend: Response: {job_id, status, filename, size}
    Frontend-->>User: Show success with job ID
```

## Analysis Pipeline Workflow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API as Backend API
    participant SQS
    participant Worker
    participant Pipeline
    participant Stages
    participant S3
    participant DB as DynamoDB

    User->>Frontend: Click "Analyze"
    Frontend->>API: POST /api/analyze/{id}
    API->>DB: Update job status (queued)
    API->>SQS: Enqueue message {job_id}
    API-->>Frontend: Response: 202 Accepted

    SQS->>Worker: Trigger Lambda
    Worker->>DB: Update job status (analyzing)
    Worker->>Pipeline: Build PipelineContext
    Pipeline->>Stages: Execute stage 1 (extraction)
    Stages->>S3: Download ZIP from jobs/{id}/raw/
    Stages->>S3: Extract to temp directory
    Stages->>S3: Write extraction artifact
    Stages->>DB: Update analysis record
    Pipeline-->>Worker: Stage 1 complete

    Pipeline->>Stages: Execute stage 2 (static_analysis)
    Stages->>Stages: Analyze Java files (regex)
    Stages->>S3: Write static_analysis artifact
    Pipeline-->>Worker: Stage 2 complete

    Pipeline->>Stages: Execute stage 3 (enterprise_analysis)
    Stages->>Stages: Run 10 analyzer plugins
    Stages->>S3: Write enterprise_analysis artifact
    Pipeline-->>Worker: Stage 3 complete

    Pipeline->>Stages: Execute stages 4-9 (AI stages)
    Stages->>Stages: Build prompts from analysis data
    Stages->>Stages: Invoke Bedrock (Nova Pro)
    Stages->>Stages: Parse & validate AI response
    Stages->>Stages: Fallback if AI fails
    Stages->>S3: Write AI artifacts
    Pipeline-->>Worker: AI stages complete

    Pipeline->>Stages: Execute stage 10 (results_assembly)
    Stages->>S3: Collect all artifacts
    Stages->>S3: Write assembled results
    Pipeline-->>Worker: Stage 10 complete

    Pipeline->>Stages: Execute stage 11 (report_generation)
    Stages->>S3: Generate executive/developer reports
    Pipeline-->>Worker: Stage 11 complete

    Pipeline->>Stages: Execute stage 12 (manifest)
    Stages->>S3: Generate deployment manifest
    Pipeline-->>Worker: Stage 12 complete

    Worker->>DB: Update job status (completed, progress: 100%)
    Worker->>SNS: Send notification (completed)

    Frontend->>API: Poll GET /api/results/{id}
    API-->>Frontend: Response with results & artifacts
    Frontend-->>User: Display full analysis dashboard
```

## Artifact Flow Between Stages

```mermaid
graph LR
    E["Extraction<br/>file_metadata.json"] --> SA["Static Analysis<br/>classes, endpoints, deps"]
    SA --> EA["Enterprise Analysis<br/>10 analyzer outputs"]
    EA --> AB["AI Boundaries<br/>service candidates"]
    AB --> AR["AI Readiness<br/>6-dim scores"]
    AR --> AD["AI ADRs<br/>decision records"]
    AD --> AM["AI Migration<br/>wave plan"]
    AM --> AC["AI Cost<br/>cost comparison"]
    AC --> AX["AI Explainability<br/>confidence, risk, reasoning"]
    AX --> RA["Results Assembly<br/>unified result"]
    RA --> RG["Report Generation<br/>executive, developer reports"]
    RA --> MF["Manifest<br/>artifact inventory"]
```

## Demo Mode Workflow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Store as Zustand Store
    participant MockData as Mock Data

    User->>Frontend: Toggle "Demo Mode"
    Frontend->>Store: setDemoMode(true)

    User->>Frontend: Navigate to Results page (no job)
    Frontend->>Store: Check demoMode
    Store-->>Frontend: true

    Frontend->>MockData: Load mockResults.ts
    MockData-->>Frontend: Full mock analysis result
    Frontend-->>User: Render dashboard with mock data

    Note over Frontend: All pages check demoMode flag.<br/>When true, they substitute mock data<br/>from data/*.ts instead of calling the API.
```

## How Results Reach the Frontend

1. Frontend calls GET /api/jobs to list jobs
2. User clicks a job → navigates to /jobs/{jobId}/results
3. Frontend calls GET /api/results/{jobId} to get status & results
4. useJobPolling hook polls every 1.5s while status is "analyzing"
5. On completion, fetches all artifact details
6. Renders data through page components → section components → card/chart components
7. Each section component receives typed props from types/results.ts computed helpers
