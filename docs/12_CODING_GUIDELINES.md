# EMIP Coding Guidelines

## Python Standards

- **Python 3.14+** — all code must target the Python 3.14 runtime used by AWS Lambda.
- **Type hints required** for every function signature — parameters, return types, and inner functions.
- `from __future__ import annotations` **at the top** of every `.py` file to enable PEP 604 syntax and deferred evaluation.
- Use `|` union syntax (`str | None`) rather than `Optional[str]`.
- Use `collections.abc` types (`Sequence`, `Mapping`) rather than `typing` equivalents.

```python
from __future__ import annotations

from collections.abc import Callable, Sequence


def process_items(items: Sequence[str], callback: Callable[[str], int] | None = None) -> dict[str, int]:
    ...
```

## FastAPI

- Every request body and response body must be a **Pydantic model** — never raw `dict` or `Request`.
- Define schemas in `backend/app/models/schemas.py` or a dedicated model module.
- Use `Field(..., description=...)` for all fields.
- Route handlers must be async.
- Use `Depends()` for dependency injection (settings, AWS clients).

```python
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    job_id: str = Field(..., description="Job identifier")
    mode: str = Field(default="normal", description="Analysis mode")
```

## Logging

- **Never use `print()` or the `logging` stdlib module directly.**
- Always use **structlog** with the configured logger from `app.monitoring.logging`.
- Import pattern: `import structlog` then `logger = structlog.get_logger(__name__)`.
- Use structured key-value pairs — never f-string interpolation in log messages.
- Log levels: `info` for normal operations, `warning` for recoverable issues, `error` for failures.

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("artifact_saved", job_id=job_id, stage=stage_name, size_bytes=size)
logger.warning("ai_stage_fallback", stage=self.name, job_id=context.job_id, error=str(exc))
```

## AWS Clients

- **Never create boto3 clients directly** — always go through `app/aws/clients.py`.
- The `AWSClients` factory provides lazy-initialized, cached clients for S3, DynamoDB, Bedrock, SQS, SNS, CloudWatch, and EventBridge.
- Access via `get_aws_clients()` from `app.core.dependencies`.
- Supported services: `s3`, `s3_resource`, `dynamodb`, `bedrock`, `sqs`, `sns`, `cloudwatch`, `events`, `sts`.

```python
from app.core.dependencies import get_aws_clients

clients = get_aws_clients()
bucket_name = clients.s3_bucket_name
clients.s3.put_object(Bucket=bucket_name, Key=key, Body=data)
```

## Pipeline Stages

- Extend `PipelineStage` (for non-AI stages) or `BaseAIStage` (for AI-powered stages).
- **Never bypass the BaseAIStage template method** — always use the `execute()` → `execute_ai()` → `fallback()` pattern.
- `BaseAIStage.execute()` handles try/except, fallback, Artifact creation, and degraded flagging automatically.
- Subclasses override `execute_ai()` to return `(result_dict, model_id)` and `fallback()` to return a default result.
- Property `depends_on` declares explicit stage dependencies for DAG scheduling.

```python
from app.pipeline.stages.base import BaseAIStage
from app.pipeline.context import PipelineContext


class MyCustomStage(BaseAIStage):
    @property
    def name(self) -> str:
        return "my_custom_stage"

    @property
    def phase(self) -> str:
        return "analysis"

    def prerequisites(self, context: PipelineContext) -> list[str]:
        return []

    def execute_ai(self, context: PipelineContext) -> tuple[dict, str]:
        result = {"key": "value"}
        return result, "amazon.nova-pro-v1:0"

    def fallback(self) -> dict:
        return {"key": "fallback", "is_degraded": True}
```

## Artifacts

- Every pipeline stage output must be an `Artifact` (from `app.artifacts.models`).
- Use `ArtifactRepository` for all persistence — never write directly to S3 or DynamoDB.
- Artifacts above 10 KB are transparently gzip-compressed by the repository.
- Always use `create_artifact()` for proper metadata generation.

```python
from app.artifacts.repository import ArtifactRepository

repo = ArtifactRepository()
artifact = repo.create_artifact(
    job_id=job_id,
    stage_name="static_analysis",
    content={"classes": [...]},
    generator="sprint4-pipeline",
)
repo.save(job_id, "static_analysis", artifact)
```

## Tests

- One test file per module, following pytest conventions.
- Test files live in `backend/tests/` — never inline tests in source directories.
- Use plain `assert` statements — never `self.assertEqual` or `unittest.TestCase`.
- Fixtures in `conftest.py` files at the appropriate level.
- Name tests with `test_` prefix and use descriptive class names for grouping.

```python
class TestStaticAnalysis:
    def test_detects_god_class(self):
        result = analyze_classes(mock_classes)
        assert result["god_classes"] > 0
```

## Imports

- **Absolute imports preferred** — never `from ..module import ...`.
- Group imports in this order, separated by blank lines:
  1. Stdlib (`os`, `json`, `dataclasses`, etc.)
  2. Third-party (`structlog`, `boto3`, `fastapi`, etc.)
  3. Local (`app.pipeline.stage`, `app.artifacts.models`, etc.)

```python
from __future__ import annotations

import json
from dataclasses import dataclass

import structlog
from fastapi import Depends

from app.artifacts.models import Artifact
from app.pipeline.context import PipelineContext
```

## Error Handling

- Raise `EMIPException` subclasses (from `app.exceptions.custom`) for all user-facing errors.
- Never expose raw exceptions to the API — exception handlers in `app.main.py` convert exceptions to JSON.
- Available subclasses: `ResourceNotFoundException` (404), `ValidationFailedException` (400), `AnalysisFailedException` (500), `AWSServiceException` (500), `FileUploadException` (400).

```python
from app.exceptions.custom import ResourceNotFoundException, ValidationFailedException

def get_job(job_id: str) -> Job:
    if not job_id:
        raise ValidationFailedException("job_id is required")
    job = find_job(job_id)
    if not job:
        raise ResourceNotFoundException("Job", job_id)
    return job
```

## Secrets

- **Never commit `.env` files or hardcode credentials** in source code.
- All configuration uses **environment variables** loaded via `pydantic-settings` in `app.core.settings`.
- The `.env.example` file documents required variables without real values.
- API keys are configured through the `API_KEY` environment variable.

## Analysis Profiles

- **Never hardcode limits** — token budgets, timeouts, thresholds, and slice limits must come from `AnalysisProfile`.
- Profiles are defined in `app.core.analysis_profile` with modes: `FAST`, `NORMAL`, `DEEP`, `BENCHMARK`.
- Access via `get_active_profile()` which returns the correct profile for the current mode.
- Always use `profile.max_classes`, `profile.bedrock_max_tokens`, etc. rather than constants.

```python
from app.core.analysis_profile import get_active_profile

profile = get_active_profile()
sliced_classes = all_classes[:profile.max_classes]
```

## Artifact Schemas

- **Never modify artifact schemas without incrementing the version field.**
- Maintain backward compatibility — consumers must handle both old and new schema versions.
- Schema version is tracked in `ARTIFACT_SCHEMA_VERSION` (currently `"1.0.0"`).
- Individual artifact versions are tracked in `ArtifactMetadata.artifact_version`.

## API Contracts

- **Never modify request/response models without versioning** — backward compatibility first.
- Add new fields as optional with defaults rather than changing existing required fields.
- Version API through `/api/v1/`, `/api/v2/` prefixes if breaking changes are required.

## Fallback Paths

- **Every AI stage must have a fallback path.**
- The pipeline never hard-fails on AI errors — `BaseAIStage` catches exceptions and calls `fallback()`.
- Degraded artifacts are flagged with `is_degraded: True` in their metadata.
- Downstream stages must handle degraded input gracefully.

## Naming Conventions

| Language | Convention | Example |
|----------|-----------|---------|
| Python | `snake_case` | `analysis_profile`, `get_active_profile()` |
| TypeScript | `camelCase` | `analysisProfile`, `getActiveProfile()` |
| Classes (all) | `PascalCase` | `AnalysisProfile`, `PipelineEngine` |
| Constants | `UPPER_SNAKE_CASE` | `FAST_PROFILE`, `S3_PREFIX` |
| Private members | `_` prefix | `_active_profile`, `_s3_client` |

## Code Review Checklist

Before submitting code, verify:

- [ ] Type hints present on every function signature
- [ ] `from __future__ import annotations` at top of `.py` files
- [ ] No `print()` or `logging` calls — structlog only
- [ ] No direct boto3 client creation — uses `AWSClients` factory
- [ ] Pipeline stages follow `execute()` → `execute_ai()` → `fallback()` pattern
- [ ] Artifact persistence uses `ArtifactRepository` — no direct S3/DynamoDB writes
- [ ] Limits come from `AnalysisProfile` — no hardcoded numbers
- [ ] AI stages have a `fallback()` implementation
- [ ] Error handling uses `EMIPException` subclasses
- [ ] Imports grouped: stdlib → third-party → local
- [ ] Absolute imports used throughout
- [ ] No `.env` files or credentials committed
- [ ] Tests pass: `python -m pytest tests/ -v`
- [ ] No commented-out code

## What NOT to Do

- ❌ Do not create boto3 clients directly — use `app/aws/clients.py`.
- ❌ Do not extend `PipelineStage` for AI stages — use `BaseAIStage`.
- ❌ Do not bypass the `execute()` template method — it handles fallback and artifact creation.
- ❌ Do not write to S3 or DynamoDB directly — go through `ArtifactRepository`.
- ❌ Do not hardcode limits — use `AnalysisProfile`.
- ❌ Do not modify artifact schemas without version bumping.
- ❌ Do not modify API contracts without versioning.
- ❌ Do not expose raw stack traces or exceptions to API responses.
- ❌ Do not use `print()` or `logging` — only structlog.
- ❌ Do not skip type hints.
- ❌ Do not commit `.env` files — commit `.env.example` instead.
- ❌ Do not import from relative paths (`from ..module`).
- ❌ Do not leave TODO comments without an associated issue.
- ❌ Do not commit test files that require real AWS credentials.
