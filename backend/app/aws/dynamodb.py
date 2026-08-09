"""DynamoDB operations for jobs and analysis data."""

from datetime import datetime, timezone
from typing import Optional

import structlog

from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class JobRepository:
    """DynamoDB operations for job metadata."""

    def __init__(self):
        settings = get_settings()
        self._clients = AWSClients(settings=settings)
        self._settings = settings
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = self._clients.dynamodb.Table(self._settings.dynamodb_jobs_table)
        return self._table

    def create_job(self, job_id: str, filename: str, file_size: int, status: str):
        from app.models.job import JobDomain

        now = datetime.now(timezone.utc).isoformat()
        job = JobDomain(
            job_id=job_id,
            status=status,
            filename=filename,
            file_size=file_size,
            created_at=now,
            updated_at=now,
        )
        self.table.put_item(Item=job.to_dict())
        logger.info("job_created", job_id=job_id)
        return job

    def get_job(self, job_id: str) -> Optional["JobDomain"]:
        from app.models.job import JobDomain

        try:
            response = self.table.get_item(Key={"job_id": job_id})
            item = response.get("Item")
            if item:
                return JobDomain.from_dict(item)
            return None
        except Exception as exc:
            logger.warning("failed_to_get_job", job_id=job_id, error=str(exc))
            return None

    def update_job(
        self,
        job_id: str,
        status: str = None,
        progress: int = None,
        current_phase: str = None,
        error: str = None,
        completed_phases: list[str] = None,
        codegen_stage: str = None,
    ):

        now = datetime.now(timezone.utc).isoformat()
        updates = {"updated_at": now}

        if status is not None:
            updates["status"] = status
        if progress is not None:
            updates["progress"] = progress
        if current_phase is not None:
            updates["current_phase"] = current_phase
        if error is not None:
            updates["error"] = error
        if completed_phases is not None:
            updates["completed_phases"] = completed_phases
        if codegen_stage is not None:
            updates["codegen_stage"] = codegen_stage

        update_expr_parts = []
        expr_names = {}
        expr_vals = {}
        for i, (k, v) in enumerate(updates.items()):
            attr_name = f"#a{i}"
            attr_val = f":v{i}"
            if k == "status":
                update_expr_parts.append(f"{attr_name} = {attr_val}")
                expr_names[attr_name] = "status"
            elif k == "error":
                update_expr_parts.append(f"{attr_name} = {attr_val}")
                expr_names[attr_name] = "error"
            else:
                update_expr_parts.append(f"{k} = {attr_val}")
            expr_vals[attr_val] = v

        update_expr = "SET " + ", ".join(update_expr_parts)

        kwargs = {
            "Key": {"job_id": job_id},
            "UpdateExpression": update_expr,
            "ExpressionAttributeValues": expr_vals,
        }
        if expr_names:
            kwargs["ExpressionAttributeNames"] = expr_names
        self.table.update_item(**kwargs)

    def list_jobs(self) -> list["JobDomain"]:
        from app.models.job import JobDomain

        try:
            response = self.table.scan()
            items = response.get("Items", [])
            jobs = [JobDomain.from_dict(item) for item in items]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)
        except Exception as exc:
            logger.warning("failed_to_list_jobs", error=str(exc))
            return []

    def delete_job(self, job_id: str):
        """Delete a job record from DynamoDB."""
        self.table.delete_item(Key={"job_id": job_id})
        logger.info("job_deleted", job_id=job_id)


class AnalysisRepository:
    """DynamoDB operations for analysis results."""

    def __init__(self):
        settings = get_settings()
        self._clients = AWSClients(settings=settings)
        self._settings = settings
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = self._clients.dynamodb.Table(self._settings.dynamodb_analysis_table)
        return self._table

    def put_analysis(self, job_id: str, analysis_type: str, data: dict) -> None:
        self.table.put_item(
            Item={
                "job_id": job_id,
                "analysis_type": analysis_type,
                "data": data,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("analysis_stored", job_id=job_id, type=analysis_type)

    def get_analysis(self, job_id: str, analysis_type: str = "full") -> dict | None:
        try:
            response = self.table.get_item(
                Key={"job_id": job_id, "analysis_type": analysis_type}
            )
            item = response.get("Item")
            return item.get("data") if item else None
        except Exception as exc:
            logger.warning("failed_to_get_analysis", job_id=job_id, error=str(exc))
            return None
