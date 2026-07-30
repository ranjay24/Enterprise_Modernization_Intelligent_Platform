"""S3 operations abstraction."""

import json
from typing import Any

import structlog

from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class S3Repository:
    """S3 operations for job artifacts and metadata."""

    def __init__(self):
        settings = get_settings()
        self._clients = AWSClients(settings=settings)
        self._settings = settings

    @property
    def client(self):
        return self._clients.s3

    @property
    def bucket(self) -> str:
        return self._settings.s3_bucket

    def put_object(self, key: str, body: Any, content_type: str = "application/json"):
        kwargs = {"Bucket": self.bucket, "Key": key}
        if isinstance(body, bytes):
            kwargs["Body"] = body
        else:
            kwargs["Body"] = body if isinstance(body, (str, bytes)) else str(body)
            kwargs["ContentType"] = content_type
        self._clients.s3.put_object(**kwargs)

    def get_object(self, key: str) -> dict:
        return self._clients.s3.get_object(Bucket=self.bucket, Key=key)

    def download_file(self, key: str, filename: str):
        self._clients.s3.download_file(self.bucket, key, filename)

    def upload_raw_file(self, job_id: str, filename: str, content: bytes) -> None:
        self.put_object(key=f"jobs/{job_id}/raw/{filename}", body=content)

    def upload_metadata(self, job_id: str, metadata: dict) -> None:
        self.put_object(
            key=f"jobs/{job_id}/metadata.json",
            body=json.dumps(metadata),
        )

    def get_metadata(self, job_id: str) -> dict | None:
        try:
            obj = self.get_object(key=f"jobs/{job_id}/metadata.json")
            return json.loads(obj["Body"].read().decode())
        except Exception:
            return None

    def get_analysis_results(self, job_id: str) -> dict | None:
        try:
            obj = self.get_object(key=f"jobs/{job_id}/analysis/results.json")
            return json.loads(obj["Body"].read().decode())
        except Exception:
            return None

    def store_analysis(self, job_id: str, analysis_data: dict) -> None:
        self.put_object(
            key=f"jobs/{job_id}/analysis/results.json",
            body=json.dumps(analysis_data, default=str),
        )

    def store_static_analysis(self, job_id: str, data: dict) -> None:
        self.put_object(
            key=f"jobs/{job_id}/analysis/static_analysis.json",
            body=json.dumps(data, default=str),
        )

    def store_deployment(self, job_id: str, deployment_id: str, code_data: dict) -> None:
        self.put_object(
            key=f"jobs/{job_id}/deployments/{deployment_id}/code.json",
            body=json.dumps(code_data, default=str),
        )

    def list_jobs(self) -> list[dict]:
        jobs = []
        try:
            paginator = self._clients.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=self.bucket,
                Prefix="jobs/",
                Delimiter="/",
            ):
                for prefix in page.get("CommonPrefixes", []):
                    job_id = prefix["Prefix"].split("/")[-2]
                    meta = self.get_metadata(job_id)
                    if meta:
                        jobs.append(meta)
        except Exception as exc:
            logger.warning("failed_to_list_jobs_from_s3", error=str(exc))
        return sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)

    def delete_prefix(self, prefix: str):
        """Delete all S3 objects under a given prefix."""
        try:
            paginator = self._clients.s3.get_paginator("list_objects_v2")
            to_delete = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    to_delete.append({"Key": obj["Key"]})
            if to_delete:
                for i in range(0, len(to_delete), 1000):
                    batch = to_delete[i:i + 1000]
                    self._clients.s3.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": batch, "Quiet": True},
                    )
                logger.info("s3_prefix_deleted", prefix=prefix, count=len(to_delete))
        except Exception as exc:
            logger.warning("s3_prefix_delete_failed", prefix=prefix, error=str(exc))
