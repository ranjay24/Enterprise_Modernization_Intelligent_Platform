import json
from functools import lru_cache
from typing import Annotated, ClassVar

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode

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

    # AWS Pricing API (ai_cost live rates)
    aws_pricing_enabled: bool = Field(
        default=False,
        description="Use AWS Pricing API for ai_cost infrastructure unit rates (falls back to fixed formulas)",
    )
    aws_pricing_region: str = Field(
        default="us-east-1",
        description="Region for the AWS Pricing API client (global endpoint: us-east-1 or ap-south-1)",
    )
    aws_pricing_cache_ttl: int = Field(
        default=86400,
        description="AWS Pricing rate cache TTL in seconds",
    )

    # S3
    s3_bucket: str = Field(default="emip-artifacts", description="S3 bucket for artifacts")
    s3_max_upload_size_mb: int = Field(default=100, description="Max upload size in MB")

    # DynamoDB
    dynamodb_jobs_table: str = Field(default="emip-jobs-dev", description="DynamoDB jobs table")
    dynamodb_analysis_table: str = Field(default="emip-analysis-dev", description="DynamoDB analysis table")

    # Analysis Mode
    analysis_mode: AnalysisMode = Field(
        default=AnalysisMode.FAST,
        description="Analysis quality mode: fast, normal, or deep",
    )

    # Bedrock
    bedrock_model_primary: str = Field(default="amazon.nova-pro-v1:0", description="Primary Bedrock model")
    bedrock_model_fallback: str = Field(default="amazon.nova-lite-v1:0", description="Fallback Bedrock model")
    bedrock_model_codegen: str = Field(default="amazon.nova-pro-v1:0", description="Code generation model")
    bedrock_max_tokens: int = Field(default=8000, description="Max tokens for Bedrock responses (NORMAL mode only)")
    bedrock_max_retries: int = Field(default=3, description="Max Bedrock retry attempts")
    codegen_parallel_files: int = Field(
        default=3,
        description="Max concurrent Bedrock calls when generating a service file-by-file",
    )

    # SQS
    sqs_analysis_queue: str = Field(default="emip-analysis-queue-dev", description="Analysis SQS queue")
    sqs_analysis_dlq: str = Field(default="emip-analysis-dlq-dev", description="Analysis dead letter queue")

    # SNS
    sns_notification_topic: str = Field(default="emip-notifications-dev", description="Notification SNS topic")

    # Security
    api_key: str = Field(
        default="",
        description="API key for authentication (empty = disabled)",
        validation_alias=AliasChoices("EMIP_API_KEY", "API_KEY", "api_key"),
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )
    # Cognito
    cognito_enabled: bool = Field(
        default=False,
        description="Enable Cognito bearer-token authentication (default off)",
        validation_alias=AliasChoices("EMIP_COGNITO_ENABLED", "COGNITO_ENABLED", "cognito_enabled"),
    )
    cognito_user_pool_id: str = Field(
        default="",
        description="Cognito user pool ID (required when cognito_enabled=true)",
        validation_alias=AliasChoices(
            "EMIP_COGNITO_USER_POOL_ID", "COGNITO_USER_POOL_ID", "cognito_user_pool_id"
        ),
    )
    cognito_region: str = Field(
        default="us-east-1",
        description="Region hosting the Cognito user pool",
        validation_alias=AliasChoices("EMIP_COGNITO_REGION", "COGNITO_REGION", "cognito_region"),
    )
    cognito_client_id: str = Field(
        default="",
        description="Cognito app client ID (required when cognito_enabled=true)",
        validation_alias=AliasChoices("EMIP_COGNITO_CLIENT_ID", "COGNITO_CLIENT_ID", "cognito_client_id"),
    )

    # Local auth provider (fallback when Cognito is not configured)
    local_auth_enabled: bool = Field(
        default=True,
        description=(
            "Built-in local auth provider: signup/login/confirm/refresh/me work out of the box "
            "when Cognito is not configured. Tokens are HMAC-signed and validated by the middleware. "
            "Production should disable this and use Cognito."
        ),
        validation_alias=AliasChoices("EMIP_LOCAL_AUTH_ENABLED", "LOCAL_AUTH_ENABLED", "local_auth_enabled"),
    )
    local_auth_secret: str = Field(
        default="emip-local-dev-secret-change-me",
        description="HMAC signing secret for local auth tokens (dev-only; override in production)",
        validation_alias=AliasChoices("EMIP_LOCAL_AUTH_SECRET", "LOCAL_AUTH_SECRET", "local_auth_secret"),
    )
    local_auth_data_dir: str = Field(
        default="./data",
        description="Directory holding the local auth user store (users.json). Persists across restarts in dev.",
        validation_alias=AliasChoices("EMIP_LOCAL_AUTH_DATA_DIR", "LOCAL_AUTH_DATA_DIR", "local_auth_data_dir"),
    )
    local_auth_token_ttl: int = Field(
        default=3600,
        description="Local access-token lifetime in seconds",
        validation_alias=AliasChoices("EMIP_LOCAL_AUTH_TOKEN_TTL", "LOCAL_AUTH_TOKEN_TTL", "local_auth_token_ttl"),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        """Accept a JSON array or a comma-separated list from the CORS_ORIGINS
        env var (the deployed value, e.g. 'origin-a,http://localhost:5173')."""
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except ValueError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

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
    eventbridge_bus_name: str = Field(default="emip-events-dev", description="EventBridge bus name")
    worker_concurrency: int = Field(default=10, description="Max concurrent analysis workers")
    checkpoint_enabled: bool = Field(default=True, description="Enable pipeline checkpointing")
    artifact_version: str = Field(default="1.0.0", description="Artifact format version")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "env_ignore_empty": True,
    }

    # Non-existent legacy placeholders — used as sentinels for startup validation
    PLACEHOLDER_RESOURCES: ClassVar[dict[str, str]] = {
        "S3_BUCKET": "emip-artifacts",
        "DYNAMODB_JOBS_TABLE": "emip-jobs",
        "DYNAMODB_ANALYSIS_TABLE": "emip-analysis",
        "SQS_ANALYSIS_QUEUE": "emip-analysis-queue",
        "SQS_ANALYSIS_DLQ": "emip-analysis-dlq",
        "SNS_NOTIFICATION_TOPIC": "emip-notifications",
        "EVENTBRIDGE_BUS_NAME": "emip-events",
    }

    @property
    def aws_config_problems(self) -> list[str]:
        """Return actionable problems when AWS resource settings still point at
        non-existent defaults (which surface later as NoSuchBucket /
        ResourceNotFoundException instead of a clear message)."""
        current = {
            "S3_BUCKET": self.s3_bucket,
            "DYNAMODB_JOBS_TABLE": self.dynamodb_jobs_table,
            "DYNAMODB_ANALYSIS_TABLE": self.dynamodb_analysis_table,
            "SQS_ANALYSIS_QUEUE": self.sqs_analysis_queue,
            "SQS_ANALYSIS_DLQ": self.sqs_analysis_dlq,
            "SNS_NOTIFICATION_TOPIC": self.sns_notification_topic,
            "EVENTBRIDGE_BUS_NAME": self.eventbridge_bus_name,
        }
        problems: list[str] = []
        for var, value in current.items():
            placeholder = self.PLACEHOLDER_RESOURCES[var]
            if not value or value == placeholder:
                problems.append(
                    f"{var} is '{value or '(empty)'}' — the default '{placeholder}' "
                    f"does not exist in AWS. Set it to a real resource name "
                    f"(e.g. '{placeholder}-dev' for dev, '{placeholder}-staging' for staging)."
                )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
