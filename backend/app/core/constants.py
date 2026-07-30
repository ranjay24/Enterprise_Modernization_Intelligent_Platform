"""Application-wide constants."""

APP_NAME = "Enterprise Modernization Intelligence Platform"
APP_VERSION = "1.0.0"

S3_KEY_PREFIX_JOBS = "jobs"
S3_KEY_METADATA = "metadata.json"
S3_KEY_RAW = "raw"
S3_KEY_ANALYSIS = "analysis"
S3_KEY_RESULTS = "results.json"
S3_KEY_STATIC_ANALYSIS = "static_analysis.json"
S3_KEY_ARTIFACTS = "artifacts"
S3_KEY_DEPLOYMENTS = "deployments"

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".zip"}

JOB_STATUS_UPLOADED = "uploaded"
JOB_STATUS_ANALYZING = "analyzing"
JOB_STATUS_ANALYSIS_COMPLETE = "analysis_complete"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_DEPLOYED = "deployed"

ANALYSIS_PHASES = [
    "upload",
    "extracting",
    "static_analysis",
    "service_boundary",
    "readiness_scoring",
    "adr_generation",
    "migration_planning",
    "cost_analysis",
    "explainability",
    "code_generation",
    "deployment",
    "analysis_complete",
]

HEALTH_CHECK_PATHS = {"/health", "/api/health", "/docs", "/openapi.json", "/redoc"}
