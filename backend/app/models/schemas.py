from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ANALYSIS_COMPLETE = "analysis_complete"
    GENERATING = "generating"
    GENERATION_COMPLETE = "generation_complete"
    GENERATION_WITH_WARNINGS = "generation_with_warnings"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class AnalysisPhase(str, Enum):
    """Real pipeline stage names emitted by the worker (see app/pipeline/stages/).

    Aligned with PipelineStage.name and frontend PipelineStages.allPhases.
    """
    EXTRACTION = "extraction"
    STATIC_ANALYSIS = "static_analysis"
    ENTERPRISE_ANALYSIS = "enterprise_analysis"
    AI_BOUNDARIES = "ai_boundaries"
    AI_READINESS = "ai_readiness"
    AI_ADRS = "ai_adrs"
    AI_MIGRATION = "ai_migration"
    AI_COST = "ai_cost"
    AI_EXPLAINABILITY = "ai_explainability"
    RESULTS_ASSEMBLY = "results_assembly"
    REPORT_GENERATION = "report_generation"
    MANIFEST = "manifest"
    CODE_GENERATION = "code_generation"
    ANALYSIS_COMPLETE = "analysis_complete"


class ServiceReadiness(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobCreate(BaseModel):
    filename: str
    file_size: int


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    created_at: str
    updated_at: str
    progress: int = Field(ge=0, le=100, default=0)
    current_phase: str | None = None
    error: str | None = None
    # Sprint 4
    checkpoint_phase: str | None = None
    retry_count: int = 0
    is_degraded: bool = False
    degraded_stages: list[str] = []
    completed_phases: list[str] = []


class CodeMetrics(BaseModel):
    total_files: int
    total_lines: int
    total_classes: int
    total_methods: int
    avg_cyclomatic_complexity: float
    god_classes: list[dict] = []
    duplicate_lines_percent: float
    long_methods: list[dict] = []
    circular_dependencies: list[dict] = []
    dead_code: list[dict] = []
    shared_entities: list[dict] = []
    injection_dependencies: list[dict] = []


class DependencyEdge(BaseModel):
    source: str
    target: str
    type: str  # import, method_call, annotation


class ClassInfo(BaseModel):
    name: str
    package: str
    file_path: str
    lines_of_code: int
    method_count: int
    annotations: list[str] = []
    imports: list[str] = []
    dependencies: list[str] = []


class APIEndpoint(BaseModel):
    method: str
    path: str
    handler_class: str
    handler_method: str
    annotations: list[str] = []


class ServiceBoundary(BaseModel):
    name: str
    description: str
    cohesion_score: float
    coupling_score: float
    classes: list[str]
    packages: list[str]
    api_endpoints: list[APIEndpoint]
    database_tables: list[str]
    confidence: float
    readiness: ServiceReadiness
    risk_level: RiskLevel
    business_capability: str | None = None


class ReadinessScores(BaseModel):
    code_quality: float
    architecture: float
    cloud_readiness: float
    service_separation: float
    database_coupling: float
    documentation: float
    overall: float
    confidence: float
    summary: str | None = None


class ADR(BaseModel):
    id: str
    title: str
    status: str
    context: str
    decision: str
    alternatives: list[dict]
    tradeoffs: dict
    consequences: dict
    confidence: float


class MigrationWave(BaseModel):
    wave_number: int
    name: str
    services: list[str]
    timeline_weeks: int
    estimated_engineers: int
    dependencies: list[str]
    risk_level: RiskLevel


class CostComparison(BaseModel):
    current_monthly: float
    post_migration_monthly: float
    monthly_savings: float
    annual_savings: float
    one_time_cost: float
    payback_months: int
    breakdown_current: dict
    breakdown_post: dict
    migration_impact: dict | None = None


class AnalysisResult(BaseModel):
    job_id: str
    metrics: CodeMetrics
    service_boundaries: list[ServiceBoundary]
    readiness: ReadinessScores
    adrs: list[ADR]
    migration_waves: list[MigrationWave]
    cost_comparison: CostComparison
    explainability: dict
    created_at: str


class DeployRequest(BaseModel):
    job_id: str
    service_name: str


class DeployResponse(BaseModel):
    deployment_id: str
    status: str
    service_name: str
    ecs_cluster: str
    ecs_service: str
    alb_dns: str | None = None
    health_check_url: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    aws_connected: bool
