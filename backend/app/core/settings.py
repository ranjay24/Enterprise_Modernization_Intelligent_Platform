from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

from app.core.analysis_profile import AnalysisMode


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Enterprise Modernization Intelligence Platform"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="dev", description="Deployment environment")

    # AWS
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_account_id: str = Field(default="", description="AWS account ID")

    # S3
    s3_bucket: str = Field(default="emip-artifacts", description="S3 bucket for artifacts")
    s3_max_upload_size_mb: int = Field(default=100, description="Max upload size in MB")

    # DynamoDB
    dynamodb_jobs_table: str = Field(default="emip-jobs", description="DynamoDB jobs table")
    dynamodb_analysis_table: str = Field(default="emip-analysis", description="DynamoDB analysis table")

    # Analysis Mode
    analysis_mode: AnalysisMode = Field(
        default=AnalysisMode.BENCHMARK,
        description="Analysis quality mode: fast, normal, or deep",
    )

    # Bedrock
    bedrock_model_primary: str = Field(default="amazon.nova-pro-v1:0", description="Primary Bedrock model")
    bedrock_model_fallback: str = Field(default="amazon.nova-lite-v1:0", description="Fallback Bedrock model")
    bedrock_model_codegen: str = Field(default="amazon.nova-pro-v1:0", description="Code generation model")
    bedrock_max_tokens: int = Field(default=8000, description="Max tokens for Bedrock responses (NORMAL mode only)")
    bedrock_max_retries: int = Field(default=3, description="Max Bedrock retry attempts")

    # SQS
    sqs_analysis_queue: str = Field(default="emip-analysis-queue", description="Analysis SQS queue")
    sqs_analysis_dlq: str = Field(default="emip-analysis-dlq", description="Analysis dead letter queue")

    # SNS
    sns_notification_topic: str = Field(default="emip-notifications", description="Notification SNS topic")

    # Security
    api_key: str = Field(default="", description="API key for authentication")
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # Monitoring
    log_level: str = Field(default="INFO", description="Logging level")
    enable_xray: bool = Field(default=False, description="Enable AWS X-Ray tracing")

    # AI Layer (Sprint 3)
    ai_model_id: str = Field(default="", description="Override AI model ID (empty = use bedrock_model_primary)")
    ai_temperature: float = Field(default=0.0, description="AI model temperature")
    ai_max_retries: int = Field(default=3, description="AI max retry attempts")
    ai_response_cache_ttl: int = Field(default=3600, description="AI response cache TTL in seconds")
    ai_enable_cost_tracking: bool = Field(default=True, description="Enable AI cost tracking")
    ai_enable_observability: bool = Field(default=True, description="Enable AI observability")
    ai_prompt_max_tokens: int = Field(default=7000, description="Max tokens for AI prompts (NORMAL mode only)")
    ai_min_confidence: float = Field(default=0.3, description="Minimum AI confidence threshold")

    # Sprint 4 — Async Pipeline
    eventbridge_bus_name: str = Field(default="emip-events", description="EventBridge bus name")
    worker_concurrency: int = Field(default=10, description="Max concurrent analysis workers")
    checkpoint_enabled: bool = Field(default=True, description="Enable pipeline checkpointing")
    artifact_version: str = Field(default="1.0.0", description="Artifact format version")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
